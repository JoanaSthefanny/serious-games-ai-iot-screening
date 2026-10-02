"""
Shared utilities for database-specific metadata importers.

All database exports are converted into the canonical schema used by
the Serious Games AI-IoT Screening pipeline.
"""

from pathlib import Path
import re

import pandas as pd

from data_management import (
    DATABASE_NAMES,
    PROCESSED_DIR,
    RAW_DIR,
    normalize_doi,
    normalize_header,
    normalize_title,
    safe_text,
    standardize_dataframe,
)


# ============================================================
# PATHS
# ============================================================

IMPORTERS_DIR = Path(__file__).resolve().parent
SRC_DIR = IMPORTERS_DIR.parent
PROJECT_ROOT = SRC_DIR.parent


RAW_DATABASE_DIRS = {
    "ieee": RAW_DIR / "ieee",
    "pubmed": RAW_DIR / "pubmed",
    "acm": RAW_DIR / "acm",
    "scopus": RAW_DIR / "scopus",
    "compendex": RAW_DIR / "compendex",
    "springer": RAW_DIR / "springer",
}


OUTPUT_FILES = {
    database: PROCESSED_DIR / f"{database}_records.xlsx"
    for database in RAW_DATABASE_DIRS
}


# ============================================================
# DOI
# ============================================================

DOI_PATTERN = re.compile(
    r"10\.\d{4,9}/[-._;()/:A-Z0-9]+",
    re.IGNORECASE,
)


def extract_doi_from_text(value):
    """
    Extracts a DOI from arbitrary text.

    Examples accepted:
        10.1007/s11036-025-02473-6
        https://doi.org/10.1007/s11036-025-02473-6
        DOI: 10.1109/ACCESS.2024.1234567
    """

    value = safe_text(value)

    if not value:
        return ""

    match = DOI_PATTERN.search(value)

    if not match:
        return ""

    doi = match.group(0)

    # Remove punctuation commonly introduced by citations/URLs.
    doi = doi.rstrip(
        ".,;:]}>'\""
    )

    # Remove a closing parenthesis only when clearly trailing.
    if doi.endswith(")") and doi.count("(") < doi.count(")"):
        doi = doi[:-1]

    return normalize_doi(doi)


def extract_doi_from_values(values):
    """
    Searches multiple values for the first valid DOI.
    """

    for value in values:
        doi = extract_doi_from_text(value)

        if doi:
            return doi

    return ""


def recover_missing_dois(dataframe):
    """
    Recovers missing DOIs from canonical fields such as URL or source ID.
    """

    df = dataframe.copy()

    if "doi" not in df.columns:
        df["doi"] = ""

    candidate_columns = [
        "doi",
        "url",
        "source_id",
    ]

    for index in df.index:

        current_doi = extract_doi_from_text(
            df.at[index, "doi"]
        )

        if current_doi:
            df.at[index, "doi"] = current_doi
            continue

        values = []

        for column in candidate_columns:

            if column in df.columns:
                values.append(
                    df.at[index, column]
                )

        recovered = extract_doi_from_values(
            values
        )

        if recovered:
            df.at[index, "doi"] = recovered

    return df


# ============================================================
# DIRECTORY MANAGEMENT
# ============================================================

def ensure_database_directory(database):
    """
    Creates data/raw/<database>/ when necessary.
    """

    if database not in RAW_DATABASE_DIRS:
        raise ValueError(
            f"Unknown database: {database}"
        )

    directory = RAW_DATABASE_DIRS[database]

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


# ============================================================
# FILE DISCOVERY
# ============================================================

def discover_files(
    database,
    extensions,
):
    """
    Finds supported files inside data/raw/<database>/.
    """

    directory = ensure_database_directory(
        database
    )

    normalized_extensions = {
        extension.lower()
        if extension.startswith(".")
        else f".{extension.lower()}"
        for extension in extensions
    }

    files = [
        file
        for file in directory.iterdir()
        if (
            file.is_file()
            and file.suffix.lower()
            in normalized_extensions
        )
    ]

    return sorted(
        files,
        key=lambda path: path.name.lower(),
    )


# ============================================================
# GENERAL CLEANING
# ============================================================

