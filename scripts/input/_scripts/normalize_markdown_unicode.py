#!/usr/bin/env python3

import argparse
import pathlib
import sys
import unicodedata


REPLACEMENTS = {
    "\u2011": "-",  # non-breaking hyphen
    "\u2010": "-",  # hyphen
    "\u2212": "-",  # minus sign
    "\u00a0": " ",  # non-breaking space
    "\u202f": " ",  # narrow no-break space
    "\ufeff": "",  # BOM / zero width no-break space
    "\u200b": "",  # zero width space
    "\u00ad": "",  # soft hyphen
}


def normalize_text(text: str) -> tuple[str, int]:
    normalized = unicodedata.normalize("NFC", text)
    changes = 0
    for src, dst in REPLACEMENTS.items():
        if src in normalized:
            changes += normalized.count(src)
            normalized = normalized.replace(src, dst)
    return normalized, changes


def iter_markdown_files(paths: list[str]) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for p in paths:
        path = pathlib.Path(p)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
        else:
            files.append(path)
    # de-dupe while preserving order
    seen: set[pathlib.Path] = set()
    unique: list[pathlib.Path] = []
    for f in files:
        rf = f.resolve()
        if rf in seen:
            continue
        seen.add(rf)
        unique.append(f)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize Markdown typography to avoid noisy diffs (e.g., non-breaking hyphen U+2011)."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Files and/or directories to process (default: current directory).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any file would be changed.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write changes back to files.",
    )
    args = parser.parse_args()

    if args.check and args.write:
        print("Use either --check or --write (not both).", file=sys.stderr)
        return 2

    files = iter_markdown_files(args.paths)
    changed_files: list[str] = []
    total_changes = 0

    for file_path in files:
        if not file_path.exists() or not file_path.is_file():
            continue

        original = file_path.read_text(encoding="utf-8")
        normalized, changes = normalize_text(original)

        if normalized != original:
            changed_files.append(str(file_path))
            total_changes += changes
            if args.write:
                with file_path.open("w", encoding="utf-8", newline="\n") as handle:
                    handle.write(normalized)

    if args.check:
        if changed_files:
            print("Would normalize:")
            for f in changed_files:
                print(f"- {f}")
            print(f"Total replacements/removals: {total_changes}")
            return 1
        return 0

    if args.write:
        if changed_files:
            print("Normalized:")
            for f in changed_files:
                print(f"- {f}")
            print(f"Total replacements/removals: {total_changes}")
        return 0

    # default behavior: check
    if changed_files:
        print("Found files that need normalization (run with --write):")
        for f in changed_files:
            print(f"- {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
