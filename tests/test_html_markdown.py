import pytest
from pathlib import Path

from job_scraper.core.html_markdown import html_to_markdown


class TestEmptyInput:
    def test_none_input(self) -> None:
        assert html_to_markdown(None) == ""

    def test_empty_string(self) -> None:
        assert html_to_markdown("") == ""

    def test_whitespace_only(self) -> None:
        assert html_to_markdown("   \n  \t  ") == ""


class TestParagraphs:
    def test_single_paragraph(self) -> None:
        html = "<p>Hello world</p>"
        assert html_to_markdown(html) == "Hello world"

    def test_multiple_paragraphs(self) -> None:
        html = "<p>First</p><p>Second</p>"
        result = html_to_markdown(html)
        assert result == "First\n\nSecond"

    def test_block_div(self) -> None:
        html = "<div><p>Paragraph</p></div>"
        assert html_to_markdown(html) == "Paragraph"

    def test_text_in_div(self) -> None:
        html = "<div>Direct text</div>"
        assert html_to_markdown(html) == "Direct text"

    def test_div_with_multiple_paragraphs(self) -> None:
        html = "<div><p>First</p><p>Second</p></div>"
        result = html_to_markdown(html)
        assert result == "First\n\nSecond"


class TestHeadings:
    def test_h1_becomes_h3(self) -> None:
        html = "<h1>Main Title</h1>"
        assert html_to_markdown(html) == "### Main Title"

    def test_h2_becomes_h3(self) -> None:
        html = "<h2>Section</h2>"
        assert html_to_markdown(html) == "### Section"

    def test_h3_becomes_h3(self) -> None:
        html = "<h3>Subsection</h3>"
        assert html_to_markdown(html) == "### Subsection"

    def test_h4_becomes_h4(self) -> None:
        html = "<h4>Subsubsection</h4>"
        assert html_to_markdown(html) == "#### Subsubsection"

    def test_h5_becomes_h4(self) -> None:
        html = "<h5>Deep</h5>"
        assert html_to_markdown(html) == "#### Deep"

    def test_h6_becomes_h4(self) -> None:
        html = "<h6>Deepest</h6>"
        assert html_to_markdown(html) == "#### Deepest"

    def test_heading_with_paragraph(self) -> None:
        html = "<h2>Title</h2><p>Content</p>"
        result = html_to_markdown(html)
        assert result == "### Title\n\nContent"


class TestInlineTags:
    def test_strong_tag(self) -> None:
        html = "<p>This is <strong>important</strong></p>"
        assert html_to_markdown(html) == "This is **important**"

    def test_b_tag(self) -> None:
        html = "<p>This is <b>bold</b></p>"
        assert html_to_markdown(html) == "This is **bold**"

    def test_em_tag(self) -> None:
        html = "<p>This is <em>emphasized</em></p>"
        assert html_to_markdown(html) == "This is emphasized"

    def test_i_tag(self) -> None:
        html = "<p>This is <i>italic</i></p>"
        assert html_to_markdown(html) == "This is italic"

    def test_span_tag(self) -> None:
        html = "<p>This is <span>text</span></p>"
        assert html_to_markdown(html) == "This is text"

    def test_link_text_only(self) -> None:
        html = '<p>Visit <a href="http://example.com">our site</a></p>'
        assert html_to_markdown(html) == "Visit our site"

    def test_u_tag(self) -> None:
        html = "<p>This is <u>underlined</u></p>"
        assert html_to_markdown(html) == "This is underlined"

    def test_image_dropped(self) -> None:
        html = '<p>Text <img src="image.jpg" alt="alt"> more</p>'
        assert html_to_markdown(html) == "Text more"


class TestLineBreaks:
    def test_br_inside_paragraph(self) -> None:
        html = "<p>Line one<br>Line two</p>"
        assert html_to_markdown(html) == "Line one  \nLine two"

    def test_multiple_br(self) -> None:
        html = "<p>A<br>B<br>C</p>"
        result = html_to_markdown(html)
        assert result == "A  \nB  \nC"


class TestLists:
    def test_unordered_list(self) -> None:
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = html_to_markdown(html)
        assert result == "- Item 1\n- Item 2"

    def test_ordered_list(self) -> None:
        html = "<ol><li>First</li><li>Second</li><li>Third</li></ol>"
        result = html_to_markdown(html)
        assert result == "1. First\n2. Second\n3. Third"

    def test_nested_ul_in_ul(self) -> None:
        html = """<ul>
            <li>Item 1
                <ul><li>Nested 1a</li><li>Nested 1b</li></ul>
            </li>
            <li>Item 2</li>
        </ul>"""
        result = html_to_markdown(html)
        assert "- Item 1" in result
        assert "    - Nested 1a" in result
        assert "    - Nested 1b" in result
        assert "- Item 2" in result

    def test_nested_ol_in_ol(self) -> None:
        html = """<ol>
            <li>First
                <ol><li>Nested 1a</li><li>Nested 1b</li></ol>
            </li>
            <li>Second</li>
        </ol>"""
        result = html_to_markdown(html)
        assert "1. First" in result
        assert "    1. Nested 1a" in result
        assert "    2. Nested 1b" in result
        assert "2. Second" in result

    def test_li_with_p_tag(self) -> None:
        html = "<ul><li><p>Item with paragraph</p></li></ul>"
        result = html_to_markdown(html)
        assert result == "- Item with paragraph"


