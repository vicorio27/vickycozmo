"""
Memory system for Cozmo autonomous agent.

Uses SQLite to store:
- Interactions (what happened, what Cozmo did, outcome)
- People seen (faces, names, frequency)
- Learned facts and preferences
- Mood history
- Successful/failed actions
"""
import os
import sqlite3
import time
import json
import threading


class Memory(object):
    """Persistent memory for the autonomous agent."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "agent_memory.db"
            )
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        """Thread-local SQLite connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def close(self):
        """Close the database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                situation TEXT,
                action TEXT,
                result TEXT,
                success INTEGER DEFAULT 1,
                emotion TEXT,
                context TEXT
            );

            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                face_id TEXT UNIQUE,
                name TEXT,
                first_seen REAL,
                last_seen REAL,
                visit_count INTEGER DEFAULT 1,
                mood TEXT DEFAULT 'neutral'
            );

            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                key TEXT,
                value TEXT,
                confidence REAL DEFAULT 0.5,
                learned_at REAL,
                source TEXT
            );

            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                situation TEXT,
                action TEXT,
                outcome TEXT,
                lesson TEXT,
                weight REAL DEFAULT 1.0,
                created_at REAL
            );

            CREATE TABLE IF NOT EXISTS mood_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                emotion TEXT,
                trigger TEXT,
                duration REAL
            );

            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                last_used REAL,
                parameters TEXT
            );
        """)
        conn.commit()

    # --- Interactions ---

    def store_interaction(self, situation, action, result, success=True, emotion=None, context=None):
        """Store an interaction for learning."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO interactions (timestamp, situation, action, result, success, emotion, context) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), situation, action, result, int(success), emotion, json.dumps(context) if context else None)
        )
        conn.commit()

    def get_recent_interactions(self, limit=10):
        """Get recent interactions for context."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM interactions ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_successful_actions(self, situation_pattern=None):
        """Get actions that worked well."""
        conn = self._get_conn()
        if situation_pattern:
            rows = conn.execute(
                "SELECT action, result, COUNT(*) as count FROM interactions WHERE success=1 AND situation LIKE ? GROUP BY action ORDER BY count DESC",
                (f"%{situation_pattern}%",)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT action, result, COUNT(*) as count FROM interactions WHERE success=1 GROUP BY action ORDER BY count DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    # --- People ---

    def store_person(self, face_id, name=None):
        """Store or update a person."""
        conn = self._get_conn()
        now = time.time()
        existing = conn.execute("SELECT * FROM people WHERE face_id=?", (face_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE people SET last_seen=?, visit_count=visit_count+1 WHERE face_id=?",
                (now, face_id)
            )
        else:
            conn.execute(
                "INSERT INTO people (face_id, name, first_seen, last_seen) VALUES (?, ?, ?, ?)",
                (face_id, name, now, now)
            )
        conn.commit()

    def get_known_people(self):
        """Get all known people."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM people ORDER BY visit_count DESC").fetchall()
        return [dict(r) for r in rows]

    def get_person(self, face_id):
        """Get a specific person."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM people WHERE face_id=?", (face_id,)).fetchone()
        return dict(row) if row else None

    # --- Facts ---

    def store_fact(self, category, key, value, confidence=0.5, source="observation"):
        """Store a learned fact."""
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT * FROM facts WHERE category=? AND key=?", (category, key)
        ).fetchone()
        if existing:
            # Update if new confidence is higher
            if confidence >= existing['confidence']:
                conn.execute(
                    "UPDATE facts SET value=?, confidence=?, learned_at=?, source=? WHERE category=? AND key=?",
                    (value, confidence, time.time(), source, category, key)
                )
        else:
            conn.execute(
                "INSERT INTO facts (category, key, value, confidence, learned_at, source) VALUES (?, ?, ?, ?, ?, ?)",
                (category, key, value, confidence, time.time(), source)
            )
        conn.commit()

    def get_facts(self, category=None):
        """Get learned facts."""
        conn = self._get_conn()
        if category:
            rows = conn.execute(
                "SELECT * FROM facts WHERE category=? ORDER BY confidence DESC", (category,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM facts ORDER BY confidence DESC").fetchall()
        return [dict(r) for r in rows]

    def get_fact(self, category, key):
        """Get a specific fact."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM facts WHERE category=? AND key=?", (category, key)
        ).fetchone()
        return dict(row) if row else None

    # --- Lessons ---

    def store_lesson(self, situation, action, outcome, lesson, weight=1.0):
        """Store a learned lesson."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO lessons (situation, action, outcome, lesson, weight, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (situation, action, outcome, lesson, weight, time.time())
        )
        conn.commit()

    def get_relevant_lessons(self, situation, limit=5):
        """Get lessons relevant to a situation."""
        conn = self._get_conn()
        # Simple keyword matching for relevance
        words = situation.lower().split()
        if not words:
            return []
        conditions = " OR ".join(["situation LIKE ?" for _ in words])
        params = [f"%{w}%" for w in words]
        rows = conn.execute(
            f"SELECT * FROM lessons WHERE {conditions} ORDER BY weight DESC, created_at DESC LIMIT ?",
            params + [limit]
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Mood ---

    def store_mood(self, emotion, trigger=None):
        """Store a mood change."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO mood_history (timestamp, emotion, trigger) VALUES (?, ?, ?)",
            (time.time(), emotion, trigger)
        )
        conn.commit()

    def get_mood_trend(self, hours=24):
        """Get mood trend over last N hours."""
        conn = self._get_conn()
        since = time.time() - (hours * 3600)
        rows = conn.execute(
            "SELECT emotion, COUNT(*) as count FROM mood_history WHERE timestamp > ? GROUP BY emotion ORDER BY count DESC",
            (since,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Skills ---

    def store_skill(self, name, description=None, parameters=None):
        """Store or update a skill."""
        conn = self._get_conn()
        existing = conn.execute("SELECT * FROM skills WHERE name=?", (name,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE skills SET last_used=? WHERE name=?", (time.time(), name)
            )
        else:
            conn.execute(
                "INSERT INTO skills (name, description, last_used, parameters) VALUES (?, ?, ?, ?)",
                (name, description, time.time(), json.dumps(parameters) if parameters else None)
            )
        conn.commit()

    def record_skill_result(self, name, success):
        """Record the result of using a skill."""
        conn = self._get_conn()
        if success:
            conn.execute(
                "UPDATE skills SET success_count=success_count+1, last_used=? WHERE name=?",
                (time.time(), name)
            )
        else:
            conn.execute(
                "UPDATE skills SET fail_count=fail_count+1, last_used=? WHERE name=?",
                (time.time(), name)
            )
        conn.commit()

    def get_skills(self):
        """Get all skills with success rates."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM skills ORDER BY success_count DESC").fetchall()
        return [dict(r) for r in rows]

    # --- Stats ---

    def get_stats(self):
        """Get memory statistics."""
        conn = self._get_conn()
        stats = {}
        stats['total_interactions'] = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        stats['successful_interactions'] = conn.execute("SELECT COUNT(*) FROM interactions WHERE success=1").fetchone()[0]
        stats['known_people'] = conn.execute("SELECT COUNT(*) FROM people").fetchone()[0]
        stats['learned_facts'] = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        stats['learned_lessons'] = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        stats['known_skills'] = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        return stats

    def get_context_string(self):
        """Build a context string from memory for the LLM."""
        parts = []

        # Recent interactions
        recent = self.get_recent_interactions(limit=5)
        if recent:
            parts.append("Recent interactions:")
            for r in recent:
                parts.append(f"  - {r['action']} -> {r['result']} ({'ok' if r['success'] else 'fail'})")

        # Known people
        people = self.get_known_people()
        if people:
            parts.append("Known people:")
            for p in people[:5]:
                name = p['name'] or f"Person #{p['id']}"
                parts.append(f"  - {name} (seen {p['visit_count']} times)")

        # Relevant lessons
        lessons = self.get_relevant_lessons("general", limit=3)
        if lessons:
            parts.append("Lessons learned:")
            for l in lessons:
                parts.append(f"  - {l['lesson']}")

        # Mood trend
        trend = self.get_mood_trend(hours=2)
        if trend:
            parts.append("Recent mood: " + ", ".join(f"{t['emotion']}({t['count']})" for t in trend[:3]))

        # Stats
        stats = self.get_stats()
        parts.append(f"Total interactions: {stats['total_interactions']}, Success rate: "
                     f"{stats['successful_interactions']}/{stats['total_interactions']}")

        return "\n".join(parts) if parts else "No memory yet."

    def clear(self):
        """Clear all memory."""
        conn = self._get_conn()
        conn.executescript("""
            DELETE FROM interactions;
            DELETE FROM people;
            DELETE FROM facts;
            DELETE FROM lessons;
            DELETE FROM mood_history;
            DELETE FROM skills;
        """)
        conn.commit()
