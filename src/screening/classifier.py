"""
Core screening classifier.

This module separates two responsibilities:

1. Gemini classifies the evidence available in title, abstract and
   keywords.
2. Python applies deterministic screening rules.

This separation improves auditability and reproducibility.

IMPORTANT
---------
The screening stage is intentionally conservative.

A study should be automatically EXCLUDED only when the available
metadata provides sufficient evidence for exclusion.

When evidence is incomplete or ambiguous, the study is routed to
UNCERTAIN for human review.
"""

from pathlib import Path
from typing import Literal
import re
import time
import unicodedata

from google.genai import types
from pydantic import BaseModel, Field


# ============================================================
# VERSIONING
# ============================================================

MODEL_NAME = "gemini-3.5-flash-lite"

PROMPT_VERSION = "1.6"

CLASSIFIER_VERSION = "1.9"

MAX_ATTEMPTS = 3


# ============================================================
# PATHS
# ============================================================

SCREENING_DIR = Path(__file__).resolve().parent
SRC_DIR = SCREENING_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

PROMPT_FILE = (
    PROJECT_ROOT
    / "prompts"
    / "screening_prompt_v1_6_pt.txt"
)


# ============================================================
# STRUCTURED GEMINI RESPONSE
# ============================================================

class ScreeningAssessment(BaseModel):

    serious_game: Literal[
        "YES",
        "NO",
        "UNCERTAIN",
    ] = Field(
        description=(
            "Whether the metadata supports the presence of a "
            "serious game, exergame, therapeutic game, health game "
            "or equivalent game-based intervention."
        )
    )

    evidence_serious_game: str = Field(
        description=(
            "Evidence supporting the serious-game classification."
        )
    )

    gamification_only: Literal[
        "YES",
        "NO",
        "UNCERTAIN",
    ] = Field(
        description=(
            "Whether the study appears to use only gamification "
            "elements rather than a serious game."
        )
    )

    evidence_gamification: str = Field(
        description=(
            "Evidence supporting the gamification-only classification."
        )
    )

    health: Literal[
        "YES",
        "NO",
        "UNCERTAIN",
    ] = Field(
        description=(
            "Whether the study has a health, healthcare, clinical, "
            "rehabilitation, diagnosis, assistive-health, therapeutic "
            "or health-related physical-activity context."
        )
    )

    evidence_health: str = Field(
        description=(
            "Evidence supporting the health classification."
        )
    )

    ai: Literal[
        "YES",
        "NO",
        "UNCERTAIN",
    ] = Field(
        description=(
            "Whether an artificial intelligence technique is "
            "actually used in the proposed system or study."
        )
    )

    evidence_ai: str = Field(
        description=(
            "Evidence supporting the AI classification."
        )
    )

    iot: Literal[
        "EXPLICIT_IOT",
        "FUNCTIONALLY_COMPATIBLE",
        "NO",
        "UNCERTAIN",
    ] = Field(
        description=(
            "Classification of IoT presence."
        )
    )

    evidence_iot: str = Field(
        description=(
            "Evidence supporting the IoT classification."
        )
    )

    secondary_or_incomplete: Literal[
        "YES",
        "NO",
        "UNCERTAIN",
    ] = Field(
        description=(
            "Whether the record is a secondary study, review, "
            "bibliometric study, protocol-only publication, abstract, "
            "poster or otherwise incomplete publication."
        )
    )

    evidence_study_type: str = Field(
        description=(
            "Evidence supporting the study-type classification."
        )
    )

    notes: str = Field(
        default="",
        description=(
            "Additional relevant observations."
        )
    )


# ============================================================
# SCREENING PROMPT
#
# Portuguese is intentionally preserved because this represents
# the language used during classifier development/calibration.
# ============================================================

