# Serious Games AI-IoT Screening

Semi-automated screening pipeline for systematic mapping studies involving **serious games**, **artificial intelligence (AI)**, **Internet of Things (IoT)** technologies, and **health applications**.

This repository contains the reproducible research software developed to support the title, abstract, and keyword screening stage of a systematic mapping study.

The pipeline combines:

- database-specific metadata import;
- metadata standardization;
- DOI recovery;
- internal and cross-database duplicate detection;
- persistent master-record identifiers;
- Springer metadata enrichment;
- LLM-assisted evidence classification;
- deterministic screening rules;
- conservative safety-rescue mechanisms;
- checkpoint-based execution;
- human-review routing.

The system was designed to prioritize **screening sensitivity** and reduce the risk of automatically excluding potentially relevant studies.

---

# Research Context

The pipeline was developed for a systematic mapping study investigating studies that simultaneously involve:

1. **Serious games or equivalent game-based interventions**
2. **Health-related applications**
3. **Artificial Intelligence**
4. **Internet of Things technologies or functionally IoT-compatible architectures**

The automated stage does not replace human judgment.

Instead, the system assists screening by classifying available evidence and applying transparent deterministic rules.

Final eligibility decisions remain under human supervision.

---

# Using the Pipeline for Other Reviews

Although the screening configuration included in this repository was developed specifically for **serious games, AI, IoT, and health**, the overall software architecture can also be used as a starting point for other systematic reviews or systematic mapping studies.

Several parts of the pipeline are relatively independent of the research topic, including:

- bibliographic metadata import;
- metadata standardization;
- DOI recovery;
- keyword consolidation;
- duplicate detection;
- master-dataset management;
- checkpoint-based execution;
- API-error handling;
- Excel output generation.

However, the screening classifier itself is **topic-specific**.

Researchers who adapt this repository to another review should revise the components that represent the eligibility criteria of the new study, including:

- the LLM screening prompt;
- structured classification fields;
- domain-specific lexical signals;
- deterministic decision rules;
- safety-rescue rules;
- classifier and prompt version information;
- calibration material.

For example, a review on virtual reality for stroke rehabilitation would not normally keep criteria related to serious games, AI, and IoT. Instead, the classifier should be redesigned around criteria relevant to that review, such as population, intervention, rehabilitation context, and study type.

The original classifier should therefore **not** be treated as a universal systematic-review screening model.

Detailed guidance for adapting the pipeline is available in:

```text
docs/adaptation_guide.md
```

Researchers adapting the software should recalibrate the modified classifier using manually assessed records before applying it to production screening.

---

# Supported Databases

The repository currently supports metadata imported from:

- IEEE Xplore
- PubMed
- ACM Digital Library
- Scopus
- Engineering Village / Compendex
- Springer Link

Detailed instructions for exporting metadata from these databases, selecting supported formats, and placing files in the expected local directories are available in:

```text
docs/database_exports.md
```

---

# Screening Architecture

The overall workflow is:

```text
Database search
      ↓
Database export
      ↓
Place metadata in data/raw/<database>/
      ↓
Database-specific importer
      ↓
Metadata standardization
      ↓
Internal deduplication
      ↓
Master dataset
      ↓
Cross-database deduplication
      ↓
LLM-assisted evidence classification
      ↓
Deterministic screening rules
      ↓
Safety-rescue mechanisms
      ↓
RETAIN / UNCERTAIN / EXCLUDE
      ↓
Human review
```

The LLM does **not** directly determine final study eligibility.

Its role is limited to structured evidence classification.

The final automated screening outcome is produced by deterministic Python rules.

---

# Screening Outcomes

Each record receives one of three screening outcomes.

## `RETAIN`

The available metadata supports all core eligibility dimensions.

The study should continue to subsequent assessment.

`RETAIN` does **not** represent definitive full-text inclusion.

## `UNCERTAIN`

The available title, abstract, or keywords are insufficient to safely determine one or more eligibility dimensions.

The record is preserved for human review.

## `EXCLUDE`

The available metadata provides sufficient evidence that at least one eligibility criterion is not satisfied and no safety-rescue rule applies.

---

# Conservative Screening Strategy

The pipeline follows the principle:

