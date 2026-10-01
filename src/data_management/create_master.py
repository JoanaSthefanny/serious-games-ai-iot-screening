"""
Create the master dataset from all available database imports.

Duplicate detection is performed using:

1. DOI, when available;
2. normalized title otherwise.

The first occurrence is preserved according to DATABASE_ORDER.
"""

from pathlib import Path

import pandas as pd

from . import (
    CANONICAL_COLUMNS,
    DATABASE_NAMES,
    DATABASE_ORDER,
    MASTER_FILE,
    PROCESSED_DIR,
    normalize_doi,
    normalize_title,
    read_table,
    resolve_database_source_file,
    standardize_dataframe,
)

from .assign_master_ids import (
    assign_master_ids,
)


# ============================================================
# OUTPUT FILES
# ============================================================

DUPLICATES_FILE = (
    PROCESSED_DIR
    / "master_duplicates_not_added.xlsx"
)


# ============================================================
# CREATE MASTER
# ============================================================

def create_master():
    """
    Creates a new master dataset from all available database files.

    Returns
    -------
    tuple
        master_dataframe, duplicates_dataframe
    """

    master_records = []
    duplicate_records = []

    doi_index = {}
    title_index = {}

    print(
        "=" * 70
    )

    print(
        "CREATE MASTER DATASET"
    )

    print(
        "=" * 70
    )

    for database in DATABASE_ORDER:

        source_file = resolve_database_source_file(
            database
        )

        database_name = DATABASE_NAMES[
            database
        ]

        print(
            f"\n{database_name}"
        )

        if source_file is None:

            print(
                "  No processed source file found."
            )

            continue

        print(
            f"  Source: {source_file.name}"
        )

        raw = read_table(
            source_file
        )

        records = standardize_dataframe(
            raw,
            database=database,
        )

        added = 0
        duplicates = 0

        for _, row in records.iterrows():

            record = row.to_dict()

            doi_key = normalize_doi(
                record.get(
                    "doi",
                    "",
                )
            )

            title_key = normalize_title(
                record.get(
                    "title",
                    "",
                )
            )

            duplicate_index = None
            duplicate_reason = ""

            # ------------------------------------------------
            # DOI DUPLICATE
            # ------------------------------------------------

            if (
                doi_key
                and doi_key in doi_index
            ):

                duplicate_index = doi_index[
                    doi_key
                ]

                duplicate_reason = "DOI"

            # ------------------------------------------------
            # TITLE DUPLICATE
            # ------------------------------------------------

            elif (
                title_key
                and title_key in title_index
            ):

                duplicate_index = title_index[
                    title_key
                ]

                duplicate_reason = "TITLE"

            # ------------------------------------------------
            # DUPLICATE FOUND
            # ------------------------------------------------

            if duplicate_index is not None:

                duplicates += 1

                existing = master_records[
                    duplicate_index
                ]

                duplicate_record = (
                    record.copy()
                )

                duplicate_record[
                    "duplicate_reason"
                ] = duplicate_reason

                duplicate_record[
                    "matched_database"
                ] = existing.get(
                    "database",
                    "",
                )

                duplicate_record[
                    "matched_title"
                ] = existing.get(
                    "title",
                    "",
                )

                duplicate_record[
                    "matched_doi"
                ] = existing.get(
                    "doi",
                    "",
                )

                duplicate_records.append(
                    duplicate_record
                )

                continue

            # ------------------------------------------------
            # NEW RECORD
            # ------------------------------------------------

            master_index = len(
                master_records
            )

            master_records.append(
                record
            )

            if doi_key:

                doi_index[
                    doi_key
                ] = master_index

            if title_key:

                title_index[
                    title_key
                ] = master_index

            added += 1

        print(
            f"  Records read: {len(records)}"
        )

        print(
            f"  Added: {added}"
        )

        print(
            f"  Duplicates skipped: {duplicates}"
        )

    # ========================================================
    # BUILD MASTER
    # ========================================================

    if master_records:

        master = pd.DataFrame(
            master_records
        )

    else:

        master = pd.DataFrame(
            columns=CANONICAL_COLUMNS
        )

    master = assign_master_ids(
        master
    )

    # Reorder canonical columns.
    for column in CANONICAL_COLUMNS:

        if column not in master.columns:

            master[
                column
            ] = ""

    master = master[
        CANONICAL_COLUMNS
    ]

    duplicates_df = pd.DataFrame(
        duplicate_records
    )

    return (
        master,
        duplicates_df,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    master, duplicates = create_master()

    MASTER_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    master.to_excel(
        MASTER_FILE,
        index=False,
    )

    if not duplicates.empty:

        duplicates.to_excel(
            DUPLICATES_FILE,
            index=False,
        )

    print(
        "\n" + "=" * 70
    )

    print(
        "MASTER DATASET CREATED"
    )

    print(
        "=" * 70
    )

    print(
        f"\nUnique records: "
        f"{len(master)}"
    )

    print(
        f"Duplicates not added: "
        f"{len(duplicates)}"
    )

    print(
        "\nMaster file:"
    )

    print(
        MASTER_FILE
    )

    if not duplicates.empty:

        print(
            "\nDuplicate report:"
        )

        print(
            DUPLICATES_FILE
        )


if __name__ == "__main__":
    main()