DEFAULT_PROMPT = """
Você está auxiliando na etapa de triagem por TÍTULO, RESUMO e
PALAVRAS-CHAVE de um mapeamento sistemático.

O objetivo do mapeamento é identificar estudos sobre JOGOS SÉRIOS
APLICADOS À SAÚDE que utilizem simultaneamente INTELIGÊNCIA
ARTIFICIAL e INTERNET DAS COISAS, incluindo arquiteturas
funcionalmente compatíveis com IoT.

A triagem deve priorizar SENSIBILIDADE. O objetivo desta etapa não é
decidir definitivamente a inclusão com base apenas no resumo, mas
evitar a exclusão indevida de estudos potencialmente relevantes.

Analise EXCLUSIVAMENTE as informações fornecidas em título, resumo e
palavras-chave.

Não utilize conhecimento externo sobre o artigo.

Não invente informações que não estejam disponíveis.

Quando a informação disponível não for suficiente para afirmar SIM ou
NÃO com segurança, utilize INCERTO.

============================================================
1. JOGO SÉRIO
============================================================

Classifique como YES quando houver evidência clara de:

- serious game;
- serious gaming;
- exergame;
- therapeutic game;
- health game;
- rehabilitation game;
- game-based rehabilitation/training/assessment;
- jogo digital utilizado com propósito não exclusivamente recreativo.

Também podem indicar jogo:

- gameplay;
- game environment;
- game task;
- game mechanics;
- player interaction;
- scores, levels, challenges ou feedback inseridos em uma experiência
  de jogo;
- tarefas interativas explicitamente descritas como game/exergame.

IMPORTANTE:

Gamificação isolada NÃO equivale automaticamente a jogo sério.

Aplicativos, telereabilitação, sistemas de monitoramento, ambientes
virtuais, realidade virtual, dashboards ou plataformas digitais também
NÃO equivalem automaticamente a jogo sério.

Entretanto, se houver sinais de uma possível experiência de jogo, mas
o resumo não permitir confirmar a natureza do jogo, utilize UNCERTAIN
em vez de NO.

Não classifique como NO apenas porque a expressão "serious game" não
aparece literalmente.

============================================================
2. GAMIFICAÇÃO APENAS
============================================================

Classifique gamification_only como YES somente quando o estudo descreve
elementos de gamificação sem evidência de um jogo propriamente dito.

Exemplos:

- pontos;
- badges;
- ranking;
- recompensas;
- desafios adicionados a uma aplicação convencional.

Se o artigo descreve um serious game ou exergame completo,
gamification_only deve ser NO.

Se não for possível distinguir com segurança, use UNCERTAIN.

============================================================
3. CONTEXTO DE SAÚDE
============================================================

Considere saúde em sentido amplo.

Inclua:

- diagnóstico;
- tratamento;
- terapia;
- reabilitação;
- fisioterapia;
- neuroreabilitação;
- saúde mental;
- monitoramento de pacientes;
- prevenção;
- avaliação funcional;
- treinamento motor;
- doenças e condições clínicas;
- pessoas idosas quando relacionado à saúde/independência funcional;
- tecnologia assistiva relacionada a condições de saúde;
- atividade física, exercício, fitness ou prevenção da inatividade
  quando o estudo estabelece relação com saúde, bem-estar, obesidade,
  reabilitação ou condição funcional.

Não classifique como NO apenas porque o estudo não utiliza a palavra
"health".

Se a relação com saúde for plausível, porém insuficientemente descrita,
use UNCERTAIN.

============================================================
4. INTELIGÊNCIA ARTIFICIAL
============================================================

Classifique como YES quando houver uso efetivo de técnicas como:

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
- pose estimation / pose recognition;
- human activity recognition;
- emotion recognition;
- natural language processing;
- explainable artificial intelligence;
- intelligent/adaptive models quando a técnica de IA estiver descrita.

Apenas processamento digital, algoritmo, automação ou software não são
suficientes para caracterizar IA.

A IA pode integrar qualquer módulo funcional da solução. Ela não
precisa necessariamente adaptar diretamente a mecânica do jogo.

Se há indícios fortes de IA, mas o resumo não descreve suficientemente
o método, use UNCERTAIN.

============================================================
5. INTERNET DAS COISAS
============================================================

Use EXPLICIT_IOT quando o artigo mencionar explicitamente:

- Internet of Things;
- IoT;
- Internet of Medical Things;
- IoMT;
- arquitetura IoT equivalente.

Use FUNCTIONALLY_COMPATIBLE quando existir uma cadeia funcional
compatível com IoT, mesmo que o termo IoT não seja utilizado.

Procure uma combinação coerente envolvendo:

1. sensor/dispositivo físico;
2. aquisição de dados;
3. comunicação/transmissão para outro componente;
4. outro componente recebendo/processando/usando os dados.

Exemplos de comunicação:

- Bluetooth;
- BLE;
- Wi-Fi;
- wireless transmission;
- UDP;
- TCP/IP;
- MQTT;
- network communication;
- cloud/edge communication;
- comunicação entre wearable/sensor e computador ou outro dispositivo.

Possíveis dispositivos incluem:

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

ATENÇÃO:

Uma webcam, câmera, smartphone, sensor ou computador utilizado
isoladamente e com processamento puramente local NÃO deve ser
automaticamente classificado como IoT.

Porém, ausência de detalhes de comunicação no resumo NÃO significa
necessariamente ausência de IoT no texto completo.

Quando o resumo mencionar dispositivos/sensores integrados a uma
solução, mas não fornecer informação suficiente sobre a arquitetura
de comunicação, prefira UNCERTAIN em vez de NO se houver plausibilidade
de conectividade.

IoT mencionada apenas na introdução, trabalhos relacionados, comparação
ou como tecnologia futura não caracteriza IoT da solução proposta.

============================================================
6. ESTUDO SECUNDÁRIO OU INCOMPLETO
============================================================

Classifique YES quando houver evidência clara de:

- systematic review;
- systematic mapping;
- scoping review;
- literature review;
- bibliometric analysis;
- meta-analysis;
- survey/review article;
- editorial;
- abstract-only publication;
- poster-only publication;
- protocolo sem resultados da solução.

NÃO considere automaticamente um artigo como secundário ou incompleto
apenas porque:

- é conference paper;
- é book chapter;
- menciona a palavra project;
- apresenta um projeto de pesquisa;
- descreve desenvolvimento de sistema.

Se houver dúvida, use UNCERTAIN.

============================================================
REGRA CENTRAL DE CONSERVADORISMO
============================================================

Nesta etapa, NO deve ser utilizado apenas quando as informações
disponíveis sustentarem razoavelmente a ausência do critério.

A simples ausência de detalhes no resumo deve resultar em UNCERTAIN
quando o estudo permanecer plausivelmente relevante.

O texto completo será utilizado posteriormente para resolver esses
casos.

Retorne somente a estrutura solicitada pelo schema.
"""


