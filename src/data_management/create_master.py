"""
Create the master dataset from all available database imports.

Reuse the update pipeline's deduplication rules:
- match by DOI first;
- otherwise require one compatible normalized-title candidate;
- preserve records with conflicting DOIs or volumes;
- recover missing metadata from duplicate records.

The first occurrence is preserved according to DATABASE_ORDER.
"""

from datetime import datetime
from pathlib import Path
import os
import shutil
import tempfile

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

    # Read from the final master so DOIs recovered later are included.
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


def create_file_backup(file_path):
    """
    Backs up an existing output before replacing it.

    Returns the backup path, or None when the output does not exist.
    Backup failures propagate to the caller.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    backup_file = file_path.with_name(
        f"{file_path.stem}_backup_before_create_{timestamp}"
        f"{file_path.suffix}"
    )

    shutil.copy2(file_path, backup_file)

    return backup_file


def stage_excel(dataframe, destination):
    """
    Writes a temporary workbook beside its destination.

    Returns its path only after the workbook has been written.
    Failed writes remove the temporary file and propagate the error.
    """
    destination = Path(destination)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.stem}_",
        suffix=".xlsx",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)

    try:
        dataframe.to_excel(
            temporary_path,
            index=False,
        )

    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise

    return temporary_path


def main():
    """
    Rebuilds and saves the master and duplicate report.

    Empty results leave existing outputs untouched and return None.

    Both workbooks are staged and existing outputs are backed up before
    replacement. Each file is replaced atomically; the pair is not a
    single transaction.

    Processing, backup and write failures propagate to the caller.
    """
    master, duplicates = create_master()

    if master.empty:
        print(
            "\nMaster creation stopped: "
            "no valid records were found."
        )
        print(
            "Existing master and duplicate report were preserved."
        )
        return None

    temporary_master = None
    temporary_duplicates = None

    try:
        # Prepare both workbooks before replacing any existing output.
        temporary_master = stage_excel(
            master,
            MASTER_FILE,
        )

        # Write headers even when there are no duplicates.
        # This replaces a previous run's report with the current one.
        temporary_duplicates = stage_excel(
            duplicates,
            DUPLICATES_FILE,
        )

        # Backup failures stop execution before either replacement.
        master_backup = create_file_backup(
            MASTER_FILE
        )

        duplicates_backup = create_file_backup(
            DUPLICATES_FILE
        )

        os.replace(
            temporary_master,
            MASTER_FILE,
        )

        os.replace(
            temporary_duplicates,
            DUPLICATES_FILE,
        )

    finally:
        for temporary_path in (
            temporary_master,
            temporary_duplicates,
        ):
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    print("\n" + "=" * 70)
    print("MASTER DATASET CREATED")
    print("=" * 70)

    print(f"\nUnique records: {len(master)}")
    print(f"Duplicates not added: {len(duplicates)}")

    print("\nMaster file:")
    print(MASTER_FILE)

    print("\nDuplicate report:")
    print(DUPLICATES_FILE)

    if master_backup:
        print("\nPrevious master backup:")
        print(master_backup)

    if duplicates_backup:
        print("\nPrevious duplicate report backup:")
        print(duplicates_backup)

    return master


if __name__ == "__main__":
    main()