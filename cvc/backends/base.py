"""
Abstract base class for robot backends.

All methods that interact with the Cozmo robot hardware must be implemented
by concrete backends (Anki SDK, pycozmo, etc.).
"""
import abc


class RobotBackend(abc.ABC):
    """Abstract interface for controlling a Cozmo robot."""

    @abc.abstractmethod
    def start(self):
        """Start the backend and connect to the robot.
        Returns True if successful."""
        pass

    @abc.abstractmethod
    def stop(self):
        """Disconnect and clean up."""
        pass

    @abc.abstractmethod
    def is_connected(self):
        """Return True if a robot is connected."""
        pass

    # --- Drive ---

    @abc.abstractmethod
    def drive_straight(self, distance_mm, speed_mmps, should_play_anim=False):
        """Drive forward/backward. Negative distance = backward."""
        pass

    @abc.abstractmethod
    def turn_in_place(self, angle_degrees):
        """Turn left (positive) or right (negative) in degrees."""
        pass

    @abc.abstractmethod
    def turn_towards_face(self, face):
        """Turn towards an observed face object."""
        pass

    @abc.abstractmethod
    def go_to_pose(self, pose):
        """Navigate to a pose object."""
        pass

    @abc.abstractmethod
    def drive_wheels(self, left_speed, right_speed, duration=0):
        """Direct wheel control."""
        pass

    @abc.abstractmethod
    def drive_off_charger(self):
        """Drive off the charger contacts."""
        pass

    # --- Lift / Head ---

    @abc.abstractmethod
    def move_lift(self, height):
        """Move lift to height (range depends on backend)."""
        pass

    @abc.abstractmethod
    def set_lift_height(self, height_normalized):
        """Set lift height (0.0 to 1.0)."""
        pass

    @abc.abstractmethod
    def set_head_angle(self, angle_degrees):
        """Set head angle in degrees."""
        pass

    @abc.abstractmethod
    def get_max_head_angle(self):
        """Return the maximum head angle in degrees."""
        pass

    # --- Speech ---

    @abc.abstractmethod
    def say_text(self, text):
        """Speak text aloud. Blocks until done."""
        pass

    # --- Animations ---

    @abc.abstractmethod
    def play_animation(self, anim_name):
        """Play a named animation. Blocks until done."""
        pass

    @abc.abstractmethod
    def play_animation_trigger(self, trigger):
        """Play an animation trigger. Blocks until done."""
        pass

    # --- Behaviors ---

    @abc.abstractmethod
    def start_behavior(self, behavior_name):
        """Start a named behavior. Returns behavior handle."""
        pass

    @abc.abstractmethod
    def run_timed_behavior(self, behavior_name, active_time_seconds):
        """Run a behavior for a fixed duration."""
        pass

    # --- Lights ---

    @abc.abstractmethod
    def set_all_backpack_lights(self, color):
        """Set all backpack LEDs to a color."""
        pass

    @abc.abstractmethod
    def set_lights_off(self):
        """Turn off all backpack lights."""
        pass

    @abc.abstractmethod
    def make_light(self, color):
        """Create a light object from a color string (green, blue, red, white, off)."""
        pass

    @abc.abstractmethod
    def make_flash_light(self, color):
        """Create a flashing light object."""
        pass

    # --- World / Perception ---

    @abc.abstractmethod
    def wait_for_observed_face(self, timeout=30):
        """Wait for a face to be observed. Returns face object or None."""
        pass

    @abc.abstractmethod
    def wait_for_observed_charger(self, timeout=30):
        """Wait for the charger to be observed. Returns charger object or None."""
        pass

    @abc.abstractmethod
    def wait_until_observe_num_objects(self, num, object_type, timeout=30):
        """Wait until num objects of given type are observed."""
        pass

    @abc.abstractmethod
    def observe_faces(self):
        """Return list of currently observed faces."""
        pass

    @abc.abstractmethod
    def observe_objects(self):
        """Return list of currently observed objects."""
        pass

    # --- Camera ---

    @abc.abstractmethod
    def set_camera_enabled(self, enabled):
        """Enable or disable the camera image stream."""
        pass

    @abc.abstractmethod
    def get_latest_image(self):
        """Return the latest camera image, or None."""
        pass

    # --- State ---

    @abc.abstractmethod
    def is_on_charger(self):
        """Return True if robot is on the charger."""
        pass

    @abc.abstractmethod
    def get_battery_voltage(self):
        """Return battery voltage as float."""
        pass

    @abc.abstractmethod
    def get_pose_origin_id(self):
        """Return the robot's pose origin ID."""
        pass

    # --- Convenience helpers ---

    def wait_for_completed(self, action):
        """Wait for an action to complete. Default: call .wait_for_completed() if available."""
        if hasattr(action, 'wait_for_completed'):
            action.wait_for_completed()
