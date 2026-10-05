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


def stem_for(posting: JobPosting) -> str:
    """Returns the file stem (filename without .md extension) for the posting."""
    return filename_for(posting)[:-3]


def md_path_for(jobs_dir: str, site_id: str, listing_id: str, title: str) -> Path:
    """Returns the path for a markdown file given its components.
    Path(jobs_dir) / f"{site_id}-{listing_id}-{slugify(title)}.md"."""
    return Path(jobs_dir) / f"{site_id}-{listing_id}-{slugify(title)}.md"


def screenshot_relpath(stem: str) -> str:
    """Returns the relative path for a screenshot file given its stem."""
    return f"screenshots/{stem}.png"


def render(
    posting: JobPosting,
    screenshot: str | None = None,
    stale_since: str | None = None,
) -> str:
    """Returns the full markdown text: '# {title}' header, then one
    '- {Field}: {value}' bullet per populated field in this order: Source
    (= source_url), Client, Category, Level, Status, Location, Workplace,
    Hours, Rate,
    Duration, Posted (= posted_date), Experience, Skills (comma-joined if
    non-empty). Skip any field that is None/empty (don't render a bullet
    for it at all). Then render one '- {Key}: {value}' bullet per entry in
    extra_fields (in insertion order). If screenshot is a non-empty string,
    add a '- Screenshot: {screenshot}' bullet. If stale_since is a non-empty
    string, add a '- Stale since: {stale_since}' bullet right after the
    screenshot bullet (or after extra fields if no screenshot). Then a blank
    line, '## Description', a blank line, description text. If scrape_note
    is set, append a blank line, '## Scrape note', a blank line, scrape_note
    text."""
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
        ("Workplace", posting.workplace),
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

    if screenshot and screenshot != "":
        lines.append(f"- Screenshot: {screenshot}")

    if stale_since and stale_since != "":
        lines.append(f"- Stale since: {stale_since}")

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


def write(
    posting: JobPosting,
    jobs_dir: str,
    screenshot: str | None = None,
    stale_since: str | None = None,
) -> str:
    """Ensures jobs_dir exists, writes render(posting, screenshot, stale_since)
    to jobs_dir/filename_for(posting), returns the full path written."""
    jobs_path = Path(jobs_dir)
    jobs_path.mkdir(parents=True, exist_ok=True)

    file_path = jobs_path / filename_for(posting)
    file_path.write_text(render(posting, screenshot, stale_since))

    return str(file_path)


def set_screenshot_line(md_path: str, screenshot: str) -> bool:
    """Updates or inserts a '- Screenshot: {screenshot}' line in a markdown file.

    If the file already has a '- Screenshot:' line, replace its value.
    Otherwise, insert the bullet after the last consecutive '- ' bullet in the
    header block (lines between '# title' and the blank line before
    '## Description'). Returns True if the file content changed, False if it
    already had exactly that line. Idempotent."""
    file_path = Path(md_path)
    original_content = file_path.read_text()
    lines = original_content.split("\n")

    target_line = f"- Screenshot: {screenshot}"

    # Find existing screenshot line
    screenshot_idx = None
    for i, line in enumerate(lines):
        if line.startswith("- Screenshot:"):
            screenshot_idx = i
            break

    if screenshot_idx is not None:
        # Replace existing line
        if lines[screenshot_idx] == target_line:
            return False
        lines[screenshot_idx] = target_line
    else:
        # Find the blank line before ## Description
        description_idx = None
        for i, line in enumerate(lines):
            if line == "## Description":
                description_idx = i
                break

        if description_idx is None:
            return False

        # Find the last consecutive bullet before description
        insert_idx = description_idx - 2  # -1 for blank line, -1 to insert before it

        # Ensure we're inserting after a bullet
        if insert_idx >= 0 and lines[insert_idx].startswith("- "):
            insert_idx += 1
            lines.insert(insert_idx, target_line)
        else:
            return False

    new_content = "\n".join(lines)
    if new_content == original_content:
        return False

    file_path.write_text(new_content)
    return True


