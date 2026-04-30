FROM geno-iso-claude:latest

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libcairo2-dev libpango1.0-dev \
    && rm -rf /var/lib/apt/lists/*
USER agent
