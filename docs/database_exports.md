# Database Metadata Export Guide

This document describes how bibliographic metadata exported from the supported databases should be organized before running the screening pipeline.

The repository does **not** include the original database exports used in the associated systematic mapping study. These files may be subject to database licensing or access restrictions and are therefore excluded from version control.

Users should export their own search results and place them in the appropriate local directory.

---

# 1. Directory structure

Metadata files should be placed under:

```text
data/raw/
```

using a separate directory for each database:

```text
serious-games-ai-iot-screening/
├── data/
│   └── raw/
│       ├── ieee/
│       ├── pubmed/
│       ├── acm/
│       ├── scopus/
│       ├── compendex/
│       └── springer/
├── docs/
├── examples/
├── prompts/
├── src/
├── README.md
└── requirements.txt
```

The `data/` directory is intentionally excluded from Git through `.gitignore`.

Therefore, these folders may not be present immediately after cloning the repository.

The pipeline creates the expected database directories when required. They may also be created manually before adding the exported files.

For example, on Windows PowerShell:

```powershell
mkdir data
mkdir data/raw
mkdir data/raw/ieee
mkdir data/raw/pubmed
mkdir data/raw/acm
mkdir data/raw/scopus
mkdir data/raw/compendex
mkdir data/raw/springer
```

On Linux or macOS:

```bash
mkdir -p data/raw/{ieee,pubmed,acm,scopus,compendex,springer}
```

---

# 2. Supported databases and formats

| Database | Local directory | Recommended format | Other supported formats |
|---|---|---|---|
| IEEE Xplore | `data/raw/ieee/` | BibTeX (`.bib`) | — |
| PubMed | `data/raw/pubmed/` | NBIB (`.nbib`) | BibTeX (`.bib`) |
| ACM Digital Library | `data/raw/acm/` | BibTeX (`.bib`) | CSV (`.csv`), Excel (`.xlsx`, `.xls`) |
| Scopus | `data/raw/scopus/` | CSV or BibTeX | `.csv`, `.bib`, `.xlsx`, `.xls` |
| Engineering Village / Compendex | `data/raw/compendex/` | CSV or Excel | `.csv`, `.xlsx`, `.xls`, `.bib` |
| Springer Link | `data/raw/springer/` | CSV or Excel | `.csv`, `.xlsx`, `.xls` |

Multiple supported files may be placed in the same database directory.

The importer processes the supported files found in the corresponding folder and consolidates their metadata.

---

# 3. Recommended metadata fields

When a database allows the user to choose which fields are exported, the most complete bibliographic export available should be selected.

Whenever possible, the export should contain:

```text
Title
Authors
Publication year
Publication or source title
Document type
Abstract
DOI
Keywords
Database record identifier
URL
```

Some databases divide keywords into multiple fields, such as author keywords, index terms, controlled terms, MeSH terms, or uncontrolled terms.

The importers attempt to combine these fields into the canonical `keywords` field whenever applicable.

The pipeline also attempts to recover missing DOI values from other metadata fields, such as DOI URLs or identifier strings.

---

# 4. IEEE Xplore

## Recommended format

```text
BibTeX (.bib)
```

Export the bibliographic records retrieved by the search and save the resulting `.bib` file in:

```text
data/raw/ieee/
```

Example:

```text
data/raw/ieee/ieee_search_results.bib
```

The filename itself is not important.

The importer extracts available fields such as title, authors, year, publication venue, abstract, DOI, keywords, and URL.

If the search results must be exported in multiple batches, all `.bib` files may be placed in the same directory:

```text
data/raw/ieee/ieee_results_01.bib
data/raw/ieee/ieee_results_02.bib
data/raw/ieee/ieee_results_03.bib
```

The importer will consolidate the records.

---

# 5. PubMed

## Recommended format

```text
NBIB (.nbib)
```

Save the exported file in:

```text
data/raw/pubmed/
```

Example:

```text
data/raw/pubmed/pubmed_results.nbib
```

BibTeX exports are also supported:

```text
data/raw/pubmed/pubmed_results.bib
```

For NBIB files, the importer can extract information including PMID, title, authors, journal information, publication year, publication type, abstract, DOI, MeSH terms, and other available keywords.

