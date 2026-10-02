"""
Data management utilities for the Serious Games AI-IoT Screening project.

This package provides utilities for:

- standardizing imported metadata;
- creating the master dataset;
- updating the master dataset;
- assigning persistent MASTER IDs;
- enriching Springer metadata.
"""

from pathlib import Path
import re
import unicodedata

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

DATA_MANAGEMENT_DIR = Path(__file__).resolve().parent
SRC_DIR = DATA_MANAGEMENT_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

MASTER_FILE = PROCESSED_DIR / "master_records.xlsx"


# ============================================================
# DATABASE ORDER
# ============================================================

DATABASE_ORDER = [
    "ieee",
    "pubmed",
    "acm",
    "scopus",
    "compendex",
    "springer",
]


DATABASE_NAMES = {
    "ieee": "IEEE Xplore",
    "pubmed": "PubMed",
    "acm": "ACM Digital Library",
    "scopus": "Scopus",
    "compendex": "Engineering Village / Compendex",
    "springer": "Springer Link",
}


# ============================================================
# POSSIBLE SOURCE FILES
#
# English public names come first.
# Legacy Portuguese names are also accepted so that data
# exported by the development repository can still be used.
# ============================================================

SOURCE_FILE_CANDIDATES = {

    "ieee": [
        "ieee_records.xlsx",
        "ieee_records_new.xlsx",
        "ieee_records_unique.xlsx",
        "ieee_registros_novos.xlsx",
        "ieee_registros_unicos.xlsx",
    ],

    "pubmed": [
        "pubmed_records.xlsx",
        "pubmed_records_new.xlsx",
        "pubmed_registros_novos.xlsx",
    ],

    "acm": [
        "acm_records.xlsx",
        "acm_records_new.xlsx",
        "acm_registros_novos.xlsx",
    ],

    "scopus": [
        "scopus_records.xlsx",
        "scopus_records_new.xlsx",
        "scopus_registros_novos.xlsx",
    ],

    "compendex": [
        "compendex_records.xlsx",
        "compendex_records_new.xlsx",
        "compendex_registros_novos.xlsx",
    ],

    "springer": [
        # Enriched files receive priority.
        "springer_records_enriched.xlsx",
        "springer_registros_enriquecidos.xlsx",

        "springer_records.xlsx",
        "springer_records_new.xlsx",
        "springer_registros_novos.xlsx",
    ],
}


# ============================================================
# CANONICAL MASTER COLUMNS
# ============================================================

CANONICAL_COLUMNS = [
    "master_id",
    "source_id",
    "database",
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
    "metadata_status",
    "metadata_source",
]


# ============================================================
# COLUMN ALIASES
#
# Allows both English and Portuguese development files to be
# standardized into the public repository schema.
# ============================================================

COLUMN_ALIASES = {

    "master_id": [
        "master_id",
        "master id",
        "master-id",
    ],

    "source_id": [
        "source_id",
        "source id",
        "id",
        "id_origem",
        "id origem",
        "record_id",
        "record id",
    ],

    "database": [
        "database",
        "base",
        "source_database",
        "source database",
    ],

    "title": [
        "title",
        "titulo",
        "título",
    ],

    "authors": [
        "authors",
        "author",
        "autores",
        "autor",
    ],

    "year": [
        "year",
        "ano",
        "publication_year",
        "publication year",
    ],

    "publication": [
        "publication",
        "journal",
        "source",
        "venue",
        "publicacao",
        "publicação",
    ],

    "document_type": [
        "document_type",
        "document type",
        "content_type",
        "content type",
        "tipo_documento",
        "tipo documento",
        "tipo",
    ],

    "doi": [
        "doi",
    ],

    "abstract": [
        "abstract",
        "abstract_api",
        "resumo",
    ],

    "keywords": [
        "keywords",
        "keywords_api",
        "keyword",
        "palavras_chave",
        "palavras-chave",
        "palavras chave",
    ],

    "url": [
        "url",
        "link",
        "article_url",
        "article url",
    ],

    "metadata_status": [
        "metadata_status",
        "metadata status",
        "status_metadata",
        "status metadata",
        "status_api",
    ],

    "metadata_source": [
        "metadata_source",
        "metadata source",
        "fonte_metadados",
        "fonte metadados",
        "fonte_api",
    ],
}


# ============================================================
# PATH INITIALIZATION
# ============================================================