def source_line_differs(md_path: str, source_url: str) -> bool:
    """Returns True if the file does not exist, has no '- Source:' line, or its value
    (after .strip()) != source_url. False when the Source line equals source_url."""
    file_path = Path(md_path)
    if not file_path.exists():
        return True

    try:
        content = file_path.read_text()
    except Exception:
        return True

    lines = content.split("\n")

    # Find the Source line in the header (before ## Description)
    description_idx = None
    for i, line in enumerate(lines):
        if line == "## Description":
            description_idx = i
            break

    # Search for Source line only in the header section
    for i in range(description_idx if description_idx else len(lines)):
        line = lines[i]
        if line.startswith("- Source:"):
            # Extract the URL after "- Source: "
            match = re.match(r"^- Source:\s*(.+)$", line)
            if match:
                url_value = match.group(1).strip()
                return url_value != source_url
            return True

    # No Source line found
    return True


def remove_screenshot_line(md_path: str) -> bool:
    """Removes the '- Screenshot:' line from a markdown file.

    Searches for and removes the first line starting with '- Screenshot:'
    found in the header block (lines before '## Description'). Returns True
    if a line was removed, False if the file does not exist, has no
    '## Description', or has no such line. Idempotent. Nothing at or after
    '## Description' is touched."""
    file_path = Path(md_path)
    if not file_path.exists():
        return False

    original_content = file_path.read_text()
    lines = original_content.split("\n")

    # Find the blank line before ## Description first (to limit search to header)
    description_idx = None
    for i, line in enumerate(lines):
        if line == "## Description":
            description_idx = i
            break

    if description_idx is None:
        return False

    # Find existing screenshot line only in the header section (before ## Description)
    screenshot_idx = None
    for i in range(description_idx):
        if lines[i].startswith("- Screenshot:"):
            screenshot_idx = i
            break

    if screenshot_idx is None:
        return False

    # Remove the line
    lines.pop(screenshot_idx)

    new_content = "\n".join(lines)
    if new_content == original_content:
        return False

    file_path.write_text(new_content)
    return True


def set_stale_line(md_path: str, stale_since: str | None) -> bool:
    """Updates, inserts, or removes a '- Stale since: {stale_since}' line.

    If stale_since is a non-empty string matching YYYY-MM-DD format, replace
    or insert the line after the last consecutive '- ' bullet (same rule as
    set_screenshot_line). If stale_since is None, remove the line if present.
    Returns True if the file content changed, False otherwise.
    Raises ValueError if stale_since doesn't match the format.
    The description and everything after '## Description' are never touched."""
    file_path = Path(md_path)
    if not file_path.exists():
        return False

    # Validate format
    if stale_since is not None and stale_since != "":
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", stale_since):
            raise ValueError(
                f"stale_since must match YYYY-MM-DD format, got: {stale_since}"
            )

    original_content = file_path.read_text()
    lines = original_content.split("\n")

    # Find the blank line before ## Description first (to limit search to header)
    description_idx = None
    for i, line in enumerate(lines):
        if line == "## Description":
            description_idx = i
            break

    if description_idx is None:
        return False

    # Find existing stale_since line only in the header section (before ## Description)
    stale_idx = None
    for i in range(description_idx):
        if lines[i].startswith("- Stale since:"):
            stale_idx = i
            break

    if stale_since is None or stale_since == "":
        # Remove the line if present
        if stale_idx is not None:
            lines.pop(stale_idx)
        else:
            return False
    else:
        # Insert or replace
        target_line = f"- Stale since: {stale_since}"

        if stale_idx is not None:
            # Replace existing line
            if lines[stale_idx] == target_line:
                return False
            lines[stale_idx] = target_line
        else:
            # Find the last consecutive bullet before description
            insert_idx = description_idx - 2  # -1 for blank line, -1 to insert before it

            # Ensure we're inserting after a bullet
            if insert_idx >= 0 and lines[insert_idx].startswith("- "):
                insert_idx += 1
                lines.insert(insert_idx, target_line)
            else:
                return False

    new_content = "\n".join(lines)
    if new_content == original_content:
        return False

    file_path.write_text(new_content)
    return True
