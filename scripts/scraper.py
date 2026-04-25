"""
Job Board Scraper for Construction/Infrastructure Roles
Scrapes: GulfTalent, LinkedIn Jobs, Bayt.com, NaukriGulf
Outputs: scraped_jobs.json (new jobs not already in data/jobs.json)
"""

import json
import hashlib
import os
import re
import time
import logging
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / 'data'
OUTPUT_FILE = SCRIPT_DIR / 'scraped_jobs.json'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


def load_profile():
    with open(SCRIPT_DIR / 'base_profile.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def load_existing_jobs():
    jobs_file = DATA_DIR / 'jobs.json'
    if jobs_file.exists():
        with open(jobs_file, 'r', encoding='utf-8') as f:
            return json.load(f).get('jobs', [])
    return []


def job_hash(title, company, location):
    """Create a unique hash for deduplication."""
    key = f"{title.lower().strip()}|{company.lower().strip()}|{location.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()


def get_existing_hashes(existing_jobs):
    return set(job_hash(j['title'], j['company'], j['location']) for j in existing_jobs)


def matches_profile(title, description, profile):
    """Pre-filter: check if job matches candidate profile using keywords."""
    text = (title + ' ' + description).lower()

    # Check exclude keywords
    for kw in profile.get('excludeKeywords', []):
        if kw.lower() in text:
            return False

    # Check if title matches target roles
    title_lower = title.lower()
    role_match = any(role.lower() in title_lower for role in profile.get('targetRoles', []))
    if not role_match:
        return False

    # Check industry relevance
    industry_match = any(ind.lower() in text for ind in profile.get('industries', []))
    return industry_match


def safe_request(url, max_retries=3, delay=2):
    """Make HTTP request with retries and rate limiting."""
    for attempt in range(max_retries):
        try:
            time.sleep(delay)
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 429:
                logger.warning(f"Rate limited on {url}, waiting 30s...")
                time.sleep(30)
            else:
                logger.warning(f"HTTP {resp.status_code} for {url}")
        except requests.RequestException as e:
            logger.warning(f"Request error (attempt {attempt+1}): {e}")
            time.sleep(delay * (attempt + 1))
    return None


# ==================== GULFTALENT SCRAPER ====================
def scrape_gulftalent(profile):
    """Scrape GulfTalent for matching jobs."""
    jobs = []
    countries = {
        'UAE': 'uae',
        'Oman': 'oman',
        'Qatar': 'qatar',
        'Saudi': 'saudi-arabia',
    }
    search_terms = [
        'project-director',
        'senior-project-manager',
        'construction-manager',
        'project-manager-infrastructure',
        'project-manager-water',
    ]

    for country_name, country_slug in countries.items():
        for term in search_terms:
            url = f"https://www.gulftalent.com/{country_slug}/jobs/title/{term}"
            logger.info(f"GulfTalent: Scraping {url}")
            resp = safe_request(url)
            if not resp:
                continue

            soup = BeautifulSoup(resp.text, 'lxml')
            listings = soup.select('.job-listing, .listing-item, article.job, div[class*="job"]')

            if not listings:
                # Try alternative selectors
                listings = soup.find_all('a', href=re.compile(r'/jobs/.*-\d+'))

            for item in listings[:20]:  # Limit per page
                try:
                    # Extract title
                    title_el = item.select_one('h2, h3, .job-title, .title') or item
                    title = title_el.get_text(strip=True) if title_el else ''
                    if not title or len(title) < 5:
                        continue

                    # Extract company
                    company_el = item.select_one('.company, .employer, span[class*="company"]')
                    company = company_el.get_text(strip=True) if company_el else 'Confidential'

                    # Extract location
                    location_el = item.select_one('.location, span[class*="location"]')
                    location = location_el.get_text(strip=True) if location_el else country_name

                    # Extract link
                    link = item.get('href') or ''
                    if not link:
                        link_el = item.select_one('a[href*="/jobs/"]')
                        link = link_el.get('href', '') if link_el else ''
                    if link and not link.startswith('http'):
                        link = 'https://www.gulftalent.com' + link

                    # Extract date
                    date_el = item.select_one('.date, time, span[class*="date"]')
                    date_posted = date_el.get_text(strip=True) if date_el else datetime.now().strftime('%b %Y')

                    description = item.get_text(' ', strip=True)

                    if matches_profile(title, description, profile):
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': location,
                            'country': country_name,
                            'datePosted': date_posted,
                            'applyUrl': link,
                            'source': 'GulfTalent',
                            'requirements': [description[:200] + '...' if len(description) > 200 else description],
                            'tags': extract_tags(title + ' ' + description),
                        })
                except Exception as e:
                    logger.debug(f"Error parsing GulfTalent listing: {e}")

    logger.info(f"GulfTalent: Found {len(jobs)} matching jobs")
    return jobs


