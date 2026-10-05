import argparse
import json
import sys
from datetime import datetime

from job_scraper.core.db import JobRepository
from job_scraper.core.rebuild import rebuild_site, NOT_REBUILDABLE
from job_scraper.core.screenshot_backfill import backfill_screenshots
from job_scraper.core.screenshots import browser_available
from job_scraper.core.stale_sync import sync_stale_markers
from job_scraper.pipeline import run
from job_scraper.sites.registry import SITE_REGISTRY


def main() -> None:
    parser = argparse.ArgumentParser(description="Job scraper CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    scrape_parser = subparsers.add_parser("scrape", help="Scrape jobs from sites")
    scrape_parser.add_argument(
        "--site",
        action="append",
        dest="sites",
        help="Site ID to scrape (repeatable, or use 'all')",
    )
    scrape_parser.add_argument(
        "--db",
        default="scraper.db",
        help="Path to database (default: scraper.db)",
    )
    scrape_parser.add_argument(
        "--jobs-dir",
        default="jobs/",
        help="Path to jobs directory (default: jobs/)",
    )
    scrape_parser.add_argument(
        "--raw-dir",
        default="raw/",
        help="Path to raw fetched-page directory, one subfolder per site "
        "(default: raw/); pass --no-raw to skip raw storage entirely",
    )
    scrape_parser.add_argument(
        "--no-raw",
        action="store_true",
        help="Skip saving raw fetched pages (raw storage is on by default)",
    )
    scrape_parser.add_argument(
        "--ignore-robots",
        action="store_true",
        help="Bypass the robots.txt check (only use for sites you have "
        "explicit permission to scrape)",
    )
    scrape_parser.add_argument(
        "--screenshots-dir",
        default="screenshots/",
        help="Path to screenshots directory (default: screenshots/); pass "
        "--no-screenshots to skip screenshot capture entirely",
    )
    scrape_parser.add_argument(
        "--no-screenshots",
        action="store_true",
        help="Skip taking screenshots (screenshot capture is on by default)",
    )

    rebuild_parser = subparsers.add_parser("rebuild", help="Rebuild jobs from raw pages")
    rebuild_parser.add_argument(
        "--site",
        action="append",
        dest="sites",
        help="Site ID to rebuild (repeatable, or use 'all')",
    )
    rebuild_parser.add_argument(
        "--db",
        default="scraper.db",
        help="Path to database (default: scraper.db)",
    )
    rebuild_parser.add_argument(
        "--jobs-dir",
        default="jobs/",
        help="Path to jobs directory (default: jobs/)",
    )
    rebuild_parser.add_argument(
        "--raw-dir",
        default="raw/",
        help="Path to raw fetched-page directory, one subfolder per site "
        "(default: raw/)",
    )

    screenshots_parser = subparsers.add_parser("screenshots", help="Backfill screenshots for existing jobs")
    screenshots_parser.add_argument(
        "--site",
        action="append",
        dest="sites",
        help="Site ID to capture screenshots for (repeatable, or use 'all')",
    )
    screenshots_parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Skip jobs that already have a screenshot",
    )
    screenshots_parser.add_argument(
        "--jobs-dir",
        default="jobs/",
        help="Path to jobs directory (default: jobs/)",
    )
    screenshots_parser.add_argument(
        "--screenshots-dir",
        default="screenshots/",
        help="Path to screenshots directory (default: screenshots/)",
    )
    screenshots_parser.add_argument(
        "--db",
        default="scraper.db",
        help="Path to SQLite database used to find stale postings (default: scraper.db)",
    )
    screenshots_parser.add_argument(
        "--include-stale",
        action="store_true",
        help="also try postings the scraper marked stale",
    )

    stale_sync_parser = subparsers.add_parser(
        "stale-sync", help="Backfill/repair Stale since bullets in markdown from the database"
    )
    stale_sync_parser.add_argument(
        "--db",
        default="scraper.db",
        help="Path to database (default: scraper.db)",
    )
    stale_sync_parser.add_argument(
        "--jobs-dir",
        default="jobs/",
        help="Path to jobs directory (default: jobs/)",
    )

    subparsers.add_parser("list-sites", help="List all available sites")

    args = parser.parse_args()

    if args.command == "scrape":
        handle_scrape(args)
    elif args.command == "rebuild":
        handle_rebuild(args)
    elif args.command == "screenshots":
        handle_screenshots(args)
    elif args.command == "stale-sync":
        handle_stale_sync(args)
    elif args.command == "list-sites":
        handle_list_sites()
    else:
        parser.print_help()
        sys.exit(1)


def handle_scrape(args: argparse.Namespace) -> None:
    if not args.sites:
        print("Error: --site is required (use --site all for all sites)", file=sys.stderr)
        sys.exit(1)

    site_ids: list[str] = []
    if args.sites == ["all"]:
        site_ids = sorted(SITE_REGISTRY.keys())
    else:
        site_ids = args.sites

    repo = JobRepository(args.db)
    raw_dir = None if args.no_raw else args.raw_dir
    screenshots_dir = None if args.no_screenshots else args.screenshots_dir
    results = run(
        site_ids, repo, args.jobs_dir, ignore_robots=args.ignore_robots, raw_dir=raw_dir, screenshots_dir=screenshots_dir
    )

    for site_id, counters in results.items():
        print(f"{site_id}: {json.dumps(counters)}")


def handle_rebuild(args: argparse.Namespace) -> None:
    if not args.sites:
        print("Error: --site is required (use --site all for all sites)", file=sys.stderr)
        sys.exit(1)

    site_ids: list[str] = []
    if args.sites == ["all"]:
        site_ids = sorted(SITE_REGISTRY.keys())
    else:
        site_ids = args.sites

    repo = JobRepository(args.db)

    for site_id in site_ids:
        if site_id in NOT_REBUILDABLE:
            if args.sites == ["all"]:
                print(f"Skipping {site_id}: {NOT_REBUILDABLE[site_id]}", file=sys.stderr)
            else:
                print(f"Error: {site_id} cannot be rebuilt from raw: {NOT_REBUILDABLE[site_id]}", file=sys.stderr)
                sys.exit(1)
            continue

        counters = rebuild_site(site_id, repo, args.jobs_dir, args.raw_dir)
        print(f"{site_id}: {json.dumps(counters)}")


def handle_screenshots(args: argparse.Namespace) -> None:
    if not browser_available():
        print('No Playwright Chromium found; see README "Screenshots (browser requirements)"', file=sys.stderr)
        sys.exit(1)

    if not args.sites:
        print("Error: --site is required (use --site all for all sites)", file=sys.stderr)
        sys.exit(1)

    site_ids: list[str] = []
    if args.sites == ["all"]:
        site_ids = sorted(SITE_REGISTRY.keys())
    else:
        site_ids = args.sites

    for site_id in site_ids:
        try:
            counters = backfill_screenshots(
                site_id,
                args.jobs_dir,
                args.screenshots_dir,
                missing_only=args.missing_only,
                db_path=args.db,
                include_stale=args.include_stale,
            )
            print(f"{site_id}: {json.dumps(counters)}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


def handle_stale_sync(args: argparse.Namespace) -> None:
    repo = JobRepository(args.db)
    today = datetime.now().date().isoformat()
    counters = sync_stale_markers(repo, args.jobs_dir, today)
    print(json.dumps(counters))


def handle_list_sites() -> None:
    for site_id in sorted(SITE_REGISTRY.keys()):
        print(site_id)


if __name__ == "__main__":
    main()
