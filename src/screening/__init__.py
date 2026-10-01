"""
Screening package for the Serious Games AI-IoT Screening project.

The screening pipeline combines:

1. LLM-assisted evidence classification;
2. deterministic eligibility rules;
3. conservative safety-rescue mechanisms;
4. routing of ambiguous studies to human review.
"""

MODEL_NAME = "gemini-3.5-flash-lite"
PROMPT_VERSION = "1.6"
CLASSIFIER_VERSION = "1.8"

__all__ = [
    "MODEL_NAME",
    "PROMPT_VERSION",
    "CLASSIFIER_VERSION",
]