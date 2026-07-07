#!/usr/bin/env python
'''
Cozmo Voice Commands (CvC)
Author: Riccardo Sallusti - http://riccardosallusti.it
Description: Issue complex voice commands to Cozmo, and watch him execute them.
More informations: https://github.com/rizal72/Cozmo-Voice-Commands
License: GNU
'''
import sys
import os
import operator
import glob
import json
import pkg_resources

try:
    from termcolor import colored, cprint
    from pynput.keyboard import Key, Listener
    import speech_recognition as sr
except ImportError:
    sys.exit('some packages are required, install them doing: `pip3 install --user termcolor SpeechRecognition PyAudio Pynput` to run this script.\nIf you are on linux do: `sudo apt-get install flac portaudio19-dev python-all-dev python3-all-dev && sudo pip3 install Pynput pyaudio`')

from . import backends
from . import voice_commands
from . import llm
from . import emotions
from . import stt_offline
from . import pet_mode
from . import web_editor
from . import agent as agent_mod
from .memory import Memory

###### VARS ######
version = pkg_resources.require("cvc")[0].version
title = "Cozmo-Voice-Commands (CvC) - Version " + version
author =" - Riccardo Sallusti (http://riccardosallusti.it)"
log = False
wait_for_shift = True
llm_enabled = False
llm_model = llm.DEFAULT_MODEL
use_pycozmo = False
autonomous_enabled = False
autonomous_agent = None
memory = None
offline_stt_enabled = False
offline_stt = None
pet_mode_enabled = False
pet_thread = None
web_editor_enabled = False
web_editor_port = 5000
web_editor_thread = None
emotion_state = None
lang = None
lang_data = None
commands_activate = ["cozmo", "robot", "cosmo", "cosimo", "cosma", "cosima", "kosmos", "cosmos", "cosmic", "osmo", "kosovo", "peau", "kosmo", "kozmo", "gizmo"]
vc = None
backend = None
languages = []

##### MAIN ######
def main():
    parse_arguments()
    clearScreen = os.system('cls' if os.name == 'nt' else 'clear')
    cprint(title, "green", attrs=['bold'], end='')
    cprint(author, "cyan")

    if use_pycozmo:
        cprint("Using pycozmo backend (direct WiFi, no mobile app required)", "cyan")
        try:
            backend = backends.create_backend("pycozmo")
            backend.start()
            run_with_backend(backend)
        except Exception as e:
            cprint("Could not start pycozmo: {0}".format(e), "red")
            cprint("Falling back to debug mode...", "yellow")
            run_debug()
    else:
        cprint("Using Anki SDK backend (requires mobile app)", "cyan")
        try:
            from .backends.anki_backend import AnkiBackend
            backend = AnkiBackend()
            backend.start()
        except SystemExit as e:
            print('exception = "%s"' % e)
            cprint('\nGoing on without Cozmo: for testing purposes only!', 'red')
            run_debug()

