"""Voice command processing for dictation.

Provides two tiers of voice commands:
1. Action commands: entire utterance is an edit action like 'delete that' (Ctrl+Z), 'select all' (Ctrl+A), etc.
2. Inline voice formatting: spoken punctuation and structural commands like 'new line', 'comma', 'period', etc.
"""
import re
from typing import Optional

# Action commands mapped to action identifiers
ACTION_COMMANDS = {
    # Undo / delete that
    "delete that": "undo",
    "delete that.": "undo",
    "scratch that": "undo",
    "scratch that.": "undo",
    "undo that": "undo",
    "undo that.": "undo",
    "undo": "undo",
    "undo.": "undo",

    # Redo
    "redo that": "redo",
    "redo that.": "redo",
    "redo": "redo",
    "redo.": "redo",

    # Select all
    "select all": "select_all",
    "select all.": "select_all",
    "select everything": "select_all",
    "select everything.": "select_all",

    # Copy / Cut / Paste
    "copy that": "copy",
    "copy that.": "copy",
    "copy this": "copy",
    "copy this.": "copy",
    "cut that": "cut",
    "cut that.": "cut",
    "paste that": "paste",
    "paste that.": "paste",
    "paste here": "paste",
    "paste here.": "paste",

    # Key presses
    "press enter": "enter",
    "press enter.": "enter",
    "hit enter": "enter",
    "hit enter.": "enter",
    "new line only": "enter",
    "press tab": "tab",
    "press backspace": "backspace",
}

# Action display labels for UI feedback
ACTION_DISPLAY_NAMES = {
    "undo": "Undone (Ctrl+Z)",
    "redo": "Redone (Ctrl+Y)",
    "select_all": "Selected All (Ctrl+A)",
    "copy": "Copied (Ctrl+C)",
    "cut": "Cut (Ctrl+X)",
    "paste": "Pasted (Ctrl+V)",
    "enter": "Enter",
    "tab": "Tab",
    "backspace": "Backspace",
}


def get_action_command(text: str) -> Optional[str]:
    """Check if the transcribed text is an action command.

    Returns the action name (e.g. 'undo', 'select_all') or None.
    """
    if not text:
        return None
    cleaned = text.strip().lower()
    return ACTION_COMMANDS.get(cleaned)


# ---------------------------------------------------------------------------
# Mid-Session Dynamic Recording Commands ("continue" / "let's start again")
# ---------------------------------------------------------------------------
RESTART_COMMANDS = {
    "let's start again",
    "lets start again",
    "start over",
    "scratch that start again",
    "scratch that, start again",
}

CONTINUE_COMMANDS = {
    "continue",
    "keep going",
    "let me continue",
}


def detect_mid_session_command(segment_text: str) -> Optional[str]:
    """Detect if an isolated speech segment matches a mid-session recording control command.

    Returns:
        'restart' for discard-and-restart commands
        'continue' for silence timer extension commands
        None if not an exact match on an isolated command phrase.

    Enforces strict whole-segment isolation: only triggers if the segment contains
    ONLY the command phrase. Embedded or mid-sentence occurrences return None.
    """
    if not segment_text:
        return None
    cleaned = segment_text.strip().lower()
    cleaned = re.sub(r"^[^\w\s']+|[^\w\s']+$", "", cleaned).strip()

    if cleaned in RESTART_COMMANDS:
        return "restart"
    if cleaned in CONTINUE_COMMANDS:
        return "continue"
    return None


def strip_continue_command(text: str) -> str:
    """Remove trailing or standalone 'continue' command phrases from transcribed text."""
    if not text:
        return ""
    t = text.strip()
    for cmd in CONTINUE_COMMANDS:
        pattern = rf"(?i)(?:^|\s+){re.escape(cmd)}[.!?]?\s*$"
        t = re.sub(pattern, "", t).strip()
    return t


# Spoken punctuation and structural substitutions
PUNCTUATION_PHRASES = [
    # Paragraphs & lines
    (r"\b(?:new|next)\s+paragraph\b", "\n\n"),
    (r"\b(?:new|next)\s+line\b", "\n"),
    (r"\bline\s+break\b", "\n"),
    (r"\btab\s+key\b", "\t"),

    # Internet / domains (e.g. "example dot com" -> "example.com")
    (r"\bdot\s+(com|org|net|io|edu|gov|co|ai|app|dev|in|uk|me|info)\b", r".\1"),

    # Terminal punctuation (only when not preceded by existing punctuation)
    (r"(?<![\.\!\?])\s*\b(?:period|full\s+stop)\b", "."),
    (r"(?<![\.\!\?])\s*\bquestion\s+mark\b", "?"),
    (r"(?<![\.\!\?])\s*\bexclamation\s+(?:mark|point)\b", "!"),

    # Pauses & separators
    (r"(?<![,;:])\s*\bcomma\b", ","),
    (r"(?<![,;:])\s*\bsemicolon|semi\s+colon\b", ";"),
    (r"(?<![,;:])\s*\bcolon\b", ":"),
    (r"\bellipsis|dot\s+dot\s+dot\b", "..."),
    (r"\bem\s+dash|long\s+dash\b", " — "),
    (r"\b(?:hyphen|dash)\b", "-"),
    (r"\bunderscore\b", "_"),

    # Quotes & Brackets
    (r"\bopen\s+(?:double\s+)?quote(?:s)?\b", ' "'),
    (r"\bclose\s+(?:double\s+)?quote(?:s)?\b", '" '),
    (r"\bopen\s+single\s+quote\b", " '"),
    (r"\bclose\s+single\s+quote\b", "' "),
    (r"\bopen\s+(?:parenthesis|paren|round\s+bracket)\b", " ("),
    (r"\bclose\s+(?:parenthesis|paren|round\s+bracket)\b", ") "),
    (r"\bopen\s+(?:bracket|square\s+bracket)\b", " ["),
    (r"\bclose\s+(?:bracket|square\s+bracket)\b", "] "),
    (r"\bopen\s+(?:brace|curly\s+bracket)\b", " {"),
    (r"\bclose\s+(?:brace|curly\s+bracket)\b", "} "),

    # Symbols & math
    (r"\bat\s+(?:sign|symbol)\b", "@"),
    (r"\bhashtag|hash\s+sign|number\s+sign|pound\s+sign\b", "#"),
    (r"\bdollar\s+sign\b", "$"),
    (r"\bpercent\s+sign\b", "%"),
    (r"\bampersand|and\s+sign\b", "&"),
    (r"\basterisk|star\s+symbol|star\s+sign\b", "*"),
    (r"\bplus\s+sign\b", "+"),
    (r"\bequals?\s+sign\b", "="),
    (r"\bforward\s+slash\b", "/"),
    (r"\bback\s*slash\b", "\\\\"),
]


def apply_voice_formatting(text: str) -> str:
    """Replace spoken punctuation phrases with actual symbols and fix casing/spacing."""
    if not text:
        return ""

    result = text

    # Pre-clean spacing before existing punctuation marks
    result = re.sub(r"[ \t]+([,.:;?!%])", r"\1", result)

    # Apply phrase replacements (case-insensitive)
    for pattern, replacement in PUNCTUATION_PHRASES:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # 1. Clean up spacing around symbols ($50, #hashtag, john@example.com)
    result = re.sub(r"\$\s+(\d)", r"$\1", result)
    result = re.sub(r"#\s+(\w)", r"#\1", result)
    result = re.sub(r"(\w)\s*@\s*(\w)", r"\1@\2", result)
    result = re.sub(r"@(\w+)\s*\.\s*([a-zA-Z]{2,})", r"@\1.\2", result)

    # 2. Hyphen between words (e.g. "semi - colon" -> "semi-colon", "well - known" -> "well-known")
    result = re.sub(r"(\w)\s*-\s*(\w)", r"\1-\2", result)

    # 3. Clean up space before punctuation marks: "hello , world ." -> "hello, world."
    result = re.sub(r"[ \t]+([,.:;?!%])", r"\1", result)

    # 4. Collapse duplicate punctuation
    result = re.sub(r"[,;:]+\s*([.!?])", r"\1", result)
    result = re.sub(r"([,.:;?!])\s*[,]+", r"\1", result)
    result = re.sub(r"([.!?])\s*\1+", r"\1", result)

    # 5. Ensure single space after punctuation (for comma, colon, semicolon, and sentence-ending punctuation)
    result = re.sub(r"([,:;?!])([^\s\n\"'\)\]\}0-9])", r"\1 \2", result)
    # For period: ensure space after period when followed by uppercase letter or space
    result = re.sub(r"(\.)([A-Z])", r"\1 \2", result)

    # 6. Clean up spaces around brackets and quotes
    result = re.sub(r"([(\[{])\s+", r"\1", result)
    result = re.sub(r"\s+([)\]}])", r"\1", result)
    result = re.sub(r'("\s*)([^"]+?)(\s*")', lambda m: f'"{m.group(2).strip()}"', result)

    # 7. Clean up spaces around newlines
    result = re.sub(r"[ \t]*\n[ \t]*", "\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result)

    # 8. Capitalize first letter of each sentence / line
    def capitalize_match(match):
        prefix = match.group(1)
        char = match.group(2)
        return prefix + char.upper()

    # Capitalize start of string
    result = re.sub(r"^(\s*)([a-z])", capitalize_match, result)
    # Capitalize after terminal punctuation (. ! ?) followed by whitespace
    result = re.sub(r"([.!?]\s+)([a-z])", capitalize_match, result)
    # Capitalize after newlines
    result = re.sub(r"(\n+)([a-z])", capitalize_match, result)

    return result.strip()
