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
    "You are an expert dictation assistant. Your task is to clean up the following speech transcript verbatim. "
    "Remove minor verbal filler words (um, uh) and fix punctuation and casing. "
    "CRITICAL REQUIREMENT: Do NOT summarize. Do NOT condense or omit any sentences or ideas. "
    "Preserve the entire full-length transcript word-for-word. "
    "DO NOT add conversational filler like 'Here is the text'. Output ONLY the cleaned transcript."
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
    api_key = settings.get("ai_polish_api_key", "").strip()
    base_url = settings.get("ai_polish_base_url", "https://integrate.api.nvidia.com/v1").strip().rstrip("/")
    model = settings.get("ai_polish_model", "nvidia/nemotron-3-nano-30b-a3b").strip()

    # If no base_url or model, fallback to light polish
    if not base_url or not model:
        return _light_polish(text, hotwords_file=hotwords_file)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Dictate/2.0 (NVIDIA-AI)",
    }
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
        # Allow up to 25 seconds for cloud NVIDIA AI inference
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
                log.warning("NVIDIA AI polish truncated text (%d -> %d words); falling back to verbatim", in_words, out_words)
                return _light_polish(text, hotwords_file=hotwords_file)

            return content
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
            err_data = json.loads(err_body)
            msg = err_data.get("error", {}).get("message") or err_data.get("message") or err_body
        except Exception:
            msg = str(e)
        log.warning("NVIDIA AI polish API call failed (HTTP %s: %s); using local fallback", e.code, msg)
        return _light_polish(text)
    except Exception as e:
        log.warning("NVIDIA AI polish API call failed (%s: %s); using local fallback", type(e).__name__, e)
        return _light_polish(text)
