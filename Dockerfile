FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install only what's needed for eval
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates git sqlite3 && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all source
COPY nanobot/ nanobot/
COPY pyproject.toml README.md LICENSE ./

# Remove bridge force-include from pyproject.toml (not needed for eval)
RUN sed -i '/"bridge".*"nanobot\/bridge"/d' pyproject.toml && \
    sed -i '/force-include/d' pyproject.toml

# Install all dependencies
RUN uv pip install --system --no-cache .

# Copy source again (overwrites installed)
COPY nanobot/ nanobot/

# Create eval workspace
RUN mkdir -p /root/.nanobot/lcm

# Copy LCM seed data
COPY eval/lcm_seed.sql /tmp/lcm_seed.sql

# Create entrypoint script
RUN echo '#!/bin/bash' > /entrypoint.sh && \
    echo 'set -e' >> /entrypoint.sh && \
    echo 'if [ ! -f /root/.nanobot/lcm/lcm.db ]; then' >> /entrypoint.sh && \
    echo '    echo "Initializing LCM with seed data..."' >> /entrypoint.sh && \
    echo '    sqlite3 /root/.nanobot/lcm/lcm.db < /tmp/lcm_seed.sql' >> /entrypoint.sh && \
    echo '    sqlite3 /root/.nanobot/lcm/lcm.db "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(content, content=messages, content_rowid=rowid); INSERT INTO messages_fts(rowid, content) SELECT rowid, content FROM messages;"' >> /entrypoint.sh && \
    echo '    sqlite3 /root/.nanobot/lcm/lcm.db "CREATE VIRTUAL TABLE IF NOT EXISTS summaries_fts USING fts5(content, content=summaries, content_rowid=rowid); INSERT INTO summaries_fts(rowid, content) SELECT rowid, content FROM summaries;"' >> /entrypoint.sh && \
    echo '    chmod 644 /root/.nanobot/lcm/lcm.db' >> /entrypoint.sh && \
    echo 'fi' >> /entrypoint.sh && \
    echo 'exec python3 -m nanobot "$@"' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
