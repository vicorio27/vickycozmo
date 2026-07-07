# Cozmo Voice Commands (CvC)

Control your [Cozmo](https://anki.com/en-us/cozmo) robot with your voice. Issue single or chained commands, have conversations with a local AI, let Cozmo roam autonomously, and customize everything through a web editor.

> **Important:** Cozmo and the Cozmo SDK are no longer maintained. The SDK works best with **Python 3.6**. Use a Python 3.6 virtual environment to avoid compatibility issues.

## Features

- **Voice commands** in English, Italian, French, German, and Dutch — easy to add more languages.
- **Chained commands** using language-specific separators like English `THEN`.
- **Two connection backends**: official Anki SDK (requires mobile app) or **pycozmo** (direct WiFi, no app needed).
- **Local AI conversation** with Ollama (LLM mode).
- **Emotional state** system that changes Cozmo's lights, animations, and replies.
- **Autonomous pet mode** for idle behavior based on mood.
- **Autonomous agent** — Cozmo observes, thinks, and acts on his own using LLM + memory.
- **Interactive web control panel** — full UI with camera, buttons, sliders, and voice.
- **Offline speech recognition** with Vosk — no internet required.
- **Web editor** to edit languages and commands from a browser.
- **Persistent memory** — SQLite database that stores interactions and learns from them.

## Requirements

- Python 3.6
- `portaudio` system library
- A microphone
- [Cozmo SDK setup](http://cozmosdk.anki.com/docs/) for your platform (only needed for the Anki backend)
- [Npcap](https://npcap.com) on Windows (only needed for pycozmo backend)

### System dependencies

**macOS:**
```bash
brew install portaudio
```

**Linux:**
```bash
sudo apt-get install flac portaudio19-dev python-all-dev python3-all-dev
```

**Windows:**
- Install [Git for Windows](https://git-scm.com/download/win)
- You may need a PyAudio wheel for your Python version

## Installation

Use Miniconda/Conda to create a Python 3.6 environment:

```bash
conda create -n cvc python=3.6
conda activate cvc
```

Install from the repository:

```bash
pip install --upgrade git+https://github.com/rizal72/Cozmo-Voice-Commands
```

Or install from source for development:

```bash
git clone https://github.com/rizal72/Cozmo-Voice-Commands.git
cd Cozmo-Voice-Commands
pip install -e .
```

### Offline speech model (optional)

For offline voice recognition, download the Vosk English model:

```bash
mkdir -p cvc/models/vosk
cd cvc/models/vosk
# Download and extract
curl -LO https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
rm vosk-model-small-en-us-0.15.zip
```

### pycozmo backend (no mobile app needed)

To control Cozmo directly over WiFi without the mobile app:

```bash
pip install pycozmo
```

**Windows:** install [Npcap](https://npcap.com) for packet capture.
**Linux:** run with `sudo` or set packet capture capabilities.

Then connect your PC to Cozmo's WiFi network and run:

```bash
cvc --use-pycozmo
```

**Feature compatibility:**

| Feature | Anki SDK (app) | pycozmo (no app) |
|---------|---------------|------------------|
| Drive forward/backward | ✅ | ✅ |
| Turn left/right | ✅ | ✅ |
| Lift/head movement | ✅ | ✅ |
| Speech (say text) | ✅ | ✅ |
| Backpack lights | ✅ | ✅ |
| Play animations | ✅ | ⚠️ Most work |
| Look around | ✅ | ✅ (simulated) |
| Find faces | ✅ | ⚠️ Limited |
| Follow face | ✅ | ⚠️ Simplified |
| Take picture | ✅ | ✅ |
| Play with blocks | ✅ | ⚠️ Simplified |
| Go to charger | ✅ | ❌ Not available |
| Battery voltage | ✅ | ⚠️ Approximate |

### Local AI model (optional)

For conversation mode, install [Ollama](https://ollama.com) and pull a model:

```bash
ollama pull phi3
```

## Usage

Run the app:

```bash
cvc
```

### Basic voice control

1. Choose a language from the menu.
2. Press **SHIFT** when you are ready to speak.
3. Say a command starting with **"Cozmo"** or **"Robot"**, for example:
   - *"Cozmo, forward 3"*
   - *"Cozmo, dance THEN take a picture THEN go to your charger"*

You have about 5 seconds to start talking after pressing SHIFT.

### Command-line options

| Flag | Description |
|------|-------------|
| `--version` / `-V` | Print version and exit |
| `--log` / `-L` | Enable verbose logging |
| `--no-wait` / `-W` | Continuous listening mode (deprecated) |
| `--use-pycozmo` | Use pycozmo backend (direct WiFi, no mobile app) |
| `--autonomous` | Enable autonomous agent mode (observe + think + act with LLM) |
| `--llm` | Enable local AI conversation mode |
| `--llm-model=MODEL` | Use a different Ollama model (default: `phi3`) |
| `--offline-stt` | Use Vosk offline speech recognition |
| `--pet-mode` | Enable autonomous pet behavior |
| `--web-editor` | Start the web editor |
| `--web-port=PORT` | Web editor port (default: 5000) |

### Example: full feature mode

```bash
cvc --llm --offline-stt --pet-mode --web-editor
```

This starts Cozmo with:
- Offline speech recognition
- Local AI conversations
- Autonomous pet behavior
- Web editor at http://127.0.0.1:5000

## Available commands

| Command | Description |
|---------|-------------|
| `forward X` | Drive forward for X seconds |
| `backward X` | Drive backward for X seconds |
| `left X` | Turn left X degrees (default 90) |
| `right X` | Turn right X degrees (default 90) |
| `lift X` | Move lift to height X (0-100) |
| `head X` | Tilt head to angle X (0-100) |
| `look` | Look around for a face |
| `follow` | Follow a visible face |
| `picture` / `photo` | Take a picture |
| `say TEXT` | Say TEXT out loud |
| `blocks` / `cubes` / `play` | Play with blocks |
| `dance` / `jump` | Dance |
| `charger` / `base` | Go park on the charger |
| `mood` / `how are you` / `feeling` | Say how Cozmo feels |
| `happy` / `cheer up` | Become happy |
| `be sad` | Become sad |
| `sleep` / `good night` | Go to sleep |

## Modes

### LLM conversation mode

Enable with `--llm`. After Cozmo executes any physical commands, the recognized speech is also sent to your local Ollama model. Cozmo speaks the AI's reply. The AI prompt includes Cozmo's current emotional state, so replies change with mood.

```bash
cvc --llm --llm-model=phi3
```

### Emotions

Cozmo tracks a mood state: `happy`, `sad`, `curious`, `excited`, `tired`, `bored`, `scared`. Mood affects backpack lights, animations, and LLM replies. Inactivity increases boredom and can make Cozmo tired.

Use voice commands like *"Cozmo, how are you?"* or *"Cozmo, cheer up"* to interact with emotions.

### Autonomous pet mode

Enable with `--pet-mode`. Cozmo will act on his own in the background based on his mood:
- **Bored:** asks for attention, dances, looks around
- **Tired:** lowers head and lift
- **Happy/Excited:** dances and moves around
- **Curious:** looks for faces or plays with blocks

Voice interactions reset boredom.

### Offline speech recognition

Enable with `--offline-stt` to avoid Google Speech Recognition and work without internet. Requires the Vosk model downloaded to `cvc/models/vosk/vosk-model-small-en-us-0.15/`.

Currently English only. Download other Vosk models and point to them to support more languages.

### Autonomous agent

Enable with `--autonomous`. Cozmo enters a continuous loop:
1. **Observe** — check battery, faces, objects, mood
2. **Think** — LLM decides what to do based on situation + memory
3. **Act** — execute the chosen action (drive, turn, speak, dance, etc.)
4. **Remember** — store the experience in SQLite database
5. **Learn** — track what works and what doesn't

```bash
cvc --autonomous --llm --use-pycozmo
```

The agent learns from interactions and stores:
- Successful/failed actions
- People it has seen
- Facts it has learned
- Lessons from experience

### Interactive web control panel

Run standalone (no app needed):

```bash
python -m cvc.web_control
```

Opens at http://127.0.0.1:8080 with:
- Camera feed and photo capture
- Movement controls (D-pad + sliders)
- Lift and head controls
- Emotion buttons
- Light color picker
- Speech text input
- Quick command buttons
- Live log of all commands

Keyboard shortcuts: arrow keys to move, space to dance, `c` for camera, `p` for picture.

### Web editor

Enable with `--web-editor` and open http://127.0.0.1:5000 in your browser. You can:
- View all loaded languages
- Edit any language JSON file
- Save changes directly
- View live status (emotion, LLM enabled)

## Customization

### Add a new command

1. Open the language file in `cvc/languages/` (e.g., `en.json`).
2. Add an entry to the `commands` list:
   ```json
   {"action": "my_command", "words": ["my command"], "usage": "Description of what it does."}
   ```
3. Implement the method in `cvc/voice_commands.py`:
   ```python
   def my_command(self, robot, cmd_args):
       # your code here
       return "Done!"
   ```

### Add a new language

1. Copy an existing file in `cvc/languages/`.
2. Change the `id` to a unique number.
3. Translate all strings.
4. The new language will appear automatically in the startup menu.

## Development

Run without installing:

```bash
python cvc.py
```

Make sure `cvc/` is on your `PYTHONPATH` or run from the repository root.

## Notes

- Cozmo does not have a built-in microphone. Use your computer's microphone.
- The original Cozmo SDK targets Python 3.6. Running on newer Python versions may fail due to SDK incompatibilities.
- Tested on macOS, Windows, and Linux.

## Future Development

### Priority improvements

**Stability (P0):**
- Add `pytest` tests for core modules
- Replace `print` with `logging` module (configurable via `--log`)
- Add type hints to all public methods
- Add retry logic for backend calls

**Developer experience (P1):**
- Add `cvc.config` for persistent settings (`~/.config/cvc/config.json`)
- Add `cvc --init` to generate config interactively
- Add `cvc --status` to check system health

**Agent intelligence (P2):**
- Vector embeddings in memory for semantic search of past experiences
- Skill registry: agent discovers and composes skills dynamically
- Function-calling support for LLM (structured JSON output)
- Multi-language agent prompts
- Curiosity drive: agent explores and tries new things

**Real-time (P3):**
- WebSocket support in web control panel
- Live camera streaming via WebSocket
- Webhook support for external integrations

**Advanced (P4):**
- Voice wake-word detection (pvporcupine/openwakeword)
- Face recognition with names
- Object detection (YOLO) for smarter behavior
- Multi-robot coordination via MQTT
- Skill learning: record and replay successful action sequences

### Contributing

- All new code must have type hints
- All public methods must have docstrings
- Run `python -m pytest` before committing
- New features need at least one test

## License

GNU General Public License v3.0

## Author

Riccardo Sallusti — https://github.com/rizal72/Cozmo-Voice-Commands
