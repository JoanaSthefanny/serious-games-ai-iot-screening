"""
Interactive semi-automated screening pipeline.

The program reads the master dataset and allows screening records from
one database or all supported databases.

Checkpoint behavior
-------------------
SUCCESS and NO_ABSTRACT results are reused only when their recorded
configuration and screening metadata still match the current record.

API_ERROR records and invalidated results are retried. Records that
no longer belong to the current collection are removed from active
results. The original workbook is backed up before removing results.

New results include metadata and prompt fingerprints. Legacy results
are checked using their recorded versions and stored metadata.

Reusable results receive current bibliographic metadata from the master
without changing their screening assessments. These updates are saved
even when no articles remain pending.
"""

from pathlib import Path
from datetime import datetime
import hashlib
import json
import shutil
import os
import re
import tempfile
import time
import unicodedata

import pandas as pd
from dotenv import load_dotenv
from google import genai

from data_management import (
    MASTER_FILE,
    PROJECT_ROOT,
    PROCESSED_DIR,
    safe_text,
)

from screening import classifier as core


PAUSE_BETWEEN_ARTICLES = 5

BIBLIOGRAPHIC_RESULT_FIELDS = (
    "source_id",
    "title",
    "authors",
    "year",
    "publication",
    "volume",
    "document_type",
    "doi",
    "url",
)

DATABASES = {
    "1": {
        "name": "IEEE Xplore",
        "slug": "ieee",
        "aliases": ["IEEE", "IEEE Xplore"],
    },
    "2": {
        "name": "PubMed",
        "slug": "pubmed",
        "aliases": ["PubMed"],
    },
    "3": {
        "name": "ACM Digital Library",
        "slug": "acm",
        "aliases": ["ACM", "ACM Digital Library"],
    },
    "4": {
        "name": "Scopus",
        "slug": "scopus",
        "aliases": ["Scopus"],
    },
    "5": {
        "name": "Engineering Village / Compendex",
        "slug": "compendex",
        "aliases": [
            "Compendex",
            "El Compendex",
            "Engineering Village",
            "Engineering Village / Compendex",
        ],
    },
    "6": {
        "name": "Springer Link",
        "slug": "springer",
        "aliases": ["Springer", "Springer Link", "Springer Nature"],
    },
}


# ============================================================
# DATABASE SELECTION AND ERROR HELPERS
# ============================================================

def normalize_text(value):
    value = safe_text(value)
    value = unicodedata.normalize("NFKD", value)

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def record_belongs_to_database(database_value, configuration):
    normalized_value = normalize_text(database_value)

    aliases = {
        normalize_text(alias)
        for alias in configuration["aliases"]
    }

    return normalized_value in aliases


def select_database_records(master, configuration):
    mask = master["database"].apply(
        lambda value: record_belongs_to_database(value, configuration)
    ).astype(bool)

    return master[mask].copy()


def is_quota_error(error):
    text = str(error).lower()

    return (
        "429" in text
        or "resource_exhausted" in text
        or "quota" in text
        or "too many requests" in text
    )


def is_authentication_error(error):
    text = str(error).lower()

    return (
        "401" in text
        or "403" in text
        or "api_key_invalid" in text
        or "api key not valid" in text
        or "invalid api key" in text
        or "permission_denied" in text
        or "unauthenticated" in text
    )


def is_service_unavailable(error):
    text = str(error).lower()

    return (
        "503" in text
        or "unavailable" in text
        or "high demand" in text
        or "service unavailable" in text
    )


# ============================================================
# FINGERPRINTS AND RESULT BUILDERS
# ============================================================

