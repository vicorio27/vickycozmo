# Agent Notes for Cozmo Voice Commands (CvC)

## Project shape
- Single Python package `cvc/` with setuptools-based install.
- Console entry point: `cvc` → `cvc.cozmo_voice_commands:main`.
- Standalone development run: `python cvc.py` from repo root (imports the package, so `cvc/` must be on `PYTHONPATH` or installed).
- No tests, no CI, no lint/typecheck config, no `pyproject.toml`.

## Python version
- Target **Python 3.6**. The Cozmo SDK is deprecated and newer Python releases break compatibility.
- Recommended: `conda create -n cvc python=3.6` then `conda activate cvc`.

## Install / run
```bash
# Install from source in editable mode for development
pip install -e .

# Run after install
cvc

# Or run without installing
python cvc.py
```

## Runtime dependencies
Declared in `setup.py`:
- `termcolor`
- `cozmo[camera]`
- `SpeechRecognition`
- `PyAudio`
- `Pynput`
- `vosk`

System requirement: **portaudio** must be installed.
- macOS: `brew install portaudio`
- Linux: `sudo apt-get install flac portaudio19-dev python-all-dev python3-all-dev`
- Windows: git (for pip install from repo); PyAudio wheel may be needed on newer Python.

Offline STT requires the Vosk English model at `cvc/models/vosk/vosk-model-small-en-us-0.15/`.

## Adding commands or languages
1. Duplicate/edit a file in `cvc/languages/*.json`.
2. Set a unique `id` for language ordering.
3. Add a command entry with `"action"` (method name), `"words"` (recognized words), `"usage"`.
4. Implement the matching method in `cvc/voice_commands.py` on the `VoiceCommands` class.
5. Language files are auto-discovered at startup and sorted by `id`.

## Key files
- `cvc/cozmo_voice_commands.py` — main program loop, speech recognition, command parsing.
- `cvc/voice_commands.py` — robot action implementations.
- `cvc/backends/base.py` — abstract robot interface (the abstraction layer).
- `cvc/backends/anki_backend.py` — implementation using the official Anki SDK (requires mobile app).
- `cvc/backends/pycozmo_backend.py` — implementation using pycozmo (direct WiFi, no mobile app).
- `cvc/emotions.py` — mood tracking and expression.
- `cvc/llm.py` — Ollama LLM integration.
- `cvc/stt_offline.py` — Vosk offline speech recognition.
- `cvc/pet_mode.py` — autonomous pet behavior thread.
- `cvc/web_editor.py` — Flask web editor for languages.
- `cvc/languages/*.json` — localized commands and prompts.
- `setup.py` — version (0.7.0), dependencies, entry point.
- `cvc.py` — standalone launcher used during development.

## Versioning
- Version is hard-coded in `setup.py` and fetched at runtime via `pkg_resources.require("cvc")[0].version`.
- `cvc` must be installed/editable for the version lookup to work; running `cvc.py` without installing will fail on that line.

## Build artifacts
- Generated: `build/`, `dist/`, `cvc.egg-info/`.
- These are partially or fully ignored in `.gitignore`; only commit source changes.

## Runtime notes
- Requires a Cozmo robot + app/SDK connection. If `cozmo.run_program` exits with `SystemExit`, the code falls back to a keyboard-only test mode (`run(None)`) that prints command usages instead of moving the robot.
- Activation words: say "Cozmo" or "Robot" (plus variants listed in `commands_activate`) before commands.
- Separate multiple commands with the language-specific separator, e.g. English "THEN".

## Backends (robot connection)
The project supports two ways to connect to Cozmo:

### Anki SDK backend (default)
- Requires the official Cozmo mobile app running on a phone/tablet.
- The app acts as a bridge: robot ↔ app ↔ SDK on PC.
- Full feature support (behaviors, face detection, charger, camera).

