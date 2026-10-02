# Screening Decision Rules

## Purpose

The screening classifier separates evidence interpretation from the final screening decision.

Gemini evaluates the available title, abstract, and keywords.

The deterministic Python classifier then assigns one of three outcomes:

```text
RETAIN
UNCERTAIN
EXCLUDE
```

The rules documented here correspond to:

```text
Classifier version: 1.11
Prompt version: 1.9
```

---

## Core Eligibility Dimensions

Four core dimensions are evaluated:

1. Serious game;
2. Health context;
3. Artificial intelligence;
4. Internet of Things.

A record must ultimately satisfy all four dimensions to meet the study's eligibility criteria.

At the title/abstract screening stage, however, incomplete information is treated conservatively.

---

## Serious Game

Possible values:

```text
YES
NO
UNCERTAIN
```

`YES` indicates evidence of a serious game, exergame, therapeutic game, health game, rehabilitation game, or equivalent game-based intervention.

`NO` indicates that the available metadata reasonably supports the absence of a game-based intervention.

`UNCERTAIN` indicates that a possible game component exists but cannot be confirmed safely from the available metadata.

---

## Gamification Only

Possible values:

```text
YES
NO
UNCERTAIN
```

Gamification alone does not satisfy the serious-game criterion.

Examples include the isolated use of:

- points;
- rankings;
- badges;
- rewards;
- challenges.

When gamification and game evidence conflict, the record is preserved for manual review.

---

## Health

Possible values:

```text
YES
NO
UNCERTAIN
```

The health criterion includes a broad range of contexts such as:

- diagnosis;
- rehabilitation;
- therapy;
- physiotherapy;
- neurorehabilitation;
- disease management;
- functional assessment;
- health-related exercise;
- physical activity;
- assistive technology;
- health-related independent living.

Exercise, fitness, and physical activity qualify when the study connects the solution to a health purpose, such as prevention, rehabilitation, sedentary behavior reduction, or functional capacity.
---

## Artificial Intelligence

Possible values:

```text
YES
NO
UNCERTAIN
```

AI evidence may include:

- machine learning;
- deep learning;
- neural networks;
- computer vision;
- pose estimation;
- activity recognition;
- pattern recognition;
- emotion recognition;
- natural language processing;
- explainable artificial intelligence.

These techniques must belong to the study's own solution or method. Mentions limited to related work, future plans, or isolated keywords do not establish their use.

Generic software processing or automation alone is not considered sufficient evidence of AI.

### YES

Use `YES` when the metadata supports the use of an AI technique or model in the proposed solution or method.

### NO

Use `NO` when the metadata supports exclusively conventional processing, fixed rules, predetermined thresholds, arithmetic calculations, or traditional statistics, without another supported AI component.

An unspecified algorithm does not automatically constitute AI.

### UNCERTAIN

Use `UNCERTAIN` when the solution describes a concrete analytical function, but its method is insufficiently characterized.

Examples include:

- classification;
- prediction;
- recognition;
- adaptation;
- computational assessment of performance, functional status, or therapeutic progress.

For computational assessment, both elements must be present:

1. Data acquired from sensors, devices, or user interaction;
2. Use of those data by the solution to produce an assessment of performance, functional status, or therapeutic progress.

The presence of sensors, robots, monitoring, storage, transmission, indicator visualization, or point calculation alone is insufficient.

When the analytical method is omitted, do not infer either an AI model or exclusively conventional processing.

If the metadata explicitly describes only conventional methods, with no other plausible AI component, maintain `ai = NO`.

### Joint Interpretation of Title and Abstract

The title and abstract should be interpreted jointly.

When the title indicates computer vision and the abstract describes gesture recognition actually used to control the game, an unspecified recognition method may justify `ai = UNCERTAIN`.

EMG sensors, gyroscopes, Arduino, displays, and programming environments do not independently characterize the recognition method.

Conventional calculations in one component do not establish that a separate recognition component also uses conventional processing.

Explicit fixed-rule or threshold-based recognition remains `ai = NO` when no other AI component is supported.

An isolated computer-vision title without support in the described solution does not justify `ai = YES`.

---

## Secondary or Incomplete Studies

Possible values:

```text
YES
NO
UNCERTAIN
```

### YES

Use `YES` when there is positive evidence that the publication is
a secondary study, an abstract-only publication, a protocol without
completed results, or another incomplete publication.

### NO

Use `NO` when the metadata sufficiently establishes an original
contribution, such as a system, method, architecture, prototype,
or evaluation.

Clinical validation is not required merely to identify a
publication as an original study.

### UNCERTAIN

Use `UNCERTAIN` when publication type cannot be determined safely
from the available metadata.

An overview of the authors' own system does not automatically
constitute a literature review.

The absence of participant counts, validation details, or
implementation details in the abstract does not by itself establish
that the publication is secondary or incomplete.

---

## Internet of Things

Possible values:

```text
EXPLICIT_IOT
FUNCTIONALLY_COMPATIBLE
NO
UNCERTAIN
```

### EXPLICIT_IOT

Used when the proposed solution explicitly mentions concepts such as:

- Internet of Things;
- IoT;
- Internet of Medical Things;
- IoMT.

### FUNCTIONALLY_COMPATIBLE

