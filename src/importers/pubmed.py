"""
PubMed metadata importer.

Supported formats:
    .nbib
    .bib

Place files inside:
    data/raw/pubmed/

Output:
    data/processed/pubmed_records.xlsx
"""

import re

import pandas as pd

from . import (
    DATABASE_NAMES,
    bibtex_files_to_dataframe,
    clean_year,
    discover_files,
    extract_doi_from_values,
    finalize_import,
    safe_text,
)


DATABASE = "pubmed"


# ============================================================
# NBIB
# ============================================================

def parse_nbib_file(file_path):
    """
    Parses PubMed NBIB / MEDLINE format.
    """

    records = []

    current_record = {}
    current_tag = None

    with open(
        file_path,
        "r",
        encoding="utf-8",
        errors="replace",
    ) as handle:

        for raw_line in handle:

            line = raw_line.rstrip(
                "\r\n"
            )

            # ------------------------------------------------
            # END OF RECORD
            # ------------------------------------------------

            if not line.strip():

                if current_record:

                    records.append(
                        current_record
                    )

                    current_record = {}
                    current_tag = None

                continue

            # ------------------------------------------------
            # MEDLINE TAG
            # ------------------------------------------------

            match = re.match(
                r"^([A-Z0-9]{2,4})\s*-\s?(.*)$",
                line,
            )

            if match:

                tag = match.group(1)

                value = match.group(
                    2
                ).strip()

                current_tag = tag

                current_record.setdefault(
                    tag,
                    [],
                )

                current_record[
                    tag
                ].append(
                    value
                )

                continue

            # ------------------------------------------------
            # CONTINUATION LINE
            # ------------------------------------------------

            if (
                current_tag
                and line.startswith(" ")
            ):

                continuation = (
                    line.strip()
                )

                if continuation:

                    values = current_record[
                        current_tag
                    ]

                    if values:

                        values[-1] = (
                            values[-1]
                            + " "
                            + continuation
                        )

    if current_record:

        records.append(
            current_record
        )

    return records


# ============================================================
# NBIB UTILITIES
# ============================================================

def first_tag(
    record,
    tag,
):

    values = record.get(
        tag,
        [],
    )

    if not values:
        return ""

    return safe_text(
        values[0]
    )


def tag_values(
    record,
    tag,
):

    return [
        safe_text(value)
        for value in record.get(
            tag,
            [],
        )
        if safe_text(value)
    ]


def join_tags(
    record,
    tags,
    separator="; ",
):
    """
    Combines values from multiple NBIB tags.
    """

    combined = []

    for tag in tags:

        for value in tag_values(
            record,
            tag,
        ):

            if value not in combined:
                combined.append(value)

    return separator.join(
        combined
    )


# ============================================================
# NBIB TO DATAFRAME
# ============================================================

def nbib_records_to_dataframe(records):

    output = []

    for sequence, record in enumerate(
        records,
        start=1,
    ):

        pmid = first_tag(
            record,
            "PMID",
        )

        source_id = (
            pmid
            if pmid
            else f"PUBMED-{sequence:04d}"
        )

        title = first_tag(
            record,
            "TI",
        )

        authors = (
            join_tags(
                record,
                ["FAU"],
            )
            or
            join_tags(
                record,
                ["AU"],
            )
        )

        year = clean_year(
            first_tag(
                record,
                "DP",
            )
        )

        publication = (
            first_tag(
                record,
                "JT",
            )
            or
            first_tag(
                record,
                "TA",
            )
        )

        document_type = join_tags(
            record,
            ["PT"],
        )

        abstract = join_tags(
            record,
            ["AB"],
            separator=" ",
        )

        # ----------------------------------------------------
        # KEYWORDS
        #
        # OT = Other Term
        # MH = MeSH Headings
        # ----------------------------------------------------

        keywords = join_tags(
            record,
            [
                "OT",
                "MH",
            ],
        )

        # ----------------------------------------------------
        # DOI
        #
        # PubMed commonly places DOI in LID or AID.
        # ----------------------------------------------------

        doi = extract_doi_from_values(
            tag_values(
                record,
                "LID",
            )
            +
            tag_values(
                record,
                "AID",
            )
        )

        url = (
            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            if pmid
            else ""
        )

        output.append(
            {
                "source_id":
                    source_id,

                "database":
                    DATABASE_NAMES[
                        DATABASE
                    ],

                "title":
                    title,

                "authors":
                    authors,

                "year":
                    year,

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
                    "PubMed NBIB export",
            }
        )

    return pd.DataFrame(
        output
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 70
    )

    print(
        "PUBMED IMPORT"
    )

    print(
        "=" * 70
    )

    nbib_files = discover_files(
        DATABASE,
        [".nbib"],
    )

    bib_files = discover_files(
        DATABASE,
        [".bib"],
    )

    if (
        not nbib_files
        and not bib_files
    ):

        print(
            "\nNo PubMed export files were found."
        )

        print(
            "Supported formats: .nbib and .bib"
        )

        print(
            "Place files inside data/raw/pubmed/"
        )

        return

    frames = []

    for file in nbib_files:

        print(
            f"\nReading NBIB: "
            f"{file.name}"
        )

        records = parse_nbib_file(
            file
        )

        frames.append(
            nbib_records_to_dataframe(
                records
            )
        )

    if bib_files:

        print(
            f"\nBibTeX files found: "
            f"{len(bib_files)}"
        )

        frames.append(
            bibtex_files_to_dataframe(
                files=bib_files,
                database=DATABASE,
            )
        )

    if not frames:

        print(
            "\nNo records were extracted."
        )

        return

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