### pycozmo backend (optional)
- Enable with `--use-pycozmo`.
- Connects directly to Cozmo over WiFi — no mobile app needed.
- Install: `pip install pycozmo`
- Windows: requires [Npcap](https://npcap.com) for packet capture.
- Linux: requires `sudo` or packet capture capabilities.
- Limitations: no behaviors (LookAroundInPlace, FindFaces, etc.), limited face detection, no charger detection.

## LLM conversation mode (optional)
- Enable with `--llm`. Requires a local Ollama server running on `localhost:11434`.
- Default model is `phi3`; override with `--llm-model=MODEL_NAME`.
- Download a model first: `ollama pull phi3`.
- When LLM mode is on, after any recognized physical command the speech text is also sent to the LLM and Cozmo speaks the reply. Physical actions are still handled by the existing voice-command parser, not the LLM.
- The LLM prompt includes Cozmo's current emotional state, so replies change with mood.

## Emotions
- `cvc/emotions.py` tracks Cozmo's mood (`happy`, `sad`, `curious`, `excited`, `tired`, `bored`, `scared`).
- Mood is reflected in backpack lights, animations, and LLM replies.
- New voice commands: `mood`, `happy`, `sad`, `sleep`.
- Boredom increases with inactivity; the autonomous pet loop uses this.

## Offline speech recognition
- Enable with `--offline-stt` to avoid Google and work without internet.
- Uses Vosk with the model at `cvc/models/vosk/vosk-model-small-en-us-0.15/`.
- Currently English only; add other Vosk models to support more languages.

## Autonomous pet mode
- Enable with `--pet-mode`.
- Runs a background thread that updates Cozmo's emotional state and chooses idle actions (dance, look, blocks, etc.) based on mood.
- Interacting with voice commands resets boredom.

## Web editor
- Enable with `--web-editor` (optionally `--web-port=8080`).
- Opens a browser UI at `http://127.0.0.1:5000` for editing language JSON files and viewing live status.

## Autonomous agent
- Enable with `--autonomous`. Requires `--llm` for the LLM brain.
- Uses `cvc/agent.py` for the observe-think-act-remember loop.
- Uses `cvc/memory.py` (SQLite) for persistent memory.
- Cozmo observes environment, asks LLM what to do, executes, and stores results.
- Learns from successful/failed actions over time.

## Interactive web control panel
- Run standalone: `python -m cvc.web_control`
- Opens at `http://127.0.0.1:8080`
- Full UI with camera, movement buttons, sliders, emotions, lights, speech, log.
- Works with pycozmo backend (no app needed).

---

## Architecture & Future Improvements

### Current architecture issues

1. **No tests** — Zero test coverage. Critical for reliability.
2. **No type hints** — Python 3.6 supports basic annotations; adding them prevents bugs.
3. **No logging framework** — Uses `print`/`cprint` everywhere. Should use `logging` module.
4. **No config file** — All settings via CLI flags. A `cvc.yaml` or `cvc.json` would persist preferences.
5. **No plugin system** — Adding new backends, STT providers, or LLM providers requires editing core files.
6. **Threading model** — pet_mode, agent, web_editor, web_control all run as separate threads with no coordination. A task queue or asyncio would be cleaner.
7. **LLM integration is basic** — No streaming, no function calling, no structured output. Agent prompts are English-only.
8. **Memory lacks semantic search** — SQLite stores facts but can't find "similar past situations." Vector embeddings would enable that.
9. **No skill system** — Agent actions are hardcoded. A skill registry would let the agent learn and compose new behaviors.
10. **No configuration persistence** — Language choice, emotion, settings are lost between runs.
11. **No health monitoring** — No way to check if Ollama is running, if Vosk model is loaded, or if the robot is connected.
12. **No REST/WebSocket API** — Web control uses HTTP polling. WebSockets would give real-time updates.

### Priority improvements (ordered by impact)

**P0 — Stability:**
- Add `pytest` tests for `memory.py`, `llm.py`, `emotions.py`, `voice_commands.py`.
- Replace `print`/`cprint` with `logging` module (configurable level via `--log`).
- Add type hints to all public methods.
- Add `try/except` around every backend call with retry logic.

**P1 — Developer experience:**
- Create `cvc/config.py` that reads `~/.config/cvc/config.json` for defaults.
- Add `cvc --init` to generate a config file interactively.
- Add `cvc --status` to print system health (Ollama, Vosk model, backend, battery).

**P2 — Agent intelligence:**
- Add vector embeddings to memory (use `sentence-transformers` or Ollama embeddings) for semantic search.
- Implement a skill registry: agent can discover and compose skills dynamically.
- Add function-calling support for LLM (structured JSON output instead of regex parsing).
- Multi-language agent prompts (detect user language, respond accordingly).
- Add "curiosity" drive — agent explores new areas, tries unfamiliar actions.

**P3 — Real-time:**
- Replace HTTP polling in web_control with WebSocket.
- Add `/api/ws` endpoint for live camera + status streaming.
- Add webhook support: Cozmo can notify external services on events (face seen, low battery).

**P4 — Advanced:**
- Add voice wake-word detection (pvporcupine or openwakeword) to replace SHIFT key.
- Add face recognition with names (face_recognition library or InsightFace).
- Add object detection (YOLO) via camera for smarter autonomous behavior.
- Multi-robot support: coordinate multiple Cozmo units via MQTT.
- Add skill learning: agent records sequences of actions that succeed and replays them.

### File structure after improvements

```
cvc/
├── __init__.py
├── cozmo_voice_commands.py   # CLI entry point
├── config.py                  # NEW: configuration management
├── voice_commands.py          # command implementations
├── backends/
│   ├── base.py               # abstract interface
│   ├── anki_backend.py       # official SDK
│   └── pycozmo_backend.py    # direct WiFi
├── llm.py                     # LLM integration
├── emotions.py                # mood system
├── memory.py                  # SQLite persistence
├── agent.py                   # autonomous loop
├── skills/                    # NEW: skill registry
│   ├── __init__.py
│   ├── base.py               # skill interface
│   ├── dance.py
│   ├── explore.py
│   └── social.py
├── stt_offline.py             # Vosk STT
├── stt_wakeword.py            # NEW: wake word detection
├── pet_mode.py                # idle behavior
├── web_editor.py              # language editor
├── web_control.py             # control panel
├── languages/*.json           # localized commands
├── models/vosk/               # Vosk models
└── tests/                     # NEW: test suite
    ├── test_memory.py
    ├── test_emotions.py
    ├── test_llm.py
    └── test_voice_commands.py
```

### Contributing guidelines

- All new code must have type hints.
- All public methods must have docstrings.
- Run `python -m pytest` before committing.
- New features need at least one test.
- Follow existing code style (no linter configured, but keep it consistent).
