"""
Backend implementation using the official Anki Cozmo SDK.
Requires Python 3.6 and the Cozmo app running on a mobile device.
"""
import cozmo
from cozmo.util import distance_mm, speed_mmps, degrees

from .base import RobotBackend


# Map behavior name strings to cozmo behavior types
BEHAVIORS = {
    "LookAroundInPlace": cozmo.behavior.BehaviorTypes.LookAroundInPlace,
    "FindFaces": cozmo.behavior.BehaviorTypes.FindFaces,
    "RollBlock": cozmo.behavior.BehaviorTypes.RollBlock,
    "StackBlocks": cozmo.behavior.BehaviorTypes.StackBlocks,
}

# Map animation trigger name strings to cozmo triggers
ANIM_TRIGGERS = {
    "MajorFail": cozmo.anim.Triggers.MajorFail,
    "LookInPlaceForFacesBodyPause": cozmo.anim.Triggers.LookInPlaceForFacesBodyPause,
}

# Map color name strings to cozmo light objects
LIGHT_COLORS = {
    "green": cozmo.lights.green_light,
    "blue": cozmo.lights.blue_light,
    "red": cozmo.lights.red_light,
    "white": cozmo.lights.white_light,
    "off": cozmo.lights.off_light,
}


class AnkiBackend(RobotBackend):
    """Cozmo backend using the official Anki SDK."""

    def __init__(self, robot=None):
        self._robot = robot
        self._connected = False

    def start(self):
        """Run cozmo.run_program with our _run method. This blocks."""
        cozmo.robot.Robot.drive_off_charger_on_connect = False
        cozmo.run_program(self._on_connect)

    def _on_connect(self, robot):
        """Called by the SDK when the robot connects."""
        self._robot = robot
        self._connected = True

    def _on_connect_standalone(self, robot):
        """For standalone testing without the main loop."""
        self._robot = robot
        self._connected = True
        self._run_func(robot)

    def stop(self):
        self._connected = False

    def is_connected(self):
        return self._connected and self._robot is not None

    def _r(self):
        """Return the raw cozmo robot object."""
        return self._robot

    # --- Drive ---

    def drive_straight(self, distance_mm, speed_mmps, should_play_anim=False):
        action = self._r().drive_straight(
            distance_mm(distance_mm), speed_mmps(speed_mmps),
            should_play_anim=should_play_anim
        )
        action.wait_for_completed()

    def turn_in_place(self, angle_degrees):
        action = self._r().turn_in_place(degrees(angle_degrees))
        action.wait_for_completed()

    def turn_towards_face(self, face):
        action = self._r().turn_towards_face(face)
        action.wait_for_completed()

    def go_to_pose(self, pose):
        action = self._r().go_to_pose(pose)
        action.wait_for_completed()

    def drive_wheels(self, left_speed, right_speed, duration=0):
        self._r().drive_wheels(left_speed, right_speed, duration=duration)

    def drive_off_charger(self):
        self._r().drive_off_charger_contacts().wait_for_completed()

    # --- Lift / Head ---

    def move_lift(self, height):
        self._r().move_lift(height)

    def set_lift_height(self, height_normalized):
        self._r().set_lift_height(height=height_normalized).wait_for_completed()

    def set_head_angle(self, angle_degrees):
        action = self._r().set_head_angle(degrees(angle_degrees))
        action.wait_for_completed()

    def get_max_head_angle(self):
        return cozmo.robot.MAX_HEAD_ANGLE.degrees

    # --- Speech ---

    def say_text(self, text):
        self._r().say_text(text).wait_for_completed()

    # --- Animations ---

    def play_animation(self, anim_name):
        self._r().play_anim(anim_name).wait_for_completed()

    def play_animation_trigger(self, trigger_name):
        trigger = ANIM_TRIGGERS.get(trigger_name)
        if trigger:
            self._r().play_anim_trigger(trigger).wait_for_completed()

    # --- Behaviors ---

    def start_behavior(self, behavior_name):
        behavior = BEHAVIORS.get(behavior_name)
        if behavior:
            return self._r().start_behavior(behavior)
        return None

    def run_timed_behavior(self, behavior_name, active_time_seconds):
        behavior = BEHAVIORS.get(behavior_name)
        if behavior:
            self._r().run_timed_behavior(behavior, active_time=active_time_seconds)

    # --- Lights ---

    def set_all_backpack_lights(self, color):
        if isinstance(color, str):
            light = LIGHT_COLORS.get(color, LIGHT_COLORS["off"])
        else:
            light = color
        self._r().set_all_backpack_lights(light)

    def set_lights_off(self):
        self._r().set_all_backpack_lights(cozmo.lights.off_light)

    def make_light(self, color):
        return LIGHT_COLORS.get(color, LIGHT_COLORS["off"])

    def make_flash_light(self, color):
        light = LIGHT_COLORS.get(color, LIGHT_COLORS["green"])
        return light.flash()

    # --- World / Perception ---

    def wait_for_observed_face(self, timeout=30):
        try:
            return self._r().world.wait_for_observed_face(timeout=timeout)
        except Exception:
            return None

    def wait_for_observed_charger(self, timeout=30):
        try:
            return self._r().world.wait_for_observed_charger(timeout=timeout)
        except Exception:
            return None

    def wait_until_observe_num_objects(self, num, object_type, timeout=30):
        try:
            return self._r().world.wait_until_observe_num_objects(
                num=num, object_type=cozmo.objects.LightCube, timeout=timeout
            )
        except Exception:
            return []

    def observe_faces(self):
        try:
            return self._r().world.observed_faces
        except Exception:
            return []

    def observe_objects(self):
        try:
            return list(self._r().world.visible_objects)
        except Exception:
            return []

    # --- Camera ---

    def set_camera_enabled(self, enabled):
        self._r().camera.image_stream_enabled = enabled

    def get_latest_image(self):
        return self._r().world.latest_image

    # --- State ---

    def is_on_charger(self):
        return self._r().is_on_charger

    def get_battery_voltage(self):
        return self._r().battery_voltage

    def get_pose_origin_id(self):
        return self._r().pose.origin_id

    # --- Extra: get raw robot for direct SDK access ---

    def get_raw_robot(self):
        """Return the underlying cozmo.robot.Robot for direct SDK calls."""
        return self._r()
