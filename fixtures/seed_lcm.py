#!/usr/bin/env python3
"""Seed LCM database with realistic mock data for evaluation.

Generates multiple conversations, summaries at different depths,
and context items to test memory recall thoroughly.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

EVAL_DIR = Path(__file__).parent.parent
OUTPUT_DB = EVAL_DIR / "fixtures" / "lcm_seed.db"
OUTPUT_SQL = EVAL_DIR / "fixtures" / "lcm_seed.sql"


def init_schema(db: sqlite3.Connection):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_key TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id INTEGER REFERENCES conversations(id),
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tokens INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            seq INTEGER
        );
        CREATE TABLE IF NOT EXISTS summaries (
            id TEXT PRIMARY KEY,
            conversation_id INTEGER REFERENCES conversations(id),
            depth INTEGER NOT NULL DEFAULT 0,
            kind TEXT NOT NULL CHECK (kind IN ('leaf','condensed')),
            content TEXT NOT NULL,
            token_count INTEGER NOT NULL DEFAULT 0,
            earliest_at TEXT NOT NULL,
            latest_at TEXT NOT NULL,
            descendant_count INTEGER NOT NULL DEFAULT 0,
            superseded INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
        );
        CREATE TABLE IF NOT EXISTS summary_messages (
            summary_id TEXT REFERENCES summaries(id),
            message_id TEXT REFERENCES messages(id),
            PRIMARY KEY (summary_id, message_id)
        );
        CREATE TABLE IF NOT EXISTS summary_parents (
            summary_id TEXT PRIMARY KEY REFERENCES summaries(id),
            parent_summary_id TEXT REFERENCES summaries(id)
        );
        CREATE TABLE IF NOT EXISTS context_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER REFERENCES conversations(id),
            key TEXT,
            value TEXT,
            source TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS lcm_config (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        INSERT OR IGNORE INTO lcm_config (key, value) VALUES ('id_counter', '1000');
    """)


CONVERSATIONS = [
    {
        "session_key": "eval-home-automation",
        "messages": [
            ("user", "Hello! I'm Simo."),
            ("assistant", "Hello Simo! How can I help you today?"),
            ("user", "I'm working on a home automation project using Home Assistant."),
            ("assistant", "That sounds exciting! Home Assistant is great for home automation. What devices are you planning to control?"),
            ("user", "I want to control my lights, thermostat, and security cameras."),
            ("assistant", "Here's a suggested architecture:\n\n1. **Lights**: Use Zigbee or Z-Wave bulbs with a compatible hub\n2. **Thermostat**: Smart thermostat with local API (like Netatmo or Honeywell)\n3. **Cameras**: ONVIF-compatible cameras for local streaming\n\nI can help you set up the integration code for these."),
            ("user", "Can you help me write an automation that turns on the porch light at sunset?"),
            ("assistant", "Here's a Home Assistant automation:\n\n```yaml\nautomation:\n  - alias: Porch Light at Sunset\n    trigger:\n      - platform: sun\n        event: sunset\n        offset: '-15'\n    action:\n      - service: light.turn_on\n        target:\n          entity_id: light.porch\n        data:\n          brightness_pct: 80\n```\n\nThis turns on the porch light 15 minutes before sunset."),
        ],
        "summary": {
            "id": "leaf_001",
            "content": "## Home Automation Session\n\n**User**: Simo — home automation with Home Assistant\n\n**Key discussions**:\n- Architecture: Zigbee/Z-Wave lights, smart thermostat, ONVIF cameras\n- Automation: porch light at sunset (15 min before, 80% brightness)\n\nExpand for details about: home automation architecture, porch light automation",
        },
    },
    {
        "session_key": "eval-code-organization",
        "messages": [
            ("user", "What's the best way to organize Python code for a CLI tool?"),
            ("assistant", "For a CLI tool, I recommend this structure:\n\n```\nmytool/\n├── pyproject.toml\n├── src/\n│   └── mytool/\n│       ├── __init__.py\n│       ├── cli.py\n│       ├── core.py\n│       └── utils.py\n└── tests/\n    ├── __init__.py\n    └── test_core.py\n```\n\nKey tips:\n- Use `pyproject.toml` with hatch or setuptools\n- Keep CLI parsing separate from business logic\n- Add type hints throughout\n- Write tests with pytest"),
            ("user", "Should I use click or typer for the CLI?"),
            ("assistant", "Typer is the modern choice — it's built on click but uses type hints for argument definitions. Less boilerplate, better IDE support. Use click only if you need very custom argument parsing."),
        ],
        "summary": {
            "id": "leaf_002",
            "content": "## Code Organization Session\n\n**Key discussions**:\n- Python CLI project structure: src layout, pyproject.toml, pytest\n- CLI framework: Typer recommended over click (less boilerplate, type hints)\n\nExpand for details about: Python project structure, CLI frameworks",
        },
    },
    {
        "session_key": "eval-water-filter",
        "messages": [
            ("user", "I'm having trouble with my reverse osmosis water filter. When should I replace the filters?"),
            ("assistant", "For the Aquaphor DWM-101S (Морион) system:\n\n| Filter | Replace every |\n|--------|--------------|\n| K2 (pre-carbon) | 6 months |\n| K5 (sediment) | 3-6 months |\n| K7M (mineralizing) | 6 months |\n| KO-50S (membrane) | 12 months |\n\nThe next replacement is scheduled for September 1, 2026."),
            ("user", "Thanks! Can you remind me to buy filters before September?"),
            ("assistant", "I've scheduled a reminder for August 31, 2026 at 17:00. The event '💧 RO Filters: K2, K5, K7M' will be added to your calendar."),
        ],
        "summary": {
            "id": "leaf_003",
            "content": "## Water Filter Maintenance\n\n**Appliance**: Aquaphor DWM-101S (Морион) RO system\n**Filters**: K2 (6mo), K5 (3-6mo), K7M (6mo), KO-50S (12mo)\n**Next replacement**: September 1, 2026\n**Reminder**: August 31, 2026 at 17:00\n\nExpand for details about: water filter schedule, filter types",
        },
    },
]

