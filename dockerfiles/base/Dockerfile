FROM node:22-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ripgrep \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    gpg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash agent
USER agent
WORKDIR /home/agent

RUN mkdir -p /home/agent/.config /home/agent/.claude