# ==================== BAYT SCRAPER ====================
def scrape_bayt(profile):
    """Scrape Bayt.com for matching jobs."""
    jobs = []
    search_queries = [
        'project+director+construction',
        'senior+project+manager+infrastructure',
        'construction+manager+water',
    ]

    for query in search_queries:
        url = f"https://www.bayt.com/en/international/jobs/{query}-jobs/"
        logger.info(f"Bayt: Scraping {url}")
        resp = safe_request(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, 'lxml')
        listings = soup.select('li[data-job-id], .job-listing, div[class*="job-item"]')

        for item in listings[:15]:
            try:
                title_el = item.select_one('h2 a, .jb-title a, a[class*="title"]')
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                company_el = item.select_one('.jb-company, span[class*="company"]')
                company = company_el.get_text(strip=True) if company_el else 'Confidential'

                location_el = item.select_one('.jb-loc, span[class*="location"]')
                location = location_el.get_text(strip=True) if location_el else ''

                link = title_el.get('href', '')
                if link and not link.startswith('http'):
                    link = 'https://www.bayt.com' + link

                country = detect_country(location)
                description = item.get_text(' ', strip=True)

                if matches_profile(title, description, profile):
                    jobs.append({
                        'title': title,
                        'company': company,
                        'location': location,
                        'country': country,
                        'datePosted': datetime.now().strftime('%b %Y'),
                        'applyUrl': link,
                        'source': 'Bayt',
                        'requirements': [description[:200] + '...' if len(description) > 200 else description],
                        'tags': extract_tags(title + ' ' + description),
                    })
            except Exception as e:
                logger.debug(f"Error parsing Bayt listing: {e}")

    logger.info(f"Bayt: Found {len(jobs)} matching jobs")
    return jobs


# ==================== NAUKRIGULF SCRAPER ====================
def scrape_naukrigulf(profile):
    """Scrape NaukriGulf for matching jobs."""
    jobs = []
    search_queries = [
        'project-director-construction',
        'senior-project-manager-infrastructure',
        'construction-manager-water',
    ]

    for query in search_queries:
        url = f"https://www.naukrigulf.com/{query}-jobs"
        logger.info(f"NaukriGulf: Scraping {url}")
        resp = safe_request(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, 'lxml')
        listings = soup.select('.srp-jobtuple, article, div[class*="jobTuple"]')

        for item in listings[:15]:
            try:
                title_el = item.select_one('a.designation, h2 a, a[class*="title"]')
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                company_el = item.select_one('.comp-name, a[class*="company"]')
                company = company_el.get_text(strip=True) if company_el else 'Confidential'

                location_el = item.select_one('.loc, span[class*="location"]')
                location = location_el.get_text(strip=True) if location_el else ''

                link = title_el.get('href', '')
                if link and not link.startswith('http'):
                    link = 'https://www.naukrigulf.com' + link

                country = detect_country(location)
                description = item.get_text(' ', strip=True)

                if matches_profile(title, description, profile):
                    jobs.append({
                        'title': title,
                        'company': company,
                        'location': location,
                        'country': country,
                        'datePosted': datetime.now().strftime('%b %Y'),
                        'applyUrl': link,
                        'source': 'NaukriGulf',
                        'requirements': [description[:200] + '...' if len(description) > 200 else description],
                        'tags': extract_tags(title + ' ' + description),
                    })
            except Exception as e:
                logger.debug(f"Error parsing NaukriGulf listing: {e}")

    logger.info(f"NaukriGulf: Found {len(jobs)} matching jobs")
    return jobs


# ==================== LINKEDIN SCRAPER ====================
def scrape_linkedin(profile):
    """Scrape LinkedIn Jobs (public guest API)."""
    jobs = []
    search_queries = [
        'project director construction',
        'senior project manager infrastructure water',
    ]
    locations = [
        ('UAE', 'ae'),
        ('Saudi', 'sa'),
        ('Oman', 'om'),
        ('Qatar', 'qa'),
        ('India', 'in'),
    ]

    for query in search_queries:
        for country_name, geo_id in locations:
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={query.replace(' ', '%20')}&location={country_name}&start=0"
            logger.info(f"LinkedIn: Scraping {country_name} - {query}")
            resp = safe_request(url, delay=3)
            if not resp:
                continue

            soup = BeautifulSoup(resp.text, 'lxml')
            listings = soup.select('li, div.base-card')

            for item in listings[:10]:
                try:
                    title_el = item.select_one('h3, .base-search-card__title')
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)

                    company_el = item.select_one('h4, .base-search-card__subtitle')
                    company = company_el.get_text(strip=True) if company_el else 'Confidential'

                    location_el = item.select_one('.job-search-card__location')
                    location = location_el.get_text(strip=True) if location_el else country_name

                    link_el = item.select_one('a[href*="linkedin.com/jobs"]')
                    link = link_el.get('href', '') if link_el else ''

                    description = item.get_text(' ', strip=True)

                    if matches_profile(title, description, profile):
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': location,
                            'country': country_name,
                            'datePosted': datetime.now().strftime('%b %Y'),
                            'applyUrl': link.split('?')[0] if link else '',
                            'source': 'LinkedIn',
                            'requirements': [description[:200] + '...' if len(description) > 200 else description],
                            'tags': extract_tags(title + ' ' + description),
                        })
                except Exception as e:
                    logger.debug(f"Error parsing LinkedIn listing: {e}")

    logger.info(f"LinkedIn: Found {len(jobs)} matching jobs")
    return jobs