def run_with_backend(robot_backend):
    '''Run the app with a connected backend.'''
    global vc, emotion_state, offline_stt, pet_thread, web_editor_thread

    backend_ref = robot_backend
    vc = voice_commands.VoiceCommands(backend_ref, log)
    emotion_state = emotions.EmotionState(backend_ref)
    vc.set_emotion_state(emotion_state)
    emotion_state.set("curious")

    if offline_stt_enabled:
        try:
            offline_stt = stt_offline.OfflineSTT()
        except Exception as e:
            cprint("Could not start offline STT: {0}".format(e), "red")

    if pet_mode_enabled:
        pet_thread = pet_mode.PetMode(backend_ref, emotion_state, vc, interval=10.0)
        pet_thread.start()

    if web_editor_enabled:
        web_editor_thread = web_editor.WebEditor(
            port=web_editor_port,
            emotion_state=emotion_state,
            vc=vc,
            llm_enabled=llm_enabled,
        )
        web_editor_thread.start()

    if autonomous_enabled:
        memory = Memory()
        autonomous_agent = agent_mod.AutonomousAgent(
            backend=backend_ref,
            emotion_state=emotion_state,
            memory=memory,
            interval=15.0,
            model=llm_model,
        )
        autonomous_agent.start()
        cprint("Autonomous agent started. Cozmo will observe, think, and act on his own.", "cyan")

    def on_press(key):
        if key == Key.shift_l or key == Key.shift_r:
            listen(backend_ref)

    def on_release(key):
        if key == Key.shift_l or key == Key.shift_r:
            pass

    if backend_ref.is_connected():
        vc.check_charger()
        backend_ref.play_animation("anim_cozmosays_getout_short_01")

    try:
        load_jsons()
        set_language()
        set_data()
        printSupportedCommands()
        prompt()

        if wait_for_shift:
            with Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
        else:
            while 1:
                listen(backend_ref)

    except KeyboardInterrupt:
        print("")
        cprint("Exit requested by user", "yellow")
    finally:
        if autonomous_agent is not None:
            cprint("Stopping autonomous agent...", "yellow")
            autonomous_agent.stop()
        if pet_thread is not None:
            cprint("Stopping pet mode...", "yellow")
            pet_thread.stop()

def run_debug():
    '''Run without a robot connection for testing.'''
    global vc, emotion_state, offline_stt, pet_thread, web_editor_thread

    vc = voice_commands.VoiceCommands(None, log)
    emotion_state = emotions.EmotionState(None)
    vc.set_emotion_state(emotion_state)
    emotion_state.set("curious")

    if offline_stt_enabled:
        try:
            offline_stt = stt_offline.OfflineSTT()
        except Exception as e:
            cprint("Could not start offline STT: {0}".format(e), "red")

    if web_editor_enabled:
        web_editor_thread = web_editor.WebEditor(
            port=web_editor_port,
            emotion_state=emotion_state,
            vc=vc,
            llm_enabled=llm_enabled,
        )
        web_editor_thread.start()

    try:
        load_jsons()
        set_language()
        set_data()
        printSupportedCommands()
        prompt()

        if wait_for_shift:
            def on_press(key):
                if key == Key.shift_l or key == Key.shift_r:
                    listen(None)
            def on_release(key):
                pass
            with Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
        else:
            while 1:
                listen(None)

    except KeyboardInterrupt:
        print("")
        cprint("Exit requested by user", "yellow")
    finally:
        if pet_thread is not None:
            pet_thread.stop()

def load_jsons():
    global languages
    cprint("\nloading languages files...","yellow")
    package_location = os.path.dirname(os.path.realpath(__file__))
    relative_location = 'languages/*.json'
    absolute_location =  package_location + "/" + relative_location

    if log:
        print("Package Location: " + package_location + "\nRelative location: " + relative_location)

    for file in glob.glob(absolute_location):
        with open(file) as json_file:
            languages.append(json.load(json_file))
            if (log):
                cprint("loaded: " + str(file) + " ", "yellow")

    if len(languages) == 0:
        cprint("\nno languages found! Quitting...", "red")
        sys.exit()
    else:
        languages.sort(key=operator.itemgetter('id'))

def set_language():
    global lang, lang_ext, lang_data

    cprint('\nCHOOSE YOUR LANGUAGE (hit "enter" for default [English]):', 'green')
    for i in range(len(languages)):
        print(i+1, end='')
        print(". " + str(languages[i]['name']))

    lang = 0
    while not lang:
        try:
            lang = int(input('>>> ').strip())
            if lang not in range(1,len(languages)+1):
                raise ValueError
        except ValueError:
            if not lang:
                break
            else:
                lang = 0
                cprint("That's not an option!", "red")

    if lang == 1 or not lang:
        lang = 0
    else:
        lang = lang - 1


