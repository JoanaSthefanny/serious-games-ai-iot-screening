# Adapting the Pipeline to Other Systematic Reviews

This repository was originally developed for a systematic mapping study involving **serious games, health, artificial intelligence, and Internet of Things technologies**.

However, the overall architecture can be reused as a starting point for other systematic reviews or systematic mapping studies.

The screening logic is **not automatically transferable to another research topic**.

Researchers adapting this repository should review and modify the topic-specific components described below before using the pipeline in another study.

---

# 1. What Can Be Reused Without Major Changes

Several components of the repository are relatively independent of the original research topic and may be reused with little or no modification.

These include:

- database metadata import;
- metadata normalization;
- DOI extraction and normalization;
- keyword consolidation;
- duplicate detection;
- master-dataset creation;
- persistent record identifiers;
- checkpoint-based processing;
- API-error handling;
- Excel output generation;
- separation between LLM assessment and deterministic decision rules.

The database importers may therefore remain useful even when the research questions and eligibility criteria change.

---

# 2. What Must Be Adapted

The screening component contains rules that are specific to the original study.

Researchers applying the pipeline to another review should examine at least the following components:

```text
prompts/screening_prompt_v1_7_pt.txt
prompts/screening_prompt_v1_7_en.md

src/screening/classifier.py
src/screening/interactive_screening.py

docs/decision_rules.md
```

The most important adaptations involve:

1. eligibility dimensions;
2. LLM prompt;
3. structured response schema;
4. lexical evidence terms;
5. deterministic decision rules;
6. safety-rescue rules;
7. calibration material.

---

# 3. Define the New Eligibility Criteria First

Before modifying the code, define the eligibility criteria of the new systematic review.

For example, a review might investigate:

```text
Population
Intervention
Comparator
Outcome
Context
```

or another framework appropriate to the research question.

The automated screening dimensions should reflect the actual inclusion and exclusion criteria of the review.

For example, a different review could require evidence of:

```text
population = older adults
intervention = virtual reality
context = rehabilitation
study_type = primary empirical study
```

These dimensions would replace the original topic-specific dimensions:

```text
serious_game
health
ai
iot
```

The software should not define the review criteria.

The review protocol should define the criteria first, and the software should then implement them.

---

# 4. Adapt the Screening Prompt

The original production prompt is stored in:

```text
prompts/screening_prompt_v1_7_pt.txt
```

This prompt was specifically designed for the original systematic mapping study.

A researcher adapting the pipeline should create a new prompt version instead of silently overwriting the existing one.

For example:

```text
prompts/screening_prompt_v2_0_pt.txt
```

or:

```text
prompts/screening_prompt_custom_review.txt
```

The new prompt should describe:

- the objective of the review;
- inclusion criteria;
- exclusion criteria;
- the evidence dimensions to classify;
- definitions of ambiguous concepts;
- how uncertainty should be handled;
- the expected structured output.

The prompt should instruct the model to classify evidence rather than independently make the final inclusion decision whenever the deterministic architecture is preserved.

A useful general principle is:

> The LLM should identify and structure evidence, while transparent programmatic rules determine the automated screening outcome.

---

# 5. Adapt the Structured Classification Schema

The current classifier uses a structured schema designed around the original review.

Examples of original fields include:

```text
serious_game
gamification_only
health
ai
iot
secondary_or_incomplete
```

These fields are defined in:

```text
src/screening/classifier.py
```

For another review, these fields should be replaced or extended according to the new eligibility criteria.

For example:

```python
population
intervention
comparison
outcome
study_type
```

Each dimension can also include an evidence field, such as:

```python
population
evidence_population

intervention
evidence_intervention
```

Preserving evidence text makes the screening process easier to audit.

---

# 6. Adapt Allowed Classification Values

The original classifier uses values such as:

```text
YES
NO
UNCERTAIN
```

and, for IoT:

```text
EXPLICIT_IOT
FUNCTIONALLY_COMPATIBLE
NO
UNCERTAIN
```

Another review may require different values.

For example:

```text
YES
NO
UNCERTAIN
NOT_APPLICABLE
```

or domain-specific categories.

The values expected by the prompt and the values accepted by the Python schema must remain consistent.

If the prompt requests one vocabulary while the structured schema expects another, model responses may fail validation.

---

# 7. Adapt Topic-Specific Lexical Signals

The current classifier contains lexical signals used as conservative checks against potentially unsafe automatic exclusions.

Examples include terms related to:

- serious games;
- exergames;
- health;
- machine learning;
- artificial intelligence;
- wearable devices;
- sensors;
- communication technologies;
- Internet of Things;
- immersive environments;
- assistive systems.

These terms are located in:

```text
src/screening/classifier.py
```

They were selected specifically for the original research topic.

For another review, these lists should be replaced with terminology relevant to the new domain.

For example, a rehabilitation review might contain signals such as:

```text
stroke
post-stroke
motor rehabilitation
upper limb
physiotherapy
functional recovery
```

while an educational review might instead use:

```text
student
learning
teaching
education
classroom
academic performance
```

Lexical signals should be derived from the terminology of the new review rather than copied from the original study without modification.

---

# 8. Adapt the Deterministic Decision Rules

The final automated screening decision is produced by deterministic Python logic.

The current rules were designed around the original requirement that a potentially relevant study should contain evidence related to:

```text
serious game
health
AI
IoT
```

For another review, the researcher must redefine what combination of criteria leads to:

```text
RETAIN
UNCERTAIN
EXCLUDE
```

For example:

```text
If all mandatory criteria are YES:
    RETAIN

If any mandatory criterion is UNCERTAIN:
    UNCERTAIN

If a mandatory criterion is clearly NO:
    EXCLUDE
```

