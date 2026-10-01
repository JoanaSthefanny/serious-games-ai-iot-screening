# Changelog

All notable changes to this project will be documented in this file.

This repository contains the public and reproducible implementation of the semi-automated screening pipeline developed for a systematic mapping study involving serious games, artificial intelligence, Internet of Things technologies, and health applications.

The project follows a simplified versioning approach for the public research software.

---

## [Unreleased]

### Planned

- Additional validation with independent datasets.
- Expanded example datasets.
- Improvements to database export documentation.
- Additional automated tests.
- Support for future metadata formats when required.

---

## [1.0.0] - 2026-09-30

### Added

- Initial public release of the research screening pipeline.
- Unified command-line interface through `src/main.py`.
- Database-specific metadata importers for:
  - IEEE Xplore;
  - PubMed;
  - ACM Digital Library;
  - Scopus;
  - Engineering Village / Compendex;
  - Springer Link.
- Support for BibTeX, NBIB, CSV, and Excel metadata exports where applicable.
- Canonical metadata schema shared across databases.
- Automatic DOI normalization.
- DOI recovery from URLs and other metadata fields.
- Consolidation of multiple keyword fields.
- Internal duplicate detection using:
  1. normalized DOI;
  2. normalized title.
- Cross-database duplicate detection.
- Persistent `MASTER-XXXX` identifiers.
- Master dataset creation and incremental updating.
- Springer Nature metadata and abstract enrichment support.
- Environment-variable configuration through `.env`.
- Public `.env.example` template.
- Gemini-assisted structured evidence classification.
- Deterministic screening layer separated from LLM interpretation.
- Three screening outcomes:
  - `RETAIN`;
  - `UNCERTAIN`;
  - `EXCLUDE`.
- Conservative handling of missing abstracts.
- Checkpoint-based screening execution.
- Automatic recovery after interrupted screening runs.
- Protection against interpreting API failures as eligibility exclusions.
- Safety-rescue mechanisms for potentially ambiguous screening cases.
- Separate screening workbooks for each database.
- Audit sheets for:
  - retained records;
  - uncertain records;
  - excluded records;
  - safety rescues;
  - records without abstracts;
  - API errors.
- Methodological documentation.
- Screening decision-rule documentation.
- Calibration documentation.
- Data-format documentation.
- Portuguese screening prompt used by the pipeline.
- English prompt translation for documentation purposes.
- MIT License.
- Citation metadata through `CITATION.cff`.

### Screening configuration

The first public release documents the following screening configuration:

```text
Gemini model:       gemini-3.5-flash-lite
Prompt version:     1.6
Classifier version: 1.8
```

### Development and calibration

The final classifier configuration was developed using manually assessed records and a sensitivity-oriented calibration process.

The documented calibration included:

```text
IEEE calibration:
Relevant records preserved: 11/11
False negatives: 0

Manually non-relevant records:
EXCLUDE:   19/22
UNCERTAIN:  3/22
RETAIN:     0/22
```

A broader positive sensitivity test included 26 previously included studies from multiple databases:

```text
Preserved: 26/26
Automatically excluded: 0
```

These records contributed to classifier development and therefore these results should not be interpreted as independent external validation.

### Documented screening run

The screening workflow documented for the associated systematic mapping study processed:

```text
Total records: 1,046

RETAIN:      37
UNCERTAIN:  141
EXCLUDE:    868

Safety rescues: 40
Records without abstracts: 74
Remaining technical errors: 0
```

The automated screening outcomes do not represent final full-text inclusion decisions.