When possible, the complete PubMed record should be exported rather than title-only or citation-only data.

---

# 6. ACM Digital Library

Supported formats include:

```text
.bib
.csv
.xlsx
.xls
```

BibTeX is recommended when it contains the complete metadata required for the study.

Place exported files in:

```text
data/raw/acm/
```

Examples:

```text
data/raw/acm/acm_results.bib
```

or:

```text
data/raw/acm/acm_results.csv
```

If tabular exports are used, the importer attempts to identify commonly used ACM fields corresponding to title, authors, abstract, DOI, publication information, keywords, index terms, and URLs.

---

# 7. Scopus

Supported formats include:

```text
.csv
.bib
.xlsx
.xls
```

Place exported records in:

```text
data/raw/scopus/
```

Example:

```text
data/raw/scopus/scopus_results.csv
```

When Scopus provides an option to choose export fields, include the complete bibliographic information whenever possible, particularly:

```text
Citation information
Bibliographical information
Abstract
Author keywords
Index keywords
DOI
Electronic identifier
Source information
```

The importer combines available keyword-related fields into the canonical `keywords` column.

---

# 8. Engineering Village / Compendex

Supported formats include:

```text
.csv
.xlsx
.xls
.bib
```

Place exported records in:

```text
data/raw/compendex/
```

Example:

```text
data/raw/compendex/compendex_results.xlsx
```

When the export interface permits field selection, include as much bibliographic metadata as possible.

Relevant keyword fields may include:

```text
Author Keywords
Controlled Terms
Uncontrolled Terms
```

These fields are combined by the importer when available.

---

# 9. Springer Link

Supported formats include:

```text
.csv
.xlsx
.xls
```

Place Springer records in:

```text
data/raw/springer/
```

Example:

```text
data/raw/springer/springer_results.csv
```

The exported metadata may contain records without abstracts.

The repository therefore includes an optional Springer Nature metadata enrichment step that can attempt to retrieve missing abstracts using the Springer Nature API.

To use this feature, configure:

```text
SPRINGER_API_KEY
```

in the local `.env` file.

See:

```text
.env.example
```

for API configuration instructions.

Records for which an abstract cannot be retrieved are not automatically excluded from screening solely because of missing abstract information.

---

# 10. File naming

There is no required filename for database exports.

For example, all of the following are valid:

```text
data/raw/scopus/results.csv
data/raw/scopus/scopus_2026.csv
data/raw/scopus/export_part_1.csv
data/raw/scopus/export_part_2.csv
```

The important requirement is that the file:

1. is placed in the correct database directory; and
2. uses one of the supported formats for that database.

---

# 11. Importing the records

After placing the exported metadata files in their corresponding directories, run:

```bash
python src/main.py
```

From the main menu, select the metadata import option and choose the corresponding database.

The importer will standardize database-specific metadata into the common schema used by the project.

Processed records are written to the local:

```text
data/processed/
```

directory.

This directory is also excluded from Git because it contains generated research data.

---

# 12. Canonical metadata representation

Regardless of the original database format, imported records are converted to a common representation containing fields such as:

```text
master_id
source_id
database
title
authors
year
publication
document_type
doi
abstract
keywords
url
metadata_status
metadata_source
```

For a complete description of these fields, see:

```text
docs/data_format.md
```

---

# 13. Duplicate handling

Duplicate detection is performed after metadata normalization.

The pipeline primarily uses:

```text
1. normalized DOI
2. normalized title
```

for duplicate identification.

Duplicate detection may occur both within individual database imports and later during construction of the cross-database master dataset.

Because bibliographic databases may provide incomplete or inconsistent metadata, duplicate detection results should remain auditable and may require human verification in ambiguous cases.

---

# 14. Raw data availability

The original search exports used in the associated systematic mapping study are not included in this public repository.

The public repository provides:

```text
import scripts
metadata normalization rules
screening logic
screening prompts
documentation
synthetic examples
```

but does not redistribute proprietary database exports or article full texts.

Users who wish to reproduce the workflow should perform their own searches in the corresponding bibliographic databases and export the retrieved metadata using the formats described in this document.