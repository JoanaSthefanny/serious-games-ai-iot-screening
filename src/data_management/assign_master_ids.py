"""
Assign persistent MASTER IDs to records.

Existing IDs are preserved. Only records without a MASTER ID receive
a new sequential identifier.
"""

from datetime import datetime
from pathlib import Path
import re
import shutil

import pandas as pd

from . import (
    MASTER_FILE,
    safe_text,
)


# ============================================================
# MASTER ID FORMAT
# ============================================================

MASTER_ID_PREFIX = "MASTER"
MASTER_ID_MIN_DIGITS = 4


# ============================================================
# ID UTILITIES
# ============================================================

def extract_master_number(
    master_id,
):
    """
    Extracts the numeric portion of IDs such as MASTER-0042.
    """

    master_id = safe_text(
        master_id
    ).upper()

    match = re.fullmatch(
        r"MASTER-(\d+)",
        master_id,
    )

    if not match:

        return None

    return int(
        match.group(1)
    )


def format_master_id(
    number,
):
    """
    Formats an integer as a persistent MASTER identifier.
    """

    digits = max(
        MASTER_ID_MIN_DIGITS,
        len(str(number)),
    )

    return (
        f"{MASTER_ID_PREFIX}-"
        f"{number:0{digits}d}"
    )


# ============================================================
# ASSIGN IDS
# ============================================================

def assign_master_ids(
    dataframe,
):
    """
    Assigns IDs only to records that do not already have one.

    Parameters
    ----------
    dataframe:
        Master DataFrame.

    Returns
    -------
    pandas.DataFrame
        Updated DataFrame.
    """

    df = dataframe.copy()

    if "master_id" not in df.columns:

        df.insert(
            0,
            "master_id",
            "",
        )

    existing_numbers = []

    for value in df[
        "master_id"
    ]:

        number = extract_master_number(
            value
        )

        if number is not None:

            existing_numbers.append(
                number
            )

    next_number = (
        max(existing_numbers) + 1
        if existing_numbers
        else 1
    )

    used_ids = {
        safe_text(value)
        for value in df["master_id"]
        if safe_text(value)
    }

    for index in df.index:

        current_id = safe_text(
            df.at[
                index,
                "master_id",
            ]
        )

        if current_id:

            continue

        while True:

            new_id = format_master_id(
                next_number
            )

            next_number += 1

            if new_id not in used_ids:

                break

        df.at[
            index,
            "master_id",
        ] = new_id

        used_ids.add(
            new_id
        )

    return df


# ============================================================
# VALIDATION
# ============================================================

def validate_master_ids(
    dataframe,
):
    """
    Returns duplicated or missing MASTER IDs.
    """

    df = dataframe.copy()

    if "master_id" not in df.columns:

        return {
            "missing": len(df),
            "duplicates": [],
        }

    values = (
        df["master_id"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    missing = int(
        (
            values == ""
        ).sum()
    )

    duplicated_values = (
        values[
            (
                values != ""
            )
            &
            values.duplicated(
                keep=False
            )
        ]
        .unique()
        .tolist()
    )

    return {
        "missing": missing,
        "duplicates": duplicated_values,
    }


# ============================================================
# FILE BACKUP
# ============================================================

def create_backup(
    file_path,
):
    """
    Creates a timestamped backup before overwriting a master file.
    """

    file_path = Path(
        file_path
    )

    if not file_path.exists():

        return None

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_path = (
        file_path.parent
        / (
            f"{file_path.stem}"
            f"_backup_before_ids_"
            f"{timestamp}"
            f"{file_path.suffix}"
        )
    )

    shutil.copy2(
        file_path,
        backup_path,
    )

    return backup_path


# ============================================================
# MAIN
# ============================================================

def main(
    file_path=None,
):
    """
    Assigns missing MASTER IDs in master_records.xlsx.
    """

    target_file = (
        Path(file_path)
        if file_path
        else MASTER_FILE
    )

    print(
        "=" * 70
    )

    print(
        "ASSIGN MASTER IDS"
    )

    print(
        "=" * 70
    )

    if not target_file.exists():

        print(
            "\nMaster dataset not found:"
        )

        print(
            target_file
        )

        return

    dataframe = pd.read_excel(
        target_file
    )

    before = validate_master_ids(
        dataframe
    )

    backup = create_backup(
        target_file
    )

    updated = assign_master_ids(
        dataframe
    )

    after = validate_master_ids(
        updated
    )

    updated.to_excel(
        target_file,
        index=False,
    )

    print(
        f"\nRecords: {len(updated)}"
    )

    print(
        f"Missing IDs before: "
        f"{before['missing']}"
    )

    print(
        f"Missing IDs after: "
        f"{after['missing']}"
    )

    print(
        f"Duplicated IDs: "
        f"{len(after['duplicates'])}"
    )

    print(
        "\nMaster updated:"
    )

    print(
        target_file
    )

    if backup:

        print(
            "\nBackup:"
        )

        print(
            backup
        )


if __name__ == "__main__":
    main()