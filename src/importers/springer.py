"""
Springer Link metadata importer.

Supported formats:
    .csv
    .xlsx
    .xls

Place files inside:
    data/raw/springer/

Output:
    data/processed/springer_records.xlsx

Missing abstracts can later be enriched through:
    data_management/springer_metadata.py
"""

import pandas as pd

from . import (
    discover_files,
    finalize_import,
    read_tabular_file,
    tabular_to_dataframe,
)


DATABASE = "springer"


SPRINGER_COLUMN_MAP = {

    "source_id": [
        "item id",
        "record id",
        "identifier",
        "id",
    ],

    "title": [
        "item title",
        "title",
        "article title",
        "chapter title",
    ],

    "authors": [
        "authors",
        "author",
        "creator",
    ],

    "year": [
        "publication year",
        "year",
        "date published",
        "publication date",
        "online date",
    ],

    "publication": [
        "publication title",
        "journal title",
        "book title",
        "book series title",
        "publication",
        "journal",
    ],

    "document_type": [
        "content type",
        "document type",
        "publication type",
        "type",
    ],

    "doi": [
        "item doi",
        "doi",
        "digital object identifier",
    ],

    "abstract": [
        "abstract",
        "abstract text",
        "description",
    ],

    "keywords": [
        "keywords",
        "keyword",
        "subject terms",
        "subjects",
    ],

    "url": [
        "url",
        "item url",
        "link",
        "doi url",
    ],
}


def main():

    print(
        "=" * 70
    )

    print(
        "SPRINGER LINK IMPORT"
    )

    print(
        "=" * 70
    )

    files = discover_files(
        DATABASE,
        [
            ".csv",
            ".xlsx",
            ".xls",
        ],
    )

    if not files:

        print(
            "\nNo Springer export files were found."
        )

        print(
            "Supported formats: .csv and .xlsx"
        )

        print(
            "Place files inside data/raw/springer/"
        )

        return

    print(
        f"\nFiles found: "
        f"{len(files)}"
    )

    frames = []

    for file in files:

        print(
            f"\nReading: {file.name}"
        )

        raw = read_tabular_file(
            file
        )

        print(
            f"  Rows: {len(raw)}"
        )

        frames.append(
            tabular_to_dataframe(
                raw,
                DATABASE,
                SPRINGER_COLUMN_MAP,
            )
        )

    dataframe = pd.concat(
        frames,
        ignore_index=True,
    )

    finalize_import(
        dataframe,
        DATABASE,
    )


if __name__ == "__main__":
    main()