def metadata_fingerprint(article):
    """Hashes the exact cleaned metadata supplied to the classifier."""

    metadata = {
        field: safe_text(article.get(field, ""))
        for field in ("title", "abstract", "keywords")
    }

    payload = json.dumps(
        metadata,
        ensure_ascii=False,
        sort_keys=True,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def current_prompt_fingerprint():
    """Hashes the prompt currently loaded by the classifier."""

    prompt = core.load_screening_prompt()

    return hashlib.sha256(
        prompt.encode("utf-8")
    ).hexdigest()


def base_result(article):
    return {
        "metadata_hash": metadata_fingerprint(article),
        "prompt_hash": current_prompt_fingerprint(),
        "master_id": safe_text(article.get("master_id", "")),
        "source_id": safe_text(article.get("source_id", "")),
        "database": safe_text(article.get("database", "")),
        "title": safe_text(article.get("title", "")),
        "authors": safe_text(article.get("authors", "")),
        "year": safe_text(article.get("year", "")),
        "publication": safe_text(article.get("publication", "")),
        "volume": safe_text(article.get("volume", "")),
        "document_type": safe_text(article.get("document_type", "")),
        "doi": safe_text(article.get("doi", "")),
        "url": safe_text(article.get("url", "")),
        "model": core.MODEL_NAME,
        "prompt_version": core.PROMPT_VERSION,
        "classifier_version": core.CLASSIFIER_VERSION,
    }


def create_success_result(
    article,
    assessment,
    decision,
    reason,
    rescue_code,
):
    result = base_result(article)

    result.update({
        "serious_game": assessment.serious_game,
        "evidence_serious_game": assessment.evidence_serious_game,
        "gamification_only": assessment.gamification_only,
        "evidence_gamification": assessment.evidence_gamification,
        "health": assessment.health,
        "evidence_health": assessment.evidence_health,
        "ai": assessment.ai,
        "evidence_ai": assessment.evidence_ai,
        "iot": assessment.iot,
        "evidence_iot": assessment.evidence_iot,
        "secondary_or_incomplete": assessment.secondary_or_incomplete,
        "evidence_study_type": assessment.evidence_study_type,
        "notes": assessment.notes,
        "decision": decision,
        "decision_reason": reason,
        "safety_rescue": "YES" if rescue_code else "NO",
        "rescue_code": rescue_code,
        "api_status": "SUCCESS",
        "api_error": "",
        "abstract": safe_text(article.get("abstract", "")),
        "keywords": safe_text(article.get("keywords", "")),
    })

    return result


def create_no_abstract_result(article):
    result = base_result(article)

    result.update({
        "serious_game": "NOT_EVALUATED",
        "evidence_serious_game": "Abstract unavailable.",
        "gamification_only": "NOT_EVALUATED",
        "evidence_gamification": "Abstract unavailable.",
        "health": "NOT_EVALUATED",
        "evidence_health": "Abstract unavailable.",
        "ai": "NOT_EVALUATED",
        "evidence_ai": "Abstract unavailable.",
        "iot": "NOT_EVALUATED",
        "evidence_iot": "Abstract unavailable.",
        "secondary_or_incomplete": "NOT_EVALUATED",
        "evidence_study_type": "Abstract unavailable.",
        "notes": (
            "Preserved for human review because the "
            "abstract was unavailable."
        ),
        "decision": "UNCERTAIN",
        "decision_reason": (
            "No abstract was available. The record must not "
            "be automatically excluded."
        ),
        "safety_rescue": "NO",
        "rescue_code": "",
        "api_status": "NO_ABSTRACT",
        "api_error": "",
        "abstract": "",
        "keywords": safe_text(article.get("keywords", "")),
    })

    return result


def create_error_result(article, error):
    result = base_result(article)

    result.update({
        "serious_game": "NOT_EVALUATED",
        "evidence_serious_game": "",
        "gamification_only": "NOT_EVALUATED",
        "evidence_gamification": "",
        "health": "NOT_EVALUATED",
        "evidence_health": "",
        "ai": "NOT_EVALUATED",
        "evidence_ai": "",
        "iot": "NOT_EVALUATED",
        "evidence_iot": "",
        "secondary_or_incomplete": "NOT_EVALUATED",
        "evidence_study_type": "",
        "notes": "",
        "decision": "API_ERROR",
        "decision_reason": (
            "Technical API failure. This result must not "
            "be interpreted as an exclusion."
        ),
        "safety_rescue": "NO",
        "rescue_code": "",
        "api_status": "API_ERROR",
        "api_error": str(error),
        "abstract": safe_text(article.get("abstract", "")),
        "keywords": safe_text(article.get("keywords", "")),
    })

    return result


def replace_result(results, new_result):
    master_id = safe_text(new_result.get("master_id", ""))

    results = [
        result
        for result in results
        if safe_text(result.get("master_id", "")) != master_id
    ]

    results.append(new_result)

    return results


# ============================================================
# CHECKPOINT VALIDATION AND RECONCILIATION
# ============================================================

def load_checkpoint(output_file):
    if not output_file.exists():
        return pd.DataFrame()

    try:
        dataframe = pd.read_excel(
            output_file,
            sheet_name="Results",
            dtype={
                "master_id": str,
                "model": str,
                "prompt_version": str,
                "classifier_version": str,
                "metadata_hash": str,
                "prompt_hash": str,
            },
        )

    except Exception as error:
        raise RuntimeError(
            f"Could not load checkpoint: {error}"
        )

    return dataframe


def checkpoint_result_is_valid(result, article, prompt_hash):
    """Checks configuration, metadata and completion status."""

    expected_configuration = {
        "model": core.MODEL_NAME,
        "prompt_version": core.PROMPT_VERSION,
        "classifier_version": core.CLASSIFIER_VERSION,
    }

    for field, expected in expected_configuration.items():
        if safe_text(result.get(field, "")) != str(expected):
            return False

    saved_prompt_hash = safe_text(
        result.get("prompt_hash", "")
    )

    if saved_prompt_hash and saved_prompt_hash != prompt_hash:
        return False

    # Legacy workbooks do not have hashes. Their stored metadata
    # and recorded configuration versions are checked directly.
    if any(
        field not in result
        for field in ("title", "abstract", "keywords")
    ):
        return False

    current_metadata_hash = metadata_fingerprint(article)

    saved_metadata_hash = safe_text(
        result.get("metadata_hash", "")
    )

    if (
        saved_metadata_hash
        and saved_metadata_hash != current_metadata_hash
    ):
        return False

    if metadata_fingerprint(result) != current_metadata_hash:
        return False

    if safe_text(result.get("database", "")) != safe_text(
        article.get("database", "")
    ):
        return False

    if safe_text(result.get("safety_rescue", "")) not in {
        "YES",
        "NO",
    }:
        return False

    status = safe_text(result.get("api_status", ""))
    decision = safe_text(result.get("decision", ""))
    has_abstract = bool(
        safe_text(article.get("abstract", ""))
    )

    if status == "SUCCESS":
        return has_abstract and decision in {
            "RETAIN",
            "UNCERTAIN",
            "EXCLUDE",
        }

    if status == "NO_ABSTRACT":
        return not has_abstract and decision == "UNCERTAIN"

    # API_ERROR and unrecognized statuses remain pending.
    return False


def refresh_bibliographic_metadata(result, article):
    """Refresh exported bibliography without modifying screening evidence.

    The current master is authoritative for fields it contains, including
    deliberate removals. Missing columns in legacy masters do not erase
    previously saved values.
    """
    refreshed = result.copy()

    for field in BIBLIOGRAPHIC_RESULT_FIELDS:
        if field in article:
            refreshed[field] = safe_text(article.get(field, ""))

    return refreshed


def reusable_bibliography_changed(checkpoint, results):
    """Detect refreshed fields, including columns absent in old checkpoints."""
    if checkpoint.empty or not results:
        return False

    latest = {
        safe_text(result.get("master_id", "")): result
        for result in checkpoint.to_dict(orient="records")
    }

    for result in results:
        previous = latest.get(safe_text(result.get("master_id", "")), {})

        for field in BIBLIOGRAPHIC_RESULT_FIELDS:
            if field not in result:
                continue

            if field not in previous or safe_text(previous[field]) != safe_text(
                result[field]
            ):
                return True

    return False


def reconcile_checkpoint(checkpoint, records):
    """Return valid results with current bibliography and original assessments."""

    if checkpoint.empty or "master_id" not in checkpoint.columns:
        return []

    current_records = {
        safe_text(article.get("master_id", "")): article
        for article in records.to_dict(orient="records")
    }

    # Keep the last saved occurrence of each ID.
    latest_results = {}

    for result in checkpoint.to_dict(orient="records"):
        master_id = safe_text(result.get("master_id", ""))

        if master_id in current_records:
            latest_results[master_id] = result

    prompt_hash = current_prompt_fingerprint()
    reusable = []

    for master_id, result in latest_results.items():
        article = current_records[master_id]

        if checkpoint_result_is_valid(
            result,
            article,
            prompt_hash,
        ):
            result = refresh_bibliographic_metadata(result, article)
            result["master_id"] = master_id
            reusable.append(result)

    return reusable


def completed_ids(checkpoint, records):
    """Returns IDs whose results remain valid for the current records."""

    return {
        safe_text(result["master_id"])
        for result in reconcile_checkpoint(checkpoint, records)
    }


def create_checkpoint_backup(output_file):
    """Preserves the original workbook before invalid results are removed."""

    if not output_file.exists():
        return None

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    backup_file = output_file.with_name(
        f"{output_file.stem}_backup_{timestamp}"
        f"{output_file.suffix}"
    )

    shutil.copy2(output_file, backup_file)

    return backup_file


# ============================================================
# SUMMARY AND WORKBOOK SAVING
# ============================================================

def calculate_summary(dataframe, database_name, total_records):
    if dataframe.empty:
        values = {
            "successful_api_analyses": 0,
            "no_abstract": 0,
            "api_errors": 0,
            "retain": 0,
            "uncertain": 0,
            "exclude": 0,
            "safety_rescues": 0,
        }

    else:
        values = {
            "successful_api_analyses": int(
                (dataframe["api_status"] == "SUCCESS").sum()
            ),
            "no_abstract": int(
                (dataframe["api_status"] == "NO_ABSTRACT").sum()
            ),
            "api_errors": int(
                (dataframe["api_status"] == "API_ERROR").sum()
            ),
            "retain": int(
                (dataframe["decision"] == "RETAIN").sum()
            ),
            "uncertain": int(
                (dataframe["decision"] == "UNCERTAIN").sum()
            ),
            "exclude": int(
                (dataframe["decision"] == "EXCLUDE").sum()
            ),
            "safety_rescues": int(
                (dataframe["safety_rescue"] == "YES").sum()
            ),
        }

    completed = (
        values["successful_api_analyses"]
        + values["no_abstract"]
    )

    pending = max(total_records - completed, 0)
    values["pending"] = pending

    summary = pd.DataFrame([
        {
            "indicator": "Database",
            "value": database_name,
        },
        {
            "indicator": "Model",
            "value": core.MODEL_NAME,
        },
        {
            "indicator": "Prompt version",
            "value": core.PROMPT_VERSION,
        },
        {
            "indicator": "Classifier version",
            "value": core.CLASSIFIER_VERSION,
        },
        {
            "indicator": "Total records",
            "value": total_records,
        },
        {
            "indicator": "Successful API analyses",
            "value": values["successful_api_analyses"],
        },
        {
            "indicator": "No abstract",
            "value": values["no_abstract"],
        },
        {
            "indicator": "API errors",
            "value": values["api_errors"],
        },
        {
            "indicator": "RETAIN",
            "value": values["retain"],
        },
        {
            "indicator": "UNCERTAIN",
            "value": values["uncertain"],
        },
        {
            "indicator": "EXCLUDE",
            "value": values["exclude"],
        },
        {
            "indicator": "Safety rescues",
            "value": values["safety_rescues"],
        },
        {
            "indicator": "Pending",
            "value": pending,
        },
    ])

    return summary, values


def save_checkpoint(
    results,
    output_file,
    database_name,
    total_records,
):
    dataframe = pd.DataFrame(results)

    if not dataframe.empty:
        dataframe = dataframe.sort_values(
            "master_id",
            kind="stable",
        ).reset_index(drop=True)

    summary, _ = calculate_summary(
        dataframe,
        database_name,
        total_records,
    )

    if dataframe.empty:
        retain = pd.DataFrame()
        uncertain = pd.DataFrame()
        exclude = pd.DataFrame()
        rescues = pd.DataFrame()
        no_abstract = pd.DataFrame()
        api_errors = pd.DataFrame()

    else:
        retain = dataframe[
            dataframe["decision"] == "RETAIN"
        ].copy()

        uncertain = dataframe[
            dataframe["decision"] == "UNCERTAIN"
        ].copy()

        exclude = dataframe[
            dataframe["decision"] == "EXCLUDE"
        ].copy()

        rescues = dataframe[
            dataframe["safety_rescue"] == "YES"
        ].copy()

        no_abstract = dataframe[
            dataframe["api_status"] == "NO_ABSTRACT"
        ].copy()

        api_errors = dataframe[
            dataframe["api_status"] == "API_ERROR"
        ].copy()

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.NamedTemporaryFile(
        dir=output_file.parent,
        prefix=f".{output_file.stem}_",
        suffix=".xlsx",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)

    try:
        with pd.ExcelWriter(
            temporary_path,
            engine="openpyxl",
        ) as writer:
            summary.to_excel(
                writer,
                sheet_name="Summary",
                index=False,
            )
            dataframe.to_excel(
                writer,
                sheet_name="Results",
                index=False,
            )
            retain.to_excel(
                writer,
                sheet_name="RETAIN",
                index=False,
            )
            uncertain.to_excel(
                writer,
                sheet_name="UNCERTAIN",
                index=False,
            )
            exclude.to_excel(
                writer,
                sheet_name="EXCLUDE",
                index=False,
            )
            rescues.to_excel(
                writer,
                sheet_name="Safety_rescue",
                index=False,
            )
            no_abstract.to_excel(
                writer,
                sheet_name="No_abstract",
                index=False,
            )
            api_errors.to_excel(
                writer,
                sheet_name="API_errors",
                index=False,
            )

        # Replace the checkpoint after all sheets are written and closed.
        os.replace(
            temporary_path,
            output_file,
        )

    finally:
        temporary_path.unlink(missing_ok=True)


def print_summary(results, database_name, total_records):
    dataframe = pd.DataFrame(results)

    _, values = calculate_summary(
        dataframe,
        database_name,
        total_records,
    )

    print("\n" + "=" * 70)
    print(f"SUMMARY - {database_name}")
    print("=" * 70)
    print(f"\nDatabase records: {total_records}")
    print(f"Successful analyses: {values['successful_api_analyses']}")
    print(f"No abstract: {values['no_abstract']}")
    print(f"Technical errors: {values['api_errors']}")
    print(f"Pending records: {values['pending']}")
    print(f"\nRETAIN: {values['retain']}")
    print(f"UNCERTAIN: {values['uncertain']}")
    print(f"EXCLUDE: {values['exclude']}")
    print(f"\nSafety rescues: {values['safety_rescues']}")


# ============================================================
# DATABASE PROCESSING
# ============================================================

def process_database(master, configuration, client):
    database_name = configuration["name"]
    slug = configuration["slug"]

    output_file = PROCESSED_DIR / (
        f"screening_{slug}_"
        f"v{core.CLASSIFIER_VERSION.replace('.', '_')}.xlsx"
    )

    print("\n" + "=" * 70)
    print(f"SCREENING - {database_name}")
    print("=" * 70)

    records = select_database_records(
        master,
        configuration,
    )

    total_records = len(records)

    print(f"\nRecords found in master: {total_records}")

    records["_master_id"] = records["master_id"].apply(safe_text)

    if (records["_master_id"] == "").any():
        raise ValueError(
            "The current collection contains records without MASTER IDs. "
            "Assign IDs before screening."
        )

    if records["_master_id"].duplicated().any():
        raise ValueError(
            "The current collection contains duplicated MASTER IDs. "
            "Resolve them before screening."
        )

    checkpoint = load_checkpoint(output_file)

    results = reconcile_checkpoint(
        checkpoint,
        records,
    )

    completed = {
        safe_text(result["master_id"])
        for result in results
    }

    discarded = len(checkpoint) - len(results)
    bibliography_changed = reusable_bibliography_changed(checkpoint, results)

    if discarded:
        backup = create_checkpoint_backup(output_file)

        print(
            "Checkpoint results removed from the active run: "
            f"{discarded}"
        )
        print(f"Original checkpoint backed up: {backup}")

    if discarded or bibliography_changed:
        save_checkpoint(
            results,
            output_file,
            database_name,
            total_records,
        )

        if bibliography_changed:
            print("Current master bibliography saved for reused results.")

    if total_records == 0:
        print("\nNo records were found for this database.")
        return "COMPLETED"

    pending = records[
        ~records["_master_id"].isin(completed)
    ].copy()

    print(f"Already completed: {len(completed)}")
    print(f"Pending: {len(pending)}")

    expected_calls = int(
        (
            pending["abstract"]
            .fillna("")
            .astype(str)
            .str.strip()
            != ""
        ).sum()
    )

    print(f"Expected Gemini calls: {expected_calls}")

    if pending.empty:
        print("\nThis database is already complete.")

        print_summary(
            results,
            database_name,
            total_records,
        )

        return "COMPLETED"

    total_pending = len(pending)

    for position, (_, article) in enumerate(
        pending.iterrows(),
        start=1,
    ):
        master_id = safe_text(article.get("master_id", ""))
        title = safe_text(article.get("title", ""))
        abstract = safe_text(article.get("abstract", ""))
        keywords = safe_text(article.get("keywords", ""))

        print("\n" + "-" * 70)
        print(f"[{position}/{total_pending}] {master_id}")
        print(f"Title: {title}")

        if not abstract:
            result = create_no_abstract_result(article)

            results = replace_result(
                results,
                result,
            )

            save_checkpoint(
                results,
                output_file,
                database_name,
                total_records,
            )

            print("    No abstract.")
            print("    Decision: UNCERTAIN")
            print("    Checkpoint saved.")
            continue

        try:
            assessment = core.analyze_article(
                client=client,
                title=title,
                abstract=abstract,
                keywords=keywords,
            )

            decision, reason, rescue_code = core.make_screening_decision(
                assessment=assessment,
                title=title,
                abstract=abstract,
                keywords=keywords,
            )

            result = create_success_result(
                article=article,
                assessment=assessment,
                decision=decision,
                reason=reason,
                rescue_code=rescue_code,
            )

        except Exception as error:
            result = create_error_result(
                article,
                error,
            )

            results = replace_result(
                results,
                result,
            )

            save_checkpoint(
                results,
                output_file,
                database_name,
                total_records,
            )

            print(f"    API ERROR: {error}")

            if is_quota_error(error):
                print("\n" + "=" * 70)
                print("GEMINI QUOTA REACHED")
                print("=" * 70)
                print("\nCheckpoint saved.")
                print(
                    "Run the program again when quota becomes available."
                )

                print_summary(
                    results,
                    database_name,
                    total_records,
                )

                return "STOP_ALL"

            if is_authentication_error(error):
                print("\n" + "=" * 70)
                print("GEMINI AUTHENTICATION ERROR")
                print("=" * 70)
                print(
                    "\nCheck GEMINI_API_KEY in the .env file."
                )

                return "STOP_ALL"

            if is_service_unavailable(error):
                print("\n" + "=" * 70)
                print("GEMINI TEMPORARILY UNAVAILABLE")
                print("=" * 70)
                print("\nCheckpoint saved.")
                print("Try again later.")

                return "STOP_ALL"

            print("    Isolated technical error recorded.")
            print("    Continuing to the next record.")

        else:
            results = replace_result(
                results,
                result,
            )

            save_checkpoint(
                results,
                output_file,
                database_name,
                total_records,
            )

            print(f"    Serious game: {assessment.serious_game}")
            print(f"    Health: {assessment.health}")
            print(f"    AI: {assessment.ai}")
            print(f"    IoT: {assessment.iot}")
            print(
                "    Secondary/incomplete: "
                f"{assessment.secondary_or_incomplete}"
            )
            print(f"    Decision: {decision}")

            if rescue_code:
                print(f"    Safety rescue: {rescue_code}")

            print(f"    Reason: {reason}")
            print("    Checkpoint saved.")

        time.sleep(PAUSE_BETWEEN_ARTICLES)

    _, final_values = calculate_summary(
        pd.DataFrame(results),
        database_name,
        total_records,
    )

    has_pending = final_values["pending"] > 0

    print("\n" + "=" * 70)

    if has_pending:
        print(f"SCREENING FINISHED WITH PENDING RECORDS - {database_name}")
    else:
        print(f"SCREENING COMPLETED - {database_name}")

    print("=" * 70)

    print_summary(
        results,
        database_name,
        total_records,
    )

    print("\nOutput file:")
    print(output_file)

    if has_pending:
        print(
            f"\nRecords requiring another attempt: "
            f"{final_values['pending']}"
        )
        print("Run the program again to retry the pending records.")
        return "COMPLETED_WITH_PENDING"

    return "COMPLETED"


# ============================================================
# MENU AND ENTRY POINT
# ============================================================

def show_menu():
    print("\n" + "=" * 70)
    print("SEMI-AUTOMATED SYSTEMATIC SCREENING")
    print("=" * 70)
    print(f"\nModel: {core.MODEL_NAME}")
    print(f"Prompt version: {core.PROMPT_VERSION}")
    print(f"Classifier version: {core.CLASSIFIER_VERSION}")
    print("\nSelect a database:")
    print("\nIEEE Xplore                     [1]")
    print("PubMed                          [2]")
    print("ACM Digital Library             [3]")
    print("Scopus                          [4]")
    print("Engineering Village / Compendex [5]")
    print("Springer Link                   [6]")
    print("All databases                   [7]")
    print("Back                            [0]")


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("\nGEMINI_API_KEY was not found.")
        print("Create a .env file based on .env.example.")
        return

    if not MASTER_FILE.exists():
        print("\nMaster dataset was not found:")
        print(MASTER_FILE)
        return

    master = pd.read_excel(MASTER_FILE)

    required_columns = {
        "master_id",
        "database",
        "title",
        "abstract",
        "keywords",
    }

    missing_columns = required_columns - set(master.columns)

    if missing_columns:
        print("\nMaster dataset is missing required columns:")
        print(missing_columns)
        return

    client = genai.Client(api_key=api_key)

    while True:
        show_menu()

        choice = input("\nEnter an option: ").strip()

        if choice == "0":
            print("\nReturning to main menu.")
            return

        if choice in DATABASES:
            status = process_database(
                master=master,
                configuration=DATABASES[choice],
                client=client,
            )

            if status == "STOP_ALL":
                return

            continue

        if choice == "7":
            print("\n" + "=" * 70)
            print("SCREENING ALL DATABASES")
            print("=" * 70)

            databases_with_pending = []

            for database_key in [
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
            ]:
                status = process_database(
                    master=master,
                    configuration=DATABASES[database_key],
                    client=client,
                )

                if status == "STOP_ALL":
                    print("\nGlobal screening interrupted.")
                    print("All checkpoints were preserved.")
                    return

                if status == "COMPLETED_WITH_PENDING":
                    databases_with_pending.append(
                        DATABASES[database_key]["name"]
                    )

            print("\n" + "=" * 70)

            if databases_with_pending:
                print("GLOBAL SCREENING FINISHED WITH PENDING RECORDS")
                print("=" * 70)
                print("\nDatabases requiring another attempt:")

                for database_name in databases_with_pending:
                    print(f"- {database_name}")

                print(
                    "\nRun the program again to retry the pending records."
                )

            else:
                print("ALL DATABASES COMPLETED")
                print("=" * 70)

            continue

        print("\nInvalid option.")


if __name__ == "__main__":
    main()
