"""Phonetic Slurring and Text Conditioning Transforms.

Provides regex-based phonetic transforms (slurring sibilants, vowel elongation,
stutters, and hiccup insertions) for tabletop character afflictions and speech states.
"""

from __future__ import annotations

import re


def apply_slurred_speech(text: str) -> str:
    """Inject inebriated slurs, elongated vowels, and hiccups into text."""
    words = text.split()
    slurred_words: list[str] = []

    for i, word in enumerate(words):
        w = word
        # Slur sibilants
        w = re.sub(r"([sS])([tTcCkKpP])", r"\1hh\2", w)
        w = re.sub(r"([sS])\b", r"\1hh", w)
        w = re.sub(r"\bth", "f", w, flags=re.IGNORECASE)

        # Elongate vowels periodically
        if len(w) > 4 and any(c in "aeiouAEIOU" for c in w):
            w = re.sub(r"([oo|ee|aa|uu|ii])", r"\1\1", w, count=1)

        slurred_words.append(w)

        # Insert hiccups every 4-6 words
        if i > 0 and i % 5 == 0:
            slurred_words.append("*hic!*")

    if not any(h in slurred_words for h in ["*hic!*", "*burp*"]):
        slurred_words.insert(0, "*hic!*")

    return " ".join(slurred_words)


def slur_phonemes(text: str) -> str:
    """Alias for apply_slurred_speech to preserve backward compatibility."""
    return apply_slurred_speech(text)


def apply_text_transforms(text: str, filters: list[str]) -> str:
    """Apply text conditioning according to active affliction filters."""
    result = text
    filters_clean = [f.lower().strip() for f in filters]

    if "drunk" in filters_clean:
        result = apply_slurred_speech(result)

    if "underwater" in filters_clean:
        result = f"*blub* {result} *gurgle*"

    if "whisper" in filters_clean:
        result = f"...*whispers* {result.lower()}..."

    if "ethereal" in filters_clean or "ghostly" in filters_clean:
        result = f"~ {result} ~ ...{result.split()[-1]}... ~"

    return result