def ensure_project_directories():
    """
    Creates the project data directories when they do not exist.
    """

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def safe_text(value):
    """
    Converts a value to a clean string.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_header(value):
    """
    Normalizes column names for alias matching.
    """

    value = safe_text(value)

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    value = re.sub(
        r"_+",
        "_",
        value,
    )

    return value.strip("_")


def normalize_title(value):
    """
    Normalizes titles for duplicate detection.
    """

    value = safe_text(value)

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    value = value.lower()

    value = (
        value
        .replace("–", "-")
        .replace("—", "-")
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def normalize_doi(value):
    """
    Normalizes DOI strings for duplicate detection.
    """

    value = safe_text(value).lower()

    value = re.sub(
        r"^https?://(dx\.)?doi\.org/",
        "",
        value,
    )

    value = re.sub(
        r"^doi\s*:\s*",
        "",
        value,
    )

    return value.rstrip(
        ".,; "
    ).strip()


# ============================================================
# DATAFRAME STANDARDIZATION
# ============================================================

def standardize_dataframe(
    dataframe,
    database=None,
):
    """
    Converts metadata exported by different databases into the
    canonical master schema.

    Unknown columns are intentionally not propagated to the master
    dataset. Database-specific raw metadata should remain in the
    original imported file.
    """

    df = dataframe.copy()

    normalized_columns = {
        column: normalize_header(column)
        for column in df.columns
    }

    result = pd.DataFrame(
        index=df.index
    )

    for canonical_column in CANONICAL_COLUMNS:

        aliases = COLUMN_ALIASES.get(
            canonical_column,
            [canonical_column],
        )

        normalized_aliases = {
            normalize_header(alias)
            for alias in aliases
        }

        candidate_columns = [
            original_column
            for original_column, normalized_column
            in normalized_columns.items()
            if normalized_column in normalized_aliases
        ]

        combined = pd.Series(
            "",
            index=df.index,
            dtype="object",
        )

        for candidate in candidate_columns:

            candidate_values = (
                df[candidate]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            missing_mask = (
                combined
                .fillna("")
                .astype(str)
                .str.strip()
                == ""
            )

            combined.loc[
                missing_mask
            ] = candidate_values.loc[
                missing_mask
            ]

        result[
            canonical_column
        ] = combined

    if database:

        database_name = DATABASE_NAMES.get(
            database,
            database,
        )

        missing_database = (
            result["database"]
            .fillna("")
            .astype(str)
            .str.strip()
            == ""
        )

        result.loc[
            missing_database,
            "database",
        ] = database_name

    # Clean important fields.
    result["title"] = (
        result["title"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    result["doi"] = (
        result["doi"]
        .apply(normalize_doi)
    )

    result["abstract"] = (
        result["abstract"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    result["keywords"] = (
        result["keywords"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # Remove completely empty records.
    result = result[
        result["title"].str.strip() != ""
    ].copy()

    return result.reset_index(
        drop=True
    )


# ============================================================
# TABLE I/O
# ============================================================

def read_table(file_path):
    """
    Reads XLSX or CSV metadata files.
    """

    file_path = Path(
        file_path
    )

    suffix = (
        file_path
        .suffix
        .lower()
    )

    if suffix in {
        ".xlsx",
        ".xls",
    }:

        return pd.read_excel(
            file_path
        )

    if suffix == ".csv":

        return pd.read_csv(
            file_path
        )

    raise ValueError(
        f"Unsupported file format: {suffix}"
    )


def write_table(
    dataframe,
    file_path,
):
    """
    Writes XLSX or CSV files.
    """

    file_path = Path(
        file_path
    )

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    suffix = (
        file_path
        .suffix
        .lower()
    )

    if suffix == ".xlsx":

        dataframe.to_excel(
            file_path,
            index=False,
        )

        return

    if suffix == ".csv":

        dataframe.to_csv(
            file_path,
            index=False,
        )

        return

    raise ValueError(
        f"Unsupported output format: {suffix}"
    )


# ============================================================
# DATABASE SOURCE RESOLUTION
# ============================================================

def resolve_database_source_file(
    database,
):
    """
    Returns the first available processed file for a database.
    """

    ensure_project_directories()

    if database not in SOURCE_FILE_CANDIDATES:

        raise ValueError(
            f"Unknown database: {database}"
        )

    for filename in SOURCE_FILE_CANDIDATES[
        database
    ]:

        candidate = (
            PROCESSED_DIR
            / filename
        )

        if candidate.exists():

            return candidate

    return None


# ============================================================
# DUPLICATE KEYS
# ============================================================

def build_doi_key(
    row,
):
    return normalize_doi(
        row.get(
            "doi",
            "",
        )
    )


def build_title_key(
    row,
):
    return normalize_title(
        row.get(
            "title",
            "",
        )
    )


# Initialize directories when the package is imported.
ensure_project_directories()

def normalize_volume(value):
    """Compare volume identifiers consistently after Excel round trips."""
    value = safe_text(value).casefold()
    value = re.sub(r"^(\d+)\.0$", r"\1", value)
    return " ".join(value.split())


def title_match_is_compatible(existing, incoming):
    """Do not merge a title match with conflicting volume evidence."""
    if not normalize_title(existing.get("title", "")):
        return False
    if normalize_title(existing.get("title", "")) != normalize_title(incoming.get("title", "")):
        return False
    left = normalize_volume(existing.get("volume", ""))
    right = normalize_volume(incoming.get("volume", ""))
    if left and right and left != right:
        return False
    return True


def find_unique_title_match(candidates, incoming):
    """Ambiguous title matches are preserved rather than arbitrarily merged."""
    compatible = [record for record in candidates if title_match_is_compatible(record, incoming)]
    return compatible[0] if len(compatible) == 1 else None
