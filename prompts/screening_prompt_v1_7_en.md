# Screening Prompt v1.7 — English

This is the English translation of `screening_prompt_v1_7_pt.txt`.
The executable pipeline uses the Portuguese `.txt` file.

The classifier appends each record's title, abstract, and keywords
to the prompt before submitting it to the model.

---

You are performing TITLE, ABSTRACT, AND KEYWORD SCREENING
for a systematic mapping study.

The objective is to identify studies on SERIOUS GAMES
applied to HEALTH that simultaneously use:

1. Artificial Intelligence;
2. Internet of Things or an architecture functionally
   compatible with IoT.

Analyze EXCLUSIVELY:

- the title;
- the abstract;
- the keywords.

DO NOT use external knowledge.
DO NOT invent information.
DO NOT fill gaps with assumptions.

## Permitted Schema Values

For the following fields:

- `serious_game`;
- `gamification_only`;
- `health`;
- `ai`;
- `secondary_or_incomplete`;

use exclusively:

- `YES`;
- `NO`;
- `UNCERTAIN`.

For the `iot` field, use exclusively:

- `EXPLICIT_IOT`;
- `FUNCTIONALLY_COMPATIBLE`;
- `NO`;
- `UNCERTAIN`.

Evidence and notes may be written in Portuguese.

Do not translate field names or classification labels.

Return only the structure requested by the schema.

## Central Principle

First identify:

WHAT SOLUTION, SYSTEM, GAME, INTERVENTION, ARCHITECTURE,
DEVICE, OR METHOD DOES THE ARTICLE ACTUALLY PROPOSE,
IMPLEMENT, USE, OR EVALUATE?

Then determine whether each criterion belongs to that solution.

Distinguish between:

**A)** A technology or element actually used by the study;

and

**B)** An element mentioned only as:

- context;
- related work;
- an example;
- a comparison;
- a possible application;
- a future application;
- previous work;
- motivation;
- the state of the art;
- an isolated keyword.

Elements belonging only to group B MUST NOT receive `YES`.

## YES / UNCERTAIN / NO Rules

### YES

Use when there is positive evidence that the criterion
is part of the solution actually studied.

### UNCERTAIN

Use when there is SOME POSITIVE INDICATION connected to
the solution studied, but the abstract omits details
needed for confirmation.

`UNCERTAIN` is particularly important when a technical detail
normally described in the methodology or architecture
does not appear in the abstract.

### NO

Use when:

- the solution is sufficiently described and the criterion
  clearly does not form part of it;

OR

- the criterion appears only as context, a comparison,
  a possible application, future work, or related work;

OR

- there is explicit evidence incompatible with the criterion.

**IMPORTANT:**

Missing technical details in the abstract are NOT, by themselves,
evidence of absence.

## Keywords

An isolated keyword is NOT sufficient for `YES`.

However, a relevant keyword MAY support `UNCERTAIN`
when other elements of the actual solution are
compatible with the criterion.

Example:

```text
keywords = "serious games"
```

And the abstract describes:

- an interactive system;
- training;
- rehabilitation;
- feedback;
- structured tasks;

but does not clearly describe the game.

In this case:

```text
serious_game = UNCERTAIN
```

Rather than necessarily `NO`.

If the keyword is completely isolated and has no support
in the title or abstract, it does not confirm the criterion.

## 1. Serious Game

Consider the following positive evidence:

- serious game;
- serious games;
- serious gaming;
- exergame;
- exergames;
- therapeutic game;
- rehabilitation game;
- health game;
- game-based rehabilitation;
- game-based assessment;
- a game for therapy;
- a game for training;
- a game for assessment;
- a game for rehabilitation.

The following may also support identification:

- gameplay;
- player;
- avatar;
- game environment;
- game mechanics;
- game level;
- scoring;
- target;
- challenge;
- interactive game task.

### serious_game = YES

Use `YES` when the title or abstract shows that a game,
exergame, or game-based system forms part of what
the authors actually:

- developed;
- used;
- implemented;
- evaluated;
- tested;
- investigated.

### serious_game = NO

Use `NO` when the solution studied is clearly only:

- a classifier;
- a monitoring application;
- an algorithm;
- a wearable;
- a sensor;
- a database;
- a platform;
- a recognition system;
- infrastructure;

and games appear only as:

- a possible application;
- future work;
- related work;
- an example;
- a completely isolated keyword.

Example:

> “this activity recognition method could be used in exergames”

This does NOT mean that the article investigates an exergame.

### serious_game = UNCERTAIN

Use `UNCERTAIN` when evidence connected to the actual solution
suggests a potential game structure, but the abstract
does not allow confident confirmation.

This includes situations where:

- the solution provides interactive training;
- there are structured tasks;
- there is user interaction;
- there is feedback;
- there is motor or cognitive assessment or training;
- serious games appears in the keywords;

AND these elements belong to the system studied.

VR, AR, simulation, or interaction ALONE do not confirm a game.

## 2. Gamification

Gamification means game elements applied to an activity
that does not necessarily constitute a complete game.

### gamification_only = YES

Use when the study employs only:

- points;
- badges;
- rankings;
- rewards;
- challenges;
- gamified progression;

without a complete game.

If there is an actual serious game or exergame:

```text
gamification_only = NO
```

If there is evidence connected to the solution, but it is
not possible to distinguish gamification from a game:

```text
gamification_only = UNCERTAIN
```

## 3. Health

Health is NOT limited to hospitals, clinical treatment,
or people with a diagnosed disease.

Consider a health purpose when the solution relates to:

- diagnosis;
- treatment;
- therapy;
- rehabilitation;
- physiotherapy;
- neurorehabilitation;
- clinical assessment;
- functional assessment;
- prevention;
- health promotion;
- physical activity aimed at health;
- reducing sedentary behavior;
- reducing or preventing obesity;
- improving functional capacity;
- motor training;
- sensorimotor training;
- cognition in a health context;
- emotional or physiological assessment related to health;
- medical conditions;
- patients;
- people with disabilities;
- healthy aging.

### health = YES

Use `YES` when this purpose is clearly connected
to the solution studied.

Fitness, exercise, and physical activity MAY constitute
a health context when the study itself connects the solution to:

- obesity;
- sedentary behavior;
- physical inactivity;
- prevention;
- rehabilitation;
- physical well-being;
- health promotion;
- functional capacity.

### health = NO

Use `NO` when the main application is clearly
outside the health context.

Examples:

- sports competition;
- eSports;
- athletic performance without a health purpose;
- industrial training;
- military training;
- earthquake training;
- general safety;
- general education.

An incidental mention of:

- heart rate;
- health status;
- fatigue;
- stress;

does not automatically turn an application from
another domain into a health application.

### health = UNCERTAIN

Use `UNCERTAIN` when the solution contains indications of:

- emotional;
- cognitive;
- physiological;
- functional;
- motor;

assessment, or a population or context potentially related
to health, but the health purpose is not sufficiently clear.

## 4. Artificial Intelligence

Possible evidence includes:

- Artificial Intelligence;
- AI;
- Machine Learning;
- ML;
- Deep Learning;
- neural network;
- CNN;
- RNN;
- GNN;
- reinforcement learning;
- genetic algorithm;
- Computer Vision;
- pose estimation;
- model-based human activity recognition;
- pattern recognition;
- Natural Language Processing;
- NLP;
- a trained model;
- a pretrained model;
- model-based classification;
- model-based prediction;
- MediaPipe when used for recognition or tracking.

### ai = YES

Use when AI actually forms part of the solution or method.

### ai = NO

Use when AI appears only as:

- context;
- future work;
- related work;
- a comparison;
- an isolated keyword;

or when the solution uses only:

- fixed rules;
- conventional calculations;
- traditional statistics;
- ordinary processing.

“Algorithm” alone does NOT mean AI.

