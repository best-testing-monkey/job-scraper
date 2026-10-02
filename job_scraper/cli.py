import argparse
import json
import sys

from job_scraper.core.db import JobRepository
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

    subparsers.add_parser("list-sites", help="List all available sites")

    args = parser.parse_args()

    if args.command == "scrape":
        handle_scrape(args)
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
    results = run(
        site_ids, repo, args.jobs_dir, ignore_robots=args.ignore_robots, raw_dir=raw_dir
    )

    for site_id, counters in results.items():
        print(f"{site_id}: {json.dumps(counters)}")


def handle_list_sites() -> None:
    for site_id in sorted(SITE_REGISTRY.keys()):
        print(site_id)


if __name__ == "__main__":
    main()
