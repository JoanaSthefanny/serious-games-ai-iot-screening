"""
Update the master dataset with newly imported database records.

Existing MASTER IDs and populated bibliographic fields are preserved.
Missing metadata can be filled from duplicate records. New records are
indexed immediately in memory, so duplicates within a new batch are safe.

Supported databases:
    ieee, pubmed, acm, scopus, compendex, springer, all
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
    safe_text,
    standardize_dataframe,
    title_match_is_compatible,
)

from .assign_master_ids import assign_master_ids


# ============================================================
# OUTPUT AND METADATA FIELDS
# ============================================================

DUPLICATES_REPORT = (
    PROCESSED_DIR / "master_duplicates_not_added.xlsx"
)

FILLABLE_METADATA_FIELDS = [
    "title",
    "authors",
    "year",
    "publication",
    "volume",
    "document_type",
    "doi",
    "abstract",
    "keywords",
    "url",
]


# ============================================================
# BACKUP
# ============================================================

def create_master_backup():
    """
    Creates a timestamped backup before updating the master.
    """

    if not MASTER_FILE.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    backup_file = MASTER_FILE.parent / (
        f"master_records_backup_{timestamp}.xlsx"
    )

    shutil.copy2(MASTER_FILE, backup_file)

    return backup_file


# ============================================================
# LOAD MASTER
# ============================================================

def load_master():
    """
    Loads the existing master or creates an empty DataFrame.
    """

    if not MASTER_FILE.exists():
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    master = pd.read_excel(MASTER_FILE)

    for column in CANONICAL_COLUMNS:
        if column not in master.columns:
            master[column] = ""

    return master.reset_index(drop=True)


# ============================================================
# DUPLICATE INDICES
# ============================================================

def build_existing_indices(master):
    """
    Builds DOI lookups and title-to-candidate-position lists.
    """

    doi_index = {}
    title_index = {}

    for index, row in master.iterrows():
        doi_key = normalize_doi(row.get("doi", ""))
        title_key = normalize_title(row.get("title", ""))

        if doi_key:
            doi_index.setdefault(doi_key, index)

        if title_key:
            title_index.setdefault(title_key, []).append(index)

    return doi_index, title_index


def index_record(records, position, doi_index, title_index):
    """
    Indexes a record already present in the in-memory list.
    """

    record = records[position]

    doi_key = normalize_doi(record.get("doi", ""))
    title_key = normalize_title(record.get("title", ""))

    if doi_key:
        doi_index.setdefault(doi_key, position)

    if title_key:
        positions = title_index.setdefault(title_key, [])

        if position not in positions:
            positions.append(position)


# ============================================================
# FILL MISSING METADATA
# ============================================================

def fill_missing_metadata(existing, incoming):
    """
    Fills only empty bibliographic fields in an existing record.

    MASTER ID, source ID and original database are preserved.
    Acquisition status and sources are updated when metadata are filled.
    Returns the names of the bibliographic fields filled.
    """

    filled_fields = []

    for column in FILLABLE_METADATA_FIELDS:
        current_value = safe_text(existing.get(column, ""))
        incoming_value = safe_text(incoming.get(column, ""))

        if not current_value and incoming_value:
            existing[column] = incoming_value
            filled_fields.append(column)

    if filled_fields:
        incoming_source = safe_text(
            incoming.get("metadata_source", "")
        )

        existing_source = safe_text(
            existing.get("metadata_source", "")
        )

        if incoming_source:
            sources = [
                source.strip()
                for source in existing_source.split(" | ")
                if source.strip()
            ]

            if incoming_source not in sources:
                sources.append(incoming_source)

            existing["metadata_source"] = " | ".join(sources)

        incoming_status = safe_text(
            incoming.get("metadata_status", "")
        )

        if incoming_status and (
            "abstract" in filled_fields
            or not safe_text(existing.get("metadata_status", ""))
        ):
            existing["metadata_status"] = incoming_status

    return filled_fields


# ============================================================
# UPDATE ONE DATABASE
# ============================================================

def update_database(master, database):
    """
    Adds new records and fills missing metadata from duplicate records.

    Matching uses DOI first, then a unique compatible title candidate.
    Title matching respects DOI and volume compatibility.

    Returns:
        updated_master, duplicate_records, added_count
    """

    source_file = resolve_database_source_file(database)
    database_name = DATABASE_NAMES[database]

    print("\n" + "-" * 70)
    print(database_name)
    print("-" * 70)

    if source_file is None:
        print("No processed source file found.")
        return master, [], 0

    print(f"Source file: {source_file.name}")

    new_records = standardize_dataframe(
        read_table(source_file),
        database=database,
    )

    working_master = master.copy().reset_index(drop=True)

    for column in CANONICAL_COLUMNS:
        if column not in working_master.columns:
            working_master[column] = ""

    working_master = assign_master_ids(working_master)

    doi_index, title_index = build_existing_indices(working_master)
    records = working_master.to_dict(orient="records")

    duplicates = []
    added_count = 0
    enriched_positions = set()

    for _, row in new_records.iterrows():
        record = row.to_dict()

        doi_key = normalize_doi(record.get("doi", ""))
        title_key = normalize_title(record.get("title", ""))

        matched_position = None
        duplicate_reason = ""

        if doi_key and doi_key in doi_index:
            matched_position = doi_index[doi_key]
            duplicate_reason = "DOI"

        elif title_key and title_key in title_index:
            compatible = [
                position
                for position in title_index[title_key]
                if title_match_is_compatible(
                    records[position],
                    record,
                )
            ]

            if len(compatible) == 1:
                matched_position = compatible[0]
                duplicate_reason = "TITLE"

        if matched_position is not None:
            # Includes both original and newly added records.
            existing = records[matched_position]

            filled_fields = fill_missing_metadata(
                existing,
                record,
            )

            if filled_fields:
                enriched_positions.add(matched_position)

            # Index a DOI recovered through title matching.
            index_record(
                records,
                matched_position,
                doi_index,
                title_index,
            )

            duplicate_record = record.copy()

            duplicate_record["duplicate_reason"] = duplicate_reason
            duplicate_record["fields_filled"] = "; ".join(
                filled_fields
            )

            duplicate_record["metadata_update_source"] = (
                safe_text(record.get("metadata_source", ""))
                if filled_fields
                else ""
            )

            duplicate_record["_matched_position"] = matched_position

            duplicates.append(duplicate_record)
            continue

        # New MASTER IDs are assigned by this pipeline, not imported.
        record["master_id"] = ""

        records.append(record)
        added_count += 1

        # Index only after the record exists in the list.
        index_record(
            records,
            len(records) - 1,
            doi_index,
            title_index,
        )

    updated_master = pd.DataFrame(
        records,
        columns=CANONICAL_COLUMNS,
    )

    updated_master = assign_master_ids(updated_master)
    updated_master = updated_master[CANONICAL_COLUMNS]

    # Resolve matched IDs after new records have received IDs.
    for duplicate_record in duplicates:
        matched_position = duplicate_record.pop(
            "_matched_position"
        )

        existing = updated_master.iloc[matched_position]

        duplicate_record["matched_master_id"] = safe_text(
            existing.get("master_id", "")
        )

        duplicate_record["matched_database"] = safe_text(
            existing.get("database", "")
        )

        duplicate_record["matched_title"] = safe_text(
            existing.get("title", "")
        )

    print(f"Records read: {len(new_records)}")
    print(f"Added: {added_count}")
    print(f"Duplicate records not added: {len(duplicates)}")
    print(f"Records with metadata filled: {len(enriched_positions)}")

    return updated_master, duplicates, added_count


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

    print("\nSelect a database:")
    print("\nIEEE Xplore                     [1]")
    print("PubMed                          [2]")
    print("ACM Digital Library             [3]")
    print("Scopus                          [4]")
    print("Engineering Village / Compendex [5]")
    print("Springer Link                   [6]")
    print("All databases                   [7]")
    print("Cancel                          [0]")

    choice = input("\nEnter an option: ").strip()

    if choice == "0":
        return None

    return options.get(choice)


# ============================================================
# MAIN
# ============================================================

def main(database=None):
    """
    Updates master_records.xlsx for one database or all databases.

    Returns the updated DataFrame only after the master and any
    duplicate report have been saved successfully.

    Returns None on cancellation.

    Read, backup and write failures propagate to the caller.
    """

    print("=" * 70)
    print("UPDATE MASTER DATASET")
    print("=" * 70)

    if database is None:
        database = choose_database()

        if database is None:
            print("\nOperation cancelled.")
            return None

    database = str(database).strip().lower()

    if database != "all" and database not in DATABASE_ORDER:
        raise ValueError(
            f"Unsupported database: {database}"
        )

    master = load_master()
    master_before = len(master)
    backup = create_master_backup()

    databases = (
        DATABASE_ORDER
        if database == "all"
        else [database]
    )

    all_duplicates = []
    total_added = 0

    for database_slug in databases:
        master, duplicates, added = update_database(
            master,
            database_slug,
        )

        all_duplicates.extend(duplicates)
        total_added += added

    MASTER_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Any write failure raises before the success return.
    master.to_excel(
        MASTER_FILE,
        index=False,
    )

    if all_duplicates:
        pd.DataFrame(all_duplicates).to_excel(
            DUPLICATES_REPORT,
            index=False,
        )

    print("\n" + "=" * 70)
    print("MASTER DATASET UPDATED")
    print("=" * 70)
    print(f"\nMaster records before: {master_before}")
    print(f"Records added: {total_added}")
    print(f"Duplicates not added: {len(all_duplicates)}")
    print(f"Master records after: {len(master)}")
    print("\nMaster file:")
    print(MASTER_FILE)

    if backup:
        print("\nBackup:")
        print(backup)

    if all_duplicates:
        print("\nDuplicate report:")
        print(DUPLICATES_REPORT)

    # Return only after all required writes have succeeded.
    return master


if __name__ == "__main__":
    main()