> **Automatic exclusion requires evidence of absence; absence of evidence should normally lead to uncertainty.**

This distinction is especially important during title and abstract screening because architecture details related to AI, IoT, or game components may only be fully described in the article's full text.

---

# Final Research Configuration

The current public implementation uses:

```text
Gemini model:       gemini-3.5-flash-lite
Prompt version:     1.7
Classifier version: 1.10
```

The authoritative Portuguese screening prompt is available at:

```text
prompts/screening_prompt_v1_7_pt.txt
```

An English translation for documentation purposes is available at:

```text
prompts/screening_prompt_v1_7_en.md
```

The translated prompt was not used to generate the reported screening results.

---

# Repository Structure

```text
serious-games-ai-iot-screening/
│
├── README.md
├── LICENSE
├── CITATION.cff
├── CHANGELOG.md
├── requirements.txt
├── .env.example
├── .gitignore
├── .gitattributes
│
├── src/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── importers/
│   │   ├── __init__.py
│   │   ├── ieee.py
│   │   ├── pubmed.py
│   │   ├── acm.py
│   │   ├── scopus.py
│   │   ├── compendex.py
│   │   └── springer.py
│   │
│   ├── data_management/
│   │   ├── __init__.py
│   │   ├── create_master.py
│   │   ├── update_master.py
│   │   ├── assign_master_ids.py
│   │   └── springer_metadata.py
│   │
│   └── screening/
│       ├── __init__.py
│       ├── classifier.py
│       └── interactive_screening.py
│
├── prompts/
│   ├── screening_prompt_v1_7_pt.txt
│   └── screening_prompt_v1_7_en.md
│
├── docs/
│   ├── methodology.md
│   ├── decision_rules.md
│   ├── calibration.md
│   ├── data_format.md
│   ├── database_exports.md
│   └── adaptation_guide.md
│
└── examples/
    ├── example_input.csv
    └── example_output.csv
```

The local `data/` directory is intentionally not included in the repository because raw database exports and generated research data are excluded through `.gitignore`.

It is created locally when the pipeline is used.

---

# Installation

## 1. Clone the repository

```bash
git clone https://github.com/JoanaSthefanny/serious-games-ai-iot-screening.git
```

Enter the project directory:

```bash
cd serious-games-ai-iot-screening
```

---

## 2. Create a virtual environment

### Windows

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

---

## 3. Install the required dependencies

Before running the software, install the Python dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

The project uses libraries including:

- pandas
- openpyxl
- python-dotenv
- google-genai
- pydantic
- bibtexparser
- requests
- rapidfuzz

---

# API Configuration

The screening pipeline requires a Gemini API key.

Springer metadata enrichment additionally requires a Springer Nature API key.

Create a local file named:

```text
.env
```

in the repository root.

The easiest approach is to copy:

```text
.env.example
```

and replace the placeholders with your own credentials.

## Windows PowerShell

```powershell
Copy-Item .env.example .env
```

## Linux / macOS

```bash
cp .env.example .env
```

Then edit the new `.env` file:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
SPRINGER_API_KEY=YOUR_SPRINGER_API_KEY
```

The `.env.example` file contains official links for obtaining and configuring the required API credentials.

## Security

Never commit your real `.env` file or API credentials.

The repository `.gitignore` excludes local environment files from version control.

---

# Preparing Database Exports

Before running the metadata import step, export the search results from the bibliographic databases used in the review.

The exported metadata must be placed under:

```text
data/raw/
```

using one directory for each database:

```text
data/
└── raw/
    ├── ieee/
    ├── pubmed/
    ├── acm/
    ├── scopus/
    ├── compendex/
    └── springer/
