"""
ACM Digital Library metadata importer.

Supported formats:
    .bib
    .csv
    .xlsx
    .xls

Place files inside:
    data/raw/acm/

Output:
    data/processed/acm_records.xlsx
"""

import pandas as pd

from . import (
    bibtex_files_to_dataframe,
    discover_files,
    finalize_import,
    read_tabular_file,
    tabular_to_dataframe,
)


DATABASE = "acm"


ACM_COLUMN_MAP = {

    "source_id": [
        "id",
        "citation key",
        "article number",
        "acm id",
    ],

    "title": [
        "title",
        "article title",
    ],

    "authors": [
        "authors",
        "author",
        "author names",
    ],

    "year": [
        "year",
        "publication year",
        "date",
    ],

    "publication": [
        "publication title",
        "booktitle",
        "journal",
        "proceedings",
        "conference",
    ],

    "document_type": [
        "document type",
        "content type",
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

    # All matching fields are combined.
    "keywords": [
        "keywords",
        "author keywords",
        "index terms",
        "ccs concepts",
    ],

    "url": [
        "url",
        "link",
        "doi url",
        "article url",
    ],
}


def main():

    print(
        "=" * 70
    )

    print(
        "ACM DIGITAL LIBRARY IMPORT"
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
            "\nNo ACM export files were found."
        )

        print(
            "Supported formats: .bib, .csv, .xlsx"
        )

        print(
            "Place files inside data/raw/acm/"
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
                ACM_COLUMN_MAP,
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