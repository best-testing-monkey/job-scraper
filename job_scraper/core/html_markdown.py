import re
from html import unescape
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag


def html_to_markdown(html: Optional[str], *, plain: bool = False) -> str:
    """Convert an HTML fragment (or plain text) into clean Markdown.

    Rules:
    - None, empty, or whitespace-only input returns "".
    - Parse with BeautifulSoup; drop <script>, <style>, comments.
    - Paragraphs (<p>, block-level <div>, text in <div>) separated by exactly one blank line.
    - Headings: <h1>-<h3> -> ### text; <h4>-<h6> -> #### text.
    - Lists: <ul> -> "- item"; <ol> -> "1. item", "2. item", etc. Nested lists indent by 4 spaces.
    - Inline tags: <strong>/<b> -> **text**. Others (<em>, <i>, <span>, <a>, <u>) contribute text only. No links or images.
    - <br> inside a paragraph -> "  \\n" (hard line break).
    - <table>: each <tr> becomes one line, cells joined with " | ".
    - Entities are decoded; \\xa0 becomes a space; whitespace collapses to one space.
    - Lines starting with # get # backslash-escaped (\\#) to prevent headings.
    - Plain text with no < or & is split on blank lines into paragraphs.
    - plain=True forces the plain-text path regardless of < or & (entities not decoded).
    - Output never starts/ends with whitespace/newlines and never has three consecutive newlines.
    """
    if not html or not html.strip():
        return ""

    # Check if input is plain text (no < or &)
    if plain or ("<" not in html and "&" not in html):
        return _convert_plain_text(html)

    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, and comments
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, str) and str(text).startswith("<!--")):
        if hasattr(comment, "extract"):
            comment.extract()

    blocks = []
    _process_nodes(soup.contents, blocks, 0)

    # Join blocks with blank lines
    output = "\n\n".join(blocks)

    # Collapse multiple newlines to max 2 (one blank line)
    output = re.sub(r"\n\n\n+", "\n\n", output)

    # Strip leading/trailing whitespace
    output = output.strip()

    return output


def _convert_plain_text(text: str) -> str:
    """Convert plain text (no HTML) into Markdown."""
    # Split on blank lines
    paragraphs = re.split(r"\n\s*\n", text)

    blocks = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Replace single newlines with hard breaks
        lines = para.split("\n")
        processed_lines = []
        for line in lines:
            line = line.strip()
            if line:
                # Normalize whitespace within the line
                line = re.sub(r"\s+", " ", line)
                processed_lines.append(line)

        para_text = "  \n".join(processed_lines)

        # Escape lines starting with #
        para_lines = para_text.split("\n")
        para_lines = [_escape_heading_marker(line) for line in para_lines]
        para_text = "\n".join(para_lines)

        blocks.append(para_text)

    output = "\n\n".join(blocks)
    output = output.strip()
    return output


def _process_nodes(nodes: list, blocks: list, indent_level: int) -> None:
    """Process a list of nodes and append blocks to the blocks list."""
    for node in nodes:
        if isinstance(node, NavigableString):
            text = str(node).strip()
            if text and not text.startswith("<!--"):
                # Will be handled by parent tag
                pass
            continue

        if not isinstance(node, Tag):
            continue

        tag_name = node.name.lower() if node.name else ""

        if tag_name in ["script", "style"]:
            continue
        elif tag_name == "p":
            blocks.append(_extract_inline_text(node))
        elif tag_name in ["div"]:
            # Check if it has block-level children
            has_block_children = any(
                isinstance(child, Tag) and child.name.lower() in [
                    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
                    "ul", "ol", "table", "blockquote"
                ]
                for child in node.children
            )

            if has_block_children:
                _process_nodes(list(node.children), blocks, indent_level)
            else:
                # Treat as a paragraph
                text = _extract_inline_text(node)
                if text:
                    blocks.append(text)
        elif tag_name in ["h1", "h2", "h3"]:
            text = _extract_inline_text(node)
            if text:
                blocks.append(f"### {text}")
        elif tag_name in ["h4", "h5", "h6"]:
            text = _extract_inline_text(node)
            if text:
                blocks.append(f"#### {text}")
        elif tag_name == "ul":
            list_block = _process_list(node, indent_level, ordered=False)
            if list_block:
                blocks.append(list_block)
        elif tag_name == "ol":
            list_block = _process_list(node, indent_level, ordered=True)
            if list_block:
                blocks.append(list_block)
        elif tag_name == "table":
            table_block = _process_table(node)
            if table_block:
                blocks.append(table_block)
        elif tag_name == "br":
            # Handled in inline context
            pass
        else:
            # For other tags, process children
            _process_nodes(list(node.children), blocks, indent_level)


