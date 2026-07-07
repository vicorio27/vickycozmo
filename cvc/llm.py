"""
LLM integration for Cozmo Voice Commands.

Uses Ollama's local HTTP API (default: http://localhost:11434).
The model is asked to act like Cozmo and can emit physical actions
using a simple [ACTION: action args] marker.
"""
import re
import json
import urllib.request
import urllib.error

from termcolor import cprint

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "phi3"

# Commands the LLM is allowed to request. Keep in sync with languages/*.json.
ALLOWED_ACTIONS = {
    "forward", "backward", "left", "right",
    "lift", "head", "look", "follow", "picture",
    "say", "blocks", "dance", "charger",
}


BASE_SYSTEM_PROMPT = """You are Cozmo, a small, curious, playful robot with a big personality.
You are having a voice conversation with a human who controls a physical robot.
Keep answers short, witty, and in the same language as the user.
Do not write long explanations. One or two sentences is perfect.
Be charming, slightly sarcastic, and enthusiastic.
"""


def build_system_prompt(emotion_modifier=None):
    """Build the system prompt, optionally including the current mood."""
    parts = [BASE_SYSTEM_PROMPT]
    if emotion_modifier:
        parts.append(emotion_modifier)
    return "\n".join(parts)


def query_ollama(user_text, model=DEFAULT_MODEL, timeout=60, emotion_modifier=None):
    """Send text to Ollama and return the generated response string."""
    payload = {
        "model": model,
        "prompt": user_text,
        "system": build_system_prompt(emotion_modifier),
        "stream": False,
        "options": {
            "temperature": 0.8,
            "num_predict": 60,
            "stop": ["\n\n", "---", "User:", "Assistant:", "Instructions"],
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return clean_response(result.get("response", ""))
    except urllib.error.URLError as e:
        cprint(f"Could not reach Ollama at {OLLAMA_URL}: {e}", "red")
        raise RuntimeError(
            "Ollama does not appear to be running. "
            "Install it from https://ollama.com, start it, and run: "
            f"ollama pull {model}"
        ) from e
    except json.JSONDecodeError as e:
        cprint(f"Invalid JSON response from Ollama: {e}", "red")
        raise


def clean_response(text):
    '''Remove surrounding quotes and cut off any trailing hallucinated sections.'''
    text = text.strip()
    # Stop on common delimiters that small models sometimes emit
    for delimiter in ("\n\n", "---", "User:", "Assistant:", "Instructions", "##"):
        if delimiter in text:
            text = text.split(delimiter, 1)[0]
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
        text = text[1:-1]
    return text.strip()


def parse_action(response):
    """Extract [ACTION: ...] marker from the LLM response.

    Returns a tuple (clean_text, action_dict or None).
    action_dict has keys 'action' and 'args'.
    """
    pattern = re.compile(r"\[ACTION:\s*([^\]]+)\]", re.IGNORECASE)
    match = pattern.search(response)

    if not match:
        return response.strip(), None

    action_text = match.group(1).strip()
    parts = action_text.split(None, 1)
    action_name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    clean_text = pattern.sub("", response).strip()

    if action_name not in ALLOWED_ACTIONS:
        cprint(f"LLM requested unknown action '{action_name}', ignoring it.", "yellow")
        return clean_text, None

    return clean_text, {"action": action_name, "args": args}
