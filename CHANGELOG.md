# Changelog

All notable changes to this project will be documented in this file.

This repository provides the public implementation of the semi-automated screening pipeline developed for a systematic mapping study involving serious games, artificial intelligence, Internet of Things technologies, and health applications.

Public software releases are versioned separately from the screening prompt and classifier.

Historical research results retain their recorded configuration identifiers. Software updates do not retroactively change those results.

---

## [Unreleased]

### Fixed

- Recover Compendex BibTeX v2 entries rejected only for repeated copyright fields; stop the import on other rejected blocks.
- Recover Compendex index terms from `key` and `note`.
- Preserve volume metadata and avoid title-only merging when volume identifiers conflict or the match is ambiguous.
- Prevent title-based merging when both records have non-empty, different normalized DOIs.
- Match Springer checkpoint records by DOI first, then by a unique compatible normalized-title candidate; preserve separate records when title candidates have conflicting DOIs or volumes, or when the match is ambiguous.
- Preserve existing Springer abstracts and API checkpoint metadata while recovering missing bibliographic fields and registering recovered DOIs for subsequent matches.
- Return the Springer enrichment dataset only after the current collection has been saved successfully, including newly imported records and previously recovered metadata.
- Stop the complete Springer workflow before the master update and screening when enrichment fails, is interrupted, or returns an empty or invalid result, including when the API key is unavailable.
- Prevent the complete workflow from silently using an outdated Springer enrichment file after an unsuccessful enrichment step.
- Preserve existing processed outputs when an import produces no records.
- Preserve empty-table columns during internal deduplication.
- Recover missing bibliographic metadata from internal duplicates.
- Return imported records from all six importers and stop the complete workflow after a failed or empty import.
- Return the master dataset only after the master workbook and duplicate report have been saved successfully.
- Stop the complete workflow before screening when the master update fails, is interrupted, or returns an empty or invalid result.
- Stop on checkpoint write failures without converting successful classifications into API errors.
- Align screening package metadata with prompt v1.9 and classifier v1.11.
- Declare `xlrd` for supported legacy `.xls` imports.
- Correct documentation inconsistencies concerning screening rules, configuration identifiers, and historical results.

### Changed

- Update the screening prompt to v1.9.
- Clarify AI uncertainty when a computational assessment function is described but its analytical method is omitted.
- Clarify joint interpretation of title and abstract for computer vision and gesture-recognition systems.
- Require supporting evidence before classifying a publication as secondary or incomplete; an overview of the authors' own system or omitted abstract details is insufficient.
- Update the classifier to v1.11.
- Add `RESGATE_AAL_METADADOS_INCOMPLETOS`, which routes qualifying assistive-health cases to `UNCERTAIN` without changing their original criterion labels.
- Align the README and methodological documentation with the current prompt, classifier, and four implemented safety-rescue rules.
- Distinguish the current implementation from the original research execution.
- Clarify that the historical 15-study positive test includes the same 11 relevant IEEE studies plus two PubMed and two ACM studies.
- Update workflow test fixtures to require a non-empty DataFrame from successful Springer enrichment instead of treating `None` as success.

### Added

- English translation of screening prompt v1.9 for transparency, reproducibility, and accessibility, with a note identifying the Portuguese prompt as the version used for screening and explaining that translated prompts may produce different model responses.
- An offline regression suite containing 27 tests, using synthetic records, temporary files, and mocked external operations.
- Regression coverage for import safety, metadata recovery, Compendex parsing, volume preservation, master-dataset updates, checkpoint failures, and screening decision precedence.
- Regression tests ensuring that records with the same title and different DOIs remain separate.
- Springer regression tests covering conflicting DOIs, distinct volumes, ambiguous title matches, and metadata recovery through a unique compatible match.
- Workflow regression tests ensuring that screening does not start after an invalid master-update result, a simulated write failure, or a user interruption, and that successful workflows continue for all six databases.
- Springer workflow regression tests ensuring that invalid enrichment results, exceptions, interruptions, and missing API keys stop the workflow before the master update and screening.
- Regression coverage verifying that Springer enrichment saves newly imported records together with an existing checkpoint, returns the saved collection, and preserves the previous checkpoint when atomic replacement fails.

