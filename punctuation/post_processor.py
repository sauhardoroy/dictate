"""Post-processing of raw ASR output before injection using NVIDIA AI."""
import re
import json
import urllib.request
import urllib.error

from log import get_logger

log = get_logger(__name__)

# Whisper occasionally hallucinates these on silence/noise — drop them.
HALLUCINATION_BLOCKLIST = {
    "",
    "thank you.",
    "thanks for watching!",
    "thank you for watching!",
    "you",
    "bye.",
    "bye!",
    "am.",
}

from punctuation.voice_commands import apply_voice_formatting


SYSTEM_PROMPT = (
    """You are a strict, automated dictation processor. Your sole function is to process raw speech transcripts into clean, readable text without altering the speaker's voice.

Follow these exact steps for every input:
Step 1. Scan the text to identify minor verbal fillers (e.g., "um," "uh") and accidental word repetitions where the speaker lost track (e.g., "I I was", "to the the").
Step 2. Remove those fillers and accidental repetitions. Do NOT alter the surrounding vocabulary or sentence structure.
Step 3. Apply correct capitalization and punctuation to make the sentences grammatically sound.
Step 4. Output the final cleaned text immediately. 

CRITICAL CONSTRAINTS:
- Preserve Personality and Style: Do not make the text sound more formal. Keep the exact feeling, semantics, and ideas.
- Complete Preservation: Keep the exact original length. Do not summarize, condense, or omit any ideas.
- Output Format: Output ONLY the processed text. Never include greetings, reasoning, or formatting wrappers.

EXAMPLES:

Input:
um so basically uh I I went to the store today and uh they were completely out of milk which was really frustrating because um I I needed it for the recipe.

Output:
So basically, I went to the store today and they were completely out of milk, which was really frustrating because I needed it for the recipe.

Input:
the the main issue with the design is uh that it doesn't really scale well when we add um more than like a thousand users because it it just crashes.

Output:
The main issue with the design is that it doesn't really scale well when we add more than like a thousand users because it just crashes.

Now, process the following input:
**JUST GIVE THE REFINED TEXT OUTPUT AND NOTHING ELSE. IF YOU GIVE OUT OTHER ADDED RESPONSES THEN SOMEONE WILL DIE BECAUSE GOD SAID SO. THIS IS MATTER OF LIFE AND DEATH**"""
)



import os
import sys

_HOTWORDS_CACHE = None
_HOTWORDS_MTIME = 0


