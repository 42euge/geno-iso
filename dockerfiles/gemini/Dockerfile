FROM geno-iso-base:latest

ARG GEMINI_CLI_VERSION=0.39.1

USER root
RUN npm install -g @google/gemini-cli@${GEMINI_CLI_VERSION}
USER agent

ENTRYPOINT ["gemini"]
CMD ["--help"]
