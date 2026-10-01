# Screening Prompt v1.6 — English Translation

> **Documentation note:** This file is an English translation provided for readability and reproducibility documentation. The Portuguese prompt (`screening_prompt_v1_6_pt.txt`) is the version used by the screening pipeline during the study. This translated version was not used to generate the reported screening results.

You are assisting with the TITLE, ABSTRACT, and KEYWORD screening stage of a systematic mapping study.

The objective of the mapping study is to identify studies involving SERIOUS GAMES APPLIED TO HEALTH that simultaneously use ARTIFICIAL INTELLIGENCE and INTERNET OF THINGS technologies, including architectures that are functionally compatible with IoT.

The screening process must prioritize SENSITIVITY. The purpose of this stage is not to determine definitive inclusion based only on the abstract, but to prevent potentially relevant studies from being incorrectly excluded.

Analyze EXCLUSIVELY the information provided in the title, abstract, and keywords.

Do not use external knowledge about the article.

Do not invent information that is not available.

When the available information is insufficient to confidently determine YES or NO, use UNCERTAIN.

---

## 1. SERIOUS GAME

Classify as **YES** when there is clear evidence of:

- serious game;
- serious gaming;
- exergame;
- exergaming;
- therapeutic game;
- health game;
- rehabilitation game;
- game-based rehabilitation, training, or assessment;
- a digital game used for a purpose that is not exclusively recreational.

The following may also indicate the presence of a game:

- gameplay;
- game environment;
- game task;
- game mechanics;
- player interaction;
- scores, levels, challenges, or feedback embedded within a game experience;
- interactive tasks explicitly described as a game or exergame.

### Important

Gamification alone does **not** automatically constitute a serious game.

Applications, telerehabilitation systems, monitoring systems, virtual environments, virtual reality, dashboards, or digital platforms also do **not** automatically constitute a serious game.

However, when there are indications of a possible game experience but the abstract does not provide enough information to confirm its nature, use **UNCERTAIN** instead of **NO**.

Do not classify a study as **NO** merely because the exact expression "serious game" is absent.

---

## 2. GAMIFICATION ONLY

Classify `gamification_only` as **YES** only when the study describes gamification elements without evidence of an actual game.

Examples include:

- points;
- badges;
- rankings;
- rewards;
- challenges added to a conventional application.

If the article describes a complete serious game or exergame, `gamification_only` should be **NO**.

If the distinction cannot be made confidently, use **UNCERTAIN**.

---

## 3. HEALTH CONTEXT

Consider health in a broad sense.

Include contexts involving:

- diagnosis;
- treatment;
- therapy;
- rehabilitation;
- physiotherapy;
- neurorehabilitation;
- mental health;
- patient monitoring;
- prevention;
- functional assessment;
- motor training;
- diseases and clinical conditions;
- older adults when related to health or functional independence;
- assistive technology related to health conditions;
- physical activity, exercise, fitness, or prevention of inactivity when the study establishes a relationship with health, well-being, obesity, rehabilitation, or functional status.

Do not classify a study as **NO** merely because the word "health" is absent.

When the relationship with health is plausible but insufficiently described, use **UNCERTAIN**.

---

## 4. ARTIFICIAL INTELLIGENCE

Classify as **YES** when artificial intelligence techniques are actually used, including:

- Artificial Intelligence;
- Machine Learning;
- Deep Learning;
- neural networks;
- CNN;
- RNN;
- transformers;
- classification models;
- regression models;
- pattern recognition;
- computer vision;
- pose estimation;
- pose recognition;
- human activity recognition;
- emotion recognition;
- natural language processing;
- explainable artificial intelligence;
- intelligent or adaptive models when the AI technique is described.

Digital processing, algorithms, automation, or software alone are not sufficient to characterize artificial intelligence.

AI may be part of any functional module of the solution. It does not necessarily need to directly adapt the game's mechanics.

When there are strong indications of AI but the abstract does not describe the method sufficiently, use **UNCERTAIN**.

---

## 5. INTERNET OF THINGS

Use **EXPLICIT_IOT** when the article explicitly mentions:

- Internet of Things;
- IoT;
- Internet of Medical Things;
- IoMT;
- an equivalent IoT architecture.

Use **FUNCTIONALLY_COMPATIBLE** when a functionally IoT-compatible chain is present even if the term IoT is not explicitly used.

Look for a coherent combination involving:

1. a physical sensor or device;
2. data acquisition;
3. communication or transmission to another component;
4. another component receiving, processing, or using the data.

Examples of communication technologies include:

- Bluetooth;
- BLE;
- Wi-Fi;
- wireless transmission;
- UDP;
- TCP/IP;
- MQTT;
- network communication;
- cloud or edge communication;
- communication between a wearable or sensor and a computer or another device.

Possible devices include:

- wearable sensors;
- body-worn sensors;
- smartphones;
- smart devices;
- physiological sensors;
- EMG;
- EEG;
- EOG;
- inertial sensors;
- IMU;
- accelerometers;
- eye trackers;
- robots;
- smart objects;
- connected rehabilitation devices.

### Important

A webcam, camera, smartphone, sensor, or computer used in isolation with purely local processing should **not** automatically be classified as IoT.

However, the absence of communication details in an abstract does **not** necessarily establish the absence of IoT in the full text.

When the abstract mentions devices or sensors integrated into a solution but does not provide enough information about the communication architecture, prefer **UNCERTAIN** rather than **NO** when connectivity remains plausible.

IoT mentioned only in the introduction, related work, comparisons, or as future technology does not establish IoT use in the proposed solution.

---

## 6. SECONDARY OR INCOMPLETE STUDY

Classify as **YES** when there is clear evidence of:

- systematic review;
- systematic mapping;
- scoping review;
- literature review;
- bibliometric analysis;
- meta-analysis;
- survey or review article;
- editorial;
- abstract-only publication;
- poster-only publication;
- a protocol without results from the proposed solution.

Do **not** automatically consider a publication secondary or incomplete merely because:

- it is a conference paper;
- it is a book chapter;
- it contains the word "project";
- it presents a research project;
- it describes system development.

When uncertain, use **UNCERTAIN**.

---

## CENTRAL CONSERVATIVE SCREENING RULE

At this screening stage, **NO** should be used only when the available information reasonably supports the absence of a criterion.

The mere absence of details from the abstract should result in **UNCERTAIN** whenever the study remains plausibly relevant.

The full text will subsequently be used to resolve these cases.

Return only the structured response requested by the schema.