This is only an example.

The actual logic must follow the protocol of the new systematic review.

---

# 9. Review the Safety-Rescue Rules

The original classifier contains safety-rescue mechanisms intended to reduce false-negative exclusions.

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

These rules are specific to the original screening problem.

A new review should determine whether similar rescue mechanisms are appropriate.

Researchers should avoid retaining original safety rules merely because they already exist in the code.

Instead, each rescue rule should have a clear methodological justification for the new review.

---

# 10. Preserve Conservative Handling of Missing Information

One principle may be broadly useful across systematic-review screening tasks:

> Missing information should not automatically be interpreted as evidence that an eligibility criterion is absent.

For example, if an abstract does not report a required methodological detail, this may justify:

```text
UNCERTAIN
```

rather than:

```text
EXCLUDE
```

Whether this principle applies should still be defined in the review protocol.

---

# 11. Update Version Information

Whenever the screening logic is modified, update the relevant version identifiers.

For example:

```python
MODEL_NAME = "..."
PROMPT_VERSION = "2.0"
CLASSIFIER_VERSION = "2.0"
```

This makes it possible to identify which configuration generated each screening result.

Researchers should avoid modifying the prompt or classifier rules without changing the corresponding version identifier.

---

# 12. Update the Documentation

After adapting the screening criteria, update:

```text
docs/methodology.md
docs/decision_rules.md
docs/calibration.md
docs/data_format.md
```

Documentation should describe the actual behavior of the modified pipeline.

The repository documentation should not continue describing the original serious-games/AI/IoT criteria after the code has been adapted to another review.

---

# 13. Create a New Calibration Dataset

The original classifier was calibrated using records relevant to the original research problem.

Those calibration results do **not** validate the classifier for another topic.

Before using an adapted classifier for a new systematic review, create a calibration dataset containing records that have already been manually assessed by researchers.

The calibration material should ideally contain:

```text
known relevant studies
known non-relevant studies
ambiguous studies
borderline cases
records with incomplete abstracts
```

The objective is not only to measure how many records are automatically excluded.

A particularly important objective during early screening is to identify potential false-negative exclusions.

---

# 14. Evaluate False Negatives Carefully

For sensitivity-oriented title and abstract screening, incorrectly excluding a relevant record can be more consequential than retaining an irrelevant record for manual assessment.

During development, researchers should therefore inspect:

```text
known relevant → EXCLUDE
```

cases carefully.

Any such case should be investigated to determine whether:

- the prompt misunderstood the evidence;
- a criterion was poorly defined;
- important terminology was missing from lexical signals;
- the deterministic rule was too aggressive;
- the abstract genuinely lacked enough information.

Changes made after observing calibration records should be documented.

---

# 15. Do Not Treat Calibration as Independent Validation

If records are repeatedly used to modify:

- the prompt;
- lexical terms;
- rescue rules;
- deterministic rules;

performance on those records represents **development or calibration performance**.

It should not be reported as independent external validation.

An independent evaluation requires records that were not used to design or tune the classifier.

---

# 16. Recommended Adaptation Workflow

A possible adaptation workflow is:

```text
Define review protocol
        ↓
Define inclusion/exclusion criteria
        ↓
Identify screening dimensions
        ↓
Create a new prompt
        ↓
Modify structured schema
        ↓
Replace topic-specific lexical signals
        ↓
Modify deterministic decision rules
        ↓
Review safety-rescue rules
        ↓
Create manually assessed calibration set
        ↓
Run calibration
        ↓
Inspect false negatives
        ↓
Refine cautiously
        ↓
Freeze prompt and classifier versions
        ↓
Evaluate on unseen records when possible
        ↓
Run production screening
```

---

# 17. Example of Conceptual Adaptation

Suppose the original pipeline evaluates:

```text
Serious Game
Health
AI
IoT
```

but another researcher wants to conduct a systematic review on:

> Virtual reality interventions for upper-limb rehabilitation after stroke.

The new screening dimensions might be:

```text
Stroke population
Upper-limb rehabilitation
Virtual reality intervention
Primary empirical study
```

The researcher would then:

1. create a new prompt describing those criteria;
2. replace the original structured fields;
3. remove AI-, IoT-, and serious-game-specific lexical terms;
4. add stroke-, rehabilitation-, and VR-related terms;
5. redefine the deterministic rules;
6. create appropriate safety-rescue conditions;
7. calibrate using manually assessed studies from that review.

The metadata-import and deduplication infrastructure could remain largely unchanged.

---

# 18. Components That Should Usually Remain Separate

When adapting the repository, maintain the separation between:

```text
LLM interpretation
        ↓
Structured evidence
        ↓
Deterministic decision logic
```

This separation improves:

- transparency;
- auditability;
- reproducibility;
- debugging;
- methodological reporting.

It also allows researchers to modify decision rules without necessarily modifying the language model prompt, and vice versa.

---

# 19. Important Limitation

This repository should be treated as a **research software framework**, not as a validated universal systematic-review screening classifier.

The original prompt, lexical rules, and calibration were developed for a specific systematic mapping study.

Researchers applying the code to another topic are responsible for:

- defining appropriate eligibility criteria;
- adapting domain-specific logic;
- validating the modified workflow;
- documenting all modifications;
- maintaining human oversight.

---

# 20. Suggested Citation and Attribution

Researchers who adapt this repository are encouraged to preserve attribution to the original software and clearly document their modifications.

When substantial changes are made, the adapted implementation should identify:

```text
original repository/version
modified prompt version
modified classifier version
new eligibility criteria
calibration procedure
date of adaptation
```

This helps distinguish the original implementation from derivative research workflows.