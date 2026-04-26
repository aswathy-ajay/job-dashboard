"""
Check unapplied job cap before scraping.
If unapplied jobs >= 100, set paused flag and skip scraping.
Writes data/dashboard_flags.json with current status.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / 'data'
JOBS_FILE = DATA_DIR / 'jobs.json'
FLAGS_FILE = DATA_DIR / 'dashboard_flags.json'

UNAPPLIED_CAP = 100


def main():
    # Load jobs
    if not JOBS_FILE.exists():
        logger.info("No jobs.json found. Not paused.")
        write_flags(paused=False, unapplied_count=0)
        return

    with open(JOBS_FILE, 'r', encoding='utf-8') as f:
        jobs_data = json.load(f)

    jobs = jobs_data.get('jobs', [])

    # Count unapplied: jobs where status is missing or "not-applied"
    unapplied = 0
    for job in jobs:
        status = job.get('status', 'not-applied')
        if status == 'not-applied':
            unapplied += 1

    logger.info(f"Total jobs: {len(jobs)}, Unapplied: {unapplied}, Cap: {UNAPPLIED_CAP}")

    paused = unapplied >= UNAPPLIED_CAP
    write_flags(paused=paused, unapplied_count=unapplied)

    if paused:
        logger.info(f"PAUSED: {unapplied} unapplied jobs >= {UNAPPLIED_CAP} cap. Scraping will be skipped.")
        print("PAUSED")
    else:
        logger.info(f"OK: {unapplied} unapplied jobs < {UNAPPLIED_CAP} cap. Proceeding with scraping.")


def write_flags(paused, unapplied_count):
    flags = {
        'paused': paused,
        'unappliedCount': unapplied_count,
        'lastCheckedAt': datetime.now().isoformat()
    }
    with open(FLAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(flags, f, indent=2)
    logger.info(f"Wrote dashboard_flags.json: paused={paused}, unapplied={unapplied_count}")


if __name__ == '__main__':
    main()
