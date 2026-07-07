"""
Backend implementation using pycozmo (direct WiFi connection, no mobile app).

pycozmo connects directly to Cozmo over WiFi. No mobile app needed.
However, some high-level SDK features (behaviors, face detection, charger
navigation) are not available and are replaced with simplified implementations.

Limitations vs the official SDK:
- No high-level behaviors (FindFaces, LookAroundInPlace, RollBlock, StackBlocks)
  → Implemented as series of turns and waits
- Limited face detection
- No charger detection/navigation
- Some animations may not be available
"""
import time
import math
import threading

from .base import RobotBackend

try:
    import pycozmo
    HAS_PYCOZMO = True
except ImportError:
    HAS_PYCOZMO = False


LIGHT_COLORS = {
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "red": (255, 0, 0),
    "white": (255, 255, 255),
    "off": (0, 0, 0),
}


class Face(object):
    """Simple face-like object for compatibility with voice_commands."""
    def __init__(self, x=0, y=0, is_visible=True):
        self.x = x
        self.y = y
        self.is_visible = is_visible
        self.name = "unknown"
        self.expression = "neutral"
        self._update_id = 0


class LookAroundBehavior(object):
    """Mimics cozmo LookAroundInPlace with a series of turns."""
    def __init__(self, client, stop_event):
        self._client = client
        self._stop_event = stop_event
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        import random
        while not self._stop_event.is_set():
            angle = random.randint(20, 90)
            left = 100.0
            right = -100.0
            duration = abs(angle) / 130.0
            self._client.drive_wheels(
                lwheel_speed=left, rwheel_speed=right,
                duration=min(duration, 0.5)
            )
            self._stop_event.wait(0.3)

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=2)
        try:
            self._client.drive_wheels(
                lwheel_speed=0.0, rwheel_speed=0.0, duration=0.1
            )
        except Exception:
            pass


class PyCozmoBackend(RobotBackend):
    """Cozmo backend using pycozmo for direct WiFi connection."""

    def __init__(self):
        if not HAS_PYCOZMO:
            raise ImportError("pycozmo is not installed. Run: pip install pycozmo")
        self._client = None
        self._connected = False
        self._robot = None
        self._active_behaviors = []

    def start(self):
        """Connect to Cozmo over WiFi and block until connected."""
        self._client = pycozmo.Client()
        self._client.start()
        self._client.connect()
        self._client.wait_for_robot()
        self._connected = True
        self._robot = self._client

    def stop(self):
        for b in self._active_behaviors:
            try:
                b.stop()
            except Exception:
                pass
        self._active_behaviors = []
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
            try:
                self._client.stop()
            except Exception:
                pass
        self._connected = False

    def is_connected(self):
        return self._connected and self._robot is not None

    # --- Drive ---

    def drive_straight(self, distance_mm, speed_mmps, should_play_anim=False):
        """Drive forward/backward."""
        if speed_mmps == 0:
            return
        duration = abs(distance_mm) / abs(speed_mmps)
        duration = max(0.1, min(duration, 5.0))
        speed = abs(speed_mmps) if distance_mm >= 0 else -abs(speed_mmps)
        self._robot.drive_wheels(
            lwheel_speed=float(speed),
            rwheel_speed=float(speed),
            duration=float(duration)
        )
        time.sleep(duration)

    def turn_in_place(self, angle_degrees):
        """Turn by rotating wheels in opposite directions."""
        speed = 100.0
        duration = abs(angle_degrees) / 130.0
        duration = max(0.1, min(duration, 2.0))
        left = speed if angle_degrees > 0 else -speed
        right = -left
        self._robot.drive_wheels(
            lwheel_speed=left,
            rwheel_speed=right,
            duration=float(duration)
        )
        time.sleep(duration + 0.1)

    def turn_towards_face(self, face):
        """Turn towards a face object."""
        if hasattr(face, 'x') and face.x != 0:
            # pycozmo face coordinates: x is -1.0 (left) to 1.0 (right)
            angle = face.x * -45
            self.turn_in_place(angle)
        else:
            self.turn_in_place(15)

    def go_to_pose(self, pose):
        """Not directly supported. Drive forward as fallback."""
        self.drive_straight(200, 80)

    def drive_wheels(self, left_speed, right_speed, duration=0):
        self._robot.drive_wheels(
            lwheel_speed=float(left_speed),
            rwheel_speed=float(right_speed),
            duration=float(duration)
        )

    def drive_off_charger(self):
        """Drive backward to leave charger."""
        self.drive_straight(-150, 80)

    # --- Lift / Head ---

    def move_lift(self, height):
        """Move lift. pycozmo uses 0-1 range."""
        normalized = max(0.0, min(1.0, (height + 8.0) / 16.0))
        self._robot.move_lift(normalized)

    def set_lift_height(self, height_normalized):
        self._robot.move_lift(float(height_normalized))

    def set_head_angle(self, angle_degrees):
        """Set head angle. pycozmo uses 0-1 range."""
        normalized = (angle_degrees + 34.5) / 57.0
        normalized = max(0.0, min(1.0, normalized))
        self._robot.move_head(normalized)

    def get_max_head_angle(self):
        return 22.5

    # --- Speech ---

    def say_text(self, text):
        """Speak text. pycozmo blocks until speech is queued."""
        self._robot.say_text(text)
        # Approximate speech duration: 0.08s per character
        duration = max(1.0, len(text) * 0.08)
        time.sleep(duration)

    # --- Animations ---

    def play_animation(self, anim_name):
        """Play a named animation."""
        try:
            self._robot.play_anim(anim_name)
            time.sleep(2)
        except Exception:
            # Some animations may not be available in pycozmo
            time.sleep(1)

    def play_animation_trigger(self, trigger_name):
        """Animation triggers are not directly available. Fallback."""
        time.sleep(1)

    # --- Behaviors ---

    def start_behavior(self, behavior_name):
        """Implement behaviors using lower-level commands."""
        if behavior_name == "LookAroundInPlace":
            stop_event = threading.Event()
            behavior = LookAroundBehavior(self._robot, stop_event)
            self._active_behaviors.append(behavior)
            return behavior
        elif behavior_name == "FindFaces":
            # Look around for faces: turn left and right
            stop_event = threading.Event()
            behavior = LookAroundBehavior(self._robot, stop_event)
            self._active_behaviors.append(behavior)
            return behavior
        return None

    def run_timed_behavior(self, behavior_name, active_time_seconds):
        """Run a behavior for a fixed duration."""
        if behavior_name == "LookAroundInPlace" or behavior_name == "FindFaces":
            start = time.time()
            while time.time() - start < active_time_seconds:
                self.turn_in_place(30)
                time.sleep(0.3)
        elif behavior_name == "RollBlock":
            # Simple block interaction: nudge forward
            for _ in range(min(3, int(active_time_seconds / 20))):
                self.drive_straight(100, 50)
                time.sleep(1)
        elif behavior_name == "StackBlocks":
            # Simple stack attempt: drive forward and lift
            self.drive_straight(80, 40)
            self.move_lift(5)
            time.sleep(1)
            self.move_lift(-5)
        else:
            time.sleep(active_time_seconds)

    # --- Lights ---

    def set_all_backpack_lights(self, color):
        if isinstance(color, str):
            rgb = LIGHT_COLORS.get(color, LIGHT_COLORS["off"])
        elif isinstance(color, tuple):
            rgb = color
        elif hasattr(color, 'color'):
            # It's a pycozmo light object, pass directly
            self._robot.set_all_backpack_lights(color)
            return
        else:
            rgb = LIGHT_COLORS["off"]
        light = pycozmo.lights.Light(
            pycozmo.lights.Color(rgb[0], rgb[1], rgb[2])
        )
        self._robot.set_all_backpack_lights(light)

    def set_lights_off(self):
        self._robot.set_all_backpack_lights(
            pycozmo.lights.Light(pycozmo.lights.Color(0, 0, 0))
        )

    def make_light(self, color):
        """Create a light object from a color name."""
        rgb = LIGHT_COLORS.get(color, LIGHT_COLORS["off"])
        return pycozmo.lights.Light(pycozmo.lights.Color(*rgb))

    def make_flash_light(self, color):
        """Create a flashing light object."""
        rgb = LIGHT_COLORS.get(color, LIGHT_COLORS["green"])
        return pycozmo.lights.Light(
            pycozmo.lights.Color(*rgb),
            rate=1.0
        )

    # --- World / Perception ---

    def wait_for_observed_face(self, timeout=30):
        """Wait for a face. pycozmo has limited face detection."""
        start = time.time()
        while time.time() - start < timeout:
            # pycozmo can detect faces but returns them as simple objects
            try:
                if hasattr(self._robot, 'observed_faces'):
                    faces = self._robot.observed_faces
                    if faces:
                        return faces[0]
            except Exception:
                pass
            time.sleep(0.5)
        return None

    def wait_for_observed_charger(self, timeout=30):
        """Charger detection is not available in pycozmo."""
        time.sleep(min(timeout, 5))
        return None

    def wait_until_observe_num_objects(self, num, object_type, timeout=30):
        """Observe objects. pycozmo has limited object detection."""
        return []

    def observe_faces(self):
        """Return list of observed faces."""
        try:
            if hasattr(self._robot, 'observed_faces'):
                return list(self._robot.observed_faces)
        except Exception:
            pass
        return []

    def observe_objects(self):
        """Return list of observed objects."""
        return []

    # --- Camera ---

    def set_camera_enabled(self, enabled):
        """Enable/disable camera stream."""
        try:
            if enabled:
                self._robot.camera.start()
            else:
                self._robot.camera.stop()
        except Exception:
            pass

    def get_latest_image(self):
        """Get the latest camera image."""
        try:
            if hasattr(self._robot, 'camera') and self._robot.camera:
                return self._robot.camera.latest_image
        except Exception:
            pass
        return None

    # --- State ---

    def is_on_charger(self):
        """Cannot reliably detect without app."""
        return False

    def get_battery_voltage(self):
        """Get battery voltage if available."""
        try:
            if hasattr(self._robot, 'battery_voltage'):
                return self._robot.battery_voltage
        except Exception:
            pass
        return 3.7

    def get_pose_origin_id(self):
        return 0

    # --- Extra ---

    def get_raw_client(self):
        """Return the underlying pycozmo.Client for direct access."""
        return self._client
