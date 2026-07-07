"""
Simple web editor for Cozmo Voice Commands languages and commands.

Run alongside the main app to edit JSON language files from a browser.
"""
import os
import json
import glob
import threading

from flask import Flask, request, jsonify, render_template_string


APP = Flask(__name__)
LANGUAGES_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "languages")

# Shared state references (set by the main app).
STATE = {
    "emotion_state": None,
    "vc": None,
    "llm_enabled": False,
}


def set_state(emotion_state=None, vc=None, llm_enabled=False):
    STATE["emotion_state"] = emotion_state
    STATE["vc"] = vc
    STATE["llm_enabled"] = llm_enabled


INDEX_HTML = """
<!doctype html>
<html>
<head>
    <title>CvC Web Editor</title>
    <style>
        body { font-family: sans-serif; margin: 2rem; background: #f5f5f5; }
        h1 { color: #333; }
        .card { background: white; padding: 1rem; margin-bottom: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        label { display: block; margin-top: 0.5rem; font-weight: bold; }
        input, textarea { width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box; }
        button { margin-top: 1rem; padding: 0.5rem 1rem; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .command { border: 1px solid #ddd; padding: 0.5rem; margin-top: 0.5rem; border-radius: 4px; }
        .status { font-family: monospace; background: #222; color: #0f0; padding: 1rem; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>Cozmo Voice Commands - Web Editor</h1>

    <div class="card">
        <h2>Status</h2>
        <div id="status" class="status">Loading...</div>
    </div>

    <div class="card">
        <h2>Languages</h2>
        <select id="langSelect" onchange="loadLanguage()"></select>
        <button onclick="saveLanguage()">Save Language</button>
        <div id="editor"></div>
    </div>

    <script>
        async function fetchStatus() {
            const res = await fetch('/api/status');
            const data = await res.json();
            document.getElementById('status').innerText = JSON.stringify(data, null, 2);
        }

        async function loadLanguages() {
            const res = await fetch('/api/languages');
            const langs = await res.json();
            const select = document.getElementById('langSelect');
            select.innerHTML = '';
            langs.forEach(l => {
                const opt = document.createElement('option');
                opt.value = l.file;
                opt.innerText = l.name;
                select.appendChild(opt);
            });
            loadLanguage();
        }

        async function loadLanguage() {
            const file = document.getElementById('langSelect').value;
            const res = await fetch('/api/language/' + file);
            const data = await res.json();
            const editor = document.getElementById('editor');
            editor.innerHTML = '<label>JSON Content</label><textarea id="jsonEditor" rows="30">' + JSON.stringify(data, null, 2) + '</textarea>';
        }

        async function saveLanguage() {
            const file = document.getElementById('langSelect').value;
            const content = document.getElementById('jsonEditor').value;
            const res = await fetch('/api/language/' + file, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: content
            });
            const result = await res.json();
            alert(result.message || result.error);
            loadLanguages();
        }

        setInterval(fetchStatus, 2000);
        loadLanguages();
    </script>
</body>
</html>
"""


@APP.route("/")
def index():
    return render_template_string(INDEX_HTML)


@APP.route("/api/status")
def api_status():
    data = {
        "llm_enabled": STATE["llm_enabled"],
        "emotion": None,
    }
    if STATE["emotion_state"]:
        data["emotion"] = STATE["emotion_state"].get()
    return jsonify(data)


@APP.route("/api/languages")
def api_languages():
    files = glob.glob(os.path.join(LANGUAGES_DIR, "*.json"))
    result = []
    for path in sorted(files):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result.append({
                "file": os.path.basename(path),
                "name": data.get("name", os.path.basename(path)),
            })
        except Exception as e:
            result.append({"file": os.path.basename(path), "name": "error: " + str(e)})
    return jsonify(result)


@APP.route("/api/language/<filename>")
def api_get_language(filename):
    path = os.path.join(LANGUAGES_DIR, filename)
    if not os.path.isfile(path):
        return jsonify({"error": "file not found"}), 404
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@APP.route("/api/language/<filename>", methods=["POST"])
def api_save_language(filename):
    path = os.path.join(LANGUAGES_DIR, filename)
    try:
        data = request.get_json(force=True)
        # Basic validation: must have required keys
        required = {"id", "name", "lang", "commands"}
        if not required.issubset(data.keys()):
            return jsonify({"error": "missing required keys: " + str(required - data.keys())}), 400

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return jsonify({"message": "saved " + filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


class WebEditor(threading.Thread):
    """Run the Flask editor in a background thread."""

    def __init__(self, host="127.0.0.1", port=5000, emotion_state=None, vc=None, llm_enabled=False):
        super(WebEditor, self).__init__(daemon=True)
        self.host = host
        self.port = port
        set_state(emotion_state, vc, llm_enabled)

    def run(self):
        APP.run(host=self.host, port=self.port, threaded=True, use_reloader=False)