class TestTables:
    def test_simple_table(self) -> None:
        html = """<table>
            <tr><td>Cell 1</td><td>Cell 2</td></tr>
            <tr><td>Cell 3</td><td>Cell 4</td></tr>
        </table>"""
        result = html_to_markdown(html)
        assert "Cell 1 | Cell 2" in result
        assert "Cell 3 | Cell 4" in result


class TestEntities:
    def test_decode_html_entities(self) -> None:
        html = "<p>&eacute;&nbsp;test</p>"
        result = html_to_markdown(html)
        assert "é" in result
        assert "test" in result

    def test_nbsp_becomes_space(self) -> None:
        html = "<p>Word&nbsp;Word</p>"
        result = html_to_markdown(html)
        assert result == "Word Word"


class TestWhitespace:
    def test_collapse_multiple_spaces(self) -> None:
        html = "<p>Multiple   spaces   here</p>"
        result = html_to_markdown(html)
        assert result == "Multiple spaces here"

    def test_no_leading_trailing_whitespace(self) -> None:
        html = "<p>  Text with spaces  </p>"
        result = html_to_markdown(html)
        assert result == "Text with spaces"

    def test_no_trailing_whitespace_on_lines(self) -> None:
        html = "<p>Line 1  <br>  Line 2</p>"
        result = html_to_markdown(html)
        assert not result.rstrip("\n").endswith(" ")
        assert not any(line.endswith("   ") for line in result.split("\n"))


class TestHeadingEscaping:
    def test_escape_line_starting_with_hash(self) -> None:
        html = "<p>#This would be a heading</p>"
        result = html_to_markdown(html)
        assert result.startswith("\\#")

    def test_escape_double_hash(self) -> None:
        html = "<p>##This is dangerous</p>"
        result = html_to_markdown(html)
        assert result.startswith("\\##")

    def test_no_line_starts_with_double_hash(self) -> None:
        html = "<p>##Section</p><p>Another ##hash</p>"
        result = html_to_markdown(html)
        assert "## " not in result


class TestRemoveScriptStyle:
    def test_remove_script_tag(self) -> None:
        html = "<p>Text</p><script>alert('hi')</script><p>More</p>"
        result = html_to_markdown(html)
        assert "alert" not in result
        assert "Text" in result
        assert "More" in result

    def test_remove_style_tag(self) -> None:
        html = "<p>Text</p><style>body { color: red; }</style><p>More</p>"
        result = html_to_markdown(html)
        assert "color: red" not in result

    def test_remove_html_comments(self) -> None:
        html = "<p>Text</p><!-- comment --><p>More</p>"
        result = html_to_markdown(html)
        assert "comment" not in result


class TestPlainText:
    def test_plain_text_no_tags(self) -> None:
        html = "Simple text without tags"
        assert html_to_markdown(html) == "Simple text without tags"

    def test_plain_text_with_newlines(self) -> None:
        html = "Line 1\nLine 2\nLine 3"
        result = html_to_markdown(html)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_plain_text_with_blank_lines(self) -> None:
        html = "Paragraph 1\n\nParagraph 2"
        result = html_to_markdown(html)
        assert result == "Paragraph 1\n\nParagraph 2"

    def test_plain_text_single_newline_as_hard_break(self) -> None:
        html = "Line 1\nLine 2"
        result = html_to_markdown(html)
        assert "Line 1  \nLine 2" in result


class TestOutputFormat:
    def test_no_triple_newlines(self) -> None:
        html = "<p>First</p><p>Second</p><p>Third</p>"
        result = html_to_markdown(html)
        assert "\n\n\n" not in result

    def test_output_stripped(self) -> None:
        html = "  <p>Text</p>  "
        result = html_to_markdown(html)
        assert not result.startswith(" ")
        assert not result.endswith(" ")


class TestGoldenFile:
    def test_sample_html_to_markdown(self) -> None:
        fixture_dir = Path(__file__).parent / "fixtures" / "html_markdown"
        sample_html = (fixture_dir / "sample.html").read_text()
        expected_md = (fixture_dir / "sample.md").read_text()

        result = html_to_markdown(sample_html)
        assert result == expected_md


class TestPlainFlag:
    def test_plain_keeps_ampersand_and_tags_literal(self):
        assert html_to_markdown("R&D &amp; <b>x</b>", plain=True) == "R&D &amp; <b>x</b>"

    def test_plain_paragraphs_and_hard_breaks(self):
        assert html_to_markdown("a & b\nc\n\nd", plain=True) == "a & b  \nc\n\nd"

    def test_plain_escapes_heading_and_collapses_whitespace(self):
        assert html_to_markdown("# Title  &   more", plain=True) == "\\# Title & more"

    def test_plain_empty(self):
        assert html_to_markdown("  ", plain=True) == ""

    def test_default_still_html(self):
        assert html_to_markdown("<p>a &amp; b</p>") == "a & b"


class TestBareTopLevelText:
    @pytest.mark.parametrize(
        "html,expected",
        [
            ("a &amp; b", "a & b"),
            ("Hello<br>world", "Hello  \nworld"),
            ("Intro text<ul><li>x</li></ul>tail", "Intro text\n\n- x\n\ntail"),
            ("<p>ok</p>trailing bare", "ok\n\ntrailing bare"),
            ("R&amp;D role &lt;remote&gt;", "R&D role <remote>"),
            ("<div>lead<p>para</p>tail</div>", "lead\n\npara\n\ntail"),
            ("<b>Bold</b> lead<p>x</p>", "**Bold** lead\n\nx"),
            ("#tag intro<p>x</p>", "\\#tag intro\n\nx"),
        ],
    )
    def test_bare_text_kept(self, html, expected):
        assert html_to_markdown(html) == expected
