"""
Autonomous agent for Cozmo.

Runs a continuous loop:
1. OBSERVE - check camera, faces, objects, battery, mood
2. THINK - use LLM to decide what to do based on context + memory
3. ACT - execute the chosen action
4. REMEMBER - store the experience
5. LEARN - analyze outcome and update behavior
"""
import time
import threading
import json
import random

from termcolor import cprint

from . import llm
from .memory import Memory


AGENT_SYSTEM_PROMPT = """You are Cozmo's autonomous brain. You observe the world and decide what to do.

You have these capabilities:
- Drive forward/backward/turn
- Lift arm up/down
- Tilt head up/down
- Say things
- Take pictures
- Dance
- Look around for faces or objects
- Play with blocks
- Express emotions through lights

RULES:
1. Be curious and playful. Explore your environment.
2. If you see a person, greet them or interact.
3. If you're bored, do something fun (dance, look around).
4. If you're tired, rest.
5. Keep actions short and varied. Don't repeat the same thing.
6. Learn from what works and what doesn't.

You must respond with EXACTLY one JSON object:
{
    "action": "action_name",
    "params": {},
    "speech": "optional thing to say",
    "reasoning": "why you chose this"
}

Available actions:
- drive_forward: move forward (params: distance, speed)
- drive_backward: move backward (params: distance, speed)
- turn_left: turn left (params: degrees)
- turn_right: turn right (params: degrees)
- lift_up: raise arm (params: height 0-100)
- lift_down: lower arm
- head_up: tilt head up (params: angle -34 to 22)
- head_down: tilt head down
- say: speak text (params: text)
- dance: do a dance
- look: look around for faces/objects
- take_picture: take a photo
- wave: wave arm
- light: change backpack lights (params: color)
- idle: do nothing for now

Current mood: {mood}
Memory context:
{memory_context}
"""


class AutonomousAgent(threading.Thread):
    """Background thread that runs the autonomous agent loop."""

    def __init__(self, backend, emotion_state, memory=None, interval=15.0, model=llm.DEFAULT_MODEL):
        super(AutonomousAgent, self).__init__(daemon=True)
        self.backend = backend
        self.emotion_state = emotion_state
        self.memory = memory or Memory()
        self.interval = interval
        self.model = model
        self._running = True
        self._lock = threading.Lock()
        self._action_count = 0
        self._last_actions = []

    def stop(self):
        with self._lock:
            self._running = False

    def is_running(self):
        with self._lock:
            return self._running

    def run(self):
        cprint("Autonomous agent started", "cyan")
        while self.is_running():
            time.sleep(self.interval)
            if not self.is_running():
                break
            try:
                self._cycle()
            except Exception as e:
                cprint(f"Agent cycle error: {e}", "red")

    def _cycle(self):
        """One observe-think-act-remember cycle."""
        # 1. OBSERVE
        situation = self._observe()

        # 2. THINK
        decision = self._think(situation)

        if decision is None:
            return

        # 3. ACT
        success = self._act(decision)

        # 4. REMEMBER
        self._remember(situation, decision, success)

        # 5. LEARN (simplified: just update action history)
        self._learn(decision, success)

        self._action_count += 1

    def _observe(self):
        """Gather information about the current state."""
        parts = []

        # Battery
        try:
            voltage = self.backend.get_battery_voltage()
            parts.append(f"Battery: {voltage:.1f}V")
            if voltage < 3.5:
                parts.append("WARNING: Low battery!")
        except Exception:
            parts.append("Battery: unknown")

        # Mood
        emotion = self.emotion_state.get()
        parts.append(f"Mood: {emotion}")

        # Faces
        try:
            faces = self.backend.observe_faces()
            if faces:
                parts.append(f"Faces visible: {len(faces)}")
            else:
                parts.append("No faces visible")
        except Exception:
            parts.append("Face detection: unavailable")

        # Objects
        try:
            objects = self.backend.observe_objects()
            if objects:
                parts.append(f"Objects visible: {len(objects)}")
            else:
                parts.append("No objects visible")
        except Exception:
            parts.append("Object detection: unavailable")

        # Recent action context
        if self._last_actions:
            recent = self._last_actions[-3:]
            parts.append("Recent actions: " + ", ".join(a["action"] for a in recent))

        # Memory context
        memory_ctx = self.memory.get_context_string()
        if memory_ctx:
            parts.append(f"Memory:\n{memory_ctx}")

        return "\n".join(parts)

    def _think(self, situation):
        """Use LLM to decide what to do."""
        mood = self.emotion_state.get()
        memory_ctx = self.memory.get_context_string()

        prompt = AGENT_SYSTEM_PROMPT.format(
            mood=mood,
            memory_context=memory_ctx
        ) + "\n\nCurrent situation:\n" + situation

        try:
            response = llm.query_ollama(
                prompt,
                model=self.model,
                timeout=60,
                emotion_modifier=self.emotion_state.modifier()
            )

            # Try to parse JSON from response
            response = response.strip()
            # Find JSON in response (might have extra text)
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                decision = json.loads(json_str)
                if "action" in decision:
                    return decision

            # Fallback: random action
            return self._random_decision()

        except Exception as e:
            cprint(f"LLM decision error: {e}", "red")
            return self._random_decision()

    def _random_decision(self):
        """Fallback random decision when LLM fails."""
        actions = [
            {"action": "look", "params": {}, "speech": "", "reasoning": "exploring"},
            {"action": "dance", "params": {}, "speech": "", "reasoning": "having fun"},
            {"action": "turn_left", "params": {"degrees": 30}, "speech": "", "reasoning": "looking around"},
            {"action": "turn_right", "params": {"degrees": 30}, "speech": "", "reasoning": "looking around"},
            {"action": "wave", "params": {}, "speech": "", "reasoning": "being friendly"},
            {"action": "idle", "params": {}, "speech": "", "reasoning": "resting"},
        ]
        return random.choice(actions)

    def _act(self, decision):
        """Execute the chosen action."""
        action = decision.get("action", "idle")
        params = decision.get("params", {})
        speech = decision.get("speech", "")

        # Say something if specified
        if speech:
            try:
                self.backend.say_text(speech)
            except Exception:
                pass

        # Execute action
        success = True
        try:
            if action == "drive_forward":
                dist = params.get("distance", 100)
                speed = params.get("speed", 50)
                self.backend.drive_straight(dist, speed)

            elif action == "drive_backward":
                dist = params.get("distance", 100)
                speed = params.get("speed", 50)
                self.backend.drive_straight(-dist, speed)

            elif action == "turn_left":
                deg = params.get("degrees", 45)
                self.backend.turn_in_place(deg)

            elif action == "turn_right":
                deg = params.get("degrees", 45)
                self.backend.turn_in_place(-deg)

            elif action == "lift_up":
                h = params.get("height", 50)
                self.backend.set_lift_height(h / 100.0)

            elif action == "lift_down":
                self.backend.set_lift_height(0.0)

            elif action == "head_up":
                a = params.get("angle", 15)
                self.backend.set_head_angle(a)

            elif action == "head_down":
                self.backend.set_head_angle(-10)

            elif action == "say":
                text = params.get("text", "Hello!")
                self.backend.say_text(text)

            elif action == "dance":
                self._do_dance()

            elif action == "look":
                self._do_look_around()

            elif action == "take_picture":
                self.backend.set_camera_enabled(True)
                time.sleep(1)
                self.backend.get_latest_image()
                self.backend.set_camera_enabled(False)

            elif action == "wave":
                self._do_wave()

            elif action == "light":
                color = params.get("color", "green")
                self.backend.set_all_backpack_lights(color)

            elif action == "idle":
                time.sleep(2)

            else:
                success = False

        except Exception as e:
            cprint(f"Action {action} failed: {e}", "red")
            success = False

        return success

    def _do_dance(self):
        """Perform a dance sequence."""
        for _ in range(2):
            self.backend.drive_wheels(100, -100, 0.3)
            time.sleep(0.1)
            self.backend.drive_wheels(-100, 100, 0.3)
            time.sleep(0.1)
        self.backend.drive_wheels(50, 50, 0.3)
        time.sleep(0.5)

    def _do_look_around(self):
        """Look around by turning."""
        for angle in [30, -60, 30, -30]:
            self.backend.turn_in_place(angle)
            time.sleep(0.3)

    def _do_wave(self):
        """Wave arm up and down."""
        for _ in range(3):
            self.backend.set_lift_height(0.8)
            time.sleep(0.3)
            self.backend.set_lift_height(0.2)
            time.sleep(0.3)

    def _remember(self, situation, decision, success):
        """Store the experience in memory."""
        self.memory.store_interaction(
            situation=situation,
            action=decision.get("action", "unknown"),
            result=f"Success={success}, speech={decision.get('speech', '')}",
            success=success,
            emotion=self.emotion_state.get(),
            context=decision
        )

    def _learn(self, decision, success):
        """Simple learning: track action success rates."""
        action = decision.get("action", "unknown")
        self.memory.store_skill(action)

        # Update last actions
        self._last_actions.append({
            "action": action,
            "success": success,
            "time": time.time()
        })
        if len(self._last_actions) > 10:
            self._last_actions = self._last_actions[-10:]

        # If action failed multiple times, store a lesson
        recent_fails = sum(1 for a in self._last_actions[-5:] if a["action"] == action and not a["success"])
        if recent_fails >= 2:
            self.memory.store_lesson(
                situation="general",
                action=action,
                outcome="failed repeatedly",
                lesson=f"Action {action} keeps failing. Try something different.",
                weight=0.5
            )

    def get_status(self):
        """Return current agent status."""
        return {
            "running": self.is_running(),
            "action_count": self._action_count,
            "recent_actions": self._last_actions[-5:],
            "memory_stats": self.memory.get_stats(),
        }
