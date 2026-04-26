"""
Merge scored jobs into data/jobs.json and new CV templates into data/cvs.json.
Reads scored_jobs.json (from claude_scorer.py) and appends new jobs with status field.
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / 'data'
SCORED_FILE = SCRIPT_DIR / 'scored_jobs.json'
JOBS_FILE = DATA_DIR / 'jobs.json'
CVS_FILE = DATA_DIR / 'cvs.json'


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

    # Load scored jobs
    if not SCORED_FILE.exists():
        logger.info("No scored_jobs.json found. Nothing to merge.")
        return

    with open(SCORED_FILE, 'r', encoding='utf-8') as f:
        scored_data = json.load(f)

    new_jobs = scored_data.get('newJobs', [])
    new_cv_templates = scored_data.get('newCvTemplates', {})

    if not new_jobs:
        logger.info("No new jobs to merge.")
        # Still clean up
        SCORED_FILE.unlink(missing_ok=True)
        return

    logger.info(f"New jobs to merge: {len(new_jobs)}")

    # Assign IDs and set default status
    added = 0
    for job in new_jobs:
        max_id += 1
        job['id'] = max_id
        job['status'] = 'not-applied'
        existing_jobs.append(job)
        added += 1
        logger.info(f"  Added #{max_id}: {job['title']} at {job['company']} ({job.get('matchPercent', '?')}%)")

    # Save updated jobs
    jobs_data['jobs'] = existing_jobs
    with open(JOBS_FILE, 'w', encoding='utf-8') as f:
        json.dump(jobs_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Merged {added} new jobs. Total: {len(existing_jobs)}")

    # Merge new CV templates into cvs.json
    if new_cv_templates:
        if CVS_FILE.exists():
            with open(CVS_FILE, 'r', encoding='utf-8') as f:
                cvs_data = json.load(f)
        else:
            cvs_data = {'cvTemplates': {}}

        for cv_id, cv_template in new_cv_templates.items():
            cvs_data['cvTemplates'][cv_id] = cv_template
            logger.info(f"  Added CV template: {cv_id}")

        with open(CVS_FILE, 'w', encoding='utf-8') as f:
            json.dump(cvs_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Merged {len(new_cv_templates)} new CV templates.")

    # Clean up scored file
    SCORED_FILE.unlink(missing_ok=True)
    logger.info("Removed scored_jobs.json")


if __name__ == '__main__':
    main()
