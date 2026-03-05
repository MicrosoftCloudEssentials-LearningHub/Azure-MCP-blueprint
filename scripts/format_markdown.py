"""Repo markdown formatter.

Applies a consistent format across all Markdown files:
- Inserts an author/location header block under the first H1
- Inserts a blockquote with the first sentence of the intro text
- Wraps H3 sections under each H2 in <details> collapsibles
- Appends a "Total views" badge block at the bottom

Designed to be idempotent.

Usage:
  python scripts/format_markdown.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today().isoformat()

EXCLUDED_DIR_NAMES = {
    ".git",
    ".github",
    ".terraform",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}

HEADER_BLOCK = (
    "Costa Rica\n\n"
    "[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)\n"
    "[brown9804](https://github.com/brown9804)\n\n"
    f"Last updated: {TODAY}\n\n"
    "----------\n"
)

FOOTER_BADGE_BLOCK_LINES = [
    "<!-- START BADGE -->\n",
    '<div align="center">\n',
    '  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">\n',
    "  <p>Refresh Date: 2025-11-03</p>\n",
    "</div>\n",
    "<!-- END BADGE -->\n",
]


@dataclass
class ParsedDoc:
    h1_line_index: int
    after_h1_index: int


@dataclass
class FooterSplit:
    body_lines: list[str]
    footer_lines: list[str]


def _find_first_h1(lines: list[str]) -> ParsedDoc | None:
    for idx, line in enumerate(lines):
        if re.match(r"^#\s+", line):
            after = idx + 1
            # Keep any immediately-following blank lines as part of the H1 block.
            while after < len(lines) and lines[after].strip() == "":
                after += 1
            return ParsedDoc(h1_line_index=idx, after_h1_index=after)
    return None


def _has_header_block(lines: list[str], start: int) -> bool:
    window = "\n".join(lines[start : min(len(lines), start + 20)])
    return "Costa Rica" in window and "Last updated:" in window and "----------" in window


def _upsert_header_block(lines: list[str]) -> list[str]:
    parsed = _find_first_h1(lines)
    if not parsed:
        return lines

    if _has_header_block(lines, parsed.after_h1_index):
        # Update Last updated value if present in the header block.
        out: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if i >= parsed.after_h1_index and "Last updated:" in line:
                out.append(f"Last updated: {TODAY}\n")
                i += 1
                continue
            out.append(line)
            i += 1
        return out

    insert = []
    # Ensure there is exactly one blank line between H1 block and header block.
    if parsed.after_h1_index > 0 and lines[parsed.after_h1_index - 1].strip() != "":
        insert.append("\n")
    insert.append(HEADER_BLOCK)
    return lines[: parsed.after_h1_index] + insert + lines[parsed.after_h1_index :]


def _strip_leading_badge_block(lines: list[str], start: int) -> tuple[list[str], int]:
    """If there is already a START BADGE block near the end, do nothing.

    This helper is for bottom insertion only; it does not remove anything.
    """

    return lines, start


def _split_footer_badge(lines: list[str]) -> FooterSplit:
    """Split an existing footer badge block (if present) from the body.

    This prevents the badge from getting wrapped inside a <details> block when
    converting H3 -> collapsibles.
    """

    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if "<!-- START BADGE -->" in line:
            start_idx = i
            continue
        if start_idx is not None and "<!-- END BADGE -->" in line:
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        return FooterSplit(body_lines=lines, footer_lines=[])

    footer_lines = lines[start_idx : end_idx + 1]
    body_lines = lines[:start_idx] + lines[end_idx + 1 :]

    # Trim trailing blank lines in body; keep body ending with exactly one newline.
    while body_lines and body_lines[-1].strip() == "":
        body_lines.pop()
    if body_lines and not body_lines[-1].endswith("\n"):
        body_lines[-1] += "\n"
    if body_lines:
        body_lines.append("\n")

    # Ensure footer starts with a blank line separation.
    if footer_lines and footer_lines[0].strip() != "":
        footer_lines = ["\n"] + footer_lines

    # Normalize footer badge content to the repo standard.
    normalized_footer_text = "".join(footer_lines)
    if "<!-- START BADGE -->" in normalized_footer_text and "<!-- END BADGE -->" in normalized_footer_text:
        footer_lines = ["\n"] + FOOTER_BADGE_BLOCK_LINES

    return FooterSplit(body_lines=body_lines, footer_lines=footer_lines)


def _ensure_footer_badge(lines: list[str]) -> list[str]:
    text = "".join(lines)
    if "<!-- START BADGE -->" in text and "<!-- END BADGE -->" in text:
        return lines

    # Trim trailing whitespace/newlines, then append.
    while lines and lines[-1].strip() == "":
        lines.pop()

    if lines:
        lines[-1] = lines[-1].rstrip("\n") + "\n"

    # Separate body from footer with a single blank line.
    return lines + ["\n"] + FOOTER_BADGE_BLOCK_LINES


def _extract_intro_sentence(lines: list[str], start: int) -> tuple[str | None, int]:
    """Extract a first-sentence intro from the document.

    Scans forward from `start` to find the first non-heading paragraph and
    returns (sentence, first_content_index).
    """

    i = start
    in_code_fence = False

    def _is_skippable_line(s: str) -> bool:
        if s == "":
            return True
        if s.startswith("<!--"):
            return True
        if s.startswith("[") and "](" in s:
            return True
        if s.startswith("!") and "[" in s:
            return True
        return False

    # Find the first paragraph block that's not a heading.
    while i < len(lines):
        s = lines[i].rstrip("\n")
        stripped = s.strip()

        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            i += 1
            continue
        if in_code_fence:
            i += 1
            continue

        if _is_skippable_line(stripped):
            i += 1
            continue

        # Skip headings; keep scanning for the first paragraph beneath them.
        if re.match(r"^#{1,6}\s+", stripped):
            i += 1
            continue

        # Collect paragraph lines until blank line or heading.
        paragraph_lines: list[str] = []
        j = i
        while j < len(lines):
            curr = lines[j].rstrip("\n")
            curr_stripped = curr.strip()

            if curr_stripped.startswith("```"):
                break
            if curr_stripped == "":
                break
            if re.match(r"^#{1,6}\s+", curr_stripped):
                break
            paragraph_lines.append(curr)
            j += 1

        paragraph = " ".join([ln.strip() for ln in paragraph_lines]).strip()
        if not paragraph:
            i = j + 1
            continue

        m = re.search(r"([.!?])\s", paragraph)
        if m:
            sentence = paragraph[: m.end(1)].strip()
        else:
            sentence = paragraph.strip()

        return sentence, i

    return None, i


def _ensure_blockquote(lines: list[str]) -> list[str]:
    parsed = _find_first_h1(lines)
    if not parsed:
        return lines

    # Find where the header block ends (look for the separator line)
    i = parsed.after_h1_index
    header_end = i

    # If our header block exists, advance past it.
    # We consider the header block ended when we see a line of dashes.
    while header_end < len(lines) and not re.match(r"^-{5,}\s*$", lines[header_end].strip()):
        header_end += 1
    if header_end < len(lines) and re.match(r"^-{5,}\s*$", lines[header_end].strip()):
        header_end += 1

    # Skip blank lines after header
    while header_end < len(lines) and lines[header_end].strip() == "":
        header_end += 1

    # If there is already a blockquote right here, keep it.
    if header_end < len(lines) and lines[header_end].lstrip().startswith(">"):
        return lines

    sentence, content_start = _extract_intro_sentence(lines, header_end)
    if not sentence:
        return lines

    # Insert a blockquote with the sentence.
    bq = [f"> {sentence}\n", "\n"]

    # Remove the extracted sentence from the first paragraph if it appears verbatim.
    # Keep it simple and safe: only strip it when it's a prefix on the first line.
    out = list(lines)
    if content_start < len(out):
        original_line = out[content_start]
        line_stripped = original_line.strip()

        if sentence and line_stripped.startswith(sentence):
            remainder = line_stripped[len(sentence) :].lstrip()
            if remainder:
                out[content_start] = remainder + "\n"
            else:
                out[content_start] = "\n"

    return out[:header_end] + bq + out[header_end:]


def _wrap_h3_as_details(section_lines: list[str]) -> list[str]:
    """Wrap H3 blocks in a section into <details> blocks.

    Expects section_lines to start at the first line after an H2 header.
    """

    out: list[str] = []
    i = 0

    while i < len(section_lines):
        line = section_lines[i]
        if line.lstrip().startswith("<details"):
            # Already collapsible; copy through the matching </details>.
            out.append(line)
            i += 1
            while i < len(section_lines):
                out.append(section_lines[i])
                if section_lines[i].strip().lower() == "</details>":
                    i += 1
                    break
                i += 1
            continue

        m = re.match(r"^###\s+(.*)\s*$", line.strip())
        if not m:
            out.append(line)
            i += 1
            continue

        title = m.group(1).strip()
        i += 1
        content: list[str] = []
        while i < len(section_lines):
            nxt = section_lines[i]
            if re.match(r"^##\s+", nxt.strip()):
                break
            if re.match(r"^###\s+", nxt.strip()):
                break
            content.append(nxt)
            i += 1

        # Trim leading/trailing blank lines in content.
        while content and content[0].strip() == "":
            content.pop(0)
        while content and content[-1].strip() == "":
            content.pop()

        out.append("<details>\n")
        out.append(f"<summary><strong>{title}</strong></summary>\n")
        out.append("\n")
        if content:
            # Ensure content ends with newline.
            for c in content:
                out.append(c)
            if not out[-1].endswith("\n"):
                out[-1] += "\n"
        out.append("\n</details>\n\n")

    return out


def _convert_h3_to_collapsible(lines: list[str]) -> list[str]:
    """Convert H3 headings into collapsible blocks, grouped under their H2."""

    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if not re.match(r"^##\s+", line.strip()):
            out.append(line)
            i += 1
            continue

        # Copy the H2 header
        out.append(line)
        i += 1

        # Collect lines until next H2 or EOF
        section: list[str] = []
        while i < len(lines) and not re.match(r"^##\s+", lines[i].strip()):
            section.append(lines[i])
            i += 1

        out.extend(_wrap_h3_as_details(section))

    return out


def _collapse_extra_blank_lines(lines: list[str]) -> list[str]:
    """Collapse runs of blank lines to a single blank line.

    This is applied only outside fenced code blocks to avoid modifying code samples.
    """

    out: list[str] = []
    blank_run = 0
    in_code_fence = False
    fence_char: str | None = None

    for line in lines:
        stripped = line.rstrip("\n")
        fence_match = re.match(r"^\s*(```+|~~~+)", stripped)
        if fence_match:
            marker = fence_match.group(1)
            marker_char = marker[0]
            if not in_code_fence:
                in_code_fence = True
                fence_char = marker_char
            elif fence_char == marker_char:
                in_code_fence = False
                fence_char = None
            blank_run = 0
            out.append(line)
            continue

        if in_code_fence:
            out.append(line)
            continue

        if line.strip() == "":
            blank_run += 1
            if blank_run <= 1:
                out.append("\n")
            continue

        blank_run = 0
        out.append(line)

    return out


def format_markdown(text: str) -> str:
    lines = [ln if ln.endswith("\n") else ln + "\n" for ln in text.splitlines()]
    # Preserve empty file / trailing newline handling
    if text.endswith("\n"):
        lines.append("\n")
        lines.pop()  # Normalize; we always join with \n

    split = _split_footer_badge(lines)
    lines = split.body_lines

    lines = _upsert_header_block(lines)
    lines = _ensure_blockquote(lines)
    lines = _convert_h3_to_collapsible(lines)

    # Re-attach existing footer badge (if any) to ensure it's outside collapsibles.
    if split.footer_lines:
        lines = lines + split.footer_lines

    lines = _ensure_footer_badge(lines)

    lines = _collapse_extra_blank_lines(lines)

    return "".join(lines)


def main() -> None:
    md_files = [
        p
        for p in sorted(ROOT.rglob("*.md"))
        if not any(part in EXCLUDED_DIR_NAMES for part in p.parts)
    ]
    for path in md_files:
        original = path.read_text(encoding="utf-8")
        formatted = format_markdown(original)
        if formatted != original:
            path.write_text(formatted, encoding="utf-8")
            print(f"Updated: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
