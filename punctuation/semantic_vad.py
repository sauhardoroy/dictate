"""Semantic Voice Activity & Thought-Completion Evaluator.

Analyzes partial/interim transcripts to distinguish between:
1. Mid-thought thinking pauses (ending in conjunctions, prepositions, articles, modal verbs, fillers)
2. Semantically complete thoughts (ending in terminal clauses, nouns, complete sentences)

Dynamically adapts the silence auto-stop threshold to prevent cutting users off mid-thought.
"""
import re

# Words that strongly indicate the speaker has paused to think and is NOT done
INCOMPLETE_TRAILING_WORDS = {
    # Conjunctions
    "and", "or", "but", "so", "because", "although", "though", "while", "if", "when",
    "that", "as", "since", "unless", "until", "whereas", "whether", "plus", "also",
    # Prepositions
    "to", "for", "in", "on", "at", "with", "about", "by", "from", "into", "through",
    "of", "towards", "toward", "over", "under", "between", "after", "before", "during",
    "without", "against", "among", "per", "via",
    # Articles & Determiners
    "the", "a", "an", "this", "that", "these", "those", "my", "your", "his", "her",
    "our", "their", "its", "some", "any", "every", "each", "both", "either", "neither",
    "such", "another", "which", "whose", "what",
    # Modals & Auxiliary Verbs (hanging sentence)
    "is", "are", "was", "were", "be", "been", "being",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
    "have", "has", "had", "do", "does", "did", "going", "trying", "wanting",
    # Common speech thinking fillers
    "um", "uh", "er", "ah", "like", "you", "know", "mean", "basically", "actually"
}

# Incomplete trailing bigram patterns (e.g. "going to", "want to", "kind of", "sort of")
INCOMPLETE_BIGRAMS = {
    ("going", "to"),
    ("want", "to"),
    ("wanted", "to"),
    ("need", "to"),
    ("needed", "to"),
    ("have", "to"),
    ("had", "to"),
    ("trying", "to"),
    ("supposed", "to"),
    ("used", "to"),
    ("able", "to"),
    ("kind", "of"),
    ("sort", "of"),
    ("type", "of"),
    ("out", "of"),
    ("because", "of"),
    ("such", "as"),
    ("as", "well"),
    ("in", "order"),
    ("you", "know"),
    ("i", "mean"),
    ("as", "to"),
    ("up", "to"),
    ("due", "to"),
}


def is_incomplete_thought(text: str) -> bool:
    """Returns True if the text ends mid-clause or in an obvious thinking pause."""
    if not text:
        return False

    cleaned = re.sub(r"[^\w\s]", " ", text.lower()).strip()
    tokens = cleaned.split()
    if not tokens:
        return False

    last_word = tokens[-1]

    # Check 1: Trailing single incomplete word
    if last_word in INCOMPLETE_TRAILING_WORDS:
        return True

    # Check 2: Trailing bigrams (e.g. "want to", "kind of")
    if len(tokens) >= 2:
        last_bigram = (tokens[-2], tokens[-1])
        if last_bigram in INCOMPLETE_BIGRAMS:
            return True

    # Check 3: Hanging comparative/superlative (e.g. "more", "less", "greater")
    if last_word in {"more", "less", "greater", "fewer", "better", "worse", "rather"}:
        return True

    return False


def get_adaptive_silence_duration(partial_transcript: str, base_silence_seconds: float = 1.2) -> float:
    """Calculates dynamic silence threshold based on grammatical completeness.

    - Complete sentence: Base silence (e.g. 1.2s)
    - Incomplete thought / thinking pause: Extended silence (e.g. 2.4s - 3.0s)
    """
    if not partial_transcript:
        return base_silence_seconds

    if is_incomplete_thought(partial_transcript):
        # Give user plenty of thinking room (2.5x base, min 2.5s)
        return max(2.5, base_silence_seconds * 2.2)

    return base_silence_seconds
