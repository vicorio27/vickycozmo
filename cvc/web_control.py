"""
Complete command center for Cozmo.

Integrates all features: voice commands, LLM, emotions, autonomous agent,
camera, movement, lights, speech, and memory.

Run standalone:
    python -m cvc.web_control

Or with flags:
    python -m cvc.web_control --use-pycozmo --llm --autonomous
"""
import os
import sys
import time
import json
import base64
import threading
import io
import argparse

from flask import Flask, request, jsonify, render_template_string

try:
    import pycozmo
    HAS_PYCOZMO = True
except ImportError:
    HAS_PYCOZMO = False

APP = Flask(__name__)

# Global state
STATE = {
    "client": None,
    "connected": False,
    "emotion": "curious",
    "battery": 3.7,
    "camera_enabled": False,
    "llm_enabled": False,
    "llm_model": "phi3",
    "autonomous_enabled": False,
    "autonomous_agent": None,
    "memory": None,
    "log": [],
    "command_count": 0,
    "voice_text": "",
}

LIGHT_COLORS = {
    "green": (0, 255, 0), "blue": (0, 0, 255), "red": (255, 0, 0),
    "white": (255, 255, 255), "off": (0, 0, 0), "yellow": (255, 255, 0),
    "purple": (128, 0, 128), "orange": (255, 165, 0),
}

