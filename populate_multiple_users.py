#!/usr/bin/env python
"""Script to populate multiple user collections in parallel."""

import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

userids = [
    "69318",
    "147986",
    "148406",
    "67384",
    "3413",
    "143225",
    "148064",
    "147701",
    "148093",
    "148706",
    "141465",
    "148254",
    "148489",
    "147854",
    "101247",
    "116258",
    "56789",
    "54949",
    "128522",
    "119969",
    "14929",
    "148085",
    "101426",
    "148146",
    "4807",
    "16323",
    "148659",
    "129939",
    "4587",
]

unique_userids = list(dict.fromkeys(userids))


def run_command(userid):
    """Run populate command for a userid."""
    import time

    time.sleep(0.5)
    cmd = [
        sys.executable,
        "manage.py",
        "populate_user_collection",
        userid,
        "--target-username",
        f"fka_user_{userid}",
        "--wait-timeout",
        "300",
    ]
    logging.info("Starting user %s...", userid)
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            cwd=".",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            check=False,
        )
        if result.returncode == 0:
            logging.info("[OK] User %s completed successfully", userid)
            return True
        logging.error("[FAIL] User %s failed: %s", userid, result.stderr[:200])
        return False  # noqa: TRY300
    except subprocess.TimeoutExpired:
        logging.exception("[FAIL] User %s timed out", userid)
        return False
    except Exception:
        logging.exception("[FAIL] User %s error", userid)
        return False


if __name__ == "__main__":
    logging.info("Processing %s unique userids...", len(unique_userids))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(run_command, userid): userid for userid in unique_userids}

        completed = 0
        failed = 0

        for future in as_completed(futures):
            userid = futures[future]
            try:
                success = future.result()
                if success:
                    completed += 1
                else:
                    failed += 1
            except Exception:
                logging.exception("[FAIL] User %s exception", userid)
                failed += 1

            logging.info(
                "Progress: %s/%s (OK: %s, FAIL: %s)",
                completed + failed,
                len(unique_userids),
                completed,
                failed,
            )

    logging.info("\nCompleted: %s successful, %s failed", completed, failed)
