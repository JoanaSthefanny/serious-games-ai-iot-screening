"""
Enrich Springer metadata using the Springer Nature Meta API.

Primary purpose:
    retrieve missing abstracts for Springer records.

Current imports are merged with the enrichment checkpoint,
preserving previously recovered metadata and API status columns.

Environment variable required:
    SPRINGER_API_KEY
"""

from html import unescape
from pathlib import Path
import os
import re
import tempfile
import time

import pandas as pd
import requests
from dotenv import load_dotenv

from . import (
    PROJECT_ROOT,
    PROCESSED_DIR,
    SOURCE_FILE_CANDIDATES,
    normalize_doi,
    normalize_title,
    safe_text,
    standardize_dataframe,
)


# ============================================================
# API CONFIGURATION
# ============================================================

SPRINGER_API_URL = (
    "https://api.springernature.com/meta/v2/json"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "springer_records_enriched.xlsx"
)

# Springer accounts may have daily request limits.
# Keeping a small safety margin avoids exhausting the full quota.
MAX_CALLS_PER_RUN = 470

REQUEST_TIMEOUT = 30

REQUEST_DELAY_SECONDS = 0.7

MAX_RETRIES = 3


FINAL_STATUSES = {
    "FOUND",
    "NOT_FOUND",
    "ALREADY_HAS_ABSTRACT",
    "NO_DOI",
}


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_html(value):
    """
    Removes basic HTML tags from API abstracts.
    """

    value = safe_text(value)

    if not value:
        return ""

    value = unescape(value)

    value = re.sub(
        r"<[^>]+>",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def extract_keywords(record):
    """
    Extracts keywords from possible Springer API representations.
    """

    for field in [
        "keyword",
        "keywords",
    ]:

        value = record.get(field)

        if not value:
            continue

        if isinstance(value, list):

            cleaned = [
                safe_text(item)
                for item in value
                if safe_text(item)
            ]

            return "; ".join(cleaned)

        return safe_text(value)

    return ""


# ============================================================
# API REQUEST
# ============================================================

def request_springer_metadata(
    api_key,
    doi,
):
    """
    Retrieves one Springer record using DOI.

    Returns
    -------
    tuple:
        status, record, error_message
    """

    normalized_doi = normalize_doi(doi)

    if not normalized_doi:

        return (
            "NO_DOI",
            None,
            "",
        )

    parameters = {
        "q": f"doi:{normalized_doi}",
        "api_key": api_key,
        "s": 1,
        "p": 1,
    }

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            response = requests.get(
                SPRINGER_API_URL,
                params=parameters,
                timeout=REQUEST_TIMEOUT,
            )

            # -----------------------------------------------
            # NOT FOUND
            # -----------------------------------------------

            if response.status_code == 404:

                return (
                    "NOT_FOUND",
                    None,
                    "HTTP 404",
                )

            # -----------------------------------------------
            # RATE LIMIT
            # -----------------------------------------------

            if response.status_code == 429:

                return (
                    "RATE_LIMIT",
                    None,
                    "HTTP 429 - rate limit reached",
                )

            # -----------------------------------------------
            # AUTHENTICATION / QUOTA
            # -----------------------------------------------

            if response.status_code in {
                401,
                403,
            }:

                return (
                    "AUTH_OR_QUOTA_ERROR",
                    None,
                    f"HTTP {response.status_code}",
                )

            response.raise_for_status()

            payload = response.json()

            records = payload.get(
                "records",
                [],
            )

            if not records:

                return (
                    "NOT_FOUND",
                    None,
                    "",
                )

            return (
                "FOUND",
                records[0],
                "",
            )

        except requests.RequestException as error:

            if attempt >= MAX_RETRIES:

                return (
                    "ERROR",
                    None,
                    str(error),
                )

            wait_seconds = 2 ** attempt

            time.sleep(wait_seconds)

        except ValueError as error:

            return (
                "ERROR",
                None,
                f"Invalid JSON response: {error}",
            )

    return (
        "ERROR",
        None,
        "Unknown request error.",
    )


# ============================================================
# LOAD INPUT / CHECKPOINT
# ============================================================

def resolve_springer_import_file():
    """
    Finds the processed import, excluding enriched checkpoint files.
    """

    enriched_names = {
        OUTPUT_FILE.name,
        "springer_records_enriched.xlsx",
        "springer_registros_enriquecidos.xlsx",
    }

    for filename in SOURCE_FILE_CANDIDATES["springer"]:

        if filename in enriched_names:
            continue

        candidate = PROCESSED_DIR / filename

        if candidate.exists():
            return candidate

    return None


def merge_springer_records(
    checkpoint,
    imported,
):
    """
    Preserves checkpoint records and appends newly imported records.

    Match by DOI first, then normalized title when the DOIs do not
    conflict. Existing values are preserved; missing fields are filled
    from the current import. API-specific checkpoint columns are retained.
    """

    records = checkpoint.to_dict(
        orient="records"
    )

    doi_index = {}
    title_index = {}

    def index_record(position):

        record = records[position]

        doi = normalize_doi(
            record.get("doi", "")
        )

        title = normalize_title(
            record.get("title", "")
        )

        if doi:
            doi_index.setdefault(
                doi,
                position,
            )

        if title:

            positions = title_index.setdefault(
                title,
                [],
            )

            if position not in positions:
                positions.append(position)

    for position in range(len(records)):
        index_record(position)

    for _, row in imported.iterrows():

        incoming = row.to_dict()

        incoming_doi = normalize_doi(
            incoming.get("doi", "")
        )

        incoming_title = normalize_title(
            incoming.get("title", "")
        )

        matched_position = None

        # ----------------------------------------------------
        # MATCH BY DOI
        # ----------------------------------------------------

        if incoming_doi:
            matched_position = doi_index.get(
                incoming_doi
            )

        # ----------------------------------------------------
        # MATCH BY TITLE WITHOUT CONFLICTING DOIS
        # ----------------------------------------------------

        if (
            matched_position is None
            and incoming_title
        ):

            for position in title_index.get(
                incoming_title,
                [],
            ):

                existing_doi = normalize_doi(
                    records[position].get(
                        "doi",
                        "",
                    )
                )

                # Different non-empty DOIs remain separate records.
                if (
                    incoming_doi
                    and existing_doi
                    and incoming_doi != existing_doi
                ):
                    continue

                matched_position = position
                break

        # ----------------------------------------------------
        # NEW RECORD
        # ----------------------------------------------------

        if matched_position is None:

            records.append(
                incoming.copy()
            )

            index_record(
                len(records) - 1
            )

            continue

        # ----------------------------------------------------
        # EXISTING RECORD
        # ----------------------------------------------------

        existing = records[
            matched_position
        ]

        previous_doi = normalize_doi(
            existing.get("doi", "")
        )

        previous_status = safe_text(
            existing.get(
                "springer_api_status",
                "",
            )
        )

        # Preserve existing values and fill only missing fields.
        for column, value in incoming.items():

            if column.startswith("springer_api_"):
                continue

            if (
                not safe_text(
                    existing.get(column, "")
                )
                and safe_text(value)
            ):

                existing[column] = value

        # A record previously lacking a DOI can now be queried.
        if (
            previous_status == "NO_DOI"
            and not previous_doi
            and normalize_doi(
                existing.get("doi", "")
            )
        ):

            existing[
                "springer_api_status"
            ] = ""

            existing[
                "springer_api_error"
            ] = ""

        index_record(
            matched_position
        )

    # Preserve checkpoint columns, including API-specific fields.
    columns = list(
        checkpoint.columns
    )

    columns.extend(
        column
        for column in imported.columns
        if column not in columns
    )

    return pd.DataFrame(
        records,
        columns=columns,
    ).reset_index(
        drop=True
    )


def load_springer_records():
    """
    Combines the current Springer import with the enriched checkpoint.

    Previously recovered metadata and API status columns are preserved.
    Newly imported records are appended for subsequent enrichment.
    """

    checkpoint = None

    if OUTPUT_FILE.exists():

        # Do not standardize the checkpoint: API-specific columns
        # must survive reloading.
        checkpoint = pd.read_excel(
            OUTPUT_FILE
        )

    source_file = resolve_springer_import_file()

    if source_file is None:

        if checkpoint is not None:
            return checkpoint

        raise FileNotFoundError(
            "No Springer processed file was found."
        )

    imported = standardize_dataframe(
        pd.read_excel(source_file),
        database="springer",
    )

    if checkpoint is None:
        return imported

    return merge_springer_records(
        checkpoint,
        imported,
    )


# ============================================================
# SAVE CHECKPOINT
# ============================================================

def save_checkpoint(
    dataframe,
):
    """
    Saves the current enrichment state using an atomic replacement.
    """

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.NamedTemporaryFile(
        dir=OUTPUT_FILE.parent,
        prefix=f".{OUTPUT_FILE.stem}_",
        suffix=".xlsx",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)

    try:
        dataframe.to_excel(
            temporary_path,
            index=False,
        )

        os.replace(
            temporary_path,
            OUTPUT_FILE,
        )

    finally:
        temporary_path.unlink(missing_ok=True)


# ============================================================
# ENRICH
# ============================================================

def enrich_records(
    dataframe,
    api_key,
):
    """
    Enriches records with missing abstracts.

    Existing abstracts are never overwritten.
    """

    df = dataframe.copy()

    # Additional API-specific columns.
    for column in [
        "springer_api_status",
        "springer_api_error",
        "springer_api_title",
        "springer_api_doi",
        "springer_api_document_type",
    ]:

        if column not in df.columns:
            df[column] = ""

    # --------------------------------------------------------
    # PRE-CALCULATE PENDING RECORDS
    # --------------------------------------------------------

    total_records = len(df)

    abstracts_before = int(
        (
            df["abstract"]
            .fillna("")
            .astype(str)
            .str.strip()
            != ""
        ).sum()
    )

    api_calls = 0
    found_count = 0
    not_found_count = 0
    errors_count = 0

    print(
        f"\nRecords: {total_records}"
    )

    print(
        f"Abstracts already available: {abstracts_before}"
    )

    for position, index in enumerate(
        df.index,
        start=1,
    ):

        title = safe_text(
            df.at[index, "title"]
        )

        doi = normalize_doi(
            df.at[index, "doi"]
        )

        abstract = safe_text(
            df.at[index, "abstract"]
        )

        previous_status = safe_text(
            df.at[
                index,
                "springer_api_status",
            ]
        )

        print(
            "\n" + "-" * 70
        )

        print(
            f"[{position}/{total_records}]"
        )

        print(
            f"Title: {title}"
        )

        print(
            f"DOI: {doi}"
        )

        # ====================================================
        # ABSTRACT ALREADY AVAILABLE
        # ====================================================

        if abstract:

            if not previous_status:

                df.at[
                    index,
                    "springer_api_status",
                ] = "ALREADY_HAS_ABSTRACT"

            print(
                "  Abstract already available."
            )

            continue

        # ====================================================
        # FINAL API STATUS
        # ====================================================

        if previous_status in FINAL_STATUSES:

            print(
                f"  Previous final status: {previous_status}"
            )

            continue

        # ====================================================
        # NO DOI
        # ====================================================

        if not doi:

            df.at[
                index,
                "springer_api_status",
            ] = "NO_DOI"

            print(
                "  No DOI available."
            )

            save_checkpoint(df)

            continue

        # ====================================================
        # SAFETY LIMIT
        # ====================================================

        if api_calls >= MAX_CALLS_PER_RUN:

            print(
                "\n" + "=" * 70
            )

            print(
                "SPRINGER API SAFETY LIMIT REACHED"
            )

            print(
                "=" * 70
            )

            print(
                f"\nCalls made this run: {api_calls}"
            )

            print(
                "Checkpoint saved."
            )

            break

        # ====================================================
        # API REQUEST
        # ====================================================

        (
            status,
            record,
            error_message,
        ) = request_springer_metadata(
            api_key=api_key,
            doi=doi,
        )

        api_calls += 1

        df.at[
            index,
            "springer_api_status",
        ] = status

        df.at[
            index,
            "springer_api_error",
        ] = error_message

        # ====================================================
        # FOUND
        # ====================================================

        if (
            status == "FOUND"
            and record
        ):

            api_abstract = clean_html(
                record.get(
                    "abstract",
                    "",
                )
            )

            api_title = safe_text(
                record.get(
                    "title",
                    "",
                )
            )

            api_doi = normalize_doi(
                record.get(
                    "doi",
                    "",
                )
            )

            api_document_type = safe_text(
                record.get(
                    "contentType",
                    "",
                )
            )

            api_keywords = extract_keywords(
                record
            )

            df.at[
                index,
                "springer_api_title",
            ] = api_title

            df.at[
                index,
                "springer_api_doi",
            ] = api_doi

            df.at[
                index,
                "springer_api_document_type",
            ] = api_document_type

            if api_abstract:

                df.at[
                    index,
                    "abstract",
                ] = api_abstract

            if (
                not safe_text(
                    df.at[index, "keywords"]
                )
                and api_keywords
            ):

                df.at[
                    index,
                    "keywords",
                ] = api_keywords

            if (
                not safe_text(
                    df.at[index, "document_type"]
                )
                and api_document_type
            ):

                df.at[
                    index,
                    "document_type",
                ] = api_document_type

            df.at[
                index,
                "metadata_status",
            ] = (
                "ABSTRACT_FOUND"
                if api_abstract
                else "METADATA_FOUND_NO_ABSTRACT"
            )

            df.at[
                index,
                "metadata_source",
            ] = "Springer Nature Meta API v2"

            if api_abstract:

                found_count += 1

                print(
                    f"  ABSTRACT FOUND "
                    f"({len(api_abstract)} characters)"
                )

            else:

                print(
                    "  Metadata found, "
                    "but no abstract returned."
                )

        # ====================================================
        # NOT FOUND
        # ====================================================

        elif status == "NOT_FOUND":

            not_found_count += 1

            print(
                "  Record not found by the API."
            )

        # ====================================================
        # RATE LIMIT
        # ====================================================

        elif status == "RATE_LIMIT":

            print(
                "\nSpringer API rate limit reached."
            )

            print(
                "Checkpoint saved."
            )

            save_checkpoint(df)

            break

        # ====================================================
        # AUTH / QUOTA
        # ====================================================

        elif status == "AUTH_OR_QUOTA_ERROR":

            print(
                "\nSpringer API authentication "
                "or quota error."
            )

            print(
                error_message
            )

            print(
                "Checkpoint saved."
            )

            save_checkpoint(df)

            break

        # ====================================================
        # OTHER ERROR
        # ====================================================

        else:

            errors_count += 1

            print(
                f"  API error: {error_message}"
            )

        # ====================================================
        # CHECKPOINT
        # ====================================================

        save_checkpoint(df)

        print(
            "  Checkpoint saved."
        )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    abstracts_after = int(
        (
            df["abstract"]
            .fillna("")
            .astype(str)
            .str.strip()
            != ""
        ).sum()
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "SPRINGER METADATA ENRICHMENT SUMMARY"
    )

    print(
        "=" * 70
    )

    print(
        f"\nRecords: {len(df)}"
    )

    print(
        f"Abstracts before: {abstracts_before}"
    )

    print(
        f"Abstracts after: {abstracts_after}"
    )

    print(
        f"New abstracts found: "
        f"{abstracts_after - abstracts_before}"
    )

    print(
        f"API calls this run: {api_calls}"
    )

    print(
        f"API records not found: {not_found_count}"
    )

    print(
        f"Technical errors: {errors_count}"
    )

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 70
    )

    print(
        "SPRINGER METADATA ENRICHMENT"
    )

    print(
        "=" * 70
    )

    load_dotenv(
        PROJECT_ROOT / ".env"
    )

    api_key = os.getenv(
        "SPRINGER_API_KEY"
    )

    if not api_key:

        print(
            "\nSPRINGER_API_KEY was not found."
        )

        print(
            "Create a .env file based on .env.example."
        )

        return

    try:

        dataframe = load_springer_records()

    except FileNotFoundError as error:

        print(
            f"\n{error}"
        )

        return

    enriched = enrich_records(
        dataframe,
        api_key,
    )

    save_checkpoint(
        enriched
    )

    print(
        "\nOutput file:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()