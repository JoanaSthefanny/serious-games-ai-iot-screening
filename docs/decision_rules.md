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
Classifier version: 1.10
Prompt version: 1.7
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

Generic software processing or automation alone is not considered sufficient evidence of AI.

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

A core criterion classified as `NO` causes exclusion unless one of the three rescues applies. This check precedes unresolved labels. Secondary/incomplete studies and gamification-only records are excluded before rescues, except for the game/gamification contradiction checked first.

---

# Safety-Rescue Rules

Safety rescues never automatically include a study.

They convert a potentially unsafe automatic exclusion into:

```text
UNCERTAIN
```

for human assessment.

---

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