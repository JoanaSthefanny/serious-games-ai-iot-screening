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
- secondary studies;
- systematic reviews;
- mapping studies;
- bibliometric analyses;
- incomplete publications;
- abstracts or posters without sufficient study information.

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
- document type;
- DOI;
- abstract;
- keywords;
- URL.

Different databases expose these fields using different names and formats.

The import layer therefore maps database-specific fields to a common canonical schema.

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

When multiple keyword fields are available, their contents are combined rather than selecting only one field.

This reduces the risk of losing terms related to AI, IoT, serious games, or health.

---

## Deduplication

Deduplication occurs at two levels.

### Internal deduplication

Duplicates inside the same database export are detected using:

1. normalized DOI, when available;
2. normalized title when DOI is unavailable.

### Cross-database deduplication

When records are incorporated into the master dataset, records already present from another database are detected using the same priority:

1. DOI;
2. normalized title.

The first occurrence is preserved in the master dataset.

Records identified as duplicates are documented separately rather than silently discarded.

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

Existing identifiers are never reassigned during subsequent updates.

This allows screening results and manual decisions to remain traceable even when new database records are added later.

---

## Springer Metadata Enrichment

The Springer Link export used in the study did not always contain abstracts.

When possible, missing metadata was supplemented through the Springer Nature Meta API.

The enrichment stage:

- preserves existing abstracts;
- attempts DOI-based metadata retrieval;
- stores API status;
- saves checkpoints during execution;
- does not interpret API failure as an exclusion criterion.

Records for which an abstract remains unavailable are preserved for manual review.

---

## LLM-Assisted Screening

The screening pipeline uses:

```text
Model: gemini-3.5-flash-lite
Prompt version: 1.6
Classifier version: 1.8
```

The LLM does **not** directly make the final inclusion or exclusion decision.

Its role is to classify evidence available in:

- title;
- abstract;
- keywords.

The LLM evaluates:

1. serious game;
2. gamification only;
3. health context;
4. artificial intelligence;
5. Internet of Things;
6. secondary or incomplete study status.

Structured output is required so that the subsequent decision stage can be handled deterministically in Python.

---

## Separation Between Evidence Classification and Decision

The pipeline deliberately separates:

```text
LLM interpretation
```

from:

```text
screening decision
```

The LLM produces structured evidence classifications.

Python then applies predefined deterministic rules.

This design reduces the dependence of the final decision on unconstrained natural-language model output and improves auditability.

---

## Conservative Screening Strategy

The screening stage was designed to prioritize sensitivity.

A record is automatically excluded only when the available metadata provides sufficient evidence that an eligibility criterion is not satisfied.

When the evidence is incomplete or ambiguous, the record is assigned:

```text
UNCERTAIN
```

and remains available for human review.

Therefore:

```text
RETAIN
```

does not mean definitive inclusion.

Likewise:

```text
UNCERTAIN
```

is not an exclusion.

Both categories are preserved for subsequent assessment.

---

## Safety-Rescue Mechanisms

Additional deterministic safety rules were introduced during classifier development to reduce false-negative screening decisions.

These mechanisms can override an aggressive automatic exclusion and route the record to:

```text
UNCERTAIN
```

instead.

Examples include situations where:

- textual game evidence contradicts an LLM `NO`;
- health-related terminology contradicts a health `NO`;
- explicit AI terminology contradicts an AI `NO`;
- IoT terminology or a connected sensor architecture contradicts an IoT `NO`;
- three of four central eligibility dimensions are strongly supported;
- a multimodal immersive system appears relevant but one architecture dimension is insufficiently described;
- an IoT-enabled assistive or ambient-assisted-living system may contain relevant functionality not sufficiently described in the abstract.

Safety rescue is deliberately conservative: it does not automatically include a study.

It prevents automatic exclusion and routes the study to human review.

---

## Records Without Abstracts

Records without abstracts are not automatically excluded.

They receive:

```text
UNCERTAIN
```

because the absence of metadata is not evidence that an eligibility criterion is absent.

These records require manual assessment or retrieval of additional information.

---

## Checkpointing

Screening results are saved incrementally.

Records with successful classifications or records intentionally routed to manual review due to missing abstracts are considered completed.

Technical API failures are not treated as screening decisions.

If processing is interrupted because of:

- API quota exhaustion;
- service unavailability;
- authentication failure;

the available results remain saved.

When execution resumes, previously completed records are skipped.

---

## Human Oversight

The pipeline is intended as a screening assistance tool rather than an autonomous systematic-review decision system.

Human assessment remains necessary for:

- uncertain records;
- records without abstracts;
- full-text eligibility assessment;
- resolution of ambiguous evidence;
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

The Portuguese prompt stored in:

```text
prompts/screening_prompt_v1_6_pt.txt
```

is the authoritative prompt associated with the screening implementation.

The English prompt file is provided for documentation and readability.