# ==================== UTILITIES ====================
def detect_country(location_str):
    """Detect country from location string."""
    loc = location_str.lower()
    if any(w in loc for w in ['dubai', 'abu dhabi', 'sharjah', 'uae', 'fujairah', 'ajman']):
        return 'UAE'
    if any(w in loc for w in ['oman', 'muscat', 'salalah']):
        return 'Oman'
    if any(w in loc for w in ['qatar', 'doha']):
        return 'Qatar'
    if any(w in loc for w in ['saudi', 'riyadh', 'jeddah', 'dammam', 'mecca', 'medina', 'ksa']):
        return 'Saudi'
    if any(w in loc for w in ['india', 'delhi', 'mumbai', 'bangalore', 'chennai', 'kerala', 'hyderabad']):
        return 'India'
    return 'Other'


def extract_tags(text):
    """Extract relevant tags from text."""
    tag_keywords = {
        'Water': ['water supply', 'water treatment', 'water infrastructure'],
        'Wastewater': ['wastewater', 'sewage', 'sewerage', 'STP'],
        'Pipelines': ['pipeline', 'pipelines', 'piping'],
        'Infrastructure': ['infrastructure'],
        'Construction': ['construction'],
        'EPC': ['epc', 'epcm'],
        'Civil': ['civil engineering', 'civil works'],
        'Utilities': ['utilities', 'utility'],
        'Energy': ['energy', 'power plant'],
        'Transmission': ['transmission', 'substation'],
        'Treatment Plants': ['treatment plant', 'WTP', 'STP', 'MBR'],
        'QA/QC': ['qa/qc', 'quality assurance', 'quality control'],
        'HSE': ['hse', 'health safety', 'safety'],
        'PMC': ['pmc', 'project management consultancy'],
        'Design & Build': ['design and build', 'design & build'],
    }
    text_lower = text.lower()
    tags = []
    for tag, keywords in tag_keywords.items():
        if any(kw in text_lower for kw in keywords):
            tags.append(tag)
    return tags[:5]  # Max 5 tags


def deduplicate(new_jobs, existing_hashes):
    """Remove jobs that already exist."""
    unique = []
    seen = set()
    for job in new_jobs:
        h = job_hash(job['title'], job['company'], job['location'])
        if h not in existing_hashes and h not in seen:
            unique.append(job)
            seen.add(h)
    return unique


# ==================== MAIN ====================
def main():
    logger.info("=" * 60)
    logger.info("Starting job scraper...")
    logger.info("=" * 60)

    profile = load_profile()
    existing_jobs = load_existing_jobs()
    existing_hashes = get_existing_hashes(existing_jobs)
    logger.info(f"Existing jobs: {len(existing_jobs)} (hashes: {len(existing_hashes)})")

    all_new_jobs = []

    # Scrape each board
    scrapers = [
        ('GulfTalent', scrape_gulftalent),
        ('Bayt', scrape_bayt),
        ('NaukriGulf', scrape_naukrigulf),
        ('LinkedIn', scrape_linkedin),
    ]

    for name, scraper_fn in scrapers:
        try:
            jobs = scraper_fn(profile)
            all_new_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Error scraping {name}: {e}")

    # Deduplicate
    unique_jobs = deduplicate(all_new_jobs, existing_hashes)
    logger.info(f"Total scraped: {len(all_new_jobs)}, After dedup: {len(unique_jobs)}")

    # Format for output (unscored - to be scored by Claude API later)
    output_jobs = []
    for job in unique_jobs:
        output_jobs.append({
            'title': job['title'],
            'company': job['company'],
            'location': job['location'],
            'country': job['country'],
            'type': guess_type(job['title']),
            'matchPercent': None,  # To be filled by Claude API
            'datePosted': job['datePosted'],
            'applyUrl': job['applyUrl'],
            'tags': job['tags'],
            'requirements': job['requirements'],
            'matchReasons': [],
            'cvId': None,  # To be assigned by Claude API
            'coverLetter': None,  # To be generated by Claude API
            'source': job['source'],
            'scrapedAt': datetime.now().isoformat(),
        })

    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({'newJobs': output_jobs}, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(output_jobs)} new jobs to {OUTPUT_FILE}")
    return output_jobs


def guess_type(title):
    """Guess role type from title."""
    title_lower = title.lower()
    if 'director' in title_lower:
        return 'PD'
    if 'senior' in title_lower and 'manager' in title_lower:
        return 'SPM'
    if 'construction manager' in title_lower or 'operations' in title_lower:
        return 'OH'
    if 'manager' in title_lower:
        return 'SPM'
    return 'SPM'  # Default


if __name__ == '__main__':
    main()
