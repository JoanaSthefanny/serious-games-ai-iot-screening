"""
Scopus metadata importer.

Supported formats:
    .bib
    .csv
    .xlsx
    .xls

Place files inside:
    data/raw/scopus/

Output:
    data/processed/scopus_records.xlsx
"""

import pandas as pd

from . import (
    bibtex_files_to_dataframe,
    discover_files,
    finalize_import,
    read_tabular_file,
    tabular_to_dataframe,
)


DATABASE = "scopus"


SCOPUS_COLUMN_MAP = {

    "source_id": [
        "eid",
        "id",
        "scopus id",
    ],

    "title": [
        "title",
        "document title",
    ],

    "authors": [
        "authors",
        "author full names",
        "author names",
    ],

    "year": [
        "year",
        "publication year",
        "cover date",
    ],

    "publication": [
        "source title",
        "publication name",
        "journal",
        "source",
    ],

    "document_type": [
        "document type",
        "publication type",
        "type",
    ],

    "doi": [
        "doi",
        "digital object identifier",
    ],

    "abstract": [
        "abstract",
        "abstract text",
    ],

    # All matching keyword columns are combined.
    "keywords": [
        "author keywords",
        "index keywords",
        "keywords",
        "controlled terms",
    ],

    "url": [
        "link",
        "url",
        "document url",
        "doi url",
    ],
}


def main():

    print(
        "=" * 70
    )

    print(
        "SCOPUS IMPORT"
    )

    print(
        "=" * 70
    )

    bib_files = discover_files(
        DATABASE,
        [".bib"],
    )

    table_files = discover_files(
        DATABASE,
        [
            ".csv",
            ".xlsx",
            ".xls",
        ],
    )

    if (
        not bib_files
        and not table_files
    ):

        print(
            "\nNo Scopus export files were found."
        )

        print(
            "Supported formats: .bib, .csv, .xlsx"
        )

        print(
            "Place files inside data/raw/scopus/"
        )

        return

    frames = []

    if bib_files:

        frames.append(
            bibtex_files_to_dataframe(
                files=bib_files,
                database=DATABASE,
            )
        )

    for file in table_files:

        print(
            f"\nReading: {file.name}"
        )

        raw = read_tabular_file(
            file
        )

        frames.append(
            tabular_to_dataframe(
                raw,
                DATABASE,
                SCOPUS_COLUMN_MAP,
            )
        )

    dataframe = pd.concat(
        frames,
        ignore_index=True,
    )

    return finalize_import(
        dataframe,
        DATABASE,
    )


if __name__ == "__main__":
    main()