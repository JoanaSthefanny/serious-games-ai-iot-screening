# Data Format

## Overview

All database-specific metadata are converted into a common canonical structure before incorporation into the master dataset.

This enables the same deduplication and screening procedures to be applied across all supported databases.

---

## Canonical Master Schema

The master dataset uses the following fields.

| Field | Description |
|---|---|
| `master_id` | Persistent identifier assigned by the pipeline |
| `source_id` | Identifier provided by the original database or importer |
| `database` | Database from which the retained master record originated |
| `title` | Article or publication title |
| `authors` | Author information |
| `year` | Publication year |
| `publication` | Journal, conference, book, or other publication venue |
| `document_type` | Article, conference paper, chapter, etc. |
| `doi` | Normalized Digital Object Identifier |
| `abstract` | Abstract text |
| `keywords` | Combined keyword metadata |
| `url` | Source or article URL |
| `metadata_status` | Metadata acquisition/enrichment status |
| `metadata_source` | Source from which metadata were obtained |

---

## MASTER Identifier

Every unique master record receives a persistent identifier:

```text
MASTER-0001
MASTER-0002
MASTER-0003
...
```

Once assigned, existing identifiers are preserved.

New records receive new sequential identifiers.

---

## DOI Format

DOIs are normalized before duplicate detection.

Accepted source formats include:

```text
10.1007/s11036-025-02473-6
```

```text
https://doi.org/10.1007/s11036-025-02473-6
```

```text
http://dx.doi.org/10.1007/s11036-025-02473-6
```

```text
DOI: 10.1007/s11036-025-02473-6
```

The canonical stored form is:

```text
10.1007/s11036-025-02473-6
```

---

## DOI Recovery

When the explicit DOI field is empty, the importer searches other metadata fields for DOI-compatible strings.

Possible sources include:

- URL;
- Link;
- article URL;
- identifiers;
- other exported metadata columns.

This recovery step occurs before deduplication.

---

## Title Handling

The original title is preserved in the dataset.

A normalized representation is generated only internally for duplicate detection.

Normalization may include:

- lowercasing;
- accent removal;
- punctuation normalization;
- whitespace normalization.

The stored publication title is not replaced by the normalized title.

---

## Abstract Handling

The original abstract is preserved whenever available.

Existing abstracts should not be overwritten by empty API responses.

Records without abstracts remain eligible for human review.

A missing abstract does not represent an automatic exclusion.

---

## Keyword Handling

Different databases provide different types of keyword metadata.

The importers attempt to preserve all useful keyword categories.

Examples include:

### Scopus

```text
Author Keywords
Index Keywords
```

### PubMed

```text
Other Terms
MeSH Headings
```

### Compendex

```text
Author Keywords
Controlled Terms
Uncontrolled Terms
```

When more than one keyword field is available, values are combined using:

```text
;
```

Example:

```text
serious games; rehabilitation; machine learning; wearable sensors
```

---

## Database Names

The canonical database names are:

```text
IEEE Xplore
PubMed
ACM Digital Library
Scopus
Engineering Village / Compendex
Springer Link
```

---

## Raw Data Location

Original database exports should be placed under:

```text
data/raw/
```

using one subdirectory per database:

```text
data/raw/
├── ieee/
├── pubmed/
├── acm/
├── scopus/
├── compendex/
└── springer/
```

---

## Processed Data Location

Standardized outputs are generated under:

```text
data/processed/
```

Examples:

```text
ieee_records.xlsx
pubmed_records.xlsx
acm_records.xlsx
scopus_records.xlsx
compendex_records.xlsx
springer_records.xlsx
master_records.xlsx
```

---

## Database-Specific Input Formats

### IEEE Xplore

Primary supported format:

```text
BibTeX (.bib)
```

### PubMed

Supported formats:

```text
NBIB (.nbib)
BibTeX (.bib)
```

### ACM Digital Library

Supported formats:

```text
BibTeX (.bib)
CSV (.csv)
Excel (.xlsx)
```

### Scopus

Supported formats:

```text
BibTeX (.bib)
CSV (.csv)
Excel (.xlsx)
```

### Engineering Village / Compendex

Supported formats:

```text
BibTeX (.bib)
CSV (.csv)
Excel (.xlsx)
```

### Springer Link

Supported formats:

```text
CSV (.csv)
Excel (.xlsx)
```

Springer metadata may subsequently be enriched through the Springer Nature API.

---

## Screening Output Schema

Each screened record contains identifying metadata plus the following fields:

| Field | Description |
|---|---|
| `model` | LLM model used |
| `prompt_version` | Screening prompt version |
| `classifier_version` | Deterministic classifier version |
| `serious_game` | Serious-game classification |
| `evidence_serious_game` | Supporting evidence |
| `gamification_only` | Gamification-only classification |
| `evidence_gamification` | Supporting evidence |
| `health` | Health-context classification |
| `evidence_health` | Supporting evidence |
| `ai` | AI classification |
| `evidence_ai` | Supporting evidence |
| `iot` | IoT classification |
| `evidence_iot` | Supporting evidence |
| `secondary_or_incomplete` | Publication-type classification |
| `evidence_study_type` | Supporting evidence |
| `decision` | Final deterministic screening outcome |
| `decision_reason` | Reason produced by deterministic rules |
| `safety_rescue` | Whether a safety rescue was activated |
| `rescue_code` | Safety-rescue identifier |
| `api_status` | API execution status |
| `api_error` | Technical error message, if applicable |

---

## Screening Decision Values

Possible decision values are:

```text
RETAIN
UNCERTAIN
EXCLUDE
API_ERROR
```

`API_ERROR` is a technical state rather than an eligibility decision.

---

## IoT Values

Possible IoT classifications are:

```text
EXPLICIT_IOT
FUNCTIONALLY_COMPATIBLE
NO
UNCERTAIN
```

---

## Missing Abstracts

Records without abstracts are represented with:

```text
api_status = NO_ABSTRACT
decision = UNCERTAIN
```

They remain available for manual review.

---

## Output Workbook

Each database screening workbook contains separate sheets for:

```text
Summary
Results
RETAIN
UNCERTAIN
EXCLUDE
Safety_rescue
No_abstract
API_errors
```

This structure supports auditing of both automated decisions and cases requiring human intervention.