def set_data():
    global vc, lang_data

    try:
        lang_data = languages[lang]
    except:
        cprint("Language is not set! Quitting...", "red")
        sys.exit()

    vc.lang_data = lang_data

    cprint("\nlanguage set to: " + lang_data['lang'] + "\n", "yellow")
    cprint(lang_data['instructions'], "green")


def listen(robot_backend):

    cprint("wait...")

    if robot_backend:
        checkBattery(robot_backend)
        flash_backpack(robot_backend, True)

    prompt(2)

    if offline_stt_enabled and offline_stt:
        recognized = listen_offline(robot_backend)
    else:
        recognized = listen_online(robot_backend)

    if recognized:
        process_recognized_text(robot_backend, recognized)


def listen_offline(robot_backend):
    '''Listen using local Vosk STT.'''
    try:
        recognized = offline_stt.listen_once()
        if robot_backend:
            flash_backpack(robot_backend, False)
        if recognized:
            cprint("Done Listening: recognizing...", "green")
            print("You said: " + recognized)
        return recognized
    except Exception as e:
        cprint("Offline STT error: {0}".format(e), "red")
        if robot_backend:
            flash_backpack(robot_backend, False)
        prompt()
        return None


def listen_online(robot_backend):
    '''Listen using Google Speech Recognition.'''
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        recognizer.pause_threshold = 0.8
        recognizer.dynamic_energy_threshold = False
        recognizer.adjust_for_ambient_noise(source)

        try:
            audio = recognizer.listen(source, timeout = 5)
        except sr.WaitTimeoutError:
            cprint("Timeout...", "red")
            if robot_backend:
                flash_backpack(robot_backend, False)
            prompt()
            return None

        cprint("Done Listening: recognizing...","green")

        if robot_backend:
            flash_backpack(robot_backend, False)

        try:
            recognized = recognizer.recognize_google(audio, key=None, language=lang_data['lang_ext']).lower()
            print("You said: " + recognized)
            return recognized
        except sr.UnknownValueError or LookupError:
            cprint("Speech Recognition service could not understand audio", "red")
            prompt()
            return None
        except sr.RequestError as e:
            cprint("Could not request results from Speech Recognition service, check your web connection; {0}".format(e), "red")
            prompt()
            return None


def process_recognized_text(robot_backend, recognized):
    found_command = set(commands_activate).intersection(recognized.split())
    if found_command:
        cprint("Action command recognized: " + str(found_command), "green")
        if emotion_state:
            emotion_state.detect_from_text(recognized)
            emotion_state.interact()
        cmd_funcs, cmd_args = extract_commands_from_string(recognized)
        executeCommands(robot_backend, cmd_funcs, cmd_args)

        if llm_enabled:
            handle_llm_response(robot_backend, recognized)
    else:
        cprint("You did not say the magic words: " + commands_activate[0] + ", " + commands_activate[1], "red")
        if robot_backend and robot_backend.is_connected():
            robot_backend.play_animation("anim_pounce_reacttoobj_01_shorter")
    prompt()


def executeCommands(robot_backend, cmd_funcs, cmd_args):
    if robot_backend and robot_backend.is_connected():
        vc.check_charger(distance=70)
    for i in range(len(cmd_funcs)):
        if cmd_funcs[i] is not None:
            if robot_backend and robot_backend.is_connected():
                result_string = getattr(vc, cmd_funcs[i]['command'])(None, cmd_args[i])
                if result_string and log:
                    print(result_string)
            else:
                commands = lang_data['commands']
                index = cmd_funcs[i]['index']
                print(commands[index]['usage'])
        else:
            cprint(lang_data['error_one'], "red")
            printSupportedCommands()

    if len(cmd_funcs) == 0:
        cprint(lang_data['error_all'], "red")
        printSupportedCommands()
        if robot_backend and robot_backend.is_connected():
            robot_backend.play_animation("anim_pounce_reacttoobj_01_shorter")


def handle_llm_response(robot_backend, user_text):
    cprint("Thinking...", "magenta")
    modifier = emotion_state.modifier() if emotion_state else ""
    try:
        response = llm.query_ollama(user_text, model=llm_model, emotion_modifier=modifier)
    except Exception as e:
        cprint("LLM error: {0}".format(e), "red")
        return

    if log:
        print("LLM response:", response)

    if response:
        if robot_backend and robot_backend.is_connected():
            robot_backend.say_text(response)
        else:
            cprint("Cozmo would say: " + response, "cyan")

###### HELPER METHODS #######

def parse_arguments():
    global wait_for_shift, log, llm_enabled, llm_model, use_pycozmo, autonomous_enabled, offline_stt_enabled, pet_mode_enabled, web_editor_enabled, web_editor_port
    if "--version" in sys.argv or "-V" in sys.argv:
        print(version)
        sys.exit()
    if "--no-wait" in sys.argv or "-W" in sys.argv:
        wait_for_shift = False
    if "--log" in sys.argv or "-L" in sys.argv:
        log = True
    if "--llm" in sys.argv:
        llm_enabled = True
    if "--offline-stt" in sys.argv:
        offline_stt_enabled = True
    if "--pet-mode" in sys.argv:
        pet_mode_enabled = True
    if "--web-editor" in sys.argv:
        web_editor_enabled = True
    if "--autonomous" in sys.argv:
        autonomous_enabled = True
    if "--use-pycozmo" in sys.argv:
        use_pycozmo = True
    for arg in sys.argv[1:]:
        if arg.startswith("--llm-model="):
            llm_model = arg.split("=", 1)[1]
        if arg.startswith("--web-port="):
            try:
                web_editor_port = int(arg.split("=", 1)[1])
            except ValueError:
                pass

    if log:
        print ('Arguments list:', str(sys.argv[1:]))


def prompt(id = 1):
    if id == 1 and wait_for_shift:
        cprint(lang_data['text_wait'], "green", attrs=['bold'])
    elif id == 2:
        cprint(lang_data['text_say'], "magenta", attrs=['bold'], end="")
        cprint(" >>>", "green", attrs=['bold'])

def checkBattery(robot_backend):
    voltage = robot_backend.get_battery_voltage()
    if (voltage <= 3.5):
        color = "red"
    else:
        color = "yellow"
    cprint("BATTERY LEVEL(RED=LOW): %f" % voltage + "v", color)

def flash_backpack(robot_backend, flag):
    if flag:
        light = robot_backend.make_flash_light("green")
    else:
        light = robot_backend.make_light("off")
    robot_backend.set_all_backpack_lights(light)

def printSupportedCommands():
    commands = lang_data['commands']
    for command in commands:
        cprint("[ ", "cyan", end="")
        words = command['words']
        for i in range(0, len(words)):
            cprint(words[i], "cyan", end="")
            if i<len(words)-1:
                cprint(", ", end="")

        cprint(" ] : ", "cyan", end="")
        cprint(command['usage'])

def get_command(command_name):
    commands = lang_data['commands']

    for i,command in enumerate(commands):
        for word in command['words']:
            wordcut = word[0:-1]
            if wordcut in command_name.lower():
                func_name = commands[i]['action']
                if log:
                    print("found the function: " + func_name + " matching the word: " + word)
                return func_name, i
    return None, None

def extract_commands_from_string(in_string):
    sentences = in_string.split(" " + lang_data['separator'] + " ")
    cmd_funcs = []
    cmd_args = []
    if log:
        print("splitted sentences: ", sentences)
    for sentence in sentences:
        words = sentence.split()
        for i in range(len(words)):
            cmd_func, cmd_index = get_command(words[i])
            if cmd_func:
                cmd_funcs.append({'index':cmd_index,'command':cmd_func})
                cmd_arg = words[i + 1:]
                cmd_args.append(cmd_arg)
                break
    if log:
        print("commands: ", cmd_funcs, "\narguments: ", cmd_args)
    return cmd_funcs, cmd_args

###### ENTRY POINT ######
if __name__ == "__main__":
    main()
