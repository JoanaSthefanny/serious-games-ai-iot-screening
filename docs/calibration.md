# Classifier Development and Calibration

## Purpose

The automated screening system was developed iteratively using previously manually assessed records.

The objective of calibration was to reduce false-negative screening decisions while maintaining the ability to automatically exclude clearly irrelevant records.

The calibration data were used during classifier development and therefore must **not** be interpreted as an independent external validation set.

---

## Development Strategy

Classifier development followed an iterative process:

```text
Initial screening rules
        ↓
Comparison with manually assessed records
        ↓
False-negative analysis
        ↓
Identification of recurring ambiguity patterns
        ↓
Conservative rule refinement
        ↓
Re-evaluation
```

Adjustments focused primarily on cases in which potentially relevant studies could be lost because title or abstract metadata did not explicitly describe every required component.

---

## IEEE Calibration Set

A calibration subset of manually assessed IEEE records was used to evaluate the final screening behavior.

The final calibration set contained:

```text
11 manually relevant records
22 manually non-relevant title/abstract records
```

Total:

```text
33 calibration records
```

---

## Relevant Records

Final classifier behavior:

```text
Relevant records evaluated: 11
Relevant records preserved: 11
False negatives: 0
Sensitivity: 100%
```

A relevant record was considered preserved when the classifier produced either:

```text
RETAIN
```

or:

```text
UNCERTAIN
```

because both outcomes prevent automatic exclusion.

---

## Non-Relevant Records

For the 22 manually non-relevant records:

```text
EXCLUDE: 19
UNCERTAIN: 3
RETAIN: 0
```

Automatic exclusion rate among these records:

```text
19 / 22 = 86.36%
```

The three uncertain records were intentionally preserved for human review rather than forced into an automatic exclusion.

---

## Global Positive Stress Test

A sensitivity-oriented test was performed using 15 previously included studies manually assessed across three databases:

| Database | Relevant studies |
|---|---:|
| IEEE Xplore | 11 |
| PubMed | 2 |
| ACM Digital Library | 2 |
| **Total** | **15** |

The 11 relevant IEEE records described in the IEEE calibration section are included in this 15-study set and must not be counted twice. The multi-database test therefore extends the IEEE positive set with four additional studies from PubMed and ACM Digital Library.

Final result:

```text
Preserved: 15 / 15
Automatically excluded: 0
Sensitivity: 100%
```

A study was considered preserved when the classifier assigned either `RETAIN` or `UNCERTAIN`, as both outcomes prevent automatic exclusion and allow subsequent human assessment.

The purpose of this test was to determine whether the automated screening stage would incorrectly eliminate known relevant studies.

These records informed classifier development. Therefore, the reported results describe performance on development/calibration material and must not be interpreted as independent external validation.

---

## Interpretation

The calibration process was intentionally optimized for high sensitivity.

The intended error trade-off is:

```text
False positive
→ additional human screening effort

False negative
→ potentially relevant study permanently lost
```

Therefore, uncertain cases are intentionally preserved even when this increases manual screening workload.

---

## Important Limitation

The calibration records influenced classifier development.

Consequently, performance on this dataset should not be reported as independent validation performance.

The reported figures demonstrate the behavior of the final classifier on the development/calibration material.

Independent external validation would require a separate dataset that was not used to design or modify the classifier.

---

## Recorded Historical Configuration

The version identifiers recorded for the historical research execution are:

```text
Gemini model: gemini-3.5-flash-lite
Prompt version: 1.6
Classifier version: 1.8
```

---

Historical results were produced by the original research scripts. Their recorded version identifiers are preserved. The current public implementation uses prompt v1.7 and classifier v1.10; the historical results do not constitute a new Gemini execution with this configuration.

## Full Screening Run

After calibration, the final screening pipeline was executed across the six database collections incorporated into the master dataset.

The combined dataset contained:

```text
1,046 records
```

Final automated screening distribution:

```text
RETAIN:     37
UNCERTAIN: 141
EXCLUDE:   868
```

Therefore:

```text
Automatically excluded: 868 / 1,046 = 82.98%
Preserved for further assessment: 178 / 1,046 = 17.02%
```

The preserved group consists of:

```text
37 RETAIN
141 UNCERTAIN
```

Additional execution information:

```text
Records without abstracts: 74
Safety rescues: 40
Technical errors remaining after completion: 0
```

Records without abstracts were included within the `UNCERTAIN` category rather than automatically excluded.

---

## Screening Results by Database

### IEEE Xplore

```text
Records: 69
RETAIN: 16
UNCERTAIN: 14
EXCLUDE: 39
Safety rescues: 5
No abstract: 1
```

### PubMed

```text
Records: 13
RETAIN: 1
UNCERTAIN: 3
EXCLUDE: 9
Safety rescues: 1
No abstract: 0
```

### ACM Digital Library

```text
Records: 7
RETAIN: 2
UNCERTAIN: 1
EXCLUDE: 4
Safety rescues: 1
No abstract: 0
```

### Scopus

```text
Records: 31
RETAIN: 5
UNCERTAIN: 4
EXCLUDE: 22
Safety rescues: 2
No abstract: 0
```

### Engineering Village / Compendex

```text
Records: 25
RETAIN: 1
UNCERTAIN: 2
EXCLUDE: 22
Safety rescues: 1
No abstract: 0
```

### Springer Link

```text
Records: 901
RETAIN: 12
UNCERTAIN: 117
EXCLUDE: 772
Safety rescues: 30
No abstract: 73
```

---

## Human Review Requirement

The automated distribution does not represent final study inclusion.

`RETAIN` and `UNCERTAIN` records remain subject to human assessment and, when required, full-text eligibility evaluation.
