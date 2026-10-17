#!/usr/bin/env python3
"""Convert CSV/TSV text into a GitHub-flavored Markdown table.

Standard library only.
"""

import argparse
import csv
import io
import sys

DELIM_NAMES = {
    "逗号": ",",
    ",": ",",
    "comma": ",",
    "tab": "\t",
    "\t": "\t",
    "制表符": "\t",
    "semicolon": ";",
    ";": ";",
    "分号": ";",
    "pipe": "|",
    "|": "|",
    "竖线": "|",
}

ALIGN_COLONS = {
    "left": ":---",
    "right": "---:",
    "center": ":---:",
    "none": "---",
}


def resolve_delim(value):
    """Map a user-supplied delimiter spec to a single character."""
    if value is None:
        return None
    if value in DELIM_NAMES:
        return DELIM_NAMES[value]
    if len(value) == 1:
        return value
    raise argparse.ArgumentTypeError("unsupported delimiter: %r" % value)


def guess_delim(filename):
    """Guess the delimiter from a file extension."""
    if filename and filename != "-" and filename.lower().endswith((".tsv", ".tab")):
        return "\t"
    return ","


def escape_cell(text):
    """Escape pipes and flatten newlines inside a cell."""
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return text.replace("|", "\\|")


def render(rows, ncols, align, header):
    """Render parsed rows as a Markdown table string."""
    if not rows:
        return ""
    lines = []
    if header:
        head, body = rows[0], rows[1:]
        lines.append("| " + " | ".join(escape_cell(c) for c in _fit(head, ncols)) + " |")
        lines.append("| " + " | ".join([ALIGN_COLONS[align]] * ncols) + " |")
    else:
        body = rows
    for row in body:
        lines.append("| " + " | ".join(escape_cell(c) for c in _fit(row, ncols)) + " |")
    return "\n".join(lines) + "\n"


def _fit(row, ncols):
    """Pad or truncate a row to exactly ncols cells."""
    cells = list(row[:ncols])
    cells.extend([""] * (ncols - len(cells)))
    return cells


def convert(text, delim, align="left", header=True):
    """Convert raw delimited text into a Markdown table string."""
    if text == "":
        return ""
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    rows = [row for row in reader]
    rows = [r for r in rows if r]  # drop fully empty records
    if not rows:
        return ""
    ncols = max(len(r) for r in rows)
    return render(rows, ncols, align, header)


def run_self_test():
    cases = []

    # quoted field containing a comma
    cases.append((
        'a,b\n"x,y",z\n',
        ",",
        "left",
        True,
        "| a | b |\n| :--- | :--- |\n| x,y | z |\n",
    ))

    # cell containing a pipe
    cases.append((
        "h1,h2\np|q,r\n",
        ",",
        "left",
        True,
        "| h1 | h2 |\n| :--- | :--- |\n| p\\|q | r |\n",
    ))

    # no header
    cases.append((
        "1,2\n3,4\n",
        ",",
        "none",
        False,
        "| 1 | 2 |\n| 3 | 4 |\n",
    ))

    # TSV with alignment
    cases.append((
        "n\tv\n1\t2\n",
        "\t",
        "right",
        True,
        "| n | v |\n| ---: | ---: |\n| 1 | 2 |\n",
    ))

    # ragged rows get padded / truncated
    cases.append((
        "a,b,c\n1\n1,2,3,4\n",
        ",",
        "left",
        True,
        "| a | b | c |  |\n| :--- | :--- | :--- | :--- |\n"
        "| 1 |  |  |  |\n| 1 | 2 | 3 | 4 |\n",
    ))

    # empty input
    cases.append(("", ",", "left", True, ""))

    for i, (text, delim, align, header, expected) in enumerate(cases, 1):
        try:
            got = convert(text, delim, align, header)
        except Exception as exc:  # noqa: BLE001
            print("FAIL case %d: raised %r" % (i, exc))
            return 1
        if got != expected:
            print("FAIL case %d: expected %r got %r" % (i, expected, got))
            return 1
    print("PASS")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Convert CSV/TSV text to a GitHub-style Markdown table."
    )
    parser.add_argument("file", nargs="?", default="-", help="input file, or - for stdin")
    parser.add_argument("--delim", help="delimiter (comma, tab, semicolon, pipe)")
    parser.add_argument(
        "--align",
        choices=["left", "right", "center", "none"],
        default="left",
        help="column alignment (default: left)",
    )
    parser.add_argument("--no-header", action="store_true", help="treat first row as data")
    parser.add_argument("--out", help="write output to FILE instead of stdout")
    parser.add_argument("--self-test", action="store_true", help="run built-in tests")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    delim = resolve_delim(args.delim)
    if delim is None:
        delim = guess_delim(args.file)

    if args.file == "-":
        text = sys.stdin.read()
    else:
        with open(args.file, "r", encoding="utf-8", newline="") as fh:
            text = fh.read()

    output = convert(text, delim, args.align, header=not args.no_header)

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(output)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