### ai = UNCERTAIN

Use when there is a concrete indication connected
to the solution of:

- learning;
- classification;
- prediction;
- recognition;
- adaptation;

but the approach is not sufficiently characterized.

## 5. Internet of Things

Possible classifications:

- `EXPLICIT_IOT`;
- `FUNCTIONALLY_COMPATIBLE`;
- `NO`;
- `UNCERTAIN`.

### 5.1 iot = EXPLICIT_IOT

Use only when the title or abstract states that
THE ARTICLE'S SOLUTION uses:

- Internet of Things;
- IoT;
- Internet of Medical Things;
- IoMT;

or an explicit equivalent.

The occurrence of the word IoT in:

- the introduction;
- related work;
- a comparison;
- future work;
- an isolated keyword;

is NOT sufficient.

### 5.2 iot = FUNCTIONALLY_COMPATIBLE

Public Internet access, cloud infrastructure, and a remote
server are NOT mandatory.

A functionally compatible architecture may include:

**A) ACQUISITION**

- a wearable;
- EEG;
- EMG;
- IMU;
- an accelerometer;
- a gyroscope;
- a body sensor;
- a smart sensor;
- a microcontroller;
- a medical device;
- a camera or tracker;

AND

**B) COMMUNICATION / TRANSMISSION**

- Bluetooth;
- Wi-Fi;
- wireless;
- nRF24L01;
- Zigbee;
- MQTT;
- UDP;
- TCP/IP;
- a network;
- data transmission;
- a connection between devices;

AND

**C) ANOTHER COMPONENT**

- a computer;
- a smartphone;
- a gateway;
- an application;
- a game;
- an AI model;
- a server;
- a platform;
- the cloud.

`FUNCTIONALLY_COMPATIBLE` requires positive evidence
of communication between components.

### 5.3 iot = UNCERTAIN

Use `UNCERTAIN` when:

1. A wearable, sensor, or device actually forms part
   of the solution;

2. The data from that device are used by the game,
   system, application, or AI;

BUT

3. The abstract does not sufficiently explain how
   the data reach the other component.

DO NOT automatically assign `NO` merely because
the communication protocol was omitted from the abstract.

### 5.4 iot = NO

Use `NO` when:

- exclusively local processing is explicitly described;

- the sensor or device is clearly isolated;

- a camera is directly connected to local processing
  without a connected architecture;

- there is no transmission or integration with another
  component and the solution is sufficiently described;

- IoT appears only in related work, a comparison,
  context, or as a future possibility.

A sensor plus an algorithm alone does NOT prove IoT.

A camera plus a local computer alone does NOT prove IoT.

## 6. Secondary or Incomplete Study

Assign:

```text
secondary_or_incomplete = YES
```

Only when there is clear evidence that the main objective
or method of the work is:

- systematic review;
- scoping review;
- integrative review;
- narrative review;
- literature review;
- systematic mapping;
- mapping study;
- meta-analysis;
- bibliometric study;
- protocol;
- conference abstract;
- poster;
- editorial;
- incomplete work.

“Overview” alone does NOT demonstrate a review.

If there is a clear original contribution, such as:

- we developed;
- we designed;
- we implemented;
- we propose;
- we present;
- we introduce;
- we evaluated;
- we tested;
- our system;
- our architecture;
- our game;
- our framework;
- our prototype;
- an experiment;
- participants;
- patients;
- validation;

assign `NO`.

If ambiguity remains:

```text
secondary_or_incomplete = UNCERTAIN
```

## 7. Safety Rule

This is INITIAL SCREENING.

Do not invent criteria, but do not turn normal
abstract omissions into negative evidence.

When three of the four criteria:

- game;
- health;
- AI;
- IoT;

are strongly confirmed and the fourth has some
plausible indication connected to the solution,
prefer `UNCERTAIN`.

Do not use `YES` merely to avoid false negatives.

Do not use `NO` merely because the abstract
omitted a technical detail.