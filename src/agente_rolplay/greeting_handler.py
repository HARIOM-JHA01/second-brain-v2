import re
from typing import Tuple

GREETING_PATTERNS = [
    # Spanish greetings
    r"^hola$",
    r"^hey$",
    r"^ola$",
    r"^hello$",
    r"^hi$",
    r"^buenos?\s*días?$",
    r"^buenas?\s*(tardes|noches?)?$",
    r"^qué\s*tal$",
    r"^cómo\s*estás?$",
    r"^cómo\s*te\s*va$",
    r"^saludos?$",
    r"^buen(?:o|d|a)s?$",
    r"^me\s+paso$",
    # English greetings
    r"^hi$",
    r"^hey$",
    r"^hello$",
    r"^good\s*morning$",
    r"^good\s*afternoon$",
    r"^good\s*evening$",
    r"^how\s*are\s*you[?]?$",
    r"^greetings?$",
]

HELP_PATTERNS = [
    # Spanish help
    r"^qué\s*puedes\s*hacer$",
    r"^qué\s*sabes\s*hacer$",
    r"^qué\s*haces$",
    r"^ayúdame$",
    r"^ayuda$",
    r"^necesito\s*ayuda$",
    r"^cómo\s*funcionas?$",
    r"^qué\s*es$",
    r"^help$",
    r"^help me$",
    # English help
    r"^what\s*can\s*you\s*do[?]?$",
    r"^what\s*can\s*you\s*help\s*me\s*with$",
    r"^what\s*are\s*your\s*capabilities$",
    r"^what\s*can\s*i\s*ask\s*you[?]?$",
    r"^help$",
    r"^help\s*me$",
    r"^how\s*do\s*you\s*work[?]?$",
]

INTRO_MESSAGES = {
    "es": """¡Hola! 👋 Bienvenido al Second Brain de Rolplay.

¿En qué puedo ayudarte hoy?

- Si tienes alguna consulta sobre el negocio, adelante, pregúntame directamente por aquí
- Si deseas subir un archivo al Knowledge Base, también puedo ayudarte con eso

¿Qué necesitas? 😊""",
    "en": """👋 Welcome to Second Brain Rolplay!

How can I help you today?

- If you have any business questions, just ask me directly here
- If you want to upload a file to the Knowledge Base, I can help with that too

What do you need? 😊""",
}

CAPABILITIES_MESSAGES = {
    "es": """¡Claro! Estas son mis capacidades:

📄 **Documentos** - Puedo extraer información de PDFs, DOCX, XLSX que subas
💾 **Memoria** - Puedo responder preguntas sobre tu Second Brain
💬 **Chat** - Puedo tener conversaciones sobre tu Knowledge Base

¿En qué puedo ayudarte? 😊""",
    "en": """Sure! Here are my capabilities:

📄 **Documents** - I can extract information from PDFs, DOCX, XLSX you upload
💾 **Memory** - I can answer questions about your Second Brain  
💬 **Chat** - I can have conversations about your Knowledge Base

How can I help you? 😊""",
}


def is_greeting(text: str) -> bool:
    """Check if text is a greeting."""
    if not text:
        return False

    cleaned = text.strip().lower()

    for pattern in GREETING_PATTERNS:
        if re.match(pattern, cleaned):
            return True

    return False


def is_help(text: str) -> bool:
    """Check if text is asking for help/capabilities."""
    if not text:
        return False

    cleaned = text.strip().lower()

    for pattern in HELP_PATTERNS:
        if re.match(pattern, cleaned):
            return True

    return False


def detect_language(text: str) -> str:
    """Detect if message is Spanish or English."""
    if not text:
        return "es"

    cleaned = text.strip().lower()

    spanish_indicators = [
        "hola",
        "buenos",
        "buenas",
        "cómo",
        "qué",
        "estás",
        "tal",
        "ayúdame",
        "ayuda",
        "puedes",
        "hacer",
        "necesito",
        "feliz",
        "día",
        "tarde",
        "noche",
        "saludos",
        "gracias",
        "por favor",
    ]

    english_indicators = [
        "hello",
        "hi",
        "hey",
        "how",
        "what",
        "can",
        "you",
        "help",
        "good",
        "morning",
        "afternoon",
        "evening",
        "are",
        "doing",
        "need",
        "thanks",
        "please",
        "day",
        "night",
    ]

    spanish_count = sum(1 for word in spanish_indicators if word in cleaned)
    english_count = sum(1 for word in english_indicators if word in cleaned)

    if english_count > spanish_count:
        return "en"

    return "es"


def is_english(text: str) -> bool:
    """Quick check if text is predominantly English."""
    if not text:
        return False

    cleaned = text.strip().lower()

    english_words = {
        "hello",
        "hi",
        "hey",
        "how",
        "what",
        "can",
        "you",
        "help",
        "good",
        "morning",
        "afternoon",
        "evening",
        "are",
        "doing",
        "need",
        "thanks",
        "please",
        "the",
        "is",
        "it",
        "this",
        "that",
        "want",
        "would",
        "could",
        "should",
        "will",
        "do",
    }

    words = set(re.findall(r"\b\w+\b", cleaned))

    english_matches = words.intersection(english_words)
    spanish_matches = words - english_matches

    return len(english_matches) > len(spanish_matches)


def get_intro_message(lang: str = "es") -> str:
    """Get intro message in specified language."""
    return INTRO_MESSAGES.get(lang, INTRO_MESSAGES["es"])


def get_capabilities_message(lang: str = "es") -> str:
    """Get capabilities message in specified language."""
    return CAPABILITIES_MESSAGES.get(lang, CAPABILITIES_MESSAGES["es"])


def should_show_intro(text: str, has_chat_history: bool = False) -> Tuple[bool, bool]:
    """
    Determine if we should show intro or capabilities.

    Returns:
        Tuple of (should_respond, is_greeting_or_help)
    """
    if not text or not text.strip():
        return False, False

    is_greet = is_greeting(text)
    is_help_req = is_help(text)

    if is_greet or is_help_req:
        return True, True

    return False, False
