# Devcontainer image for paper-notes
FROM mcr.microsoft.com/devcontainers/python:3.11

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install docs toolchain at build time
RUN pip install --no-cache-dir mkdocs-material

# Install Volta (Node toolchain) for user 'vscode' and provision Node LTS
ENV VOLTA_HOME=/home/vscode/.volta
ENV PATH=${VOLTA_HOME}/bin:${PATH}
RUN mkdir -p /home/vscode \
    && chown -R vscode:vscode /home/vscode
USER vscode
RUN curl -fsSL https://get.volta.sh | bash -s -- --skip-setup \
    && ${VOLTA_HOME}/bin/volta install node@lts npm@latest yarn@latest pnpm@latest
USER root
