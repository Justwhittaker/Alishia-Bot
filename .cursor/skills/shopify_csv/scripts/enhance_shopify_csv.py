#!/usr/bin/env python3
"""Enhance an existing Shopify product-import CSV in place.

Use when the input is already Shopify-formatted (e.g. from /shopify_scrape).
Preserves all columns and image-only rows; updates product rows only unless
--all-rows is set for Tags/Status/Published.

Shopify CSV import cannot assign manual collections directly — collection
names are written to Tags so Justin can create automated collections that
match those tags after import.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


def parse_tags(raw: str) -> list[str]:
    if not raw or not raw.strip():
        return []
    parts = re.split(r"\s*,\s*", raw.strip())
    return [p for p in parts if p]


def join_tags(tags: list[str]) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for tag in tags:
        key = tag.strip()
        if not key:
            continue
        lower = key.lower()
        if lower in seen:
            continue
        seen.add(lower)
        ordered.append(key)
    return ", ".join(ordered)


def surname_letter(title: str) -> str:
    """First alphabetic character of the surname title (A–Z)."""
    for ch in title.strip():
        if ch.isalpha():
            return ch.upper()
    return "Other"


def is_product_row(row: dict[str, str]) -> bool:
    return bool((row.get("Title") or "").strip())


def verify_unlisted(path: Path) -> None:
    bad: list[tuple[int, str, str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for i, row in enumerate(csv.DictReader(handle), start=2):
            if (row.get("Status") or "").strip().lower() != "unlisted":
                bad.append((i, "Status", row.get("Status", "")))
            if (row.get("Published") or "").strip().lower() != "false":
                bad.append((i, "Published", row.get("Published", "")))
    if bad:
        sample = bad[:10]
        raise SystemExit(f"UNLISTED CHECK FAILED: {sample}")


def enhance(
    input_csv: Path,
    output_csv: Path,
    *,
    fixed_price: str | None,
    collections: list[str],
    alpha_collection_prefix: str,
    force_status: bool,
) -> dict[str, int]:
    with input_csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"No headers in {input_csv}")
        headers = list(reader.fieldnames)
        rows = [dict(row) for row in reader]

    stats = {
        "input_rows": len(rows),
        "products": 0,
        "prices_updated": 0,
        "tags_updated": 0,
        "alpha_letters": 0,
    }
    letters_seen: set[str] = set()

    for row in rows:
        if force_status:
            row["Status"] = "unlisted"
            row["Published"] = "false"

        if not is_product_row(row):
            continue

        stats["products"] += 1
        title = (row.get("Title") or "").strip()

        extra_tags = list(collections)
        if alpha_collection_prefix:
            letter = surname_letter(title)
            letters_seen.add(letter)
            extra_tags.append(f"{alpha_collection_prefix}{letter}")

        existing = parse_tags(row.get("Tags") or "")
        merged = join_tags(existing + extra_tags)
        if merged != (row.get("Tags") or "").strip():
            row["Tags"] = merged
            stats["tags_updated"] += 1

        if fixed_price is not None:
            row["Variant Price"] = fixed_price
            stats["prices_updated"] += 1

    stats["alpha_letters"] = len(letters_seen)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enhance Shopify CSV: collections (as Tags), price, unlisted guard."
    )
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument(
        "--fixed-price",
        default=None,
        help="Set Variant Price on every product row (e.g. 12.45)",
    )
    parser.add_argument(
        "--collection",
        action="append",
        default=[],
        dest="collections",
        help="Collection name added as Tag (repeatable)",
    )
    parser.add_argument(
        "--alpha-collection-prefix",
        default="Surname ",
        help='Prefix for A–Z tag per product Title (default: "Surname ")',
    )
    parser.add_argument(
        "--no-alpha-collection",
        action="store_true",
        help="Skip alphabetical surname collection tag",
    )
    parser.add_argument(
        "--verify-unlisted",
        action="store_true",
        help="Exit non-zero if any row is not unlisted/false",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.input_csv.is_file():
        print(f"Input not found: {args.input_csv}", file=sys.stderr)
        return 1

    alpha_prefix = "" if args.no_alpha_collection else args.alpha_collection_prefix

    stats = enhance(
        args.input_csv,
        args.output,
        fixed_price=args.fixed_price,
        collections=args.collections,
        alpha_collection_prefix=alpha_prefix,
        force_status=True,
    )

    print(f"Wrote {args.output}")
    print(f"Rows: {stats['input_rows']} | Products: {stats['products']}")
    print(f"Tags updated: {stats['tags_updated']} | Prices set: {stats['prices_updated']}")
    if alpha_prefix:
        print(f"Alphabetical collection letters: {stats['alpha_letters']}")
    if args.collections:
        print("Collection tags added:")
        for name in args.collections:
            print(f"  - {name}")

    if args.verify_unlisted:
        verify_unlisted(args.output)
        print("OK: all rows Status=unlisted and Published=false")

    print("Status=unlisted and Published=false enforced on all rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