### Planned

- Additional evaluation using independent datasets.
- Expanded synthetic example datasets.
- Improvements to database export documentation.
- Additional automated tests.
- Support for future metadata formats when required.

---

## [1.0.0] - 2026-09-30

Initial public release of the research screening pipeline.

The research results documented below were produced by the original research scripts. Their counts and recorded configuration identifiers are preserved.

They do not represent a complete rerun with the prompt and classifier described under `Unreleased`.

### Added

- Unified command-line interface through `src/main.py`.
- Database-specific metadata importers for IEEE Xplore, PubMed, ACM Digital Library, Scopus, Engineering Village / Compendex, and Springer Link.
- Support for BibTeX, NBIB, CSV, and Excel metadata exports where applicable.
- Canonical metadata schema shared across databases.
- Automatic DOI normalization and DOI recovery from URLs and other metadata fields.
- Consolidation of multiple keyword fields.
- Internal duplicate detection based on normalized DOI and normalized title.
- Cross-database duplicate detection.
- Persistent `MASTER-XXXX` identifiers.
- Master-dataset creation and incremental updating.
- Springer Nature metadata and abstract enrichment support.
- Environment-variable configuration through `.env`.
- Public `.env.example` template.
- Gemini-assisted structured evidence classification.
- Deterministic screening logic separated from LLM interpretation.
- Three screening outcomes: `RETAIN`, `UNCERTAIN`, and `EXCLUDE`.
- Conservative handling of missing abstracts.
- Checkpoint-based execution and resumption after interruptions.
- Protection against interpreting API failures as eligibility exclusions.
- Safety-rescue mechanisms for ambiguous screening cases.
- Separate screening workbooks for each database.
- Audit sheets for retained, uncertain, excluded, rescued, missing-abstract, and API-error records.
- Methodological documentation.
- Screening decision-rule documentation.
- Calibration documentation.
- Data-format documentation.
- Portuguese screening prompt used by the pipeline.
- English prompt translation for documentation purposes.
- MIT License.
- Citation metadata through `CITATION.cff`.

### Recorded Historical Research Configuration

The version identifiers recorded for the original research execution are:

```text
Gemini model:       gemini-3.5-flash-lite
Prompt version:     1.6
Classifier version: 1.8
```

These identifiers describe the historical execution records, not the current implementation.

### Historical Development and Calibration

The original research classifier was developed using manually assessed records and a sensitivity-oriented calibration process.

The documented IEEE calibration included:

```text
Relevant records preserved: 11 / 11
Automatically excluded relevant records: 0

Manually non-relevant records:
EXCLUDE:   19 / 22
UNCERTAIN:  3 / 22
RETAIN:     0 / 22
```

A multi-database positive test included:

```text
IEEE Xplore:         11 studies
PubMed:               2 studies
ACM Digital Library:  2 studies
Total:               15 studies

Preserved: 15 / 15
Automatically excluded: 0
```

The 11 IEEE studies in this test were the same relevant studies used in the IEEE calibration subset. The two sets must not be counted as independent samples.

A study was considered preserved when its screening outcome was either `RETAIN` or `UNCERTAIN`.

These records contributed to classifier development. The results describe calibration performance and do not constitute independent external validation.

### Historical Screening Run

The original research execution processed:

```text
Total records: 1,046

RETAIN:     37
UNCERTAIN: 141
EXCLUDE:   868

Safety rescues: 40
Records without abstracts: 74
Remaining technical errors: 0
```

Records without abstracts were included in `UNCERTAIN`.

These counts belong to the historical execution and remain unchanged by subsequent software updates.

The automated outcomes do not represent final full-text inclusion decisions.