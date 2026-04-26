"""
Claude API Integration for Job Scoring and CV/Cover Letter Generation.
Reads scraped_jobs.json, scores each job against candidate profile,
filters by 85% threshold, generates tailored CV + cover letter for passing jobs.
Outputs scored_jobs.json.
"""

import json
import re
import time
import logging
from pathlib import Path

from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / 'data'
SCRAPED_FILE = SCRIPT_DIR / 'scraped_jobs.json'
SCORED_FILE = SCRIPT_DIR / 'scored_jobs.json'
PROFILE_FILE = SCRIPT_DIR / 'base_profile.json'
CVS_FILE = DATA_DIR / 'cvs.json'

MATCH_THRESHOLD = 85
MAX_JOBS_TO_SCORE = 50
SCORING_MODEL = 'claude-haiku-4-5-20251001'
GENERATION_MODEL = 'claude-sonnet-4-6-20250514'

client = Anthropic()


def parse_json_response(text):
    """Extract JSON from Claude's response, handling markdown code blocks."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown code fences
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try to find JSON object in text
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON from response: {text[:200]}")


def score_job(job, profile_text):
    """Score a single job against the candidate profile using Claude Haiku."""
    prompt = f"""Analyze this job posting against the candidate profile and score how well the candidate matches.

JOB POSTING:
- Title: {job['title']}
- Company: {job['company']}
- Location: {job['location']}, {job['country']}
- Requirements: {'; '.join(job.get('requirements', []))}
- Tags: {', '.join(job.get('tags', []))}

CANDIDATE PROFILE:
{profile_text}

Consider: years of experience match, industry alignment, skills overlap, location preference, certifications relevance, project scale alignment, seniority fit.

Return ONLY a JSON object (no markdown, no explanation):
{{"matchPercent": <integer 0-100>, "matchReasons": ["reason1", "reason2", "reason3", "reason4"], "type": "<PD or SPM or OH>"}}"""

    response = client.messages.create(
        model=SCORING_MODEL,
        max_tokens=400,
        messages=[{'role': 'user', 'content': prompt}]
    )
    text = response.content[0].text.strip()
    return parse_json_response(text)


def generate_cv_and_cover_letter(job, profile_text, example_cv_html):
    """Generate a tailored CV and cover letter for a qualifying job using Claude Sonnet."""
    prompt = f"""Generate a tailored CV and cover letter for this candidate targeting this specific job.

JOB:
- Title: {job['title']}
- Company: {job['company']}
- Location: {job['location']}, {job['country']}
- Requirements: {'; '.join(job.get('requirements', []))}
- Tags: {', '.join(job.get('tags', []))}

CANDIDATE PROFILE:
{profile_text}

EXAMPLE CV HTML FORMAT (follow this exact structure and styling):
{example_cv_html[:4000]}

INSTRUCTIONS:
1. Generate a CV in the same HTML format as the example, but tailor the professional summary, core competencies, and project highlights to emphasize experience most relevant to THIS specific job.
2. Generate a cover letter body (2-3 paragraphs only, no salutation/closing/signature). Focus on why this candidate is ideal for this role.
3. Separate cover letter paragraphs with double newlines.

