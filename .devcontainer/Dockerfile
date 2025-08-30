# Devcontainer image for paper-notes
FROM mcr.microsoft.com/devcontainers/python:3.11

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install docs toolchain at build time
RUN pip install --no-cache-dir mkdocs-material

