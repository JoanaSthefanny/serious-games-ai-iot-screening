"""
Engineering Village / Compendex metadata importer.

Supported formats:
    .bib
    .csv
    .xlsx
    .xls

Place files inside:
    data/raw/compendex/

Output:
    data/processed/compendex_records.xlsx
"""

import pandas as pd

from . import (
    bibtex_files_to_dataframe,
    discover_files,
    finalize_import,
    read_tabular_file,
    tabular_to_dataframe,
)


DATABASE = "compendex"


COMPENDEX_COLUMN_MAP = {

    "source_id": [
        "accession number",
        "accession no",
        "accession number (an)",
        "record id",
        "id",
    ],

    "title": [
        "title",
        "document title",
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
        "publication date",
    ],

    "publication": [
        "source",
        "source title",
        "publication",
        "journal",
        "conference title",
    ],

    "document_type": [
        "document type",
        "publication type",
        "content type",
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

    # All are preserved together.
    "keywords": [
        "author keywords",
        "controlled terms",
        "uncontrolled terms",
        "index terms",
        "keywords",
    ],

    "url": [
        "url",
        "link",
        "document url",
        "doi url",
    ],
}


def main():

    print(
        "=" * 70
    )

    print(
        "ENGINEERING VILLAGE / COMPENDEX IMPORT"
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
            "\nNo Compendex export files were found."
        )

        print(
            "Supported formats: .bib, .csv, .xlsx"
        )

        print(
            "Place files inside data/raw/compendex/"
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
                COMPENDEX_COLUMN_MAP,
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