Used when IoT terminology is absent but the proposed architecture provides a connected chain involving:

1. a physical sensor or device;
2. data acquisition;
3. communication or transmission;
4. another component that receives, processes, or uses the data.

Examples include communication using:

- Bluetooth;
- BLE;
- Wi-Fi;
- UDP;
- TCP/IP;
- MQTT;
- cloud communication;
- edge communication.

### NO

Used when the available metadata reasonably supports that neither explicit IoT nor a functionally compatible connected architecture is used.

### UNCERTAIN

Used when devices or sensors are present but the abstract does not describe the communication architecture sufficiently.

---

# Deterministic Decision Logic

## RETAIN

A record receives:

```text
RETAIN
```

when all four core dimensions are supported:

```text
Serious game = YES
Health = YES
AI = YES
IoT = EXPLICIT_IOT or FUNCTIONALLY_COMPATIBLE
```

and `gamification_only = NO` and `secondary_or_incomplete = NO`.

`RETAIN` means the study should proceed to subsequent review.

It does not represent definitive full-text inclusion.

---

## UNCERTAIN

A record receives:

```text
UNCERTAIN
```

when at least one label is `UNCERTAIN` and no earlier exclusion applies, when the game/gamification labels contradict each other, or when a safety rescue applies.

Examples include:

```text
Serious game = UNCERTAIN
```

or:

```text
IoT = UNCERTAIN
```

or when a safety-rescue mechanism is activated.

These records are preserved for human review.

---

## EXCLUDE

A record may receive:

```text
EXCLUDE
```

when there is sufficiently clear evidence of an exclusion condition.

A core criterion classified as `NO` causes exclusion unless one of the four rescues applies. This check precedes unresolved labels. Secondary/incomplete studies and gamification-only records are excluded before rescues, except for the game/gamification contradiction checked first.

---

# Safety-Rescue Rules

Safety rescues never automatically include a study.

They convert a potentially unsafe automatic exclusion into:

```text
UNCERTAIN
```

for human assessment.

---

The current classifier implements four rescues, evaluated in this order:

| Code | Required conditions |
|---|---|
| `RESGATE_IOT_3_DE_4` | Serious game, health and AI are `YES`; IoT is `NO`; an acquisition or monitoring signal is present. |
| `RESGATE_MULTIMODAL` | Health and AI are `YES`; serious game or IoT is `NO`; both interaction and acquisition signals are present. |
| `RESGATE_AAL_ESTIMULACAO` | Serious game is `NO`; health is `YES`; IoT is `EXPLICIT_IOT` or `FUNCTIONALLY_COMPATIBLE`; AI is `YES` or `UNCERTAIN`; both stimulation and assistive-platform signals are present. |
| `RESGATE_AAL_METADADOS_INCOMPLETOS` | Secondary/incomplete and gamification-only labels are `NO`; serious game and AI are `NO`; health is `YES`; the AI justification matches supported metadata-omission cues without a blocking cue; IoT is `EXPLICIT_IOT`, `FUNCTIONALLY_COMPATIBLE`, or `UNCERTAIN`; acquisition, assistive-platform and stimulation-review signals are present. |

Acquisition, interaction, stimulation and assistive-platform signals are lexical matches in title, abstract and keywords against the `CALIBRATED_*_TERMS` lists in `src/screening/classifier.py`.

The fourth rescue also uses `ai_negative_is_metadata_omission()` and `aal_stimulation_review_signal()`.

The omission helper checks predefined phrases in `evidence_ai`, with blocking phrases checked in `evidence_ai` and `notes`. These patterns can miss paraphrases and do not independently establish whether AI is present or absent.

The stimulation-review helper accepts a calibrated stimulation term or a supported English stimulation-word form occurring together with `cognitive`, `physical`, or `sedentariness` in the combined metadata.

The fourth rescue preserves the original criterion labels. It returns `UNCERTAIN` without confirming a game, AI, or connectivity.

Decision order:

1. Contradictory game/gamification labels;
2. Secondary or incomplete study;
3. Gamification only;
4. The four rescues in the order shown above;
5. Negative core criteria;
6. Uncertain labels;
7. Retention.

When `serious_game = YES` and `gamification_only = YES`, the result is `UNCERTAIN` with an empty rescue code. This contradiction is checked before study type.

An uncertain label does not prevent exclusion by another negative core criterion when no rescue applies.

There is no generic three-of-four rescue and no independent game, health or AI terminology rescue.

---

---

# Missing Abstract Rule

A missing abstract is not interpreted as evidence of absence.

Records without abstracts receive:

```text
UNCERTAIN
```

and are routed to manual review.

---

# API Error Rule

Technical API failures never produce an exclusion decision. Checkpoint write failures propagate and stop execution; they do not change a successful classification to `API_ERROR`. The previous checkpoint is replaced only after the new workbook is fully written.

The internal result is:

```text
API_ERROR
```

The record remains pending and can be retried later.

Examples include:

- temporary model unavailability;
- request errors;
- quota exhaustion;
- authentication problems.

---

# Decision Philosophy

The classifier follows the principle:

> Automatic exclusion requires evidence of absence; absence of evidence should normally lead to uncertainty.

This design prioritizes sensitivity over aggressive workload reduction during the automated screening stage.