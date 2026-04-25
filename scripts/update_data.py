"""
Merge scraped jobs into data/jobs.json
Reads scraped_jobs.json (from scraper.py) and appends new jobs.
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / 'data'
SCRAPED_FILE = SCRIPT_DIR / 'scraped_jobs.json'
JOBS_FILE = DATA_DIR / 'jobs.json'


def main():
    # Load existing jobs
    if JOBS_FILE.exists():
        with open(JOBS_FILE, 'r', encoding='utf-8') as f:
            jobs_data = json.load(f)
    else:
        jobs_data = {'jobs': []}

    existing_jobs = jobs_data['jobs']
    max_id = max((j['id'] for j in existing_jobs), default=0)
    logger.info(f"Existing jobs: {len(existing_jobs)}, max ID: {max_id}")

    # Load scraped jobs
    if not SCRAPED_FILE.exists():
        logger.info("No scraped_jobs.json found. Nothing to merge.")
        return

    with open(SCRAPED_FILE, 'r', encoding='utf-8') as f:
        scraped_data = json.load(f)

    new_jobs = scraped_data.get('newJobs', [])
    if not new_jobs:
        logger.info("No new jobs to merge.")
        return

    logger.info(f"New jobs to merge: {len(new_jobs)}")

    # Assign IDs and append
    added = 0
    for job in new_jobs:
        max_id += 1
        job['id'] = max_id
        existing_jobs.append(job)
        added += 1
        logger.info(f"  Added #{max_id}: {job['title']} at {job['company']}")

    # Save updated jobs
    jobs_data['jobs'] = existing_jobs
    with open(JOBS_FILE, 'w', encoding='utf-8') as f:
        json.dump(jobs_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Merged {added} new jobs. Total: {len(existing_jobs)}")

    # Clean up scraped file
    SCRAPED_FILE.unlink()
    logger.info("Removed scraped_jobs.json")


if __name__ == '__main__':
    main()
