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
    "You are an expert dictation assistant. Your task is to clean up the following raw speech transcript. "
    "Remove filler words (um, uh, like, you know), fix grammatical stuttering, and ensure perfect punctuation. "
    "Maintain the exact original meaning and tone. DO NOT add conversational responses like 'Here is the text'. "
    "Output ONLY the cleaned text and nothing else. JUST give the clean text as your response and nothing else"
)


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

    if settings and settings.get("ai_polish", False):
        t = _llm_polish(t, settings)
    else:
        t = _light_polish(t)
        
    return t

def _light_polish(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r"[ \t]+([,.!?;:])", r"\1", text)
    t = t[0].upper() + t[1:]
    if t.endswith(","):
        t = t[:-1]
    if t and t[-1] not in ".!?\"'\u201d\u2019\n":
        t += "."
    return t

def _llm_polish(text: str, settings: dict) -> str:
    api_key = settings.get("ai_polish_api_key", "").strip()
    base_url = settings.get("ai_polish_base_url", "https://integrate.api.nvidia.com/v1").strip().rstrip("/")
    model = settings.get("ai_polish_model", "nvidia/nemotron-3-nano-30b-a3b").strip()

    # If no base_url or model, fallback to light polish
    if not base_url or not model:
        return _light_polish(text)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Dictate/2.0 (NVIDIA-AI)",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
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
                return _light_polish(text)

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