EMOTION_EMOJIS = {
    "happy": "😊", "sad": "😢", "curious": "🤔", "excited": "🤩",
    "tired": "😴", "bored": "🙄", "scared": "😨",
}

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cozmo Command Center</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0a0a1a;color:#e0e0e0;min-height:100vh}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);padding:12px 24px;display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #0f3460;flex-wrap:wrap;gap:10px}
.header h1{color:#00d4ff;font-size:1.4em}
.status-bar{display:flex;gap:16px;font-size:.85em;flex-wrap:wrap}
.status-item{display:flex;align-items:center;gap:5px}
.dot{width:10px;height:10px;border-radius:50%;background:#ff4444}
.dot.on{background:#00ff88}
.main{display:grid;grid-template-columns:1fr 1fr 320px;gap:16px;padding:16px;max-width:1600px;margin:0 auto}
@media(max-width:1200px){.main{grid-template-columns:1fr 1fr}}
@media(max-width:800px){.main{grid-template-columns:1fr}}
.panel{background:#1a1a2e;border-radius:10px;padding:16px;border:1px solid #0f3460}
.panel h2{color:#00d4ff;margin-bottom:12px;font-size:1em;border-bottom:1px solid #0f3460;padding-bottom:6px}
.camera-box{background:#000;border-radius:8px;overflow:hidden;aspect-ratio:4/3;display:flex;align-items:center;justify-content:center;margin-bottom:12px;position:relative}
.camera-box img{width:100%;height:100%;object-fit:contain}
.cam-off{color:#555;font-size:1.1em}
.btn-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:12px}
.btn{padding:10px 6px;border:none;border-radius:8px;cursor:pointer;font-size:.8em;font-weight:600;transition:all .12s;text-align:center}
.btn:hover{transform:scale(1.04)}.btn:active{transform:scale(.96)}
.btn-green{background:#1a5c3a;color:#00ff88}.btn-blue{background:#1a3a5c;color:#00d4ff}
.btn-red{background:#5c1a1a;color:#ff4444}.btn-purple{background:#3c1a5c;color:#ff00ff}
.btn-orange{background:#5c3a1a;color:#ffaa00}.btn-cyan{background:#0a3a4a;color:#00ffff}
.btn-gray{background:#2a2a3a;color:#aaa}.btn-yellow{background:#4a4a1a;color:#ffff00}
.dpad{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;max-width:260px;margin:0 auto 16px}
.dpad-btn{width:65px;height:65px;border:none;border-radius:10px;font-size:1.4em;cursor:pointer;transition:all .12s;display:flex;align-items:center;justify-content:center}
.dpad-btn:hover{transform:scale(1.08)}.dpad-btn:active{transform:scale(.92)}
.dpad-m{background:#1a3a5c;color:#00d4ff}.dpad-d{background:#3c1a5c;color:#ff00ff}
.dpad-h{background:#5c3a1a;color:#ffaa00}.dpad-a{background:#1a5c3a;color:#00ff88}
.slider{margin-bottom:10px}
.slider label{display:block;margin-bottom:3px;color:#aaa;font-size:.85em}
input[type=range]{width:100%;accent-color:#00d4ff}
.light-grid{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.light-btn{width:36px;height:36px;border-radius:50%;border:2px solid #333;cursor:pointer;transition:all .12s}
.light-btn:hover{transform:scale(1.15);border-color:#fff}
.input-row{display:flex;gap:6px;margin-bottom:12px}
.input-row input{flex:1;padding:9px 12px;border-radius:8px;border:1px solid #0f3460;background:#0a0a1a;color:#e0e0e0;font-size:.9em}
.input-row input:focus{outline:none;border-color:#00d4ff}
.input-row button{padding:9px 16px;border-radius:8px;border:none;background:#00d4ff;color:#000;font-weight:600;cursor:pointer;font-size:.9em}
.emotion-box{text-align:center;padding:12px;background:#0a0a1a;border-radius:8px;margin-bottom:12px;border:1px solid #0f3460}
.emotion-emoji{font-size:2.8em;margin-bottom:4px}
.emotion-name{color:#00d4ff;font-size:1em;font-weight:600}
.log-box{background:#0a0a1a;border-radius:8px;padding:10px;height:180px;overflow-y:auto;font-family:Consolas,monospace;font-size:.75em;border:1px solid #0f3460}
.log-entry{margin-bottom:3px}.log-sent{color:#00d4ff}.log-recv{color:#00ff88}.log-err{color:#ff4444}.log-info{color:#aaa}
.memory-box{background:#0a0a1a;border-radius:8px;padding:10px;height:120px;overflow-y:auto;font-family:Consolas,monospace;font-size:.75em;border:1px solid #0f3460}
.section-title{color:#888;font-size:.8em;margin:8px 0 4px;text-transform:uppercase;letter-spacing:1px}
.voice-btn{width:100%;padding:14px;border:none;border-radius:10px;background:linear-gradient(135deg,#0f3460,#1a1a4e);color:#00d4ff;font-size:1.1em;font-weight:600;cursor:pointer;transition:all .2s;margin-bottom:12px}
.voice-btn:hover{background:linear-gradient(135deg,#1a4a7c,#2a2a6e)}
.voice-btn.listening{background:linear-gradient(135deg,#5c1a1a,#3a1a1a);color:#ff4444;animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.7}}
</style>
</head>
<body>
<div class="header">
<h1>Cozmo Command Center</h1>
<div class="status-bar">
<div class="status-item"><div class="dot {{ 'on' if connected else '' }}"></div><span>{{ 'Connected' if connected else 'Disconnected' }}</span></div>
<div class="status-item">🔋 <span id="battery">{{ battery }}V</span></div>
<div class="status-item">🎯 <span id="cmd-count">{{ command_count }}</span></div>
<div class="status-item" id="llm-status">🧠 {{ 'LLM ON' if llm_enabled else 'LLM OFF' }}</div>
<div class="status-item" id="agent-status">🤖 {{ 'Agent ON' if autonomous else 'Agent OFF' }}</div>
</div>
</div>

<div class="main">
<!-- LEFT COLUMN: Camera + Movement -->
<div>
<div class="panel">
<h2>📷 Camera</h2>
<div class="camera-box"><img id="cam" src="" style="display:none"><div class="cam-off" id="cam-off">Camera off</div></div>
<div class="btn-grid">
<button class="btn btn-green" onclick="cmd('camera_toggle')">📷 Toggle</button>
<button class="btn btn-blue" onclick="cmd('picture')">📸 Photo</button>
<button class="btn btn-orange" onclick="cmd('look')">🔍 Look</button>
</div>
</div>

<div class="panel">
<h2>🎮 Movement</h2>
<div class="dpad">
<div></div><button class="dpad-btn dpad-m" onclick="cmd('forward')">▲</button><div></div>
<button class="dpad-btn dpad-m" onclick="cmd('left')">◀</button>
<button class="dpad-btn dpad-a" onclick="cmd('dance')">💃</button>
<button class="dpad-btn dpad-m" onclick="cmd('right')">▶</button>
<div></div><button class="dpad-btn dpad-m" onclick="cmd('backward')">▼</button><div></div>
</div>
<div class="slider"><label>Speed: <span id="spd">50</span> mm/s</label><input type="range" id="speed" min="10" max="200" value="50" oninput="$('#spd').textContent=this.value"></div>
<div class="slider"><label>Distance: <span id="dst">100</span> mm</label><input type="range" id="dist" min="20" max="500" value="100" oninput="$('#dst').textContent=this.value"></div>
<div class="slider"><label>Degrees: <span id="deg">90</span>°</label><input type="range" id="degs" min="10" max="180" value="90" oninput="$('#deg').textContent=this.value"></div>
</div>

<div class="panel">
<h2>🦾 Lift & Head</h2>
<div class="btn-grid">
<button class="btn btn-purple" onclick="cmd('lift_up')">⬆ Lift</button>
<button class="btn btn-gray" onclick="cmd('lift_stop')">■</button>
<button class="btn btn-purple" onclick="cmd('lift_down')">⬇ Lift</button>
<button class="btn btn-orange" onclick="cmd('head_up')">⬆ Head</button>
<button class="btn btn-gray" onclick="cmd('head_stop')">■</button>
<button class="btn btn-orange" onclick="cmd('head_down')">⬇ Head</button>
</div>
<div class="slider"><label>Lift: <span id="lht">50</span>%</label><input type="range" id="lifth" min="0" max="100" value="50" oninput="$('#lht').textContent=this.value"></div>
<div class="slider"><label>Head: <span id="hdg">0</span>°</label><input type="range" id="heada" min="-34" max="22" value="0" oninput="$('#hdg').textContent=this.value"></div>
</div>
</div>

<!-- MIDDLE COLUMN: Emotions + Lights + Speech + Quick -->
<div>
<div class="panel">
<h2>😊 Emotion</h2>
<div class="emotion-box"><div class="emotion-emoji" id="emoji">🤖</div><div class="emotion-name" id="ename">{{ emotion }}</div></div>
<div class="btn-grid">
<button class="btn btn-green" onclick="cmd('happy')">😊 Happy</button>
<button class="btn btn-blue" onclick="cmd('sad')">😢 Sad</button>
<button class="btn btn-purple" onclick="cmd('excited')">🤩 Excited</button>
<button class="btn btn-orange" onclick="cmd('curious')">🤔 Curious</button>
<button class="btn btn-red" onclick="cmd('scared')">😨 Scared</button>
<button class="btn btn-blue" onclick="cmd('tired')">😴 Tired</button>
</div>
</div>

<div class="panel">
<h2>💡 Lights</h2>
<div class="light-grid">
<button class="light-btn" style="background:#0f0" onclick="cmd('light_green')"></button>
<button class="light-btn" style="background:#00f" onclick="cmd('light_blue')"></button>
<button class="light-btn" style="background:#f00" onclick="cmd('light_red')"></button>
<button class="light-btn" style="background:#fff" onclick="cmd('light_white')"></button>
<button class="light-btn" style="background:#ff0" onclick="cmd('light_yellow')"></button>
<button class="light-btn" style="background:#808" onclick="cmd('light_purple')"></button>
<button class="light-btn" style="background:#f80" onclick="cmd('light_orange')"></button>
<button class="light-btn" style="background:#000" onclick="cmd('light_off')"></button>
</div>
</div>

<div class="panel">
<h2>💬 Speech</h2>
<div class="input-row"><input type="text" id="speech" placeholder="Type what Cozmo should say..." onkeypress="if(event.key==='Enter')sendSpeech()"><button onclick="sendSpeech()">Say</button></div>
<button class="voice-btn" id="voice-btn" onclick="startVoice()">🎤 Press to Talk</button>
</div>

<div class="panel">
<h2>⚡ Quick Actions</h2>
<div class="btn-grid">
<button class="btn btn-green" onclick="cmd('dance')">💃 Dance</button>
<button class="btn btn-blue" onclick="cmd('blocks')">🧱 Blocks</button>
<button class="btn btn-purple" onclick="cmd('follow')">👤 Follow</button>
<button class="btn btn-orange" onclick="cmd('charger')">🔌 Charger</button>
<button class="btn btn-red" onclick="cmd('sleep')">😴 Sleep</button>
<button class="btn btn-cyan" onclick="cmd('wave')">👋 Wave</button>
</div>
</div>

<div class="panel">
<h2>🧠 LLM Chat</h2>
<div class="input-row"><input type="text" id="llm-input" placeholder="Ask Cozmo anything..." onkeypress="if(event.key==='Enter')sendLLM()"><button onclick="sendLLM()">Ask</button></div>
<div class="log-box" id="llm-log"></div>
</div>
</div>

<!-- RIGHT COLUMN: Status + Agent + Memory + Log -->
<div>
<div class="panel">
<h2>📊 Status</h2>
<div style="font-size:.85em;line-height:1.8">
<div>Battery: <span id="batt">{{ battery }}V</span></div>
<div>Emotion: <span id="emo">{{ emotion }}</span></div>
<div>Commands: <span id="cmds">{{ command_count }}</span></div>
<div>Backend: <span id="backend">{{ backend }}</span></div>
<div>LLM: <span id="llm">{{ llm_model if llm_enabled else 'OFF' }}</span></div>
<div>Agent: <span id="agent">{{ 'Running' if autonomous else 'OFF' }}</span></div>
</div>
</div>

<div class="panel">
<h2>🤖 Autonomous Agent</h2>
<div class="btn-grid">
<button class="btn btn-green" onclick="cmd('agent_start')">▶ Start</button>
<button class="btn btn-red" onclick="cmd('agent_stop')">⏹ Stop</button>
<button class="btn btn-blue" onclick="cmd('agent_status')">📊 Status</button>
</div>
<div class="log-box" id="agent-log"></div>
</div>

<div class="panel">
<h2>💾 Memory</h2>
<div class="btn-grid">
<button class="btn btn-blue" onclick="cmd('memory_stats')">📊 Stats</button>
<button class="btn btn-orange" onclick="cmd('memory_context')">🧠 Context</button>
<button class="btn btn-red" onclick="cmd('memory_clear')">🗑 Clear</button>
</div>
<div class="memory-box" id="memory-box">No memory loaded</div>
</div>

<div class="panel">
<h2>📋 Command Log</h2>
<div class="log-box" id="log-box"></div>
</div>
</div>
</div>

<script>
function $(id){return document.getElementById(id)}
function addLog(box,text,type='info'){const b=$(box);const d=document.createElement('div');d.className='log-entry log-'+type;d.textContent=new Date().toLocaleTimeString()+' '+text;b.appendChild(d);b.scrollTop=b.scrollHeight}
function updateCam(){fetch('/api/camera').then(r=>r.json()).then(d=>{if(d.image){$('cam').src='data:image/jpeg;base64,'+d.image;$('cam').style.display='block';$('cam-off').style.display='none'}else{$('cam').style.display='none';$('cam-off').style.display='block'}}).catch(()=>{})}
function updateStatus(){fetch('/api/status').then(r=>r.json()).then(d=>{$('batt').textContent=d.battery+'V';$('cmds').textContent=d.command_count;$('emo').textContent=d.emotion;$('emoji').textContent=EMOJI[d.emotion]||'🤖';$('ename').textContent=d.emotion}).catch(()=>{})}
const EMOJI={happy:'😊',sad:'😢',curious:'🤔',excited:'🤩',tired:'😴',bored:'🙄',scared:'😨'};
function cmd(c){const p={};if(c==='forward'||c==='backward'){p.distance=$('dist').value;p.speed=$('speed').value}else if(c==='left'||c==='right'){p.degrees=$('degs').value}else if(c==='lift_up'||c==='lift_down'){p.height=$('lifth').value}else if(c==='head_up'||c==='head_down'){p.angle=$('heada').value}addLog('log-box','→ '+c,'sent');fetch('/api/command/'+c,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}).then(r=>r.json()).then(d=>{if(d.error)addLog('log-box','Error: '+d.error,'err');else{addLog('log-box','← '+(d.message||'OK'),'recv');if(d.image){$('cam').src='data:image/jpeg;base64,'+d.image;$('cam').style.display='block';$('cam-off').style.display='none'}if(d.log)addLog('agent-log',d.log,'info');if(d.memory)$('memory-box').textContent=d.memory}}).catch(e=>addLog('log-box','Error: '+e,'err'))}
function sendSpeech(){const t=$('speech').value;if(!t)return;cmd('say');$('speech').value='';document.querySelector('[data-cmd=say]')
function sendLLM(){const t=$('llm-input').value;if(!t)return;addLog('llm-log','→ '+t,'sent');fetch('/api/llm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})}).then(r=>r.json()).then(d=>{addLog('llm-log','← '+(d.response||d.error||'No response'),'recv');$('llm-input').value=''}).catch(e=>addLog('llm-log','Error: '+e,'err'))}
function startVoice(){addLog('log-box','🎤 Voice recognition not available in web mode. Use terminal.','info')}
document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT')return;switch(e.key){case'ArrowUp':cmd('forward');break;case'ArrowDown':cmd('backward');break;case'ArrowLeft':cmd('left');break;case'ArrowRight':cmd('right');break;case' ':e.preventDefault();cmd('dance');break;case'c':cmd('camera_toggle');break;case'p':cmd('picture');break}});
setInterval(updateCam,500);setInterval(updateStatus,2000);
addLog('log-box','Command Center ready','info');
</script>
</body>
</html>
"""


@APP.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        connected=STATE["connected"],
        battery=STATE["battery"],
        emotion=STATE["emotion"],
        command_count=STATE["command_count"],
        llm_enabled=STATE["llm_enabled"],
        llm_model=STATE["llm_model"],
        autonomous=STATE["autonomous_enabled"],
        backend="pycozmo" if HAS_PYCOZMO else "anki",
    )


@APP.route("/api/status")
def api_status():
    return jsonify({
        "connected": STATE["connected"],
        "battery": STATE["battery"],
        "emotion": STATE["emotion"],
        "command_count": STATE["command_count"],
    })


@APP.route("/api/camera")
def api_camera():
    client = STATE["client"]
    if not client:
        return jsonify({"image": None})
    try:
        if hasattr(client, 'camera') and client.camera:
            img = client.camera.latest_image
            if img and hasattr(img, 'raw_image'):
                buf = io.BytesIO()
                img.raw_image.save(buf, format='JPEG', quality=60)
                return jsonify({"image": base64.b64encode(buf.getvalue()).decode()})
    except Exception:
        pass
    return jsonify({"image": None})


@APP.route("/api/command/<cmd>", methods=["POST"])
def api_command(cmd):
    client = STATE["client"]
    params = request.get_json(force=True) or {}
    STATE["command_count"] += 1

    if cmd == "say":
        text = params.get("text", "")
        if client:
            client.say_text(text)
        return {"message": f'Said: "{text}"'}

    if cmd == "agent_start":
        return _start_agent()
    if cmd == "agent_stop":
        return _stop_agent()
    if cmd == "agent_status":
        return _agent_status()
    if cmd == "memory_stats":
        return _memory_stats()
    if cmd == "memory_context":
        return _memory_context()
    if cmd == "memory_clear":
        return _memory_clear()

    if not client:
        return {"error": "Not connected to Cozmo"}

    try:
        return jsonify(_exec(client, cmd, params))
    except Exception as e:
        return jsonify({"error": str(e)})


@APP.route("/api/llm", methods=["POST"])
def api_llm():
    text = request.get_json(force=True).get("text", "")
    if not STATE["llm_enabled"]:
        return {"error": "LLM not enabled. Run with --llm."}
    try:
        from . import llm as llm_mod
        modifier = ""
        if STATE.get("autonomous_agent"):
            modifier = STATE["autonomous_agent"].emotion_state.modifier() if hasattr(STATE["autonomous_agent"], 'emotion_state') else ""
        response = llm_mod.query_ollama(text, model=STATE["llm_model"], emotion_modifier=modifier)
        return {"response": response}
    except Exception as e:
        return {"error": str(e)}


def _exec(client, cmd, p):
    if cmd == "forward":
        d = float(p.get("distance", 100)); s = float(p.get("speed", 50))
        client.drive_wheels(lwheel_speed=s, rwheel_speed=s, duration=d/s)
        return {"message": f"Forward {d}mm"}
    elif cmd == "backward":
        d = float(p.get("distance", 100)); s = float(p.get("speed", 50))
        client.drive_wheels(lwheel_speed=-s, rwheel_speed=-s, duration=d/s)
        return {"message": f"Backward {d}mm"}
    elif cmd == "left":
        deg = float(p.get("degrees", 90))
        client.drive_wheels(lwheel_speed=-100, rwheel_speed=100, duration=min(abs(deg)/130, 2))
        return {"message": f"Left {deg}°"}
    elif cmd == "right":
        deg = float(p.get("degrees", 90))
        client.drive_wheels(lwheel_speed=100, rwheel_speed=-100, duration=min(abs(deg)/130, 2))
        return {"message": f"Right {deg}°"}
    elif cmd == "dance":
        def dance():
            for _ in range(3):
                client.drive_wheels(100,-100,.3); time.sleep(.1)
                client.drive_wheels(-100,100,.3); time.sleep(.1)
        threading.Thread(target=dance, daemon=True).start()
        return {"message": "Dancing!"}
    elif cmd == "picture":
        try:
            client.camera.start(); time.sleep(1)
            img = client.camera.latest_image
            if img and hasattr(img, 'raw_image'):
                buf = io.BytesIO(); img.raw_image.save(buf, format='JPEG', quality=80)
                b64 = base64.b64encode(buf.getvalue()).decode()
                fname = f"cozmo_{int(time.time())}.jpg"; img.raw_image.save(fname)
                client.camera.stop()
                return {"message": f"Saved: {fname}", "image": b64}
        except Exception as e:
            return {"error": str(e)}
    elif cmd == "camera_toggle":
        STATE["camera_enabled"] = not STATE["camera_enabled"]
        if STATE["camera_enabled"]: client.camera.start()
        else: client.camera.stop()
        return {"message": f"Camera {'on' if STATE['camera_enabled'] else 'off'}"}
    elif cmd == "lift_up":
        client.move_lift(float(p.get("height", 50))/100)
        return {"message": "Lift up"}
    elif cmd == "lift_down":
        client.move_lift(0.0); return {"message": "Lift down"}
    elif cmd == "lift_stop":
        client.move_lift(0.5); return {"message": "Lift stop"}
    elif cmd == "head_up":
        a = float(p.get("angle", 0)); n = max(0, min(1, (a+34.5)/57))
        client.move_head(n); return {"message": f"Head {a}°"}
    elif cmd == "head_down":
        client.move_head(0.0); return {"message": "Head down"}
    elif cmd == "head_stop":
        client.move_head(0.5); return {"message": "Head stop"}
    elif cmd.startswith("light_"):
        color = cmd.replace("light_", "")
        rgb = LIGHT_COLORS.get(color, (255,255,255)) if color != "off" else (0,0,0)
        client.set_all_backpack_lights(pycozmo.lights.Light(pycozmo.lights.Color(*rgb)))
        return {"message": f"Lights: {color}"}
    elif cmd in ("happy","sad","excited","curious","scared","tired"):
        STATE["emotion"] = cmd
        cm = {"happy":(0,255,0),"sad":(0,0,255),"excited":(255,0,0),"curious":(255,255,255),"scared":(255,0,0),"tired":(0,0,128)}
        rgb = cm.get(cmd, (255,255,255))
        client.set_all_backpack_lights(pycozmo.lights.Light(pycozmo.lights.Color(*rgb)))
        return {"message": f"Emotion: {cmd}"}
    elif cmd == "blocks":
        def blocks():
            for _ in range(5):
                client.drive_wheels(40,40,.5); time.sleep(.3)
                client.drive_wheels(-40,-40,.5); time.sleep(.3)
        threading.Thread(target=blocks, daemon=True).start()
        return {"message": "Looking for blocks..."}
    elif cmd == "look":
        def look():
            for a in [30,-60,30,-30]:
                l = 100 if a>0 else -100
                client.drive_wheels(l,-l,min(abs(a)/130,.5)); time.sleep(.2)
        threading.Thread(target=look, daemon=True).start()
        return {"message": "Looking around..."}
    elif cmd == "follow":
        return {"message": "Follow mode: use look/turn to track faces"}
    elif cmd == "charger":
        return {"message": "Charger navigation not available without app"}
    elif cmd == "sleep":
        def sleep(): client.move_lift(0); client.move_head(0)
        threading.Thread(target=sleep, daemon=True).start()
        return {"message": "Goodnight..."}
    elif cmd == "wave":
        def wave():
            for _ in range(3): client.move_lift(.8); time.sleep(.3); client.move_lift(.2); time.sleep(.3)
        threading.Thread(target=wave, daemon=True).start()
        return {"message": "Waving!"}
    return {"error": f"Unknown: {cmd}"}


def _start_agent():
    if STATE["autonomous_agent"] and STATE["autonomous_agent"].is_running():
        return {"message": "Agent already running"}
    try:
        from . import agent as agent_mod
        from .memory import Memory
        from . import emotions
        mem = STATE.get("memory") or Memory()
        STATE["memory"] = mem
        emo = emotions.EmotionState(STATE["client"])
        ag = agent_mod.AutonomousAgent(STATE["client"], emo, mem, interval=15.0, model=STATE["llm_model"])
        ag.start()
        STATE["autonomous_agent"] = ag
        STATE["autonomous_enabled"] = True
        return {"message": "Agent started", "log": "Autonomous agent started"}
    except Exception as e:
        return {"error": str(e)}


def _stop_agent():
    ag = STATE.get("autonomous_agent")
    if ag:
        ag.stop()
        STATE["autonomous_enabled"] = False
        return {"message": "Agent stopped"}
    return {"message": "Agent not running"}


def _agent_status():
    ag = STATE.get("autonomous_agent")
    if ag:
        s = ag.get_status()
        return {"message": json.dumps(s, indent=2), "log": f"Actions: {s['action_count']}, Memory: {s['memory_stats']}"}
    return {"message": "Agent not running"}


def _memory_stats():
    mem = STATE.get("memory")
    if mem:
        stats = mem.get_stats()
        text = "\n".join(f"{k}: {v}" for k,v in stats.items())
        return {"message": text, "memory": text}
    return {"message": "No memory"}


def _memory_context():
    mem = STATE.get("memory")
    if mem:
        ctx = mem.get_context_string()
        return {"message": ctx, "memory": ctx}
    return {"message": "No memory"}


def _memory_clear():
    mem = STATE.get("memory")
    if mem:
        mem.clear()
        return {"message": "Memory cleared", "memory": "Memory cleared"}
    return {"message": "No memory"}


def main():
    parser = argparse.ArgumentParser(description="Cozmo Command Center")
    parser.add_argument("--use-pycozmo", action="store_true", help="Use pycozmo backend")
    parser.add_argument("--llm", action="store_true", help="Enable LLM")
    parser.add_argument("--llm-model", default="phi3", help="LLM model name")
    parser.add_argument("--autonomous", action="store_true", help="Enable autonomous agent")
    parser.add_argument("--port", type=int, default=8080, help="Web server port")
    parser.add_argument("--host", default="0.0.0.0", help="Web server host")
    args = parser.parse_args()

    STATE["llm_enabled"] = args.llm
    STATE["llm_model"] = args.llm_model

    if args.use_pycozmo:
        if not HAS_PYCOZMO:
            print("pycozmo not installed. Run: pip install pycozmo")
            sys.exit(1)
        print("Connecting to Cozmo via pycozmo (direct WiFi)...")
        print("Make sure your PC is connected to Cozmo's WiFi network.")
        client = pycozmo.Client()
        client.start()
        client.connect()
        print("Waiting for robot...")
        try:
            client.wait_for_robot()
        except Exception as e:
            print(f"Could not connect: {e}")
            client.stop()
            sys.exit(1)
        print("Connected!")
        STATE["client"] = client
        STATE["connected"] = True
        try:
            STATE["battery"] = client.battery_voltage
        except Exception:
            pass
    else:
        print("No robot backend. Running in demo mode.")
        print("Use --use-pycozmo to connect to a real robot.")

    if args.autonomous:
        args.llm = True
        STATE["llm_enabled"] = True

    print(f"\nStarting Command Center at http://{args.host}:{args.port}")
    print("Open this URL in your browser.")
    if args.llm:
        print("LLM enabled. Make sure Ollama is running: ollama serve")
    if args.autonomous:
        print("Autonomous agent enabled.")
    print("Press Ctrl+C to stop.\n")

    APP.run(host=args.host, port=args.port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
