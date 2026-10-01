"""
Update the master dataset with newly imported database records.

This module replaces database-specific master update scripts.

Supported databases:

- ieee
- pubmed
- acm
- scopus
- compendex
- springer
- all
"""

from datetime import datetime
from pathlib import Path
import shutil

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
# REPORT FILE
# ============================================================

DUPLICATES_REPORT = (
    PROCESSED_DIR
    / "master_duplicates_not_added.xlsx"
)


# ============================================================
# BACKUP
# ============================================================

def create_master_backup():
    """
    Creates a timestamped backup before updating the master dataset.
    """

    if not MASTER_FILE.exists():

        return None

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_file = (
        MASTER_FILE.parent
        / (
            "master_records_backup_"
            f"{timestamp}.xlsx"
        )
    )

    shutil.copy2(
        MASTER_FILE,
        backup_file,
    )

    return backup_file


# ============================================================
# LOAD MASTER
# ============================================================

def load_master():
    """
    Loads the existing master dataset or creates an empty one.
    """

    if not MASTER_FILE.exists():

        return pd.DataFrame(
            columns=CANONICAL_COLUMNS
        )

    master = pd.read_excel(
        MASTER_FILE
    )

    for column in CANONICAL_COLUMNS:

        if column not in master.columns:

            master[
                column
            ] = ""

    return master


# ============================================================
# DUPLICATE INDICES
# ============================================================

def build_existing_indices(
    master,
):
    """
    Builds DOI and title lookup dictionaries.
    """

    doi_index = {}
    title_index = {}

    for index, row in master.iterrows():

        doi_key = normalize_doi(
            row.get(
                "doi",
                "",
            )
        )

        title_key = normalize_title(
            row.get(
                "title",
                "",
            )
        )

        if (
            doi_key
            and doi_key not in doi_index
        ):

            doi_index[
                doi_key
            ] = index

        if (
            title_key
            and title_key not in title_index
        ):

            title_index[
                title_key
            ] = index

    return (
        doi_index,
        title_index,
    )


# ============================================================
# UPDATE ONE DATABASE
# ============================================================

def update_database(
    master,
    database,
):
    """
    Adds new records from one database to the master dataset.

    Existing records are detected by DOI first and normalized title
    second.

    Returns
    -------
    tuple
        updated_master,
        duplicate_records,
        added_count
    """

    source_file = resolve_database_source_file(
        database
    )

    database_name = DATABASE_NAMES[
        database
    ]

    print(
        "\n" + "-" * 70
    )

    print(
        database_name
    )

    print(
        "-" * 70
    )

    if source_file is None:

        print(
            "No processed source file found."
        )

        return (
            master,
            [],
            0,
        )

    print(
        f"Source file: "
        f"{source_file.name}"
    )

    raw = read_table(
        source_file
    )

    new_records = standardize_dataframe(
        raw,
        database=database,
    )

    (
        doi_index,
        title_index,
    ) = build_existing_indices(
        master
    )

    duplicates = []
    additions = []

    for _, row in new_records.iterrows():

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

        matched_index = None
        duplicate_reason = ""

        # ----------------------------------------------------
        # DOI DUPLICATE
        # ----------------------------------------------------

        if (
            doi_key
            and doi_key in doi_index
        ):

            matched_index = doi_index[
                doi_key
            ]

            duplicate_reason = "DOI"

        # ----------------------------------------------------
        # TITLE DUPLICATE
        # ----------------------------------------------------

        elif (
            title_key
            and title_key in title_index
        ):

            matched_index = title_index[
                title_key
            ]

            duplicate_reason = "TITLE"

        # ----------------------------------------------------
        # DUPLICATE
        # ----------------------------------------------------

        if matched_index is not None:

            existing = master.loc[
                matched_index
            ]

            duplicate_record = (
                record.copy()
            )

            duplicate_record[
                "duplicate_reason"
            ] = duplicate_reason

            duplicate_record[
                "matched_master_id"
            ] = existing.get(
                "master_id",
                "",
            )

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

            duplicates.append(
                duplicate_record
            )

            continue

        # ----------------------------------------------------
        # NEW RECORD
        # ----------------------------------------------------

        additions.append(
            record
        )

        future_index = (
            len(master)
            + len(additions)
            - 1
        )

        if doi_key:

            doi_index[
                doi_key
            ] = future_index

        if title_key:

            title_index[
                title_key
            ] = future_index

    # ========================================================
    # APPEND
    # ========================================================

    if additions:

        additions_df = pd.DataFrame(
            additions
        )

        master = pd.concat(
            [
                master,
                additions_df,
            ],
            ignore_index=True,
        )

    master = assign_master_ids(
        master
    )

    for column in CANONICAL_COLUMNS:

        if column not in master.columns:

            master[
                column
            ] = ""

    master = master[
        CANONICAL_COLUMNS
    ]

    print(
        f"Records read: "
        f"{len(new_records)}"
    )

    print(
        f"Added: "
        f"{len(additions)}"
    )

    print(
        f"Duplicates skipped: "
        f"{len(duplicates)}"
    )

    return (
        master,
        duplicates,
        len(additions),
    )


