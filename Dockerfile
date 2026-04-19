FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates git sqlite3 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY nanobot/ nanobot/
COPY pyproject.toml README.md LICENSE ./

# Remove bridge (not needed for eval)
RUN sed -i '/"bridge".*"nanobot\/bridge"/d' pyproject.toml && \
    sed -i '/force-include/d' pyproject.toml

RUN uv pip install --system --no-cache .

# Overwrite with source (in case install clobbered anything)
COPY nanobot/ nanobot/

# Workspace structure
RUN mkdir -p /root/.nanobot/lcm /root/.nanobot/credentials

# LCM seed data (SQL loaded by entrypoint)
COPY eval/fixtures/lcm_seed.sql /tmp/lcm_seed.sql

# Pre-baked config — merge_config.py already injected secrets at build time
COPY eval/config/merged_config.json /root/.nanobot/config.json

COPY eval/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
