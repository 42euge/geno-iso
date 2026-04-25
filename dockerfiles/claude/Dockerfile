FROM geno-iso-base:latest

ARG CLAUDE_CODE_VERSION=2.1.119

USER root
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
USER agent

RUN mkdir -p /home/agent/.claude

ENTRYPOINT ["claude"]
CMD ["--help"]
