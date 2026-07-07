"""
Autonomous pet mode for Cozmo.

Runs in a background thread and lets Cozmo act on his own based on his
current emotional state and boredom level.
"""
import threading
import time
import random

from termcolor import cprint


class PetMode(threading.Thread):
    """Background thread that drives autonomous behavior."""

    def __init__(self, robot, emotion_state, vc, interval=5.0):
        super(PetMode, self).__init__(daemon=True)
        self.robot = robot
        self.emotion_state = emotion_state
        self.vc = vc
        self.interval = interval
        self._running = True
        self._lock = threading.Lock()

    def stop(self):
        with self._lock:
            self._running = False

    def is_running(self):
        with self._lock:
            return self._running

    def run(self):
        cprint("Autonomous pet mode started", "cyan")
        while self.is_running():
            time.sleep(self.interval)
            if not self.is_running():
                break

            if self.emotion_state is None:
                continue

            # Advance emotional state (boredom, tiredness, etc.)
            changed = self.emotion_state.tick(self.interval)
            if changed and self.robot:
                self.emotion_state.express_current()

            emotion = self.emotion_state.get()
            if self.robot:
                self._behave(emotion)
            else:
                self._debug_behave(emotion)

    def _behave(self, emotion):
        """Pick and execute an action based on mood."""
        action = self._choose_action(emotion)
        if action is None:
            return

        name, args = action
        try:
            getattr(self.vc, name)(self.robot, args)
        except Exception as e:
            if self.vc and self.vc.log:
                print("Pet mode action {} failed: {}".format(name, e))

    def _debug_behave(self, emotion):
        """Print what the robot would do when running without hardware."""
        action = self._choose_action(emotion)
        if action:
            cprint("[PET MODE] feeling {}, would execute: {} {}".format(
                emotion, action[0], action[1]), "cyan")

    def _choose_action(self, emotion):
        """Return a tuple (method_name, args_list) or None."""
        if emotion == "bored":
            # Try to get attention
            return random.choice([
                ("dance", []),
                ("look", []),
                ("say", ["somebody", "play", "with", "me"]),
            ])

        if emotion == "tired":
            # Low energy movement
            return random.choice([
                ("head", ["0"]),
                ("lift", ["0"]),
                None,
            ])

        if emotion == "happy":
            return random.choice([
                ("dance", []),
                ("say", ["i", "am", "happy"]),
                None,
            ])

        if emotion == "excited":
            return random.choice([
                ("dance", []),
                ("forward", ["2"]),
                ("say", ["yahoo"]),
            ])

        if emotion == "curious":
            return random.choice([
                ("look", []),
                ("blocks", []),
                None,
            ])

        if emotion == "sad":
            return random.choice([
                ("say", ["i", "am", "sad"]),
                ("head", ["10"]),
                None,
            ])

        if emotion == "scared":
            return random.choice([
                ("backward", ["1"]),
                None,
            ])

        return None