Return ONLY a JSON object (no markdown):
{{"cvDisplayName": "short_descriptive_name", "cvHtmlContent": "<full CV HTML string>", "coverLetterBody": "paragraph1\\n\\nparagraph2\\n\\nparagraph3"}}"""

    response = client.messages.create(
        model=GENERATION_MODEL,
        max_tokens=8000,
        messages=[{'role': 'user', 'content': prompt}]
    )
    text = response.content[0].text.strip()
    return parse_json_response(text)


def main():
    # Load scraped jobs
    if not SCRAPED_FILE.exists():
        logger.info("No scraped_jobs.json found. Nothing to score.")
        # Write empty output so update_data.py can still run
        with open(SCORED_FILE, 'w', encoding='utf-8') as f:
            json.dump({'newJobs': [], 'newCvTemplates': {}}, f, indent=2)
        return

    with open(SCRAPED_FILE, 'r', encoding='utf-8') as f:
        scraped_data = json.load(f)

    new_jobs = scraped_data.get('newJobs', [])
    if not new_jobs:
        logger.info("No new jobs to score.")
        with open(SCORED_FILE, 'w', encoding='utf-8') as f:
            json.dump({'newJobs': [], 'newCvTemplates': {}}, f, indent=2)
        return

    # Load profile
    with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    profile_text = json.dumps(profile, indent=2)

    # Load example CV for format reference
    example_cv_html = ''
    if CVS_FILE.exists():
        with open(CVS_FILE, 'r', encoding='utf-8') as f:
            cvs_data = json.load(f)
        templates = cvs_data.get('cvTemplates', {})
        if templates:
            first_cv = next(iter(templates.values()))
            example_cv_html = first_cv.get('htmlContent', '')

    # Cap the number of jobs to score
    jobs_to_score = new_jobs[:MAX_JOBS_TO_SCORE]
    if len(new_jobs) > MAX_JOBS_TO_SCORE:
        logger.warning(f"Capping scoring at {MAX_JOBS_TO_SCORE} jobs (had {len(new_jobs)})")

    logger.info(f"Scoring {len(jobs_to_score)} jobs against candidate profile...")

    passing_jobs = []
    new_cv_templates = {}

    for i, job in enumerate(jobs_to_score):
        logger.info(f"[{i+1}/{len(jobs_to_score)}] Scoring: {job['title']} at {job['company']}")

        # Score the job
        try:
            result = score_job(job, profile_text)
            job['matchPercent'] = result['matchPercent']
            job['matchReasons'] = result.get('matchReasons', [])
            job['type'] = result.get('type', job.get('type', 'SPM'))

            logger.info(f"  Score: {result['matchPercent']}%")

            if result['matchPercent'] >= MATCH_THRESHOLD:
                logger.info(f"  PASS (>= {MATCH_THRESHOLD}%) - Generating CV and cover letter...")
                time.sleep(1)

                try:
                    cv_cl = generate_cv_and_cover_letter(job, profile_text, example_cv_html)
                    cv_id = f"cv_auto_{job['title'][:30].lower().replace(' ', '_').replace('/', '_')}"
                    # Ensure unique cv_id
                    if cv_id in new_cv_templates:
                        cv_id += f"_{i}"

                    job['cvId'] = cv_id
                    job['coverLetter'] = {'body': cv_cl.get('coverLetterBody', '')}
                    new_cv_templates[cv_id] = {
                        'id': cv_id,
                        'displayName': cv_cl.get('cvDisplayName', job['title']),
                        'htmlContent': cv_cl.get('cvHtmlContent', '')
                    }
                    passing_jobs.append(job)
                    logger.info(f"  CV/CL generated: {cv_id}")
                except Exception as e:
                    logger.error(f"  Error generating CV/CL: {e}")
                    # Still include the job even if CV generation fails
                    job['cvId'] = None
                    job['coverLetter'] = None
                    passing_jobs.append(job)
            else:
                logger.info(f"  SKIP (< {MATCH_THRESHOLD}%)")

        except Exception as e:
            logger.error(f"  Error scoring job: {e}")

        # Rate limit between API calls
        time.sleep(1)

    # Write output
    output = {
        'newJobs': passing_jobs,
        'newCvTemplates': new_cv_templates
    }
    with open(SCORED_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Clean up scraped file
    SCRAPED_FILE.unlink(missing_ok=True)

    logger.info(f"Done. Scored {len(jobs_to_score)} jobs, {len(passing_jobs)} passed {MATCH_THRESHOLD}% threshold.")
    logger.info(f"Generated {len(new_cv_templates)} new CV templates.")


if __name__ == '__main__':
    main()
