import re
from pathlib import Path

from job_scraper.core.models import JobPosting


def slugify(text: str) -> str:
    """Lowercase, non-alphanumeric runs -> single hyphen, no leading/
    trailing hyphens. e.g. "Senior Tester (RVO)!" -> "senior-tester-rvo"."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text


def filename_for(posting: JobPosting) -> str:
    """f"{posting.site_id}-{posting.listing_id}-{slugify(posting.title)}.md" """
    return f"{posting.site_id}-{posting.listing_id}-{slugify(posting.title)}.md"


def render(posting: JobPosting) -> str:
    """Returns the full markdown text: '# {title}' header, then one
    '- {Field}: {value}' bullet per populated field in this order: Source
    (= source_url), Client, Category, Level, Status, Location, Hours, Rate,
    Duration, Posted (= posted_date), Experience, Skills (comma-joined if
    non-empty). Skip any field that is None/empty (don't render a bullet
    for it at all). Then render one '- {Key}: {value}' bullet per entry in
    extra_fields (in insertion order), then a blank line, '## Description',
    a blank line, description text. If scrape_note is set, append a blank
    line, '## Scrape note', a blank line, scrape_note text."""
    lines = []

    lines.append(f"# {posting.title}")
    lines.append("")

    fields = [
        ("Source", posting.source_url),
        ("Client", posting.client),
        ("Category", posting.category),
        ("Level", posting.level),
        ("Status", posting.status),
        ("Location", posting.location),
        ("Hours", posting.hours),
        ("Rate", posting.rate),
        ("Duration", posting.duration),
        ("Posted", posting.posted_date),
        ("Experience", posting.experience),
    ]

    for field_name, field_value in fields:
        if field_value is not None and field_value != "":
            lines.append(f"- {field_name}: {field_value}")

    if posting.skills:
        skills_text = ", ".join(posting.skills)
        lines.append(f"- Skills: {skills_text}")

    for key, value in posting.extra_fields.items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("## Description")
    lines.append("")
    lines.append(posting.description)

    if posting.scrape_note is not None and posting.scrape_note != "":
        lines.append("")
        lines.append("## Scrape note")
        lines.append("")
        lines.append(posting.scrape_note)

    return "\n".join(lines)


def write(posting: JobPosting, jobs_dir: str) -> str:
    """Ensures jobs_dir exists, writes render(posting) to
    jobs_dir/filename_for(posting), returns the full path written."""
    jobs_path = Path(jobs_dir)
    jobs_path.mkdir(parents=True, exist_ok=True)

    file_path = jobs_path / filename_for(posting)
    file_path.write_text(render(posting))

    return str(file_path)
