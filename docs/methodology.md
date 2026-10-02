# Methodology

## Overview

This repository contains the semi-automated screening pipeline developed for a systematic mapping study investigating the intersection of **serious games**, **artificial intelligence (AI)**, **Internet of Things (IoT)** technologies, and **health applications**.

The pipeline was designed to support the title, abstract, and keyword screening stage while prioritizing **high sensitivity** and minimizing the risk of incorrectly excluding potentially relevant studies.

The system does not replace human judgment. Instead, it combines large language model (LLM)-assisted evidence classification with deterministic decision rules and conservative safety mechanisms.

---

## Study Scope

The systematic mapping study investigates studies that involve:

1. serious games or equivalent game-based interventions;
2. a health-related context;
3. artificial intelligence;
4. Internet of Things technologies or architectures functionally compatible with IoT.

The screening process considers these four dimensions simultaneously.

Studies are also assessed for exclusion criteria such as:

- gamification without an actual serious game;
- secondary studies, including systematic reviews, mapping studies, and bibliometric analyses;
- protocols without a completed study;
- explicitly incomplete publications;
- abstracts, posters, editorials, or other publication types covered by the exclusion criteria.

Evidence must refer to the study's own contribution. Technologies mentioned only in related work or as future possibilities do not establish their use in the current solution.

Full-text eligibility, access requirements, and final inclusion decisions remain subject to human assessment.

---

## Databases

Records were collected from the following scientific databases:

- IEEE Xplore;
- PubMed;
- ACM Digital Library;
- Scopus;
- Engineering Village / Compendex;
- Springer Link.

Database-specific exports are first processed by the import modules located in:

```text
src/importers/
```

Each importer converts the original database metadata into a common schema before records are incorporated into the master dataset.

---

## Pipeline Architecture

The overall workflow is:

```text
Database search
      ↓
Database export
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

---

## Metadata Import

Each database-specific importer attempts to recover the following metadata:

- source identifier;
- database;
- title;
- authors;
- publication year;
- publication venue;
- volume;
- document type;
- DOI;
- abstract;
- keywords;
- URL.

The canonical schema also includes:

- persistent master identifier;
- metadata acquisition status;
- metadata source.

Different databases expose these fields using different names and formats. Database-specific fields are therefore mapped to a common canonical schema.

Records without a title are removed during standardization.

An import that produces no valid records preserves the existing processed output files. The complete workflow stops after a failed or empty import.

---

## DOI Recovery

DOIs are not always provided in a dedicated DOI field.

The pipeline attempts to recover DOIs from:

- explicit DOI fields;
- URLs;
- links;
- identifiers;
- other metadata fields containing strings compatible with DOI syntax.

For example:

```text
https://doi.org/10.1007/s11036-025-02473-6
```

is normalized to:

```text
10.1007/s11036-025-02473-6
```

DOI normalization improves duplicate detection across database exports.

---

## Keyword Consolidation

Some databases provide more than one type of keyword metadata.

Examples include:

- Author Keywords;
- Index Keywords;
- Controlled Terms;
- Uncontrolled Terms;
- MeSH headings.

The importers consolidate supported keyword fields into the canonical `keywords` field.

For Engineering Village / Compendex BibTeX exports, the `key` and `note` fields are also interpreted as sources of index terms.

This interpretation is specific to the Compendex export format. Administrative notes from other databases are not automatically treated as keywords.

Keyword consolidation helps preserve terminology related to AI, IoT, serious games, and health.

---

## Deduplication

Deduplication occurs at two levels.

### Internal deduplication

Records within the imported collection for a database are compared using:

1. normalized DOI;
2. a unique normalized-title candidate with compatible volume information when no DOI match is found.

Conflicting nonempty volume identifiers prevent title-based merging. Multiple compatible title candidates are treated as ambiguous and preserved separately.

The first retained record preserves its identity and populated bibliographic fields. Missing fields can be filled from a duplicate record.

A DOI recovered during this process is indexed for subsequent duplicate checks.


### Master-dataset deduplication

Incoming records are compared against the existing master dataset and records added earlier in the same update.

The matching priority is:

1. normalized DOI;
2. a unique normalized-title candidate with compatible volume information when no DOI match is found.

The existing record preserves its MASTER ID, source ID, original database, and populated bibliographic values. Missing bibliographic metadata can be filled from an incoming duplicate.

Duplicate records are documented in separate reports rather than silently discarded.

---

## Master Dataset

All standardized records are stored in a master dataset.

Each unique record receives a persistent identifier:

```text
MASTER-0001
MASTER-0002
MASTER-0003
...
```

Existing identifiers are preserved during subsequent updates. New identifiers are assigned to records without a MASTER ID.

This allows screening results and manual decisions to remain traceable even when new database records are added later.

A timestamped backup is created before updating an existing master workbook.


---

## Springer Metadata Enrichment

The Springer Link export used in the study did not always contain abstracts.

When possible, missing metadata was supplemented through the Springer Nature Meta API.

The enrichment stage:

- combines the current import with an existing enrichment checkpoint;
- preserves previously recovered metadata and API status columns;
- preserves existing abstracts;
- attempts DOI-based metadata retrieval;
- stores API status and error information;
- saves checkpoints during execution;
- does not interpret API failure as an eligibility exclusion.

Records for which an abstract remains unavailable are preserved for manual review.

Enrichment checkpoints are written to a temporary workbook and replaced atomically after the write completes.

---

## LLM-Assisted Screening

The current screening implementation is configured with:

```text
Model: gemini-3.5-flash-lite
Prompt version: 1.9
Classifier version: 1.11
```

The LLM does **not** directly make the final inclusion or exclusion decision.

Its role is to classify evidence available in:

- title;
- abstract;
- keywords.

The structured response evaluates six fields:

| Field | Allowed values |
|---|---|
| `serious_game` | `YES`, `NO`, `UNCERTAIN` |
| `gamification_only` | `YES`, `NO`, `UNCERTAIN` |
| `health` | `YES`, `NO`, `UNCERTAIN` |
| `ai` | `YES`, `NO`, `UNCERTAIN` |
| `iot` | `EXPLICIT_IOT`, `FUNCTIONALLY_COMPATIBLE`, `NO`, `UNCERTAIN` |
| `secondary_or_incomplete` | `YES`, `NO`, `UNCERTAIN` |

Each field has an accompanying evidence explanation. An additional `notes` field records relevant observations.

The response is validated against the `ScreeningAssessment` schema before deterministic rules are applied.

---

### AI evidence and uncertainty

A positive AI classification requires evidence of an AI technique used in the study's own solution.

An analytical function whose method is omitted can support `UNCERTAIN`. Examples include classification, prediction, recognition, adaptation, or computational assessment of therapeutic performance from acquired data.

Sensors, monitoring, an IDE, EMG, or Arduino alone do not establish AI.

The absence of the term “AI” does not, by itself, resolve an ambiguous analytical function. Conversely, explicitly described fixed rules or conventional calculations without another AI component can support `NO`.

### Secondary or incomplete studies

A positive `secondary_or_incomplete` classification requires supporting evidence of a secondary study, an excluded publication type, or an explicitly incomplete contribution.

An overview of the authors' own system does not, by itself, establish that the publication is a review.

The absence of experimental details in the abstract does not, by itself, establish that the publication is incomplete.

---

## Separation Between Evidence Classification and Decision

The pipeline separates two responsibilities:

1. the LLM interprets the evidence and produces structured classifications;
2. Python applies predefined deterministic decision rules.

This design reduces dependence on unconstrained natural-language decisions and improves auditability.

It does not eliminate errors in evidence interpretation. Human review remains necessary.

---

## Conservative Screening Strategy

The screening stage is designed to prioritize sensitivity.

The deterministic rules operate on the LLM's classifications and calibrated lexical signals.

A negative core criterion can lead to `EXCLUDE` unless a preceding contradiction rule or safety-rescue rule applies.

When no earlier exclusion rule applies and at least one criterion remains unresolved, the record is assigned:

```text
UNCERTAIN
```

The three outcomes have the following meanings:

| Outcome | Meaning |
|---|---|
| `RETAIN` | Metadata supports the required criteria; the record proceeds to subsequent assessment. |
| `UNCERTAIN` | Unresolved evidence, contradictory labels, a safety rescue, or missing abstract requires human review. |
| `EXCLUDE` | The deterministic rules identify an exclusion condition from the available classifications. |

`RETAIN` does not mean definitive inclusion.

`UNCERTAIN` is not an exclusion.

Both categories are preserved for subsequent assessment.

---

## Safety-Rescue Mechanisms

Additional deterministic safety rules were introduced during classifier development to reduce false-negative screening decisions.

These mechanisms can override an aggressive automatic exclusion and route the record to:

```text
UNCERTAIN
```

instead.

The current classifier implements exactly three rescues, evaluated in this order:

It does not confirm eligibility or automatically include the study.

The current classifier implements four rescues, evaluated in this order:

| Code | Required conditions |
|---|---|
| `RESGATE_IOT_3_DE_4` | Serious game, health, and AI are `YES`; IoT is `NO`; an acquisition or monitoring signal is present. |
| `RESGATE_MULTIMODAL` | Health and AI are `YES`; serious game or IoT is `NO`; both interaction and acquisition signals are present. |
| `RESGATE_AAL_ESTIMULACAO` | Serious game is `NO`; health is `YES`; AI is `YES` or `UNCERTAIN`; IoT is `EXPLICIT_IOT` or `FUNCTIONALLY_COMPATIBLE`; both stimulation and assistive-platform signals are present. |
| `RESGATE_AAL_METADADOS_INCOMPLETOS` | Study type and gamification-only are `NO`; serious game is `NO`; health is `YES`; AI is `NO` with a justification indicating metadata omission; IoT is `EXPLICIT_IOT`, `FUNCTIONALLY_COMPATIBLE`, or `UNCERTAIN`; acquisition, assistive-platform, and cognitive or physical stimulation signals are present. |

The first three rescues are evaluated after the contradiction, secondary-study, and gamification-only rules. The fourth rescue additionally requires both `secondary_or_incomplete` and `gamification_only` to be `NO`.

### Lexical signals

Acquisition, interaction, stimulation, and assistive-platform signals are matched in title, abstract, and keywords using the `CALIBRATED_*_TERMS` lists in:

```text
src/screening/classifier.py
```

The fourth rescue also uses:

```text
ai_negative_is_metadata_omission()
aal_stimulation_review_signal()
```

`ai_negative_is_metadata_omission()` examines the AI justification for omission cues. Explicit descriptions of absent AI or conventional-only methods block this rescue.

Its free-text checks can miss paraphrases. They are review cues, not evidence that AI is present.

`aal_stimulation_review_signal()` checks calibrated stimulation phrases or stimulation terminology in a cognitive or physical context.

### Decision precedence

The deterministic decision order is:

1. contradictory serious-game and gamification-only labels;
2. secondary or incomplete study;
3. gamification only;
4. the four safety rescues, in the order listed above;
5. negative core criteria;
6. unresolved labels;
7. retention.

When:

```text
serious_game = YES
gamification_only = YES
```

the result is `UNCERTAIN` with an empty rescue code. This contradiction is checked before study type.

An uncertain label does not prevent exclusion by another negative core criterion when no rescue applies.

There is no generic three-of-four rescue and no independent game, health, or AI terminology rescue.

Safety rescues preserve the original criterion labels. They change the screening outcome to `UNCERTAIN` and record the applicable rescue code.

---

## Records Without Abstracts

Records without abstracts are not sent to Gemini for classification.

They receive:

```text
decision = UNCERTAIN
api_status = NO_ABSTRACT
```

Their eligibility fields are recorded as:

```text
NOT_EVALUATED
```

`NOT_EVALUATED` is an output placeholder for unassessed records. It is not an allowed classification returned by the LLM schema.

These records require manual assessment or retrieval of additional information.

If an abstract becomes available later, the previous missing-abstract result is invalidated and the record becomes eligible for automated analysis.

---

## Checkpointing

Screening results are saved incrementally in database-specific workbooks.

New results record:

- model identifier;
- prompt version;
- classifier version;
- prompt-content fingerprint;
- metadata fingerprint.

The metadata fingerprint covers the title, abstract, and keywords used for screening.

### Resuming execution

Results with `SUCCESS` or `NO_ABSTRACT` status are reused only when their configuration, metadata, and completion status remain compatible with the current record.

A successful classification is therefore not skipped unconditionally.

Changes to screening metadata, prompt content, model, or version identifiers can invalidate a saved result.

Legacy results without fingerprints are checked using their stored metadata and recorded configuration versions.

`API_ERROR` records remain pending and are retried during a subsequent execution.

Results that no longer belong to the current collection, or fail validation, are removed from the active results. The original workbook is backed up before this reconciliation is saved.

### Write failures

Screening checkpoints are written to a temporary workbook and replaced atomically after all sheets have been written and closed.

A checkpoint write failure stops processing. It is not converted into an API error or an eligibility exclusion.

When API quota exhaustion, service unavailability, or authentication failure interrupts processing, successfully saved results remain available for resumption.

---

## Human Oversight

The pipeline is intended as a screening assistance tool rather than an autonomous systematic-review decision system.

Human assessment remains necessary for:

- uncertain records;
- records without abstracts;
- ambiguous bibliographic identities;
- full-text eligibility assessment;
- resolution of contradictory evidence;
- verification of automated classifications;
- final inclusion and exclusion decisions.

The automated stage therefore functions as a conservative prioritization mechanism within a human-supervised evidence synthesis workflow.

---

## Reproducibility

The repository documents:

- source code;
- model identifier;
- prompt version;
- classifier version;
- screening rules;
- safety-rescue rules;
- metadata schema;
- calibration procedure.

The current operational Portuguese prompt is stored in:

```text
prompts/screening_prompt_v1_9_pt.txt
```

Prompt loading is controlled by:

```text
src/screening/classifier.py
```

The loader uses the external prompt when the file exists and contains text. Otherwise, it uses the embedded `DEFAULT_PROMPT`.

The external prompt and embedded fallback should remain consistent.

An English translation, when provided, is documentation material. It does not change the operational prompt unless the classifier is explicitly configured to load it.

Public software releases, screening prompts, and deterministic classifiers have separate version identifiers.

Changes to the prompt or decision rules should be accompanied by updated version identifiers. Historical outputs must retain their original recorded configuration.

---

## Historical Results

Historical research results were produced by the original research scripts.

Their counts and recorded configuration identifiers are preserved. They do not represent a complete rerun with the current public implementation:

```text
Prompt version: 1.9
Classifier version: 1.11
```

The historical results and calibration material are described in:

```text
README.md
docs/calibration.md
CHANGELOG.md
```

Records used to develop or tune the classifier constitute development or calibration material. Performance on those records must not be interpreted as independent external validation.

The current configuration must not be assigned retrospectively to historical outputs.
