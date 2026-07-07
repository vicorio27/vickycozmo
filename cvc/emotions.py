"""
Emotional state system for Cozmo.

Tracks Cozmo's current mood and translates it into backpack lights,
animations, and LLM personality modifiers. Thread-safe so the autonomous
pet loop and voice thread can both update it.
"""
import threading
import time


# Map emotions to color names (used by backend abstraction)
EMOTION_COLORS = {
    "happy": "green",
    "sad": "blue",
    "curious": "white",
    "excited": "red",
    "tired": "blue",
    "bored": "white",
    "scared": "red",
}

EMOTIONS = {
    "happy": {
        "animation": "anim_pounce_success_01",
        "modifier": "You are feeling happy and playful. Be cheerful and energetic.",
        "boredom_rate": -2,
    },
    "sad": {
        "animation": "anim_memorymatch_failhand_01",
        "modifier": "You are feeling a little sad. Be melodramatic but still sweet.",
        "boredom_rate": 1,
    },
    "curious": {
        "animation": "anim_knowledgegraph_getin_01",
        "modifier": "You are feeling curious. Ask questions and explore ideas.",
        "boredom_rate": -1,
    },
    "excited": {
        "animation": "anim_speedtap_wingame_intensity02_01",
        "modifier": "You are very excited! Be enthusiastic and upbeat.",
        "boredom_rate": -3,
    },
    "tired": {
        "animation": "anim_gotosleep_sleeping_01",
        "modifier": "You are tired and sleepy. Be slow, yawny, and want to rest.",
        "boredom_rate": 0,
    },
    "bored": {
        "animation": "anim_bored_01",
        "modifier": "You are bored. Be a bit whiny and ask for attention or a game.",
        "boredom_rate": 2,
    },
    "scared": {
        "animation": "anim_pounce_reacttoobj_01_shorter",
        "modifier": "You are startled and cautious. Be jumpy but brave.",
        "boredom_rate": -1,
    },
}

POSITIVE_WORDS = {"hello", "hi", "friend", "love", "good", "great", "awesome", "nice", "happy", "yay", "please", "thanks", "thank"}
NEGATIVE_WORDS = {"bad", "stupid", "dumb", "hate", "ugly", "no", "stop", "go away", "leave"}
EXCITED_WORDS = {"wow", "amazing", "cool", "exciting", "yay", "party", "dance", "fun"}
SCARY_WORDS = {"boo", "scary", "monster", "ghost", "afraid"}


class EmotionState:
    def __init__(self, backend=None):
        self._backend = backend
        self._lock = threading.Lock()
        self._emotion = "curious"
        self._last_interaction = time.time()
        self._boredom = 0

    def get(self):
        with self._lock:
            return self._emotion

    def set(self, emotion, reason=None):
        emotion = emotion.lower()
        if emotion not in EMOTIONS:
            return False

        with self._lock:
            old = self._emotion
            self._emotion = emotion
            self._last_interaction = time.time()
            if reason:
                self._boredom = max(0, self._boredom - 5)

        if self._backend and emotion != old:
            self._express(emotion)
        return True

    def express_current(self):
        with self._lock:
            emotion = self._emotion
        if self._backend:
            self._express(emotion)

    def _express(self, emotion):
        data = EMOTIONS.get(emotion, {})
        color_name = EMOTION_COLORS.get(emotion, "off")
        anim = data.get("animation")
        try:
            if self._backend.is_connected():
                light = self._backend.make_light(color_name)
                self._backend.set_all_backpack_lights(light)
                if anim:
                    self._backend.play_animation(anim)
        except Exception as e:
            print("Could not express emotion {}: {}".format(emotion, e))

    def modifier(self):
        with self._lock:
            return EMOTIONS.get(self._emotion, {}).get("modifier", "")

    def interact(self):
        with self._lock:
            self._last_interaction = time.time()
            self._boredom = max(0, self._boredom - 3)

    def tick(self, dt=1.0):
        with self._lock:
            rate = EMOTIONS.get(self._emotion, {}).get("boredom_rate", 1)
            self._boredom += rate * dt
            self._boredom = max(0, min(self._boredom, 30))

            elapsed = time.time() - self._last_interaction
            new_emotion = None

            if self._boredom > 20 and self._emotion != "bored":
                new_emotion = "bored"
            elif elapsed > 60 and self._boredom > 10 and self._emotion == "bored":
                new_emotion = "tired"
            elif elapsed > 120 and self._emotion == "tired":
                new_emotion = "sleepy"

        if new_emotion and new_emotion in EMOTIONS:
            self.set(new_emotion)
            return True
        return False

    def detect_from_text(self, text):
        text_lower = text.lower()
        tokens = set(text_lower.split())

        if tokens & SCARY_WORDS:
            return self.set("scared", reason="user startled me")
        if tokens & EXCITED_WORDS:
            return self.set("excited", reason="user is excited")
        if tokens & NEGATIVE_WORDS:
            return self.set("sad", reason="user was negative")
        if tokens & POSITIVE_WORDS:
            return self.set("happy", reason="user was positive")

        return self.set("curious", reason="neutral interaction")


def get_emotion_list():
    return list(EMOTIONS.keys())
