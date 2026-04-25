FROM node:22-slim

ARG CLAUDE_CODE_VERSION=2.1.119

RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash claude
USER claude
WORKDIR /home/claude

RUN mkdir -p /home/claude/.claude

ENTRYPOINT ["claude"]
CMD ["--help"]
