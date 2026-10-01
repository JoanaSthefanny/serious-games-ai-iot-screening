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
Classifier version: 1.8
Prompt version: 1.6
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

and no exclusion condition applies.

`RETAIN` means the study should proceed to subsequent review.

It does not represent definitive full-text inclusion.

---

## UNCERTAIN

A record receives:

```text
UNCERTAIN
```

when at least one relevant dimension cannot be determined safely from title, abstract, and keywords.

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

Examples include:

```text
Serious game = NO
```

with no relevant rescue signal;

```text
Health = NO
```

with no health-related metadata signal;

```text
AI = NO
```

with no explicit AI evidence;

```text
IoT = NO
```

with no explicit or functionally compatible connected architecture;

or clear evidence that the publication is:

- a systematic review;
- mapping study;
- bibliometric study;
- secondary study;
- incomplete publication.

---

# Safety-Rescue Rules

Safety rescues never automatically include a study.

They convert a potentially unsafe automatic exclusion into:

```text
UNCERTAIN
```

for human assessment.

---

## RESCUE_CONTRADICTORY_GAME_LABELS

Activated when:

```text
serious_game = YES
```

and:

```text
gamification_only = YES
```

occur simultaneously.

The contradictory interpretation must be resolved manually.

---

## RESCUE_STUDY_TYPE_AMBIGUITY

Activated when the LLM marks a record as secondary or incomplete, but title/abstract/keywords do not provide sufficiently clear secondary-study evidence.

This protects primary studies whose titles contain terms such as:

```text
project
system
framework
development
```

that could otherwise be misinterpreted.

---

## RESCUE_GAME_AMBIGUITY

Activated when gamification is detected but metadata also contains possible evidence of an actual game.

The distinction is deferred to human review.

---

## RESCUE_GAME_EVIDENCE

Activated when:

```text
serious_game = NO
```

but title, abstract, or keywords contain explicit game-related terminology such as:

- serious game;
- exergame;
- gameplay;
- game-based;
- gaming.

---

## RESCUE_HEALTH_EVIDENCE

Activated when:

```text
health = NO
```

but the metadata includes health-related terminology.

Examples include:

- rehabilitation;
- therapy;
- patients;
- neurological conditions;
- physical activity;
- assistive technology.

---

## RESCUE_AI_EVIDENCE

Activated when:

```text
AI = NO
```

but explicit AI-related terminology occurs in the metadata.

Examples include:

- machine learning;
- deep learning;
- neural network;
- computer vision;
- pose recognition;
- activity recognition;
- explainable AI.

---

## RESCUE_IOT_ARCHITECTURE

Activated when:

```text
IoT = NO
```

but metadata contains either:

- explicit IoT terminology; or
- evidence of a connected sensor/device architecture.

The record is routed to manual review rather than excluded.

---

## RESCUE_3_OF_4

The four central criteria are:

```text
Serious game
Health
Artificial intelligence
Internet of Things
```

When at least three are strongly supported and one is classified as absent, automatic exclusion is considered potentially unsafe.

The record is therefore assigned:

```text
UNCERTAIN
```

This rule is particularly relevant when abstracts omit architecture details that may be available only in the full text.

---

## RESCUE_MULTIMODAL_SYSTEM

Activated for technically rich immersive systems combining evidence such as:

- virtual or extended reality;
- AI;
- sensors or connected devices;
- health applications.

If one screening dimension is insufficiently described, the record is preserved for human assessment.

---

## RESCUE_AAL_ASSISTIVE_SYSTEM

Activated for connected assistive-health or ambient-assisted-living systems when:

- health is supported;
- IoT is supported;
- AI is supported or plausible;
- the game component cannot be safely determined from metadata.

This protects complex systems where game-based activities may only be described in the full text.

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

Technical API failures never produce an exclusion decision.

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