def clean_bibtex_value(value):
    """
    Performs light BibTeX cleanup without changing scientific content.
    """

    value = safe_text(value)

    if not value:
        return ""

    if (
        value.startswith("{")
        and value.endswith("}")
    ):
        value = value[1:-1].strip()

    if (
        value.startswith('"')
        and value.endswith('"')
    ):
        value = value[1:-1].strip()

    value = (
        value
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("\t", " ")
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def clean_year(value):
    """
    Extracts a four-digit year when possible.
    """

    value = safe_text(value)

    match = re.search(
        r"\b(?:19|20)\d{2}\b",
        value,
    )

    if match:
        return match.group(0)

    return value


# ============================================================
# BIBTEX SUPPORT
# ============================================================

def _field_object_to_value(field):
    """
    Extracts text from different bibtexparser field representations.
    """

    if isinstance(field, str):
        return field

    if hasattr(field, "value"):
        return getattr(
            field,
            "value",
        )

    return field


def bibtex_entry_to_dict(entry):
    """
    Converts different bibtexparser entry representations into dicts.
    """

    if isinstance(entry, dict):
        return dict(entry)

    result = {}

    for attribute in [
        "key",
        "citation_key",
    ]:

        if hasattr(entry, attribute):

            value = getattr(
                entry,
                attribute,
            )

            if value:
                result["ID"] = str(value)
                break

    for attribute in [
        "entry_type",
        "type",
    ]:

        if hasattr(entry, attribute):

            value = getattr(
                entry,
                attribute,
            )

            if value:
                result["ENTRYTYPE"] = str(value)
                break

    if hasattr(entry, "fields_dict"):

        fields_dict = getattr(
            entry,
            "fields_dict",
        )

        if isinstance(fields_dict, dict):

            for key, value in fields_dict.items():

                result[str(key)] = (
                    _field_object_to_value(value)
                )

    if hasattr(entry, "fields"):

        fields = getattr(
            entry,
            "fields",
        )

        try:

            for field in fields:

                field_key = (
                    getattr(
                        field,
                        "key",
                        None,
                    )
                    or
                    getattr(
                        field,
                        "name",
                        None,
                    )
                )

                field_value = getattr(
                    field,
                    "value",
                    None,
                )

                if field_key:
                    result[str(field_key)] = field_value

        except TypeError:
            pass

    return result


def load_bibtex_file(file_path):
    """
    Loads BibTeX using either bibtexparser v1 or newer APIs.
    """

    try:
        import bibtexparser

    except ImportError as error:

        raise ImportError(
            "bibtexparser is required to import BibTeX files."
        ) from error

    # --------------------------------------------------------
    # bibtexparser v1
    # --------------------------------------------------------

    if hasattr(bibtexparser, "load"):

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="replace",
            ) as handle:

                library = bibtexparser.load(
                    handle
                )

            entries = getattr(
                library,
                "entries",
                [],
            )

            if entries:

                return [
                    bibtex_entry_to_dict(entry)
                    for entry in entries
                ]

        except Exception:
            pass

    # --------------------------------------------------------
    # Newer bibtexparser
    # --------------------------------------------------------

    if hasattr(bibtexparser, "parse_file"):

        library = bibtexparser.parse_file(
            str(file_path)
        )

        entries = getattr(
            library,
            "entries",
            [],
        )

        return [
            bibtex_entry_to_dict(entry)
            for entry in entries
        ]

    raise RuntimeError(
        "The installed bibtexparser version could not be used."
    )


def bibtex_values(
    fields,
    names,
):
    """
    Returns all non-empty values matching BibTeX field names.
    """

    lowered = {
        str(key).lower():
            clean_bibtex_value(value)
        for key, value in fields.items()
    }

    output = []

    for name in names:

        value = lowered.get(
            name.lower(),
            "",
        )

        if (
            value
            and value not in output
        ):
            output.append(value)

    return output


def first_bibtex_value(
    fields,
    names,
):
    """
    Returns the first matching BibTeX value.
    """

    values = bibtex_values(
        fields,
        names,
    )

    return values[0] if values else ""


def combine_bibtex_values(
    fields,
    names,
    separator="; ",
):
    """
    Combines multiple BibTeX fields.

    Useful for multiple keyword fields.
    """

    values = bibtex_values(
        fields,
        names,
    )

    return separator.join(values)


