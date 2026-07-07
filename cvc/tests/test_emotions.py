"""Tests for cvc.emotions module."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cvc.emotions import EmotionState, get_emotion_list, EMOTIONS


class TestEmotions(unittest.TestCase):

    def setUp(self):
        self.state = EmotionState(backend=None)

    def test_default_emotion(self):
        self.assertEqual(self.state.get(), "curious")

    def test_set_emotion(self):
        result = self.state.set("happy")
        self.assertTrue(result)
        self.assertEqual(self.state.get(), "happy")

    def test_set_invalid_emotion(self):
        result = self.state.set("nonexistent")
        self.assertFalse(result)
        self.assertEqual(self.state.get(), "curious")

    def test_emotion_list(self):
        emotions = get_emotion_list()
        self.assertIn("happy", emotions)
        self.assertIn("sad", emotions)
        self.assertIn("curious", emotions)
        self.assertIn("excited", emotions)
        self.assertIn("tired", emotions)
        self.assertIn("bored", emotions)
        self.assertIn("scared", emotions)

    def test_all_emotions_have_required_keys(self):
        for emotion, data in EMOTIONS.items():
            self.assertIn("animation", data, f"{emotion} missing animation")
            self.assertIn("modifier", data, f"{emotion} missing modifier")
            self.assertIn("boredom_rate", data, f"{emotion} missing boredom_rate")

    def test_modifier(self):
        self.state.set("happy")
        mod = self.state.modifier()
        self.assertIn("happy", mod.lower())

    def test_detect_from_text_positive(self):
        self.state.detect_from_text("hello friend")
        self.assertEqual(self.state.get(), "happy")

    def test_detect_from_text_negative(self):
        self.state.detect_from_text("you are stupid")
        self.assertEqual(self.state.get(), "sad")

    def test_detect_from_text_excited(self):
        self.state.detect_from_text("wow amazing")
        self.assertEqual(self.state.get(), "excited")

    def test_detect_from_text_scary(self):
        self.state.detect_from_text("boo scary ghost")
        self.assertEqual(self.state.get(), "scared")

    def test_detect_from_text_neutral(self):
        self.state.detect_from_text("the weather is normal")
        self.assertEqual(self.state.get(), "curious")

    def test_interact_resets_boredom(self):
        self.state._boredom = 15
        self.state.interact()
        self.assertLess(self.state._boredom, 15)

    def test_tick_boredom(self):
        self.state.set("bored")
        old_boredom = self.state._boredom
        self.state.tick(dt=5.0)
        self.assertGreater(self.state._boredom, old_boredom)

    def test_thread_safety(self):
        import threading
        def set_emotion():
            for _ in range(100):
                self.state.set("happy")
                self.state.set("sad")

        threads = [threading.Thread(target=set_emotion) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertIn(self.state.get(), ["happy", "sad"])


if __name__ == '__main__':
    unittest.main()
