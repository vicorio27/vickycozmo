"""
Configuration management for CvC.

Reads/writes configuration from ~/.config/cvc/config.json.
Provides defaults and allows CLI flags to override.
"""
import os
import json
import sys


DEFAULT_CONFIG = {
    "backend": "anki",
    "llm_enabled": False,
    "llm_model": "phi3",
    "llm_url": "http://localhost:11434",
    "offline_stt": False,
    "pet_mode": False,
    "autonomous": False,
    "web_editor": False,
    "web_editor_port": 5000,
    "web_control": False,
    "web_control_port": 8080,
    "language": None,
    "log_level": "INFO",
    "voice_activation": ["cozmo", "robot"],
    "emotion_default": "curious",
    "agent_interval": 15,
    "pet_interval": 10,
    "camera_quality": 70,
    "max_tokens": 60,
    "temperature": 0.8,
}


def get_config_dir():
    """Return the config directory path."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(base, "cvc")


def get_config_path():
    """Return the config file path."""
    return os.path.join(get_config_dir(), "config.json")


def load_config(config_path=None):
    """Load configuration from file, merging with defaults."""
    config = dict(DEFAULT_CONFIG)
    path = config_path or get_config_path()

    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            config.update(user_config)
        except (json.JSONDecodeError, IOError) as e:
            print("Warning: could not load config from {}: {}".format(path, e))

    return config


def save_config(config, config_path=None):
    """Save configuration to file."""
    path = config_path or get_config_path()
    config_dir = os.path.dirname(path)

    if not os.path.isdir(config_dir):
        os.makedirs(config_dir, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    return path


def init_config_interactive():
    """Generate a config file interactively."""
    print("CvC Configuration Setup")
    print("=" * 40)
    print()

    config = dict(DEFAULT_CONFIG)

    # Backend
    print("Robot connection backend:")
    print("  1. Anki SDK (requires mobile app)")
    print("  2. pycozmo (direct WiFi, no app)")
    choice = input("Choose [1]: ").strip()
    config["backend"] = "pycozmo" if choice == "2" else "anki"

    # LLM
    print()
    use_llm = input("Enable LLM conversation? (y/N): ").strip().lower()
    config["llm_enabled"] = use_llm == "y"
    if config["llm_enabled"]:
        model = input("LLM model [phi3]: ").strip()
        config["llm_model"] = model or "phi3"

    # Offline STT
    print()
    use_offline = input("Enable offline speech recognition? (y/N): ").strip().lower()
    config["offline_stt"] = use_offline == "y"

    # Autonomous agent
    print()
    use_autonomous = input("Enable autonomous agent? (y/N): ").strip().lower()
    config["autonomous"] = use_autonomous == "y"

    # Web control
    print()
    use_web = input("Enable web control panel? (y/N): ").strip().lower()
    config["web_control"] = use_web == "y"
    if config["web_control"]:
        port = input("Web control port [8080]: ").strip()
        config["web_control_port"] = int(port) if port else 8080

    # Log level
    print()
    print("Log level: DEBUG, INFO, WARNING, ERROR")
    level = input("Log level [INFO]: ").strip().upper()
    config["log_level"] = level if level in ("DEBUG", "INFO", "WARNING", "ERROR") else "INFO"

    # Save
    path = save_config(config)
    print()
    print("Config saved to: {}".format(path))
    print("You can edit it manually anytime.")
    return config


def get_status():
    """Check system health and return status dict."""
    status = {}

    # Check Ollama
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        status["ollama"] = "running"
    except Exception:
        status["ollama"] = "not running"

    # Check Vosk model
    model_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "models", "vosk", "vosk-model-small-en-us-0.15"
    )
    status["vosk_model"] = "found" if os.path.isdir(model_path) else "not found"

    # Check pycozmo
    try:
        import pycozmo
        status["pycozmo"] = "installed"
    except ImportError:
        status["pycozmo"] = "not installed"

    # Check audio
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        pa.terminate()
        status["audio"] = "available"
    except Exception:
        status["audio"] = "unavailable"

    return status