def _extract_inline_text(node: Tag) -> str:
    """Extract inline text from a node, handling <br>, <strong>, etc."""
    parts = []

    for child in node.children:
        if isinstance(child, NavigableString):
            text = str(child)
            text = unescape(text)
            text = text.replace("\xa0", " ")
            # Normalize whitespace
            text = re.sub(r"\s+", " ", text)
            parts.append(text)
        elif isinstance(child, Tag):
            child_name = child.name.lower() if child.name else ""

            if child_name == "br":
                parts.append("  \n")
            elif child_name in ["strong", "b"]:
                text = _extract_inline_text(child)
                if text:
                    parts.append(f"**{text}**")
            elif child_name in ["em", "i", "span", "a", "u"]:
                # Just extract text, no formatting
                text = _extract_inline_text(child)
                if text:
                    parts.append(text)
            elif child_name == "img":
                # Drop images
                pass
            else:
                # For other tags, extract text
                text = _extract_inline_text(child)
                if text:
                    parts.append(text)

    result = "".join(parts)

    # Normalize whitespace (but preserve hard line breaks)
    lines = result.split("  \n")
    lines = [re.sub(r"\s+", " ", line.strip()) for line in lines]
    result = "  \n".join(line for line in lines if line)

    # Remove trailing whitespace except for hard breaks
    result = result.rstrip()

    # Escape lines starting with #
    result_lines = result.split("\n")
    result_lines = [_escape_heading_marker(line) for line in result_lines]
    result = "\n".join(result_lines)

    return result


def _escape_heading_marker(line: str) -> str:
    """Escape # at the start of a line to prevent it from becoming a heading."""
    stripped = line.lstrip()
    if stripped.startswith("#"):
        # Escape the first #
        leading_spaces = line[:len(line) - len(stripped)]
        return leading_spaces + "\\" + stripped
    return line


def _process_list(node: Tag, indent_level: int, ordered: bool = False) -> str:
    """Process a <ul> or <ol> tag and return the markdown."""
    items = node.find_all("li", recursive=False)
    lines = []

    for idx, item in enumerate(items, 1):
        prefix = f"{idx}." if ordered else "-"
        indent = "    " * indent_level

        # Check for nested lists
        nested_lists = item.find_all(["ul", "ol"], recursive=False)

        # Build item text by creating a wrapper that excludes nested lists
        # We need to extract text while preserving formatting
        item_children = list(item.children)
        nested_set = set(nested_lists)

        # Create wrapper to extract text from
        wrapper = BeautifulSoup("", "html.parser").new_tag("div")
        for child in item_children:
            if isinstance(child, NavigableString):
                wrapper.append(str(child))
            elif isinstance(child, Tag) and child not in nested_set:
                # Deep copy the child to avoid modifying the original
                child_copy = BeautifulSoup(str(child), "html.parser").contents[0]
                wrapper.append(child_copy)

        item_text = _extract_inline_text(wrapper)

        lines.append(f"{indent}{prefix} {item_text}")

        # Process nested lists
        for nested_list in nested_lists:
            nested_ordered = nested_list.name.lower() == "ol"
            nested_block = _process_list(nested_list, indent_level + 1, ordered=nested_ordered)
            if nested_block:
                for nested_line in nested_block.split("\n"):
                    lines.append(nested_line)

    return "\n".join(lines)


def _process_table(node: Tag) -> str:
    """Process a <table> tag and return the markdown."""
    rows = node.find_all("tr")
    lines = []

    for row in rows:
        cells = row.find_all(["td", "th"])
        cell_texts = []

        for cell in cells:
            text = _extract_inline_text(cell)
            text = re.sub(r"\s+", " ", text).strip()
            cell_texts.append(text)

        if cell_texts:
            lines.append(" | ".join(cell_texts))

    return "\n".join(lines)
