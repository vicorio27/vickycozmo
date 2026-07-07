'''
##Customization
You can add as many new commands as you like:
just prefix their function names with the language they are spoken in, *i.e. "it_" for italian, "en_" for english, so for instance you'll create the method "en_smile()" and the voice command you'll have to say will be "smile"*.
Some commands support one argument, for example: if you say *"drive for 10 seconds"*, 10 will be passed to the method *"en_drive"*, any other words will be ignored.
'''
import asyncio
import time
from threading import Timer

from termcolor import colored, cprint

speed = 80
words_to_numbers = ['one', 'uno', 'i', 'un']

def extract_float(cmd_args, index=0):
    if len(cmd_args) > index:
        try:
            float_val = float(cmd_args[index])
            return float_val
        except ValueError:
            pass
    return None


def extract_next_float(cmd_args, index=0):
    for i in range(index, len(cmd_args)):
        try:
            float_val = float(cmd_args[i])
            return float_val
        except ValueError:
            if "zero" in cmd_args:
                return 0
            if len(set(cmd_args).intersection(words_to_numbers)) != 0:
                return 1
    return None


class VoiceCommands():

    def __init__(self, backend, log=False):
        self.backend = backend
        self.lang_data = None
        self.log = log
        self.emotion_state = None

    def set_emotion_state(self, emotion_state):
        self.emotion_state = emotion_state

    ##### NOT A VOICE COMMAND FOR NOW #####
    def check_charger(self, distance=150, spd=100):
        if self.backend.is_on_charger():
            if self.log:
                print("I am on the charger. Driving off the charger...")
            self.backend.drive_off_charger()
            self.backend.drive_straight(distance, spd)
            self.backend.move_lift(-8)

    ###### BLOCKS ######
    def blocks(self, robot=None, cmd_args=None):

        print("looking for my blocks for 1 minute...")
        lookaround = self.backend.start_behavior("LookAroundInPlace")

        cubes = self.backend.wait_until_observe_num_objects(3, "LightCube", timeout=60)

        print("found %s cube(s)" % len(cubes))

        if lookaround:
            lookaround.stop()

        for cube in cubes:
            if hasattr(cube, 'set_lights'):
                cube.set_lights(self.backend.make_flash_light("green"))

        Timer(5, self._turn_off_cube_lights, [cubes]).start()

        if len(cubes) == 0:
            self.backend.play_animation_trigger("MajorFail")
        elif len(cubes) == 1:
            self.backend.run_timed_behavior("RollBlock", 60)
        else:
            self.backend.run_timed_behavior("StackBlocks", 120)
        return

    def _turn_off_cube_lights(self, cubes):
        for cube in cubes:
            if hasattr(cube, 'set_lights_off'):
                cube.set_lights_off()

    ###### DANCE ######

    def dance(self, robot=None, cmd_args=None):
        print("dancing...")
        self.backend.play_animation("anim_speedtap_wingame_intensity02_01")
        return

    ###### LOOK ######

    def look(self, robot=None, cmd_args=None):
        any_face = None
        print("Looking for a face...")
        self.backend.set_head_angle(self.backend.get_max_head_angle())
        self.backend.move_lift(-3)
        look_around = self.backend.start_behavior("FindFaces")

        try:
            any_face = self.backend.wait_for_observed_face(timeout=30)
        except Exception:
            print("Didn't find anyone :-(")
        finally:
            if look_around:
                look_around.stop()

        if any_face is None:
            self.backend.play_animation_trigger("MajorFail")
            return

        print("Yay, found someone!")
        self.backend.play_animation_trigger("LookInPlaceForFacesBodyPause")
        return

    ###### FOLLOW ######

    def follow(self, robot=None, cmd_args=None):
        print("Following your face - any face...")
        self.backend.move_lift(-3)
        self.backend.set_head_angle(self.backend.get_max_head_angle())

        face_to_follow = None

        while True:
            turn_action = None
            if face_to_follow:
                self.backend.turn_towards_face(face_to_follow)

            if not (face_to_follow and getattr(face_to_follow, 'is_visible', False)):
                try:
                    face_to_follow = self.backend.wait_for_observed_face(timeout=30)
                except Exception:
                    return "Didn't find a face - exiting!"
                if face_to_follow is None:
                    return "Didn't find a face - exiting!"
        return

    ###### PICTURE ######

    def picture(self, robot=None, cmd_args=None):
        self.backend.set_camera_enabled(True)
        print("taking a picture...")
        message = ""
        pic_filename = "cozmo_pic_" + str(int(time.time())) + ".png"
        self.backend.say_text("Say cheese!")
        latest_image = self.backend.get_latest_image()
        if latest_image:
            if hasattr(latest_image, 'raw_image'):
                latest_image.raw_image.convert('L').save(pic_filename)
            message = "picture saved as: " + pic_filename
        else:
            message = "no picture saved"
        self.backend.set_camera_enabled(False)
        return message

    ###### DRIVE ######

    def forward(self, robot=None, cmd_args=None, invert=False):
        if self.log:
            print(cmd_args)

        drive_duration = extract_next_float(cmd_args)

        if drive_duration is not None:
            if invert:
                drive_dir = "backwards"
            else:
                drive_dir = "forward"

            distance = drive_duration * speed
            self.backend.drive_straight(distance, speed, should_play_anim=True)
            return "I drove " + drive_dir + " for " + str(drive_duration) + " seconds!"

        return "Error: bad drive duration!"

    def backward(self, robot=None, cmd_args=None):
        self.forward(robot, cmd_args, True)

    ###### TURN ######

    def left(self, robot=None, cmd_args=None, invert=False):
        drive_angle = extract_next_float(cmd_args)

        if drive_angle is None:
            drive_angle = 90

        if invert:
            drive_angle = -drive_angle

        self.backend.turn_in_place(drive_angle)
        return "I turned " + str(drive_angle) + " degrees!"

    def right(self, robot=None, cmd_args=None, invert=False):
        self.left(robot, cmd_args, True)

    ###### LIFT ######

    def lift(self, robot=None, cmd_args=None):
        lift_height = extract_next_float(cmd_args)

        if lift_height is not None:
            self.backend.set_lift_height(lift_height / 100)
            return "I moved lift to " + str(lift_height)

        return "Error: bad height!"

    ###### HEAD ######

    def head(self, robot=None, cmd_args=None):
        head_angle_100 = extract_next_float(cmd_args)

        if head_angle_100 is not None:
            head_angle = head_angle_100 / 100 * (44 + 25) - 25
            if self.log:
                print("head angle = ", head_angle)
            self.backend.set_head_angle(head_angle)
            resultString = "I moved head to " + "{0:.1f}".format(head_angle)
            return resultString

        return "Error: bad angle!"

    ###### SAY ######

    def say(self, robot=None, cmd_args=None):
        entire_message = None
        if cmd_args and len(cmd_args) > 0:
            try:
                entire_message = " ".join(str(s) for s in cmd_args).strip()
            except:
                pass

        if (entire_message is not None) and (len(entire_message) > 0):
            self.backend.say_text(entire_message)
            return 'I said "' + entire_message + '"!'

        return "Error: no message!"

    ###### MOOD ######

    def mood(self, robot=None, cmd_args=None):
        if self.emotion_state:
            emotion = self.emotion_state.get()
            message = "I am feeling " + emotion + "!"
            if self.backend.is_connected():
                self.emotion_state.express_current()
            else:
                print(message)
            return message
        return "I don't know how I feel."

    def happy(self, robot=None, cmd_args=None):
        if self.emotion_state:
            self.emotion_state.set("happy")
        return "I am happy!"

    def sad(self, robot=None, cmd_args=None):
        if self.emotion_state:
            self.emotion_state.set("sad")
        return "I am sad."

    def sleep(self, robot=None, cmd_args=None):
        if self.backend.is_connected():
            self.backend.play_animation("anim_gotosleep_sleeping_01")
        return "Good night!"

    ###### CHARGER ######

    def charger(self, robot=None, cmd_args=None):
        trial = 1
        charger = None

        # try to find the charger - simplified for backend abstraction
        if self.log:
            print("looking for the charger now...")
        look_around = self.backend.start_behavior("LookAroundInPlace")
        try:
            charger = self.backend.wait_for_observed_charger(timeout=60)
            if charger:
                print("Found charger: %s" % charger)
            else:
                print("Didn't see the charger")
        except Exception:
            print("Didn't see the charger")
        finally:
            if look_around:
                look_around.stop()

        if charger:
            if self.log:
                print("lifting my arms to manouver...")
            self.backend.move_lift(10)
            if self.log:
                print("Going for the charger!!!")
            self.backend.go_to_pose(charger.pose if hasattr(charger, 'pose') else None)
            self.backend.drive_straight(-30, 50)
            if self.log:
                print("Turning...")
            self.backend.turn_in_place(90)
            self.backend.turn_in_place(95)
            time.sleep(1)
            if self.log:
                print("Parking!")
            self.backend.drive_straight(-130, 150)
            if self.log:
                print("checking if I did it...")
            if self.backend.is_on_charger():
                self.backend.move_lift(-8)
                print("I did it! Yay!")
            else:
                print("I did not manage to dock in the charger =(")
                if self.log:
                    print("let me go a little bit further...")
                self.backend.drive_straight(90, 50)
                trial += 1
                if trial < 4:
                    self.charger()
                else:
                    print("tired of trying. Giving up =(")

        return