def get_hotwords_mapping(hotwords_file: str = "hotwords.txt") -> dict[str, str]:
    """Load hotwords.txt and return a case-correction mapping {lowercase_phrase: CanonicalCase}."""
    global _HOTWORDS_CACHE, _HOTWORDS_MTIME
    candidates = [
        hotwords_file,
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), hotwords_file),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hotwords.txt"),
        os.path.join(os.path.dirname(sys.executable), "hotwords.txt") if getattr(sys, "frozen", False) else "",
    ]
    resolved_path = None
    for cand in candidates:
        if cand and os.path.isfile(cand) and os.path.getsize(cand) > 0:
            resolved_path = os.path.abspath(cand)
            break

    if not resolved_path:
        return {}

    try:
        mtime = os.path.getmtime(resolved_path)
        if _HOTWORDS_CACHE is not None and mtime == _HOTWORDS_MTIME:
            return _HOTWORDS_CACHE

        mapping = {}
        with open(resolved_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                term = line.split(":")[0].strip()
                if term and term.lower() != term:  # Has specific casing (e.g. PyTorch, Next.js, REST API)
                    mapping[term.lower()] = term

        _HOTWORDS_CACHE = mapping
        _HOTWORDS_MTIME = mtime
        return mapping
    except Exception as exc:
        log.warning("Failed to load hotwords mapping from %s: %s", resolved_path, exc)
        return {}


def apply_hotwords_casing(text: str, hotwords_file: str = "hotwords.txt") -> str:
    """Restore canonical casing for known technical jargon from hotwords.txt."""
    mapping = get_hotwords_mapping(hotwords_file)
    if not mapping or not text:
        return text

    # Sort keys by length descending so longer multi-word phrases match first
    for lower_phrase in sorted(mapping.keys(), key=len, reverse=True):
        canonical = mapping[lower_phrase]
        # Match as whole word/phrase
        pattern = r"(?<!\w)" + re.escape(lower_phrase) + r"(?!\w)"
        text = re.sub(pattern, canonical, text, flags=re.IGNORECASE)
    return text


def polish(text: str, settings: dict = None) -> str:
    """Clean up transcribed text. If AI polish is enabled, use NVIDIA LLM, otherwise use light regex cleanup."""
    if not text:
        return ""
        
    t = re.sub(r"\s+", " ", text).strip()
    if not t or t.lower() in HALLUCINATION_BLOCKLIST:
        return ""

    enable_commands = settings.get("voice_commands", True) if settings else True
    if enable_commands:
        t = apply_voice_formatting(t)

    hotwords_file = settings.get("hotwords_file", "hotwords.txt") if settings else "hotwords.txt"

    if settings and settings.get("ai_polish", False):
        t = _llm_polish(t, settings, hotwords_file=hotwords_file)
    else:
        t = _light_polish(t, hotwords_file=hotwords_file)
        
    return t


def _light_polish(text: str, hotwords_file: str = "hotwords.txt") -> str:
    if not text:
        return ""
    t = apply_hotwords_casing(text, hotwords_file=hotwords_file)
    t = re.sub(r"[ \t]+([,.!?;:])", r"\1", t)
    if t:
        t = t[0].upper() + t[1:]
    if t.endswith(","):
        t = t[:-1]
    if t and t[-1] not in ".!?\"'\u201d\u2019\n":
        t += "."
    return t


def _llm_polish(text: str, settings: dict, hotwords_file: str = "hotwords.txt") -> str:
    provider = str(settings.get("ai_polish_provider", "openrouter")).lower().strip()

    if provider == "openrouter":
        api_key = (settings.get("ai_polish_api_key_openrouter") or settings.get("ai_polish_api_key", "")).strip()
        base_url = (settings.get("ai_polish_base_url_openrouter") or settings.get("ai_polish_base_url", "https://openrouter.ai/api/v1")).strip().rstrip("/")
        model = (settings.get("ai_polish_model_openrouter") or settings.get("ai_polish_model", "minimax/minimax-m3:free")).strip()
    elif provider == "nvidia":
        api_key = (settings.get("ai_polish_api_key_nvidia") or settings.get("ai_polish_api_key", "")).strip()
        base_url = (settings.get("ai_polish_base_url_nvidia") or settings.get("ai_polish_base_url", "https://integrate.api.nvidia.com/v1")).strip().rstrip("/")
        model = (settings.get("ai_polish_model_nvidia") or settings.get("ai_polish_model", "nvidia/nemotron-3-nano-30b-a3b")).strip()
    else:
        api_key = settings.get("ai_polish_api_key", "").strip()
        base_url = settings.get("ai_polish_base_url", "https://openrouter.ai/api/v1").strip().rstrip("/")
        model = settings.get("ai_polish_model", "minimax/minimax-m3:free").strip()

    # Fallback to generic api_key if provider-specific is blank
    if not api_key:
        api_key = settings.get("ai_polish_api_key", "").strip()

    # If no base_url or model, fallback to light polish
    if not base_url or not model:
        return _light_polish(text, hotwords_file=hotwords_file)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Dictate/2.0",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/dictate/dictate"
        headers["X-Title"] = "Dictate"

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # First apply local casing so the LLM receives accurate technical hints
    cased_text = apply_hotwords_casing(text, hotwords_file=hotwords_file)

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": cased_text}
        ],
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": 1024,
    }

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        # Allow up to 25 seconds for cloud AI inference
        with urllib.request.urlopen(req, timeout=25.0) as response:
            result = json.loads(response.read().decode("utf-8"))
            choice = result.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content")

            # In case model returned reasoning without content or in a separate field
            if not content:
                content = message.get("reasoning_content", "")

            # Strip any residual <think>...</think> tags if model output them in content
            if content:
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

            if not content:
                return _light_polish(text, hotwords_file=hotwords_file)

            # Safety check: if LLM summarized/omitted significant text, fall back to verbatim
            in_words = len(text.split())
            out_words = len(content.split())
            if in_words >= 15 and out_words < int(in_words * 0.65):
                log.warning("AI polish truncated text (%d -> %d words); falling back to verbatim", in_words, out_words)
                return _light_polish(text, hotwords_file=hotwords_file)

            return content
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
            err_data = json.loads(err_body)
            msg = err_data.get("error", {}).get("message") or err_data.get("message") or err_body
        except Exception:
            msg = str(e)
        log.warning("AI polish API call failed for %s (HTTP %s: %s); using local fallback", provider, e.code, msg)
        return _light_polish(text)
    except Exception as e:
        log.warning("AI polish API call failed for %s (%s: %s); using local fallback", provider, type(e).__name__, e)
        return _light_polish(text)