# ============================================================
# PROMPT LOADING
# ============================================================

def load_screening_prompt():
    """
    Loads the documented prompt when available.

    An embedded fallback is kept so the software remains executable
    even when the documentation file has not yet been created.
    """

    if PROMPT_FILE.exists():

        content = PROMPT_FILE.read_text(
            encoding="utf-8"
        ).strip()

        if content:
            return content

    return DEFAULT_PROMPT.strip()


# ============================================================
# TEXT UTILITIES
# ============================================================

def safe_text(value):

    if value is None:
        return ""

    return str(value).strip()


def normalize_text(value):

    value = safe_text(value)

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    value = value.lower()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def combined_metadata(
    title,
    abstract,
    keywords,
):

    return normalize_text(
        " ".join(
            [
                safe_text(title),
                safe_text(abstract),
                safe_text(keywords),
            ]
        )
    )


# Acronyms must appear as complete terms, not inside other words.
ACRONYM_SIGNALS = {
    "cnn",
    "rnn",
    "xai",
    "emg",
    "eeg",
    "eog",
    "imu",
    "ble",
    "udp",
    "tcp",
    "mqtt",
    "iot",
    "iomt",
    "xr",
}


def contains_any(
    text,
    terms,
):

    for term in terms:

        if term in ACRONYM_SIGNALS:

            pattern = (
                rf"(?<!\w){re.escape(term)}(?!\w)"
            )

            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):
                return True

        elif term in text:
            return True

    return False


# ============================================================
# LEXICAL SAFETY SIGNALS
#
# These do NOT automatically include an article.
# They only prevent aggressive automatic exclusion.
# ============================================================

GAME_SIGNALS = [
    "serious game",
    "serious gaming",
    "exergame",
    "exergaming",
    "therapeutic game",
    "health game",
    "rehabilitation game",
    "game-based",
    "game based",
    "gameplay",
    "gaming",
    "video game",
    "virtual game",
    "game environment",
    "game task",
]


HEALTH_SIGNALS = [
    "health",
    "healthcare",
    "patient",
    "clinical",
    "rehabilitation",
    "rehabilit",
    "therapy",
    "therapeutic",
    "physiotherapy",
    "physical therapy",
    "diagnos",
    "cerebral palsy",
    "sarcopenia",
    "neurolog",
    "cognitive impairment",
    "autism",
    "stroke",
    "elderly",
    "older adult",
    "obesity",
    "physical activity",
    "exercise",
    "fitness",
    "assistive technology",
]


AI_SIGNALS = [
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "neural network",
    "cnn",
    "rnn",
    "transformer",
    "computer vision",
    "pose estimation",
    "pose recognition",
    "human activity recognition",
    "pattern recognition",
    "emotion recognition",
    "classification model",
    "predictive model",
    "explainable artificial intelligence",
    "explainable ai",
    "xai",
]


DEVICE_SIGNALS = [
    "wearable",
    "sensor",
    "body-worn",
    "body worn",
    "smart device",
    "smart object",
    "emg",
    "eeg",
    "eog",
    "imu",
    "accelerometer",
    "eye tracking",
    "eye tracker",
    "robot",
    "smartphone",
    "physiological data",
]


COMMUNICATION_SIGNALS = [
    "bluetooth",
    "ble",
    "wi-fi",
    "wifi",
    "wireless",
    "udp",
    "tcp",
    "mqtt",
    "network",
    "cloud",
    "edge",
    "connected",
    "communication",
    "transmission",
    "transmit",
]


IOT_EXPLICIT_SIGNALS = [
    "internet of things",
    "internet of medical things",
    "iot",
    "iomt",
]


IMMERSIVE_SIGNALS = [
    "virtual reality",
    "vr environment",
    "immersive",
    "extended reality",
    "xr",
    "automated vr",
]


AAL_SIGNALS = [
    "ambient assisted living",
    "assisted living",
    "independent living",
    "elderly",
    "older adults",
    "assistive robot",
    "assistive robots",
    "smart objects",
    "smart home",
    "virtual communities",
    "cognitive stimulation",
    "physical stimulation",
]


SECONDARY_SIGNALS = [
    "systematic review",
    "systematic literature review",
    "systematic mapping",
    "scoping review",
    "literature review",
    "bibliometric analysis",
    "bibliometric study",
    "meta-analysis",
    "meta analysis",
    "review article",
]


# ============================================================
# SAFETY SIGNAL FUNCTIONS
# ============================================================

def has_game_signal(text):

    return contains_any(
        text,
        GAME_SIGNALS,
    )


def has_health_signal(text):

    return contains_any(
        text,
        HEALTH_SIGNALS,
    )


def has_ai_signal(text):

    return contains_any(
        text,
        AI_SIGNALS,
    )


def has_iot_explicit_signal(text):

    return contains_any(
        text,
        IOT_EXPLICIT_SIGNALS,
    )


def has_connected_architecture_signal(text):
    """
    Requires both a device/sensor signal and communication signal.
    """

    return (
        contains_any(
            text,
            DEVICE_SIGNALS,
        )
        and
        contains_any(
            text,
            COMMUNICATION_SIGNALS,
        )
    )


def has_multimodal_signal(text):
    """
    Conservative signal for technically rich immersive systems where
    title/abstract may omit one architecture detail.
    """

    immersive = contains_any(
        text,
        IMMERSIVE_SIGNALS,
    )

    intelligent = contains_any(
        text,
        AI_SIGNALS,
    )

    device_or_connection = (
        contains_any(
            text,
            DEVICE_SIGNALS,
        )
        or
        contains_any(
            text,
            COMMUNICATION_SIGNALS,
        )
    )

    return (
        immersive
        and intelligent
        and device_or_connection
    )


def has_aal_signal(text):

    return contains_any(
        text,
        AAL_SIGNALS,
    )


def has_clear_secondary_signal(text):

    return contains_any(
        text,
        SECONDARY_SIGNALS,
    )


# ============================================================
# GEMINI REQUEST
# ============================================================

def build_request_text(
    title,
    abstract,
    keywords,
):

    prompt = load_screening_prompt()

    return f"""
{prompt}

============================================================
REGISTRO A SER ANALISADO
============================================================

TÍTULO:
{safe_text(title)}

RESUMO:
{safe_text(abstract)}

PALAVRAS-CHAVE:
{safe_text(keywords)}
""".strip()


def is_quota_error(error):

    text = str(error).lower()

    return (
        "429" in text
        or
        "resource_exhausted" in text
        or
        "quota" in text
        or
        "too many requests" in text
    )


def analyze_article(
    client,
    title,
    abstract,
    keywords="",
):
    """
    Runs Gemini evidence classification.

    Gemini does NOT make the final eligibility decision.
    """

    request_text = build_request_text(
        title=title,
        abstract=abstract,
        keywords=keywords,
    )

    last_error = None

    for attempt in range(
        1,
        MAX_ATTEMPTS + 1,
    ):

        try:

            response = (
                client.models.generate_content(
                    model=MODEL_NAME,
                    contents=request_text,
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                        response_schema=ScreeningAssessment,
                    ),
                )
            )

            parsed = getattr(
                response,
                "parsed",
                None,
            )

            if parsed is not None:

                if isinstance(
                    parsed,
                    ScreeningAssessment,
                ):
                    return parsed

                return ScreeningAssessment.model_validate(
                    parsed
                )

            response_text = safe_text(
                getattr(
                    response,
                    "text",
                    "",
                )
            )

            if not response_text:

                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            return ScreeningAssessment.model_validate_json(
                response_text
            )

        except Exception as error:

            last_error = error

            # A quota error should be handled immediately by the
            # checkpoint layer instead of wasting additional calls.
            if is_quota_error(error):
                raise

            if attempt >= MAX_ATTEMPTS:
                raise

            wait_seconds = (
                2 ** attempt
            )

            print(
                f"    Attempt {attempt} failed: {error}"
            )

            print(
                f"    Retrying in {wait_seconds} seconds..."
            )

            time.sleep(
                wait_seconds
            )

    raise last_error


# ============================================================
# DETERMINISTIC CLASSIFIER V1.9
# ============================================================

def make_screening_decision(
    assessment,
    title="",
    abstract="",
    keywords="",
):
    """
    Applies deterministic screening rules.

    Returns
    -------
    tuple
        decision, reason, rescue_code

    decision:
        RETAIN
        UNCERTAIN
        EXCLUDE
    """

    text = combined_metadata(
        title,
        abstract,
        keywords,
    )

    serious_game = assessment.serious_game
    health = assessment.health
    ai = assessment.ai
    iot = assessment.iot

    gamification_only = (
        assessment.gamification_only
    )

    study_type = (
        assessment.secondary_or_incomplete
    )

    iot_positive = iot in {
        "EXPLICIT_IOT",
        "FUNCTIONALLY_COMPATIBLE",
    }

    # ========================================================
    # CONTRADICTORY GAME CLASSIFICATION
    # ========================================================

    if (
        serious_game == "YES"
        and gamification_only == "YES"
    ):

        return (
            "UNCERTAIN",
            (
                "The metadata produced contradictory game labels. "
                "Human review is required."
            ),
            "RESCUE_CONTRADICTORY_GAME_LABELS",
        )

    # ========================================================
    # SECONDARY / INCOMPLETE STUDIES
    #
    # Do not trust a model-only secondary classification unless
    # title/abstract/keywords contain a clear secondary-study signal.
    # ========================================================

    if study_type == "YES":

        if has_clear_secondary_signal(
            text
        ):

            return (
                "EXCLUDE",
                (
                    "Clear evidence of a secondary study, review, "
                    "bibliometric study or other ineligible "
                    "publication type."
                ),
                "",
            )

        return (
            "UNCERTAIN",
            (
                "The LLM classified the publication as secondary "
                "or incomplete, but the metadata does not contain "
                "a sufficiently clear secondary-study signal."
            ),
            "RESCUE_STUDY_TYPE_AMBIGUITY",
        )

    # ========================================================
    # GAMIFICATION ONLY
    # ========================================================

    if gamification_only == "YES":

        if (
            serious_game == "UNCERTAIN"
            or has_game_signal(text)
        ):

            return (
                "UNCERTAIN",
                (
                    "Gamification was detected, but the metadata also "
                    "contains possible game evidence."
                ),
                "RESCUE_GAME_AMBIGUITY",
            )

        return (
            "EXCLUDE",
            (
                "The study appears to use gamification only rather "
                "than a serious game."
            ),
            "",
        )

    # ========================================================
    # EXPLICIT TEXTUAL RESCUES
    #
    # If the model says NO while the actual metadata contains
    # explicit terminology for that dimension, do not automatically
    # discard the record.
    # ========================================================

    if (
        serious_game == "NO"
        and has_game_signal(text)
    ):

        return (
            "UNCERTAIN",
            (
                "The LLM classified the game criterion as absent, "
                "but title/abstract/keywords contain game-related "
                "terminology."
            ),
            "RESCUE_GAME_EVIDENCE",
        )

    if (
        health == "NO"
        and has_health_signal(text)
    ):

        return (
            "UNCERTAIN",
            (
                "The LLM classified the health criterion as absent, "
                "but the metadata contains health-related evidence."
            ),
            "RESCUE_HEALTH_EVIDENCE",
        )

    if (
        ai == "NO"
        and has_ai_signal(text)
    ):

        return (
            "UNCERTAIN",
            (
                "The LLM classified AI as absent, but explicit "
                "AI-related terminology appears in the metadata."
            ),
            "RESCUE_AI_EVIDENCE",
        )

    if (
        iot == "NO"
        and (
            has_iot_explicit_signal(text)
            or
            has_connected_architecture_signal(text)
        )
    ):

        return (
            "UNCERTAIN",
            (
                "The LLM classified IoT as absent, but the metadata "
                "contains explicit IoT terminology or a connected "
                "device/sensor architecture signal."
            ),
            "RESCUE_IOT_ARCHITECTURE",
        )

    # ========================================================
    # 3-OF-4 CORE CRITERIA SAFETY RESCUE
    #
    # This protects studies where one dimension is not sufficiently
    # described in the abstract but the remaining three criteria are
    # strongly supported.
    # ========================================================

    positive_count = sum(
        [
            serious_game == "YES",
            health == "YES",
            ai == "YES",
            iot_positive,
        ]
    )

    core_no_count = sum(
        [
            serious_game == "NO",
            health == "NO",
            ai == "NO",
            iot == "NO",
        ]
    )

    if (
        positive_count >= 3
        and core_no_count >= 1
    ):

        return (
            "UNCERTAIN",
            (
                "Three of the four core eligibility dimensions are "
                "supported, while one dimension is reported as absent. "
                "The record is preserved for human review."
            ),
            "RESCUE_3_OF_4",
        )

    # ========================================================
    # MULTIMODAL / IMMERSIVE SYSTEM RESCUE
    #
    # Used only to prevent automatic exclusion when an immersive,
    # intelligent and device-connected system is incompletely
    # described in the abstract.
    # ========================================================

    if (
        health == "YES"
        and ai in {
            "YES",
            "UNCERTAIN",
        }
        and has_multimodal_signal(text)
        and (
            serious_game == "NO"
            or iot == "NO"
        )
    ):

        return (
            "UNCERTAIN",
            (
                "The record describes a multimodal immersive "
                "intelligent system, but one screening dimension is "
                "insufficiently explicit in the metadata."
            ),
            "RESCUE_MULTIMODAL_SYSTEM",
        )

    # ========================================================
    # AAL / ASSISTIVE ENVIRONMENT RESCUE
    #
    # Protects connected assistive-health systems where the game or AI
    # component may only be described in the full text.
    # ========================================================

    if (
        health == "YES"
        and iot_positive
        and ai in {
            "YES",
            "UNCERTAIN",
        }
        and serious_game == "NO"
        and has_aal_signal(text)
    ):

        return (
            "UNCERTAIN",
            (
                "The record describes an IoT-enabled assistive or "
                "independent-living health environment, but the game "
                "component cannot be resolved safely from metadata."
            ),
            "RESCUE_AAL_ASSISTIVE_SYSTEM",
        )

    # ========================================================
    # UNCERTAINTY
    # ========================================================

    if (
        serious_game == "UNCERTAIN"
        or
        health == "UNCERTAIN"
        or
        ai == "UNCERTAIN"
        or
        iot == "UNCERTAIN"
        or
        gamification_only == "UNCERTAIN"
        or
        study_type == "UNCERTAIN"
    ):

        return (
            "UNCERTAIN",
            (
                "At least one eligibility criterion cannot be "
                "determined safely from title, abstract and keywords."
            ),
            "",
        )

    # ========================================================
    # CORE EXCLUSIONS
    # ========================================================

    if serious_game == "NO":

        return (
            "EXCLUDE",
            (
                "No sufficient evidence of a serious game or "
                "equivalent game-based intervention."
            ),
            "",
        )

    if health == "NO":

        return (
            "EXCLUDE",
            (
                "No sufficient evidence of a health-related context."
            ),
            "",
        )

    if ai == "NO":

        return (
            "EXCLUDE",
            (
                "No sufficient evidence that artificial intelligence "
                "is used in the proposed study or system."
            ),
            "",
        )

    if iot == "NO":

        return (
            "EXCLUDE",
            (
                "No explicit IoT or functionally compatible IoT "
                "architecture is supported by the available metadata."
            ),
            "",
        )

    # ========================================================
    # ALL CORE CRITERIA SATISFIED
    # ========================================================

    return (
        "RETAIN",
        (
            "Title, abstract and keywords support serious game, "
            "health, AI and IoT eligibility criteria."
        ),
        "",
    )