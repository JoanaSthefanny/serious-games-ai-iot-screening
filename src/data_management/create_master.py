"""
Create the master dataset from all available database imports.

Reuse the update pipeline's deduplication rules:
- match by DOI first;
- otherwise require one compatible normalized-title candidate;
- preserve records with conflicting DOIs or volumes;
- recover missing metadata from duplicate records.

The first occurrence is preserved according to DATABASE_ORDER.
"""

import pandas as pd

from . import (
    CANONICAL_COLUMNS,
    DATABASE_ORDER,
    MASTER_FILE,
    PROCESSED_DIR,
    safe_text,
)
from .update_master import update_database


DUPLICATES_FILE = PROCESSED_DIR / "master_duplicates_not_added.xlsx"

DUPLICATE_COLUMNS = CANONICAL_COLUMNS + [
    "duplicate_reason",
    "fields_filled",
    "metadata_update_source",
    "matched_master_id",
    "matched_database",
    "matched_title",
    "matched_doi",
]


def create_master():
    """
    Builds a new master from processed imports, without writing files.

    Returns:
        master_dataframe, duplicates_dataframe

    This function starts from an empty master. Use update_master.main()
    to update an existing master while preserving its existing IDs.
    """
    master = pd.DataFrame(columns=CANONICAL_COLUMNS)
    duplicate_records = []

    print("=" * 70)
    print("CREATE MASTER DATASET")
    print("=" * 70)

    for database in DATABASE_ORDER:
        master, duplicates, _ = update_database(master, database)
        duplicate_records.extend(duplicates)

    master = master[CANONICAL_COLUMNS].reset_index(drop=True)

    # Retain the original report's matched_doi field. Read from the
    # final master so DOIs recovered in later databases are included.
    matched_dois = {
        safe_text(record["master_id"]): safe_text(record["doi"])
        for record in master.to_dict(orient="records")
    }

    for duplicate in duplicate_records:
        duplicate["matched_doi"] = matched_dois.get(
            safe_text(duplicate.get("matched_master_id", "")),
            "",
        )

    duplicates = pd.DataFrame(
        duplicate_records,
        columns=DUPLICATE_COLUMNS,
    )

    return master, duplicates


def main():
    master, duplicates = create_master()

    MASTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    master.to_excel(MASTER_FILE, index=False)

    # Always write the report, including headers when there are no
    # duplicates, so a previous run's report cannot remain active.
    duplicates.to_excel(DUPLICATES_FILE, index=False)

    print("\n" + "=" * 70)
    print("MASTER DATASET CREATED")
    print("=" * 70)
    print(f"\nUnique records: {len(master)}")
    print(f"Duplicates not added: {len(duplicates)}")
    print("\nMaster file:")
    print(MASTER_FILE)
    print("\nDuplicate report:")
    print(DUPLICATES_FILE)

    return master


if __name__ == "__main__":
    main()