# ============================================================
# INTERACTIVE DATABASE SELECTION
# ============================================================

def choose_database():
    """
    Used only when this module is executed directly.
    """

    options = {
        "1": "ieee",
        "2": "pubmed",
        "3": "acm",
        "4": "scopus",
        "5": "compendex",
        "6": "springer",
        "7": "all",
    }

    print(
        "\nSelect a database:"
    )

    print(
        "\nIEEE Xplore                     [1]"
    )

    print(
        "PubMed                          [2]"
    )

    print(
        "ACM Digital Library             [3]"
    )

    print(
        "Scopus                          [4]"
    )

    print(
        "Engineering Village / Compendex [5]"
    )

    print(
        "Springer Link                   [6]"
    )

    print(
        "All databases                   [7]"
    )

    print(
        "Cancel                          [0]"
    )

    choice = input(
        "\nEnter an option: "
    ).strip()

    if choice == "0":

        return None

    return options.get(
        choice
    )


# ============================================================
# MAIN
# ============================================================

def main(
    database=None,
):
    """
    Updates master_records.xlsx.

    Parameters
    ----------
    database:
        One of:
        ieee, pubmed, acm, scopus, compendex, springer, all.
    """

    print(
        "=" * 70
    )

    print(
        "UPDATE MASTER DATASET"
    )

    print(
        "=" * 70
    )

    if database is None:

        database = choose_database()

        if database is None:

            print(
                "\nOperation cancelled."
            )

            return

    database = str(
        database
    ).strip().lower()

    if (
        database != "all"
        and database not in DATABASE_ORDER
    ):

        raise ValueError(
            f"Unsupported database: {database}"
        )

    master = load_master()

    master_before = len(
        master
    )

    backup = create_master_backup()

    databases = (
        DATABASE_ORDER
        if database == "all"
        else [database]
    )

    all_duplicates = []
    total_added = 0

    for database_slug in databases:

        (
            master,
            duplicates,
            added,
        ) = update_database(
            master,
            database_slug,
        )

        all_duplicates.extend(
            duplicates
        )

        total_added += added

    # ========================================================
    # SAVE MASTER
    # ========================================================

    MASTER_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    master.to_excel(
        MASTER_FILE,
        index=False,
    )

    # ========================================================
    # SAVE DUPLICATE REPORT
    # ========================================================

    if all_duplicates:

        duplicates_df = pd.DataFrame(
            all_duplicates
        )

        duplicates_df.to_excel(
            DUPLICATES_REPORT,
            index=False,
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "MASTER DATASET UPDATED"
    )

    print(
        "=" * 70
    )

    print(
        f"\nMaster records before: "
        f"{master_before}"
    )

    print(
        f"Records added: "
        f"{total_added}"
    )

    print(
        f"Duplicates not added: "
        f"{len(all_duplicates)}"
    )

    print(
        f"Master records after: "
        f"{len(master)}"
    )

    print(
        "\nMaster file:"
    )

    print(
        MASTER_FILE
    )

    if backup:

        print(
            "\nBackup:"
        )

        print(
            backup
        )

    if all_duplicates:

        print(
            "\nDuplicate report:"
        )

        print(
            DUPLICATES_REPORT
        )


if __name__ == "__main__":
    main()