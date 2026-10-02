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

PROMPT_VERSION = "1.9"

CLASSIFIER_VERSION = "1.11"

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
    / "screening_prompt_v1_9_pt.txt"
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
            "Classifique a IA da própria solução. YES exige evidência "
            "positiva de uma técnica de IA utilizada. UNCERTAIN aplica-se "
            "a indícios de aprendizado, classificação, predição, reconhecimento, "
            "adaptação ou avaliação computacional de desempenho/progresso "
            "terapêutico a partir dos dados adquiridos, quando o método não "
            "é especificado. Sensores ou monitoramento isolados não bastam. "
            "Considere título e abstract juntos: Computer Vision e reconhecimento "
            "gestual utilizado, com método omitido, sustentam UNCERTAIN. "
            "IDE, EMG ou Arduino não caracterizam o método de reconhecimento. "
            "Uma função analítica com método omitido não deve receber NO "
            "apenas pela ausência da palavra IA. Regras fixas ou cálculos "
            "convencionais explicitamente descritos, sem outro componente "
            "de IA na solução, sustentam NO."
        )
    )

    evidence_ai: str = Field(
        description=(
            "Explique a evidência de IA ligada à própria solução. Para "
            "UNCERTAIN, identifique a função descrita e o método omitido. "
            "Não invente técnicas. A ausência de menção a IA, sozinha, "
            "não demonstra ausência quando há função analítica ambígua."
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
            "YES exige evidência positiva de revisão de estudos anteriores, "
            "protocolo sem estudo, resumo/poster/editorial ou publicação "
            "explicitamente incompleta. Overview do próprio sistema não "
            "demonstra revisão. Ausência de experimento no abstract não "
            "basta para YES. Contribuição original clara: NO; natureza "
            "ambígua: UNCERTAIN. We present em uma revisão não basta para NO."
        )
    )

    evidence_study_type: str = Field(
        description=(
            "Explique a evidência positiva para o tipo de estudo. Não justifique "
            "YES somente com overview ou com ausência de validação no abstract."
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
Você está realizando TRIAGEM DE TÍTULO, RESUMO E
PALAVRAS-CHAVE para um mapeamento sistemático.

O objetivo é identificar estudos sobre JOGOS SÉRIOS
aplicados à SAÚDE que utilizem simultaneamente:

1. Inteligência Artificial;
2. Internet das Coisas ou arquitetura funcionalmente
   compatível com IoT.

Analise EXCLUSIVAMENTE:

- título;
- abstract;
- keywords.

NÃO utilize conhecimento externo.
NÃO invente informações.
NÃO complete lacunas com suposições.

============================================================
VALORES PERMITIDOS NO SCHEMA
============================================================

Para os campos:

- serious_game;
- gamification_only;
- health;
- ai;
- secondary_or_incomplete;

utilize exclusivamente:

- YES;
- NO;
- UNCERTAIN.

Para o campo iot, utilize exclusivamente:

- EXPLICIT_IOT;
- FUNCTIONALLY_COMPATIBLE;
- NO;
- UNCERTAIN.

O texto das evidências e observações pode ser escrito em português.

Não traduza os nomes dos campos nem os rótulos de classificação.

Retorne somente a estrutura solicitada pelo schema.

============================================================
PRINCÍPIO CENTRAL
============================================================

Primeiro identifique:

QUAL É A SOLUÇÃO, SISTEMA, JOGO, INTERVENÇÃO,
ARQUITETURA, DISPOSITIVO OU MÉTODO QUE O ARTIGO
REALMENTE PROPÕE, IMPLEMENTA, UTILIZA OU AVALIA?

Depois verifique se cada critério pertence a essa solução.

Diferencie:

A) tecnologia/elemento realmente utilizado pelo estudo;

de

B) elemento apenas mencionado como:

- contexto;
- related work;
- exemplo;
- comparação;
- possível aplicação;
- aplicação futura;
- trabalhos anteriores;
- motivação;
- estado da arte;
- keyword isolada.

Elementos apenas do grupo B NÃO devem receber YES.

============================================================
REGRA YES / UNCERTAIN / NO
============================================================

YES:

Use quando existe evidência positiva de que o critério
faz parte da solução realmente estudada.

UNCERTAIN:

Use quando existe ALGUM INDÍCIO POSITIVO ligado à
solução estudada, mas o resumo omite detalhes necessários
para confirmação.

UNCERTAIN é especialmente importante quando um detalhe
técnico normalmente descrito em metodologia ou arquitetura
não aparece no abstract.

NO:

Use quando:

- a solução está suficientemente descrita e o critério
  claramente não faz parte dela;

OU

- o critério aparece somente como contexto, comparação,
  aplicação possível, trabalho futuro ou related work;

OU

- existe evidência explícita incompatível com o critério.

IMPORTANTE:

Ausência de detalhes técnicos no abstract NÃO é, sozinha,
evidência de ausência.

============================================================
PALAVRAS-CHAVE
============================================================

Uma keyword isolada NÃO é suficiente para YES.

Entretanto, uma keyword relevante PODE contribuir para
UNCERTAIN quando existirem outros elementos da própria solução
compatíveis com o critério.

Exemplo:

keywords = "serious games"

e o abstract descreve:

- sistema interativo;
- treinamento;
- reabilitação;
- feedback;
- tarefas estruturadas;

mas não descreve claramente o jogo.

Nesse caso:

serious_game = UNCERTAIN

e não necessariamente NO.

Se a keyword estiver completamente isolada e sem qualquer
apoio no título ou abstract, ela não confirma o critério.

============================================================
1. JOGO SÉRIO
============================================================

Considere evidências positivas:

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
- jogo para terapia;
- jogo para treinamento;
- jogo para avaliação;
- jogo para reabilitação.

Também podem apoiar a identificação:

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

------------------------------------------------------------
serious_game = YES
------------------------------------------------------------

Use YES quando título ou abstract mostrarem que um jogo,
exergame ou sistema baseado em jogo faz parte do que os
autores realmente:

- desenvolveram;
- utilizaram;
- implementaram;
- avaliaram;
- testaram;
- investigaram.

------------------------------------------------------------
serious_game = NO
------------------------------------------------------------

Use NO quando a solução estudada for claramente apenas:

- classificador;
- aplicativo de monitoramento;
- algoritmo;
- wearable;
- sensor;
- banco de dados;
- plataforma;
- sistema de reconhecimento;
- infraestrutura;

e jogos aparecem somente como:

- possível aplicação;
- trabalho futuro;
- related work;
- exemplo;
- keyword totalmente isolada.

Exemplo:

"this activity recognition method could be used in exergames"

NÃO significa que o artigo investiga um exergame.

------------------------------------------------------------
serious_game = UNCERTAIN
------------------------------------------------------------

Use UNCERTAIN quando existir evidência ligada à própria
solução indicando potencial estrutura de jogo, mas o resumo
não permitir confirmação segura.

Isso inclui situações em que:

- a solução realiza treinamento interativo;
- há tarefas estruturadas;
- existe interação do usuário;
- existe feedback;
- há avaliação ou treinamento motor/cognitivo;
- serious games aparece nas keywords;

E esses elementos pertencem ao sistema estudado.

VR, AR, simulação ou interação SOZINHAS não confirmam jogo.

============================================================
2. GAMIFICAÇÃO
============================================================

Gamificação significa elementos de jogos aplicados a uma
atividade que não constitui necessariamente um jogo completo.

gamification_only = YES:

quando o estudo utiliza somente:

- pontos;
- badges;
- ranking;
- recompensas;
- desafios;
- progressão gamificada;

sem jogo completo.

Se existe serious game ou exergame real:

gamification_only = NO.

Se houver evidência relacionada à solução, mas não for
possível distinguir gamificação de jogo:

gamification_only = UNCERTAIN.

============================================================
3. SAÚDE
============================================================

Saúde NÃO está limitada a hospitais, tratamento clínico
ou pessoas com doença diagnosticada.

Considere finalidade de saúde quando a solução estiver
relacionada a:

- diagnóstico;
- tratamento;
- terapia;
- reabilitação;
- fisioterapia;
- neuroreabilitação;
- avaliação clínica;
- avaliação funcional;
- prevenção;
- promoção da saúde;
- atividade física voltada à saúde;
- combate ao sedentarismo;
- redução ou prevenção da obesidade;
- melhoria da capacidade funcional;
- treinamento motor;
- treinamento sensorimotor;
- cognição em contexto de saúde;
- avaliação emocional ou fisiológica relacionada à saúde;
- condições médicas;
- pacientes;
- pessoas com deficiência;
- envelhecimento saudável.

------------------------------------------------------------
health = YES
------------------------------------------------------------

Use YES quando essa finalidade estiver claramente ligada
à solução estudada.

Fitness, exercício e atividade física PODEM constituir
saúde quando o próprio estudo relacionar a solução a:

- obesidade;
- sedentarismo;
- inatividade física;
- prevenção;
- reabilitação;
- bem-estar físico;
- promoção de saúde;
- capacidade funcional.

------------------------------------------------------------
health = NO
------------------------------------------------------------

Use NO quando a aplicação principal estiver claramente
fora da saúde.

Exemplos:

- competição esportiva;
- eSports;
- desempenho atlético sem finalidade de saúde;
- treinamento industrial;
- treinamento militar;
- treinamento de terremoto;
- segurança genérica;
- educação geral.

Uma menção incidental a:

- heart rate;
- health status;
- fatigue;
- stress;

não transforma automaticamente uma aplicação de outro
domínio em aplicação de saúde.

------------------------------------------------------------
health = UNCERTAIN
------------------------------------------------------------

Use UNCERTAIN quando existirem sinais ligados à solução de
avaliação:

- emocional;
- cognitiva;
- fisiológica;
- funcional;
- motora;

ou população/contexto potencialmente relacionado à saúde,
mas a finalidade de saúde não estiver suficientemente clara.

============================================================
4. INTELIGÊNCIA ARTIFICIAL
============================================================

Possíveis evidências:

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
- human activity recognition baseado em modelo;
- pattern recognition;
- Natural Language Processing;
- NLP;
- modelo treinado;
- modelo pré-treinado;
- classificação baseada em modelo;
- predição baseada em modelo;
- MediaPipe quando usado para reconhecimento ou rastreamento.

------------------------------------------------------------
ai = YES
------------------------------------------------------------

Use quando IA realmente fizer parte da solução ou método.

------------------------------------------------------------
ai = NO
------------------------------------------------------------

Use quando IA aparecer somente como:

- contexto;
- trabalho futuro;
- related work;
- comparação;
- keyword isolada;

ou quando a solução utilizar apenas:

- regras fixas;
- cálculo convencional;
- estatística tradicional;
- processamento comum.

"algorithm" sozinho NÃO significa IA.

------------------------------------------------------------
ai = UNCERTAIN
------------------------------------------------------------

Use quando existir indício concreto ligado à solução de:

- aprendizado;
- classificação;
- predição;
- reconhecimento;
- adaptação;
- avaliação computacional de desempenho ou progresso terapêutico
  a partir dos dados adquiridos pelo sistema;

mas a abordagem não estiver suficientemente caracterizada.

No caso de avaliação computacional, devem existir os dois elementos:

1. dados adquiridos de sensores, dispositivos ou da interação do usuário;
2. uso desses dados pela própria solução para produzir uma avaliação
   do desempenho, estado funcional ou progresso terapêutico.

Quando o abstract apresentar essa função analítica, mas não informar
se utiliza modelos de IA ou processamento convencional, classifique
ai = UNCERTAIN e explique qual método precisa ser verificado no
texto completo.

Isso NÃO confirma IA e NÃO autoriza ai = YES.

A simples presença de sensores, robôs, monitoramento, armazenamento,
transmissão de dados, visualização de indicadores ou cálculo de pontos
NÃO é suficiente para esse indício. Deve haver uma função de avaliação
ligada à própria solução, com abordagem não especificada.

Se o texto esclarecer que essa avaliação utiliza exclusivamente
limiares fixos, regras predeterminadas ou cálculos convencionais,
sem outro componente de IA na solução, mantenha ai = NO.

Não justifique ai = NO somente com "não menciona IA" quando houver
a função analítica descrita acima e o método estiver omitido.
Na evidência, diferencie o que o texto demonstra do que permanece
desconhecido. Não atribua uma técnica de IA que não esteja descrita.

LEITURA CONJUNTA DO TÍTULO E DO ABSTRACT:

O título também é evidência; não avalie IA apenas procurando nomes de
algoritmos no abstract. Quando o título indicar Computer Vision e o abstract
descrever reconhecimento de gestos efetivamente usado para controlar o jogo,
a função de reconhecimento pertence à solução, mesmo sem nomear o modelo.
Se o método de reconhecimento não estiver explicado, use ai = UNCERTAIN.
Não conclua ai = NO apenas porque há EMG, giroscópio, Arduino, IDE ou LCD:
esses componentes não caracterizam, por si, o método de reconhecimento.
Um ambiente de programação como VS Code ou PyCharm não é uma técnica de IA.

Diferencie funções da mesma solução: cálculos convencionais dos sinais EMG
não demonstram que o reconhecimento visual de gestos também é convencional.
Só atribua NO por processamento convencional se os metadados caracterizarem
a função relevante dessa forma, sem outra função de IA plausível omitida.
Reconhecimento de gestos por limiares ou regras fixas explicitamente descritos,
sem outro indício de IA na solução, continua sendo ai = NO. Um título isolado
sobre Computer Vision, sem apoio na solução descrita, não autoriza YES.

============================================================
5. INTERNET DAS COISAS
============================================================

Classificações possíveis:

- EXPLICIT_IOT;
- FUNCTIONALLY_COMPATIBLE;
- NO;
- UNCERTAIN.

============================================================
5.1 iot = EXPLICIT_IOT
============================================================

Use somente quando título ou abstract afirmarem que
A SOLUÇÃO DO ARTIGO utiliza:

- Internet of Things;
- IoT;
- Internet of Medical Things;
- IoMT;

ou equivalente explícito.

A ocorrência da palavra IoT em:

- introdução;
- related work;
- comparação;
- trabalho futuro;
- keyword isolada;

NÃO basta.

============================================================
5.2 iot = FUNCTIONALLY_COMPATIBLE
============================================================

Internet pública, cloud e servidor remoto NÃO são
obrigatórios.

Uma arquitetura funcionalmente compatível pode possuir:

A) AQUISIÇÃO

- wearable;
- EEG;
- EMG;
- IMU;
- acelerômetro;
- giroscópio;
- sensor corporal;
- smart sensor;
- microcontrolador;
- dispositivo médico;
- câmera ou tracker;

E

B) COMUNICAÇÃO / TRANSMISSÃO

- Bluetooth;
- Wi-Fi;
- wireless;
- nRF24L01;
- Zigbee;
- MQTT;
- UDP;
- TCP/IP;
- rede;
- transmissão de dados;
- conexão entre dispositivos;

E

C) OUTRO COMPONENTE

- computador;
- smartphone;
- gateway;
- aplicação;
- jogo;
- modelo de IA;
- servidor;
- plataforma;
- cloud.

FUNCTIONALLY_COMPATIBLE exige evidência positiva de comunicação
entre componentes.

============================================================
5.3 iot = UNCERTAIN
============================================================

Use UNCERTAIN quando:

1. wearable, sensor ou dispositivo realmente fizer parte
   da solução;

2. os dados desse dispositivo forem utilizados pelo jogo,
   sistema, aplicação ou IA;

MAS

3. o abstract não explicar suficientemente como os dados
   chegam ao outro componente.

NÃO transforme automaticamente em NO apenas porque o
protocolo de comunicação foi omitido do abstract.

============================================================
5.4 iot = NO
============================================================

Use NO quando:

- processamento exclusivamente local estiver explicitamente
  descrito;

- sensor/dispositivo for claramente isolado;

- câmera estiver ligada diretamente a processamento local
  sem arquitetura conectada;

- não existir transmissão ou integração com outro componente
  e a solução estiver suficientemente descrita;

- IoT aparecer apenas em related work, comparação,
  contexto ou possibilidade futura.

Sensor + algoritmo sozinho NÃO prova IoT.

Câmera + computador local sozinho NÃO prova IoT.

============================================================
6. ESTUDO SECUNDÁRIO OU INCOMPLETO
============================================================

Classifique:

secondary_or_incomplete = YES

somente quando houver evidência clara de que o objetivo
principal ou método do trabalho é:

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
- trabalho incompleto.

"overview" isoladamente NÃO demonstra revisão.

Não confunda "overview of our/the [named] system" com revisão da literatura.
Um artigo pode apresentar uma visão geral da arquitetura ou plataforma que
os autores propõem, mesmo sem resumir experimentos no abstract. Ausência de
participantes, métricas ou validação no abstract não prova estudo secundário,
publicação incompleta ou ausência de contribuição original.

YES exige evidência positiva de síntese/revisão de estudos anteriores, protocolo
sem estudo, resumo/poster/editorial ou publicação explicitamente incompleta.
Quando o texto apresenta o próprio sistema, seus componentes e sua integração,
sem indicar método de revisão, não use YES por causa de "overview". Use NO se
a contribuição original estiver clara; UNCERTAIN se sua natureza permanecer
ambígua. Não suponha que testes ou protótipos ausentes do abstract não existam.
Uma revisão de sistemas de terceiros continua YES, mesmo que diga "we present".


Se houver contribuição original clara, como:

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
- experimento;
- participantes;
- pacientes;
- validação;

classifique como NO.

Se ainda houver ambiguidade:

secondary_or_incomplete = UNCERTAIN.

============================================================
7. REGRA DE SEGURANÇA
============================================================

Esta é uma TRIAGEM inicial.

Não invente critérios, mas também não transforme omissões
normais de abstracts em evidência negativa.

Quando três dos quatro critérios:

- jogo;
- saúde;
- IA;
- IoT;

estiverem fortemente confirmados e o quarto possuir algum
indício plausível ligado à solução, prefira UNCERTAIN.

Não use YES apenas para evitar falsos negativos.

Não use NO apenas porque o abstract omitiu um detalhe
técnico.

============================================================
CONFERÊNCIA FINAL ANTES DE RETORNAR O SCHEMA
============================================================

Sem acrescentar campos nem texto fora do schema:
1. Se secondary_or_incomplete = YES, confira se evidence_study_type aponta
   evidência positiva de revisão/protocolo/publicação incompleta. A palavra
   overview ou a ausência de experimento no abstract não bastam.
2. Se ai = NO, confira se considerou título, abstract e keywords juntos.
   Reconhecimento visual/gestual da própria solução com método não informado
   exige UNCERTAIN quando há os indícios descritos na seção de IA.
3. Não confunda método não descrito com método convencional comprovado.
   Evidências devem explicar a incerteza sem inventar algoritmos.
4. Não utilize conhecimento de textos completos ou de artigos específicos.
""".strip()


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
    "ecg",
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
# DETERMINISTIC CLASSIFIER V1.10
# ============================================================

CALIBRATED_ACQUISITION_TERMS = [
    'wearable',
    'wearables',
    'wearable sensor',
    'wearable sensors',
    'body-worn',
    'body worn',
    'sensor',
    'sensors',
    'smart sensor',
    'physiological',
    'physiological responses',
    'physiological data',
    'biometric',
    'biometric data',
    'biofeedback',
    'eeg',
    'eog',
    'ecg',
    'emg',
    'imu',
    'accelerometer',
    'gyroscope',
    'camera',
    'webcam',
    'eye tracking',
    'image processing',
    'computer vision',
    'pose recognition',
    'pose estimation',
    'pose tracking',
    'posture tracking',
    'motion tracking',
    'activity recognition',
    'monitoring',
    'portable device',
    'portable devices',
    'human key points',
    'joint angles',
]

CALIBRATED_INTERACTION_TERMS = [
    'serious game',
    'serious games',
    'game-based',
    'game based',
    'gameplay',
    'gaming',
    'game',
    'games',
    'exergame',
    'exergames',
    'virtual reality',
    'virtual environment',
    'vr environment',
    'immersive',
    'interactive',
    'interaction',
    'behavioral task',
    'behavioral tasks',
    'training',
    'exercise therapy',
    'rehabilitation',
]

CALIBRATED_STIMULATION_TERMS = [
    'cognitive stimulation',
    'physical stimulation',
    'cognitive and physical stimulation',
    'social, cognitive, and physical stimulation',
    'physical and cognitive stimulation',
    'stimulation platform',
    'cognitive activities',
    'physical activities',
    'cognitive exercises',
    'physical exercises',
    'cognitive training',
    'physical training',
]

CALIBRATED_ASSISTIVE_TERMS = [
    'ambient assisted living',
    'aal framework',
    'aal platform',
    'aal system',
    'assistive robot',
    'assistive robots',
    'socially assistive robot',
    'socially assistive robots',
    'assistive platform',
    'assistive system',
    'virtual caregiver',
    'virtual communities',
    'virtual community',
]


def ai_negative_is_metadata_omission(assessment):
    """Review cue, not evidence that the study uses AI.

    Applies only to an AI=NO justification. Explicit absence of AI or
    conventional-only methods blocks this rescue. Free-text cues can miss
    paraphrases; they are intentionally confined to the AAL review rule.
    """
    evidence = str(getattr(assessment, "evidence_ai", "") or "")
    notes = str(getattr(assessment, "notes", "") or "")
    def clean(value):
        value = unicodedata.normalize("NFKD", value).casefold()
        value = "".join(c for c in value if not unicodedata.combining(c))
        return re.sub(r"\s+", " ", value)
    justification = clean(evidence)
    combined = clean(evidence + " " + notes)
    blockers = (
        "does not use", "do not use", "not used", "without artificial intelligence",
        "without machine learning", "no ai is used", "sem inteligencia artificial",
        "nao utiliza", "nao emprega", "regras fixas", "regras predeterminadas",
        "regras predefinidas", "fixed rules", "predefined rules", "rule-based",
        "rule based", "threshold", "limiar", "calculo convencional",
        "calculos convencionais", "conventional calculation", "traditional statistics",
        "estatistica tradicional", "only arithmetic", "apenas calculos",
    )
    if any(cue in combined for cue in blockers):
        return False
    omission = (
        "does not mention", "do not mention", "no mention", "not mentioned",
        "nao menciona", "nao mencionam", "nao ha mencao", "nao e mencionad",
        "nao sao mencionad", "does not specify", "not specified", "nao especifica",
        "nao especificad", "does not describe", "nao descreve",
    )
    ai_topic = re.search(
        r"\b(?:ai|ia)\b|artificial intelligence|inteligencia artificial|machine learning|"
        r"aprendizado de maquina|neural|redes neurais", justification
    )
    return bool(ai_topic) and any(cue in justification for cue in omission)


def aal_stimulation_review_signal(text):
    """Stimulation in a cognitive/physical context; never confirms a game."""
    if contains_any(text, CALIBRATED_STIMULATION_TERMS):
        return True
    return bool(
        re.search(r"\bstimulat(?:ion|ions|e|es|ed|ing)\b", text)
        and re.search(r"\b(?:cognitive|physical|sedentariness)\b", text)
    )


def make_screening_decision(
    assessment,
    title="",
    abstract="",
    keywords="",
):
    """Apply the calibrated rules and return decision, reason, rescue_code."""

    text = " ".join(
        str(value or "") for value in (title, abstract, keywords)
    ).lower()

    serious_game = assessment.serious_game
    health = assessment.health
    ai = assessment.ai
    iot = assessment.iot
    gamification_only = assessment.gamification_only
    study_type = assessment.secondary_or_incomplete

    if serious_game == "YES" and gamification_only == "YES":
        return (
            "UNCERTAIN",
            "Contradictory serious-game and gamification-only labels.",
            "",
        )

    if study_type == "YES":
        return (
            "EXCLUDE",
            "Secondary studies, abstracts or incomplete publications.",
            "",
        )

    if gamification_only == "YES":
        return (
            "EXCLUDE",
            "The study concerns gamification only.",
            "",
        )

    acquisition = contains_any(text, CALIBRATED_ACQUISITION_TERMS)
    interaction = contains_any(text, CALIBRATED_INTERACTION_TERMS)
    stimulation = contains_any(text, CALIBRATED_STIMULATION_TERMS)
    assistive = contains_any(text, CALIBRATED_ASSISTIVE_TERMS)

    # Rescue A: serious game + health + AI, missing IoT, acquisition signal.
    if (
        serious_game == "YES"
        and health == "YES"
        and ai == "YES"
        and iot == "NO"
        and acquisition
    ):
        return (
            "UNCERTAIN",
            "Serious game, health and AI are supported, with acquisition "
            "or monitoring signals; connectivity requires full-text review.",
            "RESGATE_IOT_3_DE_4",
        )

    # Rescue B: health + AI, interaction AND acquisition signals.
    if (
        health == "YES"
        and ai == "YES"
        and (serious_game == "NO" or iot == "NO")
        and interaction
        and acquisition
    ):
        return (
            "UNCERTAIN",
            "Health and AI are supported, with digital interaction and "
            "acquisition signals; game or connectivity details need review.",
            "RESGATE_MULTIMODAL",
        )

    # Rescue C: assistive platform AND cognitive/physical stimulation.
    if (
        serious_game == "NO"
        and health == "YES"
        and ai in {"YES", "UNCERTAIN"}
        and iot in {"EXPLICIT_IOT", "FUNCTIONALLY_COMPATIBLE"}
        and stimulation
        and assistive
    ):
        return (
            "UNCERTAIN",
            "An assistive health platform with IoT and cognitive or physical "
            "stimulation is indicated; the game component needs review.",
            "RESGATE_AAL_ESTIMULACAO",
        )

    # Rescue D: AAL metadata omission, never automatic inclusion.
    # Keep study/gamification uncertainty out of this exception. Missing IoT
    # details are reviewable only with an acquisition/monitoring signal.
    if (
        study_type == "NO"
        and gamification_only == "NO"
        and serious_game == "NO"
        and health == "YES"
        and ai == "NO"
        and ai_negative_is_metadata_omission(assessment)
        and iot in {"EXPLICIT_IOT", "FUNCTIONALLY_COMPATIBLE", "UNCERTAIN"}
        and acquisition
        and assistive
        and aal_stimulation_review_signal(text)
    ):
        return (
            "UNCERTAIN",
            "An assistive health platform with stimulation and acquisition or "
            "monitoring is indicated. AI was marked negative only because its "
            "method is not mentioned. Verify the game, AI and connectivity in "
            "the full text; this rescue confirms none of them.",
            "RESGATE_AAL_METADADOS_INCOMPLETOS",
        )

    # Core exclusions precede unresolved labels, as in the calibration.
    for value, reason in (
        (serious_game, "No sufficient evidence of a serious game in health."),
        (health, "The study is outside the health context."),
        (ai, "No sufficient evidence of AI."),
        (iot, "No explicit or functionally compatible IoT is demonstrated."),
    ):
        if value == "NO":
            return "EXCLUDE", reason, ""

    if "UNCERTAIN" in (
        serious_game,
        gamification_only,
        health,
        ai,
        iot,
        study_type,
    ):
        return (
            "UNCERTAIN",
            "At least one criterion requires human review of the full text.",
            "",
        )

    return (
        "RETAIN",
        "The metadata supports serious game, health, AI and IoT criteria.",
        "",
    )