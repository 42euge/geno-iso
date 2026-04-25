FROM geno-iso-base:latest

ARG CODEX_VERSION=latest

USER root
RUN npm install -g @openai/codex@${CODEX_VERSION}
USER agent

ENTRYPOINT ["codex"]
CMD ["--help"]