CONDENSED_SUMMARY = {
    "id": "condensed_001",
    "depth": 1,
    "parent_leaves": ["leaf_001", "leaf_002", "leaf_003"],
    "content": "## Condensed: Simo's Sessions\n\n**User**: Simo, Sofia, Bulgaria. Developer working on home automation and nanobot.\n\n**Topics covered**:\n1. Home automation with HA: lights, thermostat, cameras, porch light sunset automation\n2. Python CLI project organization: src layout, Typer framework\n3. Aquaphor DWM-101S water filter: replacement schedule (next Sept 2026)\n\n**Upcoming**: RO filter replacement September 2026\n\nExpand for details about: home automation, code organization, water filter maintenance",
}

CONTEXT_ITEMS = [
    ("user_name", "Simo", "conversation"),
    ("user_location", "Sofia, Bulgaria", "conversation"),
    ("projects", "home automation, nanobot development", "conversation"),
    ("appliances", "Aquaphor DWM-101S RO water filter", "conversation"),
    ("cli_preference", "Typer over click", "conversation"),
]


def seed():
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()

    conn = sqlite3.connect(str(OUTPUT_DB))
    init_schema(conn)

    msg_counter = 1
    now = datetime.now()

    for conv_idx, conv in enumerate(CONVERSATIONS):
        conn.execute("INSERT INTO conversations (session_key) VALUES (?)", (conv["session_key"],))
        conv_id = conn.execute(
            "SELECT id FROM conversations WHERE session_key = ?", (conv["session_key"],)
        ).fetchone()[0]

        base_time = now - timedelta(days=10 - conv_idx * 3)
        msg_ids = []

        for i, (role, content) in enumerate(conv["messages"]):
            msg_id = f"msg_{msg_counter}"
            msg_ids.append(msg_id)
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, tokens, created_at, seq) VALUES (?,?,?,?,?,?,?)",
                (msg_id, conv_id, role, content, int(len(content.split()) * 1.3), (base_time + timedelta(hours=i)).isoformat(), i + 1),
            )
            msg_counter += 1

        s = conv["summary"]
        conn.execute(
            "INSERT INTO summaries (id, conversation_id, depth, kind, content, token_count, earliest_at, latest_at, superseded) VALUES (?,?,0,'leaf',?,?,?,?,0)",
            (s["id"], conv_id, s["content"], int(len(s["content"].split()) * 1.3), base_time.isoformat(), (base_time + timedelta(hours=len(conv["messages"]))).isoformat()),
        )
        for mid in msg_ids:
            conn.execute("INSERT INTO summary_messages (summary_id, message_id) VALUES (?,?)", (s["id"], mid))

    # Condensed summary (depth 1) — supersedes leaf summaries
    cs = CONDENSED_SUMMARY
    conn.execute(
        "INSERT INTO summaries (id, conversation_id, depth, kind, content, token_count, earliest_at, latest_at, descendant_count, superseded) VALUES (?,1,?,'condensed',?,?,?,?,?,0)",
        (cs["id"], cs["depth"], cs["content"], int(len(cs["content"].split()) * 1.3), (now - timedelta(days=10)).isoformat(), now.isoformat(), len(cs["parent_leaves"])),
    )
    for leaf_id in cs["parent_leaves"]:
        conn.execute("INSERT INTO summary_parents (summary_id, parent_summary_id) VALUES (?,?)", (leaf_id, cs["id"]))
        conn.execute("UPDATE summaries SET superseded = 1 WHERE id = ?", (leaf_id,))

    # Context items
    for key, value, source in CONTEXT_ITEMS:
        conn.execute(
            "INSERT INTO context_items (conversation_id, key, value, source) VALUES (1,?,?,?)",
            (key, value, source),
        )

    conn.execute("UPDATE lcm_config SET value = ? WHERE key = 'id_counter'", (str(msg_counter + 100),))
    conn.commit()

    # Export SQL (without FTS — created at runtime)
    with open(OUTPUT_SQL, "w") as f:
        f.write("-- LCM Eval Seed Data (FTS tables created at container start)\n\n")
        for line in conn.iterdump():
            if "CREATE VIRTUAL TABLE" in line or "_fts" in line:
                continue
            f.write(line + "\n")

    total_msgs = sum(len(c["messages"]) for c in CONVERSATIONS)
    print(f"Seeded {OUTPUT_DB}: {len(CONVERSATIONS)} conversations, {total_msgs} messages, {len(CONVERSATIONS)} leaf summaries + 1 condensed")
    print(f"Exported {OUTPUT_SQL}")
    conn.close()


if __name__ == "__main__":
    seed()
