FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates procps \
    && rm -rf /var/lib/apt/lists/*

# Install cloudflared (amd64 — we'll handle arm64 later)
RUN curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
    -o /tmp/cloudflared.deb && dpkg -i /tmp/cloudflared.deb && rm /tmp/cloudflared.deb

# Create non-root user
RUN groupadd -r corvus && useradd -r -g corvus -m -d /home/corvus -s /bin/bash corvus

# Install agy as corvus user
USER corvus
RUN curl -fsSL https://antigravity.google/cli/install.sh | bash
ENV PATH="/home/corvus/.local/bin:${PATH}"
USER root

# Python deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .
RUN chown -R corvus:corvus /app

# Create workspace mount point
RUN mkdir -p /workspace && chown corvus:corvus /workspace

# Boot script
COPY boot.py /app/boot.py
RUN chmod +x /app/entrypoint.sh

USER corvus
WORKDIR /app

EXPOSE 8000 8001

VOLUME /workspace

ENTRYPOINT ["/app/entrypoint.sh"]
