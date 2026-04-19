#!/usr/bin/env python3
"""
Seed LCM database with mock data for evaluation.
Run this BEFORE eval to populate memory context.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

WORKSPACE_DIR = Path(__file__).parent
LCM_DB = Path.home() / ".nanobot" / "lcm" / "lcm.db"
EVAL_DB = Path(__file__).parent / "lcm_seed.db"


def init_lcm_schema(db: sqlite3.Connection):
    """Create LCM schema if not exists."""
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
        
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
            content, content=messages, content_rowid=rowid
        );
        
        CREATE VIRTUAL TABLE IF NOT EXISTS summaries_fts USING fts5(
            content, content=summaries, content_rowid=rowid
        );
        
        INSERT OR IGNORE INTO lcm_config (key, value) VALUES ('id_counter', '1000');
    """)


def seed_lcm_data():
    """Seed the eval LCM database with mock data."""
    
    # Create fresh eval database
    if EVAL_DB.exists():
        EVAL_DB.unlink()
    
    conn = sqlite3.connect(str(EVAL_DB))
    init_lcm_schema(conn)
    
    # Create a conversation
    session_key = "eval-test"
    conn.execute("INSERT INTO conversations (session_key) VALUES (?)", (session_key,))
    conv_id = conn.execute("SELECT id FROM conversations WHERE session_key = ?", (session_key,)).fetchone()[0]
    
    # Increment ID counter
    id_counter = 1000
    conn.execute("UPDATE lcm_config SET value = ? WHERE key = 'id_counter'", (str(id_counter + 100),))
    
    # Create messages that simulate past conversations
    past_messages = [
        {"role": "user", "content": "Hello! I'm Simo."},
        {"role": "assistant", "content": "Hello Simo! How can I help you today?"},
        {"role": "user", "content": "I'm working on a home automation project using Home Assistant."},
        {"role": "assistant", "content": "That sounds exciting! Home Assistant is great for home automation. What devices are you planning to control?"},
        {"role": "user", "content": "I want to control my lights, thermostat, and security cameras."},
        {"role": "assistant", "content": "Here's a suggested architecture:\n\n1. **Lights**: Use Zigbee or Z-Wave bulbs with a compatible hub\n2. **Thermostat**: Smart thermostat with local API (like Netatmo or Honeywell)\n3. **Cameras**: ONVIF-compatible cameras for local streaming\n\nI can help you set up the integration code for these."},
        {"role": "user", "content": "Can you help me write an automation that turns on the porch light at sunset?"},
        {"role": "assistant", "content": """Here's a Home Assistant automation for that:

```yaml
automation:
  - alias: Porch Light at Sunset
    trigger:
      - platform: sun
        event: sunset
        offset: '-15'
    action:
      - service: light.turn_on
        target:
          entity_id: light.porch
        data:
          brightness_pct: 80
```

This turns on the porch light 15 minutes before sunset."""},
        {"role": "user", "content": "What's the best way to organize Python code for a CLI tool?"},
        {"role": "assistant", "content": """For a CLI tool, I recommend this structure:

```
mytool/
├── pyproject.toml
├── src/
│   └── mytool/
│       ├── __init__.py
│       ├── cli.py
│       ├── core.py
│       └── utils.py
└── tests/
    ├── __init__.py
    └── test_core.py
```

Key tips:
- Use `pyproject.toml` with hatch or setuptools
- Keep CLI parsing separate from business logic
- Add type hints throughout
- Write tests with pytest"""},
        {"role": "user", "content": "I'm having trouble with my reverse osmosis water filter. When should I replace the filters?"},
        {"role": "assistant", "content": """For the Aquaphor DWM-101S (Mорион) system:

| Filter | Replace every |
|--------|--------------|
| K2 (pre-carbon) | 6 months |
| K5 (sediment) | 3-6 months |
| K7M (mineralizing) | 6 months |
| KO-50S (membrane) | 12 months |

The next replacement is scheduled for September 1, 2026."""},
        {"role": "user", "content": "Thanks! Can you remind me to buy filters before September?"},
        {"role": "assistant", "content": "I've scheduled a reminder for August 31, 2026 at 17:00. The event '💧 RO Filters: K2, K5, K7M' will be added to your calendar. You can also add 'k2, k5, ro50s' to your shopping list."},
    ]
    
    # Insert messages
    msg_id_counter = 1
    for i, msg in enumerate(past_messages):
        msg_id = f"msg_{msg_id_counter}"
        conn.execute("""
            INSERT INTO messages (id, conversation_id, role, content, tokens, created_at, seq)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id, conv_id, msg["role"], msg["content"],
            len(msg["content"].split()) * 1.3,  # rough token estimate
            (datetime.now() - timedelta(days=5, hours=i)).isoformat(),
            i + 1
        ))
        msg_id_counter += 1
    
    # Create a leaf summary
    summary_id = "leaf_001"
    summary_content = """## Past Conversation Summary

**User**: Simo - working on home automation with Home Assistant

**Key discussions**:
- Home automation project: lights, thermostat, security cameras
- Automation example: porch light at sunset (15 min before)
- Code organization: src/ layout with CLI separated from core
- RO water filter: Aquaphor DWM-101S filters scheduled for Sept 2026

**Upcoming events**:
- RO filter replacement: September 1, 2026 (K2, K5, K7M)

Expand for details about: home automation, Python project structure, water filter maintenance"""
    
    conn.execute("""
        INSERT INTO summaries (id, conversation_id, depth, kind, content, token_count, earliest_at, latest_at, superseded, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        summary_id, conv_id, 0, 'leaf', summary_content,
        len(summary_content.split()) * 1.3,
        (datetime.now() - timedelta(days=1)).isoformat(),
        datetime.now().isoformat(),
        0,
        datetime.now().isoformat()
    ))
    
    # Link summary to messages
    for i in range(1, msg_id_counter):
        conn.execute("""
            INSERT INTO summary_messages (summary_id, message_id)
            VALUES (?, ?)
        """, (summary_id, f"msg_{i}"))
    
    # Add some context items
    context_items = [
        {"key": "user_name", "value": "Simo", "source": "conversation"},
        {"key": "user_location", "value": "Sofia, Bulgaria", "source": "conversation"},
        {"key": "projects", "value": "home automation, nanobot development", "source": "conversation"},
        {"key": "appliances", "value": "Aquaphor DWM-101S RO water filter", "source": "conversation"},
    ]
    
    for item in context_items:
        conn.execute("""
            INSERT INTO context_items (conversation_id, key, value, source, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (conv_id, item["key"], item["value"], item["source"], datetime.now().isoformat()))
    
    conn.commit()
    
    # Create FTS index
    conn.execute("""
        INSERT INTO messages_fts(rowid, content)
        SELECT rowid, content FROM messages
    """)
    conn.execute("""
        INSERT INTO summaries_fts(rowid, content)
        SELECT rowid, content FROM summaries
    """)
    conn.commit()
    
    print(f"✅ Seeded LCM database: {EVAL_DB}")
    print(f"   Conversations: 1")
    print(f"   Messages: {len(past_messages)}")
    print(f"   Summaries: 1")
    print(f"   Context items: {len(context_items)}")
    
    return EVAL_DB


def export_for_docker():
    """Export seed data as SQL file for Docker COPY (without FTS which needs special handling)."""
    conn = sqlite3.connect(str(EVAL_DB))
    
    with open(Path(__file__).parent / "lcm_seed.sql", "w") as f:
        f.write("-- LCM Seed Data (FTS tables created at runtime)\n\n")
        
        # Write schema (excluding FTS which we'll create separately)
        for line in conn.iterdump():
            if "CREATE VIRTUAL TABLE" in line:
                continue  # Skip FTS table definitions
            if "messages_fts" in line or "summaries_fts" in line:
                continue  # Skip FTS references
            f.write(line + "\n")
    
    print(f"✅ Exported SQL seed: {Path(__file__).parent / 'lcm_seed.sql'}")


if __name__ == "__main__":
    seed_lcm_data()
    export_for_docker()
