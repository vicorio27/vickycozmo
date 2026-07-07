"""Tests for cvc.memory module."""
import os
import sys
import time
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cvc.memory import Memory


class TestMemory(unittest.TestCase):

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)  # Close immediately, let SQLite handle it
        self.memory = Memory(self.db_path)

    def tearDown(self):
        self.memory.close()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_store_and_get_interaction(self):
        self.memory.store_interaction(
            situation="test situation",
            action="dance",
            result="success",
            success=True,
            emotion="happy"
        )
        interactions = self.memory.get_recent_interactions(limit=1)
        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0]['action'], 'dance')
        self.assertEqual(interactions[0]['success'], 1)

    def test_store_person(self):
        self.memory.store_person("face_001", name="Alice")
        people = self.memory.get_known_people()
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0]['name'], 'Alice')

    def test_store_person_visit_count(self):
        self.memory.store_person("face_001", name="Alice")
        self.memory.store_person("face_001")
        people = self.memory.get_known_people()
        self.assertEqual(people[0]['visit_count'], 2)

    def test_store_fact(self):
        self.memory.store_fact("color", "favorite", "blue", confidence=0.8)
        fact = self.memory.get_fact("color", "favorite")
        self.assertIsNotNone(fact)
        self.assertEqual(fact['value'], 'blue')
        self.assertAlmostEqual(fact['confidence'], 0.8)

    def test_store_fact_update(self):
        self.memory.store_fact("color", "favorite", "blue", confidence=0.5)
        self.memory.store_fact("color", "favorite", "red", confidence=0.8)
        fact = self.memory.get_fact("color", "favorite")
        self.assertEqual(fact['value'], 'red')

    def test_store_lesson(self):
        self.memory.store_lesson(
            situation="dark room",
            action="look",
            outcome="found face",
            lesson="look works in dark rooms"
        )
        lessons = self.memory.get_relevant_lessons("look around dark")
        self.assertGreater(len(lessons), 0)

    def test_store_mood(self):
        self.memory.store_mood("happy", trigger="user smiled")
        trend = self.memory.get_mood_trend(hours=1)
        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0]['emotion'], 'happy')

    def test_store_skill(self):
        self.memory.store_skill("dance", description="dance routine")
        skills = self.memory.get_skills()
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]['name'], 'dance')

    def test_skill_success_rate(self):
        self.memory.store_skill("dance")
        self.memory.record_skill_result("dance", True)
        self.memory.record_skill_result("dance", True)
        self.memory.record_skill_result("dance", False)
        skills = self.memory.get_skills()
        self.assertEqual(skills[0]['success_count'], 2)
        self.assertEqual(skills[0]['fail_count'], 1)

    def test_get_stats(self):
        self.memory.store_interaction("s1", "a1", "r1", True)
        self.memory.store_person("f1")
        self.memory.store_fact("cat", "key", "val")
        stats = self.memory.get_stats()
        self.assertEqual(stats['total_interactions'], 1)
        self.assertEqual(stats['known_people'], 1)
        self.assertEqual(stats['learned_facts'], 1)

    def test_clear(self):
        self.memory.store_interaction("s1", "a1", "r1")
        self.memory.store_person("f1")
        self.memory.clear()
        stats = self.memory.get_stats()
        self.assertEqual(stats['total_interactions'], 0)
        self.assertEqual(stats['known_people'], 0)

    def test_context_string(self):
        self.memory.store_interaction("s1", "dance", "ok", True)
        ctx = self.memory.get_context_string()
        self.assertIn("dance", ctx)


if __name__ == '__main__':
    unittest.main()