```

These folders may not be visible immediately after cloning the repository because the `data/` directory is excluded from Git.

The pipeline creates the expected database directories when required.

They may also be created manually before adding exported files.

## Windows PowerShell

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

## Linux / macOS

```bash
mkdir -p data/raw/{ieee,pubmed,acm,scopus,compendex,springer}
```

For complete database-specific instructions, including recommended export formats, expected metadata fields, file placement, and examples, see:

```text
docs/database_exports.md
```

The original database exports used in the associated systematic mapping study are not distributed through this repository.

Users should export their own search results from the corresponding bibliographic databases.

---

# Supported Input Formats

The table below provides a quick reference.

| Database | Input directory | Recommended format | Supported formats |
|---|---|---|---|
| IEEE Xplore | `data/raw/ieee/` | BibTeX | `.bib` |
| PubMed | `data/raw/pubmed/` | NBIB | `.nbib`, `.bib` |
| ACM Digital Library | `data/raw/acm/` | BibTeX | `.bib`, `.csv`, `.xlsx`, `.xls` |
| Scopus | `data/raw/scopus/` | CSV or BibTeX | `.csv`, `.bib`, `.xlsx`, `.xls` |
| Engineering Village / Compendex | `data/raw/compendex/` | CSV or Excel | `.csv`, `.xlsx`, `.xls`, `.bib` |
| Springer Link | `data/raw/springer/` | CSV or Excel | `.csv`, `.xlsx`, `.xls` |

Multiple supported files may be placed in the same database directory.

For example:

```text
data/raw/scopus/export_part_1.csv
data/raw/scopus/export_part_2.csv
data/raw/scopus/export_part_3.csv
```

The importer processes supported files found in the corresponding directory and consolidates the records.

For detailed export and file-preparation instructions, see:

```text
docs/database_exports.md
```

---

# Recommended Metadata Fields

When a database allows export-field selection, users should export the most complete bibliographic metadata available.

Whenever possible, include:

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

Some databases provide multiple keyword-related fields.

The importers attempt to preserve and consolidate these fields whenever applicable.

---

# Metadata Standardization

Database exports are converted into a common structure containing:

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

The original title and abstract text are preserved.

Normalized representations are only used internally where necessary, such as during duplicate detection.

A complete description of the canonical data representation is available in:

```text
docs/data_format.md
```

---

# DOI Recovery

The importer does not rely exclusively on a dedicated DOI column.

If the DOI field is empty, the software searches other metadata fields for DOI-compatible strings.

For example:

```text
https://doi.org/10.1007/s11036-025-02473-6
```

is normalized to:

```text
10.1007/s11036-025-02473-6
```

This improves duplicate detection when different database exports represent DOIs differently.

---

# Keyword Consolidation

Some databases provide more than one keyword field.

For example, Scopus may provide:

```text
Author Keywords
Index Keywords
```

The importer combines these values rather than discarding one source.

Likewise, PubMed may combine:

```text
Other Terms
MeSH Headings
```

and Compendex may combine:

```text
Author Keywords
Controlled Terms
Uncontrolled Terms
```

This helps preserve evidence relevant to AI, IoT, serious games, and health.

---

# Running the Software

The recommended entry point is:

```bash
python src/main.py
```

The main menu provides access to the primary pipeline components.

Example:

```text
======================================================================
SERIOUS GAMES AI-IOT SCREENING
======================================================================

What would you like to do?

Import records                          [1]
Update master dataset                   [2]
Enrich Springer metadata                [3]
Run semi-automated screening            [4]
Run complete workflow for one database  [5]
About                                   [6]
Exit                                    [0]
```

---

# Importing Records

Before importing records:

1. perform the database search;
2. export the retrieved metadata;
3. place the file in the corresponding `data/raw/<database>/` directory.

Detailed instructions are available in:

```text
docs/database_exports.md
```

Then run:

```bash
python src/main.py
```

Select:

```text
Import records [1]
```

and choose the database.

Example:

```text
IEEE Xplore                     [1]
PubMed                          [2]
ACM Digital Library             [3]
Scopus                          [4]
Engineering Village / Compendex [5]
Springer Link                   [6]
```

The standardized output is written to:

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
```

---

# Master Dataset

The master dataset is stored as:

```text
data/processed/master_records.xlsx
```

Each unique record receives a persistent identifier:

```text
MASTER-0001
MASTER-0002
MASTER-0003
...
```

Existing identifiers are preserved when new records are added.

---

# Duplicate Detection

Duplicate detection follows this priority:

```text
1. normalized DOI
2. normalized title
```

Duplicates are documented separately rather than silently discarded.

This improves auditability of the record-selection workflow.

---

# Springer Metadata Enrichment

Springer exports may contain records without abstracts.

The enrichment component can query the Springer Nature Meta API using DOI or available metadata information.

A Springer Nature API key must be configured in the local `.env` file:

```env
SPRINGER_API_KEY=YOUR_SPRINGER_API_KEY
```

Instructions for obtaining the key are provided in:

```text
.env.example
```

Run the enrichment process from the main menu:

```text
Enrich Springer metadata [3]
```

The process:

- preserves existing abstracts;
- attempts metadata retrieval only when needed;
- saves checkpoints;
- records unsuccessful retrieval attempts;
- does not interpret API errors as screening exclusions.

Records whose abstracts cannot be retrieved are preserved for further assessment rather than automatically excluded because of missing metadata.

---

# Semi-Automated Screening

Select:

```text
Run semi-automated screening [4]
```

The user can screen:

```text
IEEE Xplore                     [1]
PubMed                          [2]
ACM Digital Library             [3]
Scopus                          [4]
Engineering Village / Compendex [5]
Springer Link                   [6]
All databases                   [7]
```

Each database produces an independent screening workbook.

---

# Screening Output

Each workbook contains the following sheets:

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

This structure enables manual auditing of automated decisions.

---

# LLM-Assisted Evidence Classification

Gemini evaluates evidence related to:

1. serious game;
2. gamification only;
3. health context;
4. artificial intelligence;
5. Internet of Things;
6. secondary or incomplete publication type.

The model returns structured classifications and supporting evidence.

It does not directly assign the final screening outcome.

---

# Deterministic Decision Rules

After the LLM response, Python applies deterministic rules.

The core logic is documented in:

```text
docs/decision_rules.md
```

The deterministic layer decides between:

```text
RETAIN
UNCERTAIN
EXCLUDE
```

---

# Topic-Specific Lexical Signals

The screening classifier includes domain-specific lexical signals used as conservative checks during automated screening.

For the original study, these include terminology associated with areas such as:

- serious games;
- exergames;
- health;
- rehabilitation;
- artificial intelligence;
- machine learning;
- wearable devices;
- sensors;
- connected devices;
- IoT;
- immersive environments;
- assistive systems.

These signals are part of the classifier logic and are **specific to the original research problem**.

Researchers adapting the pipeline to another systematic review should replace or revise these terms according to the terminology and eligibility criteria of the new study.

Detailed adaptation guidance is available in:

```text
docs/adaptation_guide.md
```

---

# Safety-Rescue Mechanisms

The classifier includes conservative safety rules designed to reduce false-negative automatic exclusions.

The current classifier implements exactly three rescues, evaluated in this order:

| Code | Required conditions |
|---|---|
| `RESGATE_IOT_3_DE_4` | Serious game, health and AI are `YES`; IoT is `NO`; an acquisition or monitoring signal is present. |
| `RESGATE_MULTIMODAL` | Health and AI are `YES`; serious game or IoT is `NO`; both interaction and acquisition signals are present. |
| `RESGATE_AAL_ESTIMULACAO` | Serious game is `NO`; health is `YES`; IoT is `EXPLICIT_IOT` or `FUNCTIONALLY_COMPATIBLE`; AI is `YES` or `UNCERTAIN`; both stimulation and assistive-platform signals are present. |

Signals are lexical matches in title, abstract and keywords against the `CALIBRATED_*_TERMS` lists in `src/screening/classifier.py`.

Decision order: contradictory game/gamification labels → secondary or incomplete study → gamification only → the three rescues above → negative core criteria → uncertain labels → retention.

When `serious_game = YES` and `gamification_only = YES`, the result is `UNCERTAIN` with an empty rescue code. This contradiction is checked before study type.

An uncertain label does not prevent exclusion by another negative core criterion when no rescue applies. There is no generic three-of-four rescue and no independent game, health or AI terminology rescue.

A safety rescue does **not** automatically include the study.

Instead, it converts the outcome to:

```text
UNCERTAIN
```

so that the study can be reviewed manually.

Safety-rescue rules are also topic-specific and should be reassessed when adapting the pipeline to another review.

---

# Records Without Abstracts

Missing metadata is not treated as evidence of ineligibility.

Records without abstracts receive:

```text
decision = UNCERTAIN
api_status = NO_ABSTRACT
```

and remain available for human assessment.

---

# Checkpoints and API Interruptions

The screening process saves results incrementally.

If execution is interrupted because of:

- Gemini quota exhaustion;
- temporary service unavailability;
- authentication errors;
- other technical failures;

the already completed records remain saved.

When screening resumes, completed records are skipped.

Technical API errors are never interpreted as eligibility exclusions.

---

# Development and Calibration

The classifier was iteratively developed using previously manually assessed studies.

The final development configuration preserved all relevant studies in the calibration material while automatically excluding a large proportion of manually non-relevant records.

Detailed calibration information is available in:

```text
docs/calibration.md
```

Because the calibration material influenced classifier development, these results should not be interpreted as independent external validation.

---

# Adapting the Screening Classifier

The metadata-processing infrastructure can be reused across different review topics more easily than the screening classifier itself.

For another review, researchers should typically:

```text
Define the review protocol
        ↓
Define inclusion and exclusion criteria
        ↓
Identify screening dimensions
        ↓
Create a new screening prompt
        ↓
Modify the structured response schema
        ↓
Replace topic-specific lexical signals
        ↓
Modify deterministic decision rules
        ↓
Review safety-rescue mechanisms
        ↓
Create a manually assessed calibration dataset
        ↓
Evaluate false-negative exclusions
        ↓
Freeze prompt and classifier versions
        ↓
Run production screening
```

Researchers should create new prompt and classifier versions rather than silently modifying the original configuration.

For example:

```text
Prompt version:     2.0
Classifier version: 2.0
```

The documentation should also be updated so that the recorded methodology reflects the actual modified implementation.

The calibration results reported for this repository apply only to the original screening problem and should **not** be interpreted as validation for another review topic.

See:

```text
docs/adaptation_guide.md
```

for detailed instructions.

---

# Screening Run Documented in the Study

Historical results were produced by the original research scripts. Their recorded version identifiers are preserved. The current public implementation uses prompt v1.7 and classifier v1.10; the historical results do not constitute a new Gemini execution with this configuration.

The completed screening dataset contained:

```text
1,046 records
```

The final automated screening distribution was:

| Outcome | Records | Percentage |
|---|---:|---:|
| RETAIN | 37 | 3.54% |
| UNCERTAIN | 141 | 13.48% |
| EXCLUDE | 868 | 82.98% |
| **Total** | **1,046** | **100%** |

Therefore:

```text
Records preserved for further assessment: 178 / 1,046 (17.02%)
Automatically excluded:                  868 / 1,046 (82.98%)
```

Additional execution information:

```text
Records without abstracts: 74
Safety rescues:             40
Remaining technical errors: 0
```

The 74 records without abstracts are included within the `UNCERTAIN` category.

These automated screening outcomes do not represent final full-text inclusion decisions.

---

# Results by Database

| Database | Records | RETAIN | UNCERTAIN | EXCLUDE | Safety rescues |
|---|---:|---:|---:|---:|---:|
| IEEE Xplore | 69 | 16 | 14 | 39 | 5 |
| PubMed | 13 | 1 | 3 | 9 | 1 |
| ACM Digital Library | 7 | 2 | 1 | 4 | 1 |
| Scopus | 31 | 5 | 4 | 22 | 2 |
| Engineering Village / Compendex | 25 | 1 | 2 | 22 | 1 |
| Springer Link | 901 | 12 | 117 | 772 | 30 |
| **Total** | **1,046** | **37** | **141** | **868** | **40** |

---

# Documentation

Additional methodological and technical documentation is available in the `docs/` directory.

## Methodology

```text
docs/methodology.md
```

Describes the overall research and processing workflow.

## Decision Rules

```text
docs/decision_rules.md
```

Documents the deterministic screening and safety-rescue logic.

## Calibration

```text
docs/calibration.md
```

Documents classifier development and calibration results.

## Data Format

```text
docs/data_format.md
```

Documents input, master-dataset, and screening-output formats.

## Database Export Guide

```text
docs/database_exports.md
```

Explains how to prepare metadata exported from each supported bibliographic database.

It documents:

- supported export formats;
- recommended metadata fields;
- the local folder required for each database;
- creation of the `data/raw/` directory structure;
- examples of valid file placement;
- handling of multiple export files;
- Springer metadata enrichment;
- raw-data availability and licensing considerations.

Users who wish to run the pipeline on their own searches should read this document before importing database records.

## Adaptation Guide

```text
docs/adaptation_guide.md
```

Explains how the software architecture can be adapted to other systematic reviews or systematic mapping studies.

It covers:

- identifying new eligibility dimensions;
- creating a new LLM prompt;
- modifying the structured classification schema;
- replacing domain-specific lexical signals;
- adapting deterministic decision rules;
- reviewing safety-rescue mechanisms;
- versioning modified classifiers;
- creating a new calibration dataset;
- evaluating false-negative exclusions;
- distinguishing calibration from independent validation.

The guide should be consulted before applying the screening classifier to a research topic different from the one for which this repository was originally developed.

---

# Example Data

The repository does not distribute copyrighted full-text articles or the original database-export datasets from the study.

Small synthetic examples are provided in:

```text
examples/example_input.csv
examples/example_output.csv
```

The example files contain fully synthetic records created only to demonstrate the expected input and output data structures.

They are not records from the associated systematic mapping study and do not correspond to real publications.

`example_input.csv` illustrates the standardized bibliographic metadata available before the semi-automated screening stage.

`example_output.csv` illustrates the screening information produced after LLM-assisted evidence classification and application of the deterministic decision rules, including the final `RETAIN`, `UNCERTAIN`, or `EXCLUDE` outcome.

The CSV files in the `examples/` directory are simplified representations provided for easy inspection directly on GitHub.

The actual pipeline stores processed metadata and screening results as Excel (`.xlsx`) workbooks.

In particular, the screening stage generates Excel workbooks containing multiple sheets, including:

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

Therefore, `example_output.csv` should be interpreted as a simplified representation of the `Results` content rather than the exact file format generated by the software.

---

# Data Availability and Copyright

Full-text publications used during the systematic mapping study are **not distributed through this repository**.

The original bibliographic database exports used in the study are also not redistributed.

Users are responsible for obtaining publications and database exports through the appropriate publishers, institutions, libraries, bibliographic databases, or licensed services.

The repository provides:

- source code;
- metadata import logic;
- metadata normalization rules;
- screening logic;
- prompts;
- methodological documentation;
- adaptation guidance;
- synthetic examples.

For instructions on preparing your own database exports, see:

```text
docs/database_exports.md
```

---

# Reproducibility Notes

LLM-based systems may exhibit variation across:

- model updates;
- API versions;
- provider-side changes;
- service availability.

For this reason, the pipeline records:

```text
model
prompt_version
classifier_version
```

alongside screening results.

The deterministic decision rules are versioned separately from the LLM prompt.

The public software release is versioned independently from the internal screening-classifier version.

For the documented study:

```text
Public software version: 1.0.0
Prompt version:          1.7
Classifier version:      1.10
```

When adapting the system to another review, researchers should assign new prompt and classifier versions to the modified configuration.

---

# Human Oversight

This pipeline is intended to support systematic-review screening.

It is **not** intended to replace researcher judgment.

Human review remains required for:

- uncertain studies;
- records with insufficient metadata;
- full-text eligibility assessment;
- resolution of conflicting evidence;
- final inclusion and exclusion decisions.

Researchers adapting the pipeline to another topic remain responsible for validating the modified screening logic and ensuring that it reflects the eligibility criteria defined in their review protocol.

---

# Changelog

Changes to the public software are documented in:

```text
CHANGELOG.md
```

The changelog distinguishes public software releases from the internal prompt and classifier versions used during development.

---

# Citation

Citation metadata for this repository is available in:

```text
CITATION.cff
```

GitHub can use this file to provide a **Cite this repository** option.

If you use this software or adapt it as a basis for another systematic review, please cite the repository and clearly document any modifications made to the original implementation.

Once available, the associated systematic mapping study should also be cited.

The full article citation will be added after publication.

Until then, the repository may be cited using its GitHub URL and release/version information.

Repository:

```text
https://github.com/JoanaSthefanny/serious-games-ai-iot-screening
```

---

# Author

**Joana Sthefanny Gomes Costa dos Santos**

Federal University of Ceará (UFC), Brazil.

Systematic mapping research on serious games, artificial intelligence, Internet of Things, and health.

---

# License

This project is distributed under the MIT License.

See:

```text
LICENSE
```

for the complete license terms.