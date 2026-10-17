#!/usr/bin/env python3
"""Parse Markdown ATX headings and print an outline or a TOC.

Standard library only.
"""

import argparse
import re
import sys

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
FENCE_RE = re.compile(r"^\s*```")
SLUG_KEEP_RE = re.compile(r"[^\w\s-]", re.UNICODE)
SLUG_SPACE_RE = re.compile(r"\s+")


def parse_headings(lines):
    """Return a list of (lineno, level, text) for ATX headings outside fences."""
    headings = []
    in_fence = False
    for lineno, raw in enumerate(lines, start=1):
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(raw)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append((lineno, level, text))
    return headings


def slugify(text):
    """GitHub-style anchor: lowercase, drop punctuation, spaces -> hyphens."""
    slug = text.lower()
    slug = SLUG_KEEP_RE.sub("", slug)
    slug = SLUG_SPACE_RE.sub("-", slug.strip())
    return slug


def filter_headings(headings, max_level):
    return [h for h in headings if h[1] <= max_level]


def render_outline(headings, with_lines):
    out = []
    for lineno, level, text in headings:
        prefix = "%d: " % lineno if with_lines else ""
        out.append("%s%s%s" % (prefix, "  " * (level - 1), text))
    return "\n".join(out)


def render_toc(headings):
    out = []
    for _lineno, level, text in headings:
        out.append("%s- [%s](#%s)" % ("  " * (level - 1), text, slugify(text)))
    return "\n".join(out)


def run_self_test():
    fixture = [
        "# Title",          # 1
        "",                 # 2
        "## Section A",     # 3
        "```",              # 4
        "# not a heading",  # 5
        "## also ignored",  # 6
        "```",              # 7
        "### Deep",         # 8
        "#### Too deep",    # 9
    ]
    try:
        headings = parse_headings(fixture)
        assert headings == [
            (1, 1, "Title"),
            (3, 2, "Section A"),
            (8, 3, "Deep"),
            (9, 4, "Too deep"),
        ], headings

        assert slugify("Hello, World!") == "hello-world"
        assert slugify("  API  v2.0  ") == "api-v20"
        assert slugify("C# & C++") == "c-c"

        limited = filter_headings(headings, 2)
        assert [h[2] for h in limited] == ["Title", "Section A"], limited

        outline = render_outline(limited, with_lines=True)
        assert outline == "1: Title\n3:   Section A", repr(outline)

        toc = render_toc(limited)
        assert toc == "- [Title](#title)\n  - [Section A](#section-a)", repr(toc)
    except AssertionError as exc:
        print("FAIL: %s" % exc)
        return 1
    print("PASS")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="md_toc.py",
        description="Print an outline of Markdown ATX headings.",
    )
    parser.add_argument("file", nargs="?", help="Markdown file to parse")
    parser.add_argument("--max-level", type=int, default=6, metavar="N",
                        help="only show headings with level <= N (default 6)")
    parser.add_argument("--with-lines", action="store_true",
                        help="prefix each line with its line number")
    parser.add_argument("--toc", action="store_true",
                        help="emit a GitHub-style table of contents")
    parser.add_argument("--self-test", action="store_true",
                        help="run built-in tests and exit")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if not args.file:
        parser.print_usage(sys.stderr)
        print("md_toc.py: error: a Markdown file is required", file=sys.stderr)
        return 2

    try:
        with open(args.file, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except FileNotFoundError:
        print("md_toc.py: error: file not found: %s" % args.file, file=sys.stderr)
        return 1
    except OSError as exc:
        print("md_toc.py: error: cannot read %s: %s" % (args.file, exc),
              file=sys.stderr)
        return 1

    headings = filter_headings(parse_headings(lines), args.max_level)
    if args.toc:
        output = render_toc(headings)
    else:
        output = render_outline(headings, args.with_lines)

    if output:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
