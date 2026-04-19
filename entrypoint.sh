#!/bin/bash
set -e

# Initialize LCM database from seed if not already present
if [ ! -f /root/.nanobot/lcm/lcm.db ]; then
    sqlite3 /root/.nanobot/lcm/lcm.db < /tmp/lcm_seed.sql
    sqlite3 /root/.nanobot/lcm/lcm.db "
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(content, content=messages, content_rowid=rowid);
        INSERT INTO messages_fts(rowid, content) SELECT rowid, content FROM messages;
        CREATE VIRTUAL TABLE IF NOT EXISTS summaries_fts USING fts5(content, content=summaries, content_rowid=rowid);
        INSERT INTO summaries_fts(rowid, content) SELECT rowid, content FROM summaries;
    "
fi

exec python3 -m nanobot "$@"
