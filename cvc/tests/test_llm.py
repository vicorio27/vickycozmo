"""Tests for cvc.llm module."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cvc.llm import clean_response, parse_action, build_system_prompt, BASE_SYSTEM_PROMPT


class TestLLM(unittest.TestCase):

    def test_clean_response_removes_quotes(self):
        result = clean_response('"Hello world"')
        self.assertEqual(result, "Hello world")

    def test_clean_response_removes_single_quotes(self):
        result = clean_response("'Hello world'")
        self.assertEqual(result, "Hello world")

    def test_clean_response_strips_whitespace(self):
        result = clean_response("  Hello world  ")
        self.assertEqual(result, "Hello world")

    def test_clean_response_cuts_at_delimiter(self):
        result = clean_response("Hello\n\nMore text")
        self.assertEqual(result, "Hello")

    def test_clean_response_cuts_at_dash(self):
        result = clean_response("Hello\n---\nMore text")
        self.assertEqual(result, "Hello")

    def test_parse_action_no_action(self):
        text, action = parse_action("Just talking, no action")
        self.assertEqual(text, "Just talking, no action")
        self.assertIsNone(action)

    def test_parse_action_with_dance(self):
        text, action = parse_action("I will dance! [ACTION: dance]")
        self.assertEqual(text, "I will dance!")
        self.assertEqual(action["action"], "dance")
        self.assertEqual(action["args"], "")

    def test_parse_action_with_forward(self):
        text, action = parse_action("Moving forward [ACTION: forward 10]")
        self.assertEqual(text, "Moving forward")
        self.assertEqual(action["action"], "forward")
        self.assertEqual(action["args"], "10")

    def test_parse_action_ignores_unknown(self):
        text, action = parse_action("[ACTION: nonexistent]")
        self.assertEqual(text, "")
        self.assertIsNone(action)

    def test_build_system_prompt_base(self):
        prompt = build_system_prompt()
        self.assertIn("Cozmo", prompt)
        self.assertEqual(prompt, BASE_SYSTEM_PROMPT)

    def test_build_system_prompt_with_emotion(self):
        prompt = build_system_prompt(emotion_modifier="You are happy!")
        self.assertIn("You are happy!", prompt)
        self.assertIn("Cozmo", prompt)

    def test_clean_response_cuts_at_user(self):
        result = clean_response("Hello\nUser: what?")
        self.assertEqual(result, "Hello")

    def test_clean_response_cuts_at_instructions(self):
        result = clean_response("Hello\nInstructions: do stuff")
        self.assertEqual(result, "Hello")


if __name__ == '__main__':
    unittest.main()
