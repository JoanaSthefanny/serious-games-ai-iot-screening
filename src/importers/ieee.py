"""
IEEE Xplore metadata importer.

Expected input:
    one or more BibTeX (.bib) exports inside:

        data/raw/ieee/

Output:
    data/processed/ieee_records.xlsx
"""

from . import (
    bibtex_files_to_dataframe,
    discover_files,
    finalize_import,
)


DATABASE = "ieee"


def main():

    print(
        "=" * 70
    )

    print(
        "IEEE XPLORE IMPORT"
    )

    print(
        "=" * 70
    )

    files = discover_files(
        DATABASE,
        [".bib"],
    )

    if not files:

        print(
            "\nNo IEEE BibTeX files were found."
        )

        print(
            "Place one or more .bib files inside:"
        )

        print(
            "data/raw/ieee/"
        )

        return

    print(
        f"\nBibTeX files found: "
        f"{len(files)}"
    )

    for file in files:

        print(
            f"  - {file.name}"
        )

    dataframe = bibtex_files_to_dataframe(
        files=files,
        database=DATABASE,
    )

    if dataframe.empty:

        print(
            "\nNo records were extracted."
        )

        return

    finalize_import(
        dataframe,
        DATABASE,
    )


if __name__ == "__main__":
    main()