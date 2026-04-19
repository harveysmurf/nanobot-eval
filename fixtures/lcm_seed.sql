-- LCM Eval Seed Data (FTS tables created at container start)

BEGIN TRANSACTION;
CREATE TABLE context_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER REFERENCES conversations(id),
            key TEXT,
            value TEXT,
            source TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
INSERT INTO "context_items" VALUES(1,1,'user_name','Simo','conversation','2026-04-19 10:28:24');
INSERT INTO "context_items" VALUES(2,1,'user_location','Sofia, Bulgaria','conversation','2026-04-19 10:28:24');
INSERT INTO "context_items" VALUES(3,1,'projects','home automation, nanobot development','conversation','2026-04-19 10:28:24');
INSERT INTO "context_items" VALUES(4,1,'appliances','Aquaphor DWM-101S RO water filter','conversation','2026-04-19 10:28:24');
INSERT INTO "context_items" VALUES(5,1,'cli_preference','Typer over click','conversation','2026-04-19 10:28:24');
CREATE TABLE conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_key TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
INSERT INTO "conversations" VALUES(1,'eval-home-automation','2026-04-19 10:28:24');
INSERT INTO "conversations" VALUES(2,'eval-code-organization','2026-04-19 10:28:24');
INSERT INTO "conversations" VALUES(3,'eval-water-filter','2026-04-19 10:28:24');
CREATE TABLE lcm_config (
            key TEXT PRIMARY KEY,
            value TEXT
        );
INSERT INTO "lcm_config" VALUES('id_counter','117');
CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            conversation_id INTEGER REFERENCES conversations(id),
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tokens INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            seq INTEGER
        );
INSERT INTO "messages" VALUES('msg_1',1,'user','Hello! I''m Simo.',3,'2026-04-09T13:28:24.379231',1);
INSERT INTO "messages" VALUES('msg_2',1,'assistant','Hello Simo! How can I help you today?',10,'2026-04-09T14:28:24.379231',2);
INSERT INTO "messages" VALUES('msg_3',1,'user','I''m working on a home automation project using Home Assistant.',13,'2026-04-09T15:28:24.379231',3);
INSERT INTO "messages" VALUES('msg_4',1,'assistant','That sounds exciting! Home Assistant is great for home automation. What devices are you planning to control?',22,'2026-04-09T16:28:24.379231',4);
INSERT INTO "messages" VALUES('msg_5',1,'user','I want to control my lights, thermostat, and security cameras.',13,'2026-04-09T17:28:24.379231',5);
INSERT INTO "messages" VALUES('msg_6',1,'assistant','Here''s a suggested architecture:

1. **Lights**: Use Zigbee or Z-Wave bulbs with a compatible hub
2. **Thermostat**: Smart thermostat with local API (like Netatmo or Honeywell)
3. **Cameras**: ONVIF-compatible cameras for local streaming

I can help you set up the integration code for these.',57,'2026-04-09T18:28:24.379231',6);
INSERT INTO "messages" VALUES('msg_7',1,'user','Can you help me write an automation that turns on the porch light at sunset?',19,'2026-04-09T19:28:24.379231',7);
INSERT INTO "messages" VALUES('msg_8',1,'assistant','Here''s a Home Assistant automation:

```yaml
automation:
  - alias: Porch Light at Sunset
    trigger:
      - platform: sun
        event: sunset
        offset: ''-15''
    action:
      - service: light.turn_on
        target:
          entity_id: light.porch
        data:
          brightness_pct: 80
```

This turns on the porch light 15 minutes before sunset.',54,'2026-04-09T20:28:24.379231',8);
INSERT INTO "messages" VALUES('msg_9',2,'user','What''s the best way to organize Python code for a CLI tool?',15,'2026-04-12T13:28:24.379231',1);
INSERT INTO "messages" VALUES('msg_10',2,'assistant','For a CLI tool, I recommend this structure:

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
- Write tests with pytest',81,'2026-04-12T14:28:24.379231',2);
INSERT INTO "messages" VALUES('msg_11',2,'user','Should I use click or typer for the CLI?',11,'2026-04-12T15:28:24.379231',3);
INSERT INTO "messages" VALUES('msg_12',2,'assistant','Typer is the modern choice — it''s built on click but uses type hints for argument definitions. Less boilerplate, better IDE support. Use click only if you need very custom argument parsing.',41,'2026-04-12T16:28:24.379231',4);
INSERT INTO "messages" VALUES('msg_13',3,'user','I''m having trouble with my reverse osmosis water filter. When should I replace the filters?',19,'2026-04-15T13:28:24.379231',1);
INSERT INTO "messages" VALUES('msg_14',3,'assistant','For the Aquaphor DWM-101S (Морион) system:

| Filter | Replace every |
|--------|--------------|
| K2 (pre-carbon) | 6 months |
| K5 (sediment) | 3-6 months |
| K7M (mineralizing) | 6 months |
| KO-50S (membrane) | 12 months |

The next replacement is scheduled for September 1, 2026.',65,'2026-04-15T14:28:24.379231',2);
INSERT INTO "messages" VALUES('msg_15',3,'user','Thanks! Can you remind me to buy filters before September?',13,'2026-04-15T15:28:24.379231',3);
INSERT INTO "messages" VALUES('msg_16',3,'assistant','I''ve scheduled a reminder for August 31, 2026 at 17:00. The event ''💧 RO Filters: K2, K5, K7M'' will be added to your calendar.',31,'2026-04-15T16:28:24.379231',4);
CREATE TABLE summaries (
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
INSERT INTO "summaries" VALUES('leaf_001',1,0,'leaf','## Home Automation Session

**User**: Simo — home automation with Home Assistant

**Key discussions**:
- Architecture: Zigbee/Z-Wave lights, smart thermostat, ONVIF cameras
- Automation: porch light at sunset (15 min before, 80% brightness)

Expand for details about: home automation architecture, porch light automation',55,'2026-04-09T13:28:24.379231','2026-04-09T21:28:24.379231',0,1,'2026-04-19T10:28:24');
INSERT INTO "summaries" VALUES('leaf_002',2,0,'leaf','## Code Organization Session

**Key discussions**:
- Python CLI project structure: src layout, pyproject.toml, pytest
- CLI framework: Typer recommended over click (less boilerplate, type hints)

Expand for details about: Python project structure, CLI frameworks',45,'2026-04-12T13:28:24.379231','2026-04-12T17:28:24.379231',0,1,'2026-04-19T10:28:24');
INSERT INTO "summaries" VALUES('leaf_003',3,0,'leaf','## Water Filter Maintenance

**Appliance**: Aquaphor DWM-101S (Морион) RO system
**Filters**: K2 (6mo), K5 (3-6mo), K7M (6mo), KO-50S (12mo)
**Next replacement**: September 1, 2026
**Reminder**: August 31, 2026 at 17:00

Expand for details about: water filter schedule, filter types',50,'2026-04-15T13:28:24.379231','2026-04-15T17:28:24.379231',0,1,'2026-04-19T10:28:24');
INSERT INTO "summaries" VALUES('condensed_001',1,1,'condensed','## Condensed: Simo''s Sessions

**User**: Simo, Sofia, Bulgaria. Developer working on home automation and nanobot.

**Topics covered**:
1. Home automation with HA: lights, thermostat, cameras, porch light sunset automation
2. Python CLI project organization: src layout, Typer framework
3. Aquaphor DWM-101S water filter: replacement schedule (next Sept 2026)

**Upcoming**: RO filter replacement September 2026

Expand for details about: home automation, code organization, water filter maintenance',84,'2026-04-09T13:28:24.379231','2026-04-19T13:28:24.379231',3,0,'2026-04-19T10:28:24');
CREATE TABLE summary_messages (
            summary_id TEXT REFERENCES summaries(id),
            message_id TEXT REFERENCES messages(id),
            PRIMARY KEY (summary_id, message_id)
        );
INSERT INTO "summary_messages" VALUES('leaf_001','msg_1');
INSERT INTO "summary_messages" VALUES('leaf_001','msg_2');
INSERT INTO "summary_messages" VALUES('leaf_001','msg_3');
INSERT INTO "summary_messages" VALUES('leaf_001','msg_4');
INSERT INTO "summary_messages" VALUES('leaf_001','msg_5');
INSERT INTO "summary_messages" VALUES('leaf_001','msg_6');
INSERT INTO "summary_messages" VALUES('leaf_001','msg_7');
INSERT INTO "summary_messages" VALUES('leaf_001','msg_8');
INSERT INTO "summary_messages" VALUES('leaf_002','msg_9');
INSERT INTO "summary_messages" VALUES('leaf_002','msg_10');
INSERT INTO "summary_messages" VALUES('leaf_002','msg_11');
INSERT INTO "summary_messages" VALUES('leaf_002','msg_12');
INSERT INTO "summary_messages" VALUES('leaf_003','msg_13');
INSERT INTO "summary_messages" VALUES('leaf_003','msg_14');
INSERT INTO "summary_messages" VALUES('leaf_003','msg_15');
INSERT INTO "summary_messages" VALUES('leaf_003','msg_16');
CREATE TABLE summary_parents (
            summary_id TEXT PRIMARY KEY REFERENCES summaries(id),
            parent_summary_id TEXT REFERENCES summaries(id)
        );
INSERT INTO "summary_parents" VALUES('leaf_001','condensed_001');
INSERT INTO "summary_parents" VALUES('leaf_002','condensed_001');
INSERT INTO "summary_parents" VALUES('leaf_003','condensed_001');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('conversations',3);
INSERT INTO "sqlite_sequence" VALUES('context_items',5);
COMMIT;