def bibtex_files_to_dataframe(
    files,
    database,
):
    """
    Converts one or more BibTeX files into canonical metadata.
    """

    records = []

    sequence = 1

    for file_path in files:

        entries = load_bibtex_file(
            file_path
        )

        for entry in entries:

            source_id = first_bibtex_value(
                entry,
                [
                    "ID",
                    "key",
                    "citation_key",
                ],
            )

            if not source_id:

                source_id = (
                    f"{database.upper()}-"
                    f"{sequence:04d}"
                )

            title = first_bibtex_value(
                entry,
                ["title"],
            )

            authors = first_bibtex_value(
                entry,
                [
                    "author",
                    "authors",
                ],
            )

            year = first_bibtex_value(
                entry,
                [
                    "year",
                    "date",
                ],
            )

            publication = first_bibtex_value(
                entry,
                [
                    "journal",
                    "booktitle",
                    "publication",
                    "series",
                    "publisher",
                ],
            )

            document_type = first_bibtex_value(
                entry,
                [
                    "document_type",
                    "documenttype",
                    "content_type",
                    "type",
                    "ENTRYTYPE",
                ],
            )

            # ------------------------------------------------
            # DOI
            # ------------------------------------------------

            explicit_doi = first_bibtex_value(
                entry,
                ["doi"],
            )

            doi = extract_doi_from_text(
                explicit_doi
            )

            # DOI may appear in URL or another BibTeX field.
            if not doi:

                doi = extract_doi_from_values(
                    entry.values()
                )

            abstract = first_bibtex_value(
                entry,
                [
                    "abstract",
                    "summary",
                ],
            )

            # ------------------------------------------------
            # KEYWORDS
            # ------------------------------------------------

            keywords = combine_bibtex_values(
                entry,
                [
                    "keywords",
                    "keyword",
                    "author_keywords",
                    "author keywords",
                    "index_keywords",
                    "index keywords",
                    "controlled_terms",
                    "controlled terms",
                    "uncontrolled_terms",
                    "uncontrolled terms",
                ],
            )

            url = first_bibtex_value(
                entry,
                [
                    "url",
                    "link",
                ],
            )

            records.append(
                {
                    "source_id":
                        source_id,

                    "database":
                        DATABASE_NAMES.get(
                            database,
                            database,
                        ),

                    "title":
                        title,

                    "authors":
                        authors,

                    "year":
                        clean_year(year),

                    "publication":
                        publication,

                    "document_type":
                        document_type,

                    "doi":
                        doi,

                    "abstract":
                        abstract,

                    "keywords":
                        keywords,

                    "url":
                        url,

                    "metadata_status":
                        "IMPORTED",

                    "metadata_source":
                        (
                            f"{DATABASE_NAMES.get(database, database)} "
                            f"export"
                        ),
                }
            )

            sequence += 1

    return pd.DataFrame(
        records
    )


# ============================================================
# TABULAR SUPPORT
# ============================================================

def read_tabular_file(file_path):
    """
    Reads CSV, TSV or Excel files with encoding fallback.
    """

    suffix = file_path.suffix.lower()

    if suffix in {
        ".xlsx",
        ".xls",
    }:

        return pd.read_excel(
            file_path
        )

    if suffix in {
        ".csv",
        ".txt",
        ".tsv",
    }:

        encodings = [
            "utf-8-sig",
            "utf-8",
            "latin-1",
            "cp1252",
        ]

        last_error = None

        for encoding in encodings:

            try:

                return pd.read_csv(
                    file_path,
                    sep=None,
                    engine="python",
                    encoding=encoding,
                )

            except Exception as error:
                last_error = error

        raise RuntimeError(
            f"Could not read {file_path.name}: {last_error}"
        )

    raise ValueError(
        f"Unsupported tabular format: {suffix}"
    )


# ============================================================
# COLUMN DISCOVERY
# ============================================================

def find_columns(
    dataframe,
    aliases,
):
    """
    Finds all columns matching any alias.
    """

    normalized_aliases = {
        normalize_header(alias)
        for alias in aliases
    }

    return [
        column
        for column in dataframe.columns
        if normalize_header(column)
        in normalized_aliases
    ]


def extract_first_value_series(
    dataframe,
    aliases,
):
    """
    Combines aliases row-by-row using the first non-empty value.
    """

    columns = find_columns(
        dataframe,
        aliases,
    )

    result = pd.Series(
        "",
        index=dataframe.index,
        dtype="object",
    )

    for column in columns:

        values = (
            dataframe[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        missing = (
            result
            .fillna("")
            .astype(str)
            .str.strip()
            == ""
        )

        result.loc[missing] = (
            values.loc[missing]
        )

    return result


def _combine_unique_values(values):
    """
    Combines unique non-empty strings using '; '.
    """

    output = []

    for value in values:

        value = safe_text(value)

        if not value:
            continue

        if value not in output:
            output.append(value)

    return "; ".join(output)


def extract_combined_series(
    dataframe,
    aliases,
):
    """
    Combines all matching columns row-by-row.

    This is mainly used for keyword fields.
    """

    columns = find_columns(
        dataframe,
        aliases,
    )

    if not columns:

        return pd.Series(
            "",
            index=dataframe.index,
            dtype="object",
        )

    return dataframe[
        columns
    ].apply(
        lambda row:
            _combine_unique_values(
                row.tolist()
            ),
        axis=1,
    )


# ============================================================
# TABULAR CONVERSION
# ============================================================

def tabular_to_dataframe(
    dataframe,
    database,
    column_map,
):
    """
    Converts a database-specific CSV/XLSX table into the canonical
    importer representation.

    Multiple keyword columns are combined automatically.

    Missing DOIs are searched across the entire original row,
    allowing DOI recovery from URL/link/identifier fields.
    """

    result = pd.DataFrame(
        index=dataframe.index
    )

    for canonical_field, aliases in column_map.items():

        if canonical_field == "keywords":

            result[
                canonical_field
            ] = extract_combined_series(
                dataframe,
                aliases,
            )

        else:

            result[
                canonical_field
            ] = extract_first_value_series(
                dataframe,
                aliases,
            )

    # Ensure expected columns.
    for column in [
        "source_id",
        "title",
        "authors",
        "year",
        "publication",
        "document_type",
        "doi",
        "abstract",
        "keywords",
        "url",
    ]:

        if column not in result.columns:
            result[column] = ""

    result[
        "database"
    ] = DATABASE_NAMES.get(
        database,
        database,
    )

    result[
        "metadata_status"
    ] = "IMPORTED"

    result[
        "metadata_source"
    ] = (
        f"{DATABASE_NAMES.get(database, database)} export"
    )

    # ========================================================
    # DOI RECOVERY
    #
    # Search the entire original source row when the explicit
    # DOI column is missing or empty.
    # ========================================================

    for index in dataframe.index:

        current_doi = extract_doi_from_text(
            result.at[index, "doi"]
        )

        if current_doi:

            result.at[
                index,
                "doi",
            ] = current_doi

            continue

        recovered_doi = extract_doi_from_values(
            dataframe.loc[
                index
            ].tolist()
        )

        if recovered_doi:

            result.at[
                index,
                "doi",
            ] = recovered_doi

    return result


# ============================================================
# INTERNAL DEDUPLICATION
# ============================================================

def deduplicate_records(dataframe):
    """
    Removes duplicates inside the same database.

    Priority:
        1. DOI
        2. normalized title
    """

    unique_records = []
    duplicate_records = []

    doi_seen = {}
    title_seen = {}

    for _, row in dataframe.iterrows():

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

        duplicate_reason = ""
        matched_record = None

        if (
            doi_key
            and doi_key in doi_seen
        ):

            duplicate_reason = "DOI"

            matched_record = (
                doi_seen[
                    doi_key
                ]
            )

        elif (
            title_key
            and title_key in title_seen
        ):

            duplicate_reason = "TITLE"

            matched_record = (
                title_seen[
                    title_key
                ]
            )

        if matched_record is not None:

            # Preserve the first record's identity and nonempty values.
            # Recover bibliographic metadata before discarding the duplicate.
            for field in (
                "title", "authors", "year", "publication", "document_type",
                "doi", "abstract", "keywords", "url",
            ):
                if not safe_text(matched_record.get(field, "")):
                    value = record.get(field, "")
                    if safe_text(value):
                        matched_record[field] = value

            # Make recovered identifiers available to subsequent matches.
            if doi_key:
                doi_seen.setdefault(doi_key, matched_record)
            if title_key:
                title_seen.setdefault(title_key, matched_record)

            duplicate = (
                record.copy()
            )

            duplicate[
                "duplicate_reason"
            ] = duplicate_reason

            duplicate[
                "matched_source_id"
            ] = matched_record.get(
                "source_id",
                "",
            )

            duplicate[
                "matched_title"
            ] = matched_record.get(
                "title",
                "",
            )

            duplicate_records.append(
                duplicate
            )

            continue

        unique_records.append(
            record
        )

        if doi_key:

            doi_seen[
                doi_key
            ] = record

        if title_key:

            title_seen[
                title_key
            ] = record

    return (
        pd.DataFrame(
            unique_records,
            columns=dataframe.columns,
        ),
        pd.DataFrame(
            duplicate_records,
            columns=list(dataframe.columns) + [
                "duplicate_reason", "matched_source_id", "matched_title",
            ],
        ),
    )


# ============================================================
# FINALIZE IMPORT
# ============================================================

def finalize_import(
    dataframe,
    database,
):
    """
    Standardizes, recovers DOIs, deduplicates and saves one database.
    """

    standardized = standardize_dataframe(
        dataframe,
        database=database,
    )

    if standardized.empty:
        print("\nNo records imported. Existing output files were preserved.")
        return standardized

    # Extra DOI recovery after canonical standardization.
    standardized = recover_missing_dois(
        standardized
    )

    # --------------------------------------------------------
    # SOURCE IDS
    # --------------------------------------------------------

    for sequence, index in enumerate(
        standardized.index,
        start=1,
    ):

        source_id = safe_text(
            standardized.at[
                index,
                "source_id",
            ]
        )

        if not source_id:

            standardized.at[
                index,
                "source_id",
            ] = (
                f"{database.upper()}-"
                f"{sequence:04d}"
            )

    # --------------------------------------------------------
    # YEAR
    # --------------------------------------------------------

    standardized[
        "year"
    ] = standardized[
        "year"
    ].apply(
        clean_year
    )

    # --------------------------------------------------------
    # DEDUPLICATION
    # --------------------------------------------------------

    (
        unique_records,
        duplicates,
    ) = deduplicate_records(
        standardized
    )

    output_file = OUTPUT_FILES[
        database
    ]

    duplicate_file = (
        PROCESSED_DIR
        / (
            f"{database}"
            f"_duplicates_internal.xlsx"
        )
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    unique_records.to_excel(
        output_file,
        index=False,
    )

    if not duplicates.empty:

        duplicates.to_excel(
            duplicate_file,
            index=False,
        )

    elif duplicate_file.exists():

        duplicate_file.unlink()

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    total_input = len(
        standardized
    )

    total_unique = len(
        unique_records
    )

    total_duplicates = len(
        duplicates
    )

    abstracts = int(
        (
            unique_records[
                "abstract"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
            != ""
        ).sum()
    )

    dois = int(
        (
            unique_records[
                "doi"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
            != ""
        ).sum()
    )

    keywords = int(
        (
            unique_records[
                "keywords"
            ]
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
        f"{DATABASE_NAMES.get(database, database).upper()} "
        f"IMPORT COMPLETED"
    )

    print(
        "=" * 70
    )

    print(
        f"\nRecords imported: "
        f"{total_input}"
    )

    print(
        f"Unique records: "
        f"{total_unique}"
    )

    print(
        f"Internal duplicates: "
        f"{total_duplicates}"
    )

    print(
        f"Records with abstract: "
        f"{abstracts}"
    )

    print(
        f"Records with DOI: "
        f"{dois}"
    )

    print(
        f"Records with keywords: "
        f"{keywords}"
    )

    print(
        "\nOutput file:"
    )

    print(
        output_file
    )

    if total_duplicates:

        print(
            "\nInternal duplicate report:"
        )

        print(
            duplicate_file
        )

    return unique_records