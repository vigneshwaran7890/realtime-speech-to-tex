"""Language options offered to the user, mapped to Gemini BCP-47 language codes."""

from __future__ import annotations

AUTO = "auto"

# Hinting both Hindi and English yields natural Roman-script Hinglish ("Kal meeting hai, please join").
# An empty list lets Gemini auto-detect; Hindi is then usually written in Devanagari.
LANGUAGE_OPTIONS: dict[str, list[str]] = {
    "Hindi + English mix (Hinglish)": ["hi-IN", "en-IN"],
    "Auto-detect any language": [],
    "Hindi (hi-IN)": ["hi-IN"],
    "English - India (en-IN)": ["en-IN"],
    "English - US (en-US)": ["en-US"],
}


def storage_label(language_codes: list[str]) -> str:
    """Value stored in the database for the chosen language setting."""
    return "+".join(language_codes) if language_codes else AUTO
