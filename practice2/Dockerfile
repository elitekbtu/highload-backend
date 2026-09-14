FROM python:3.12-bookworm

ARG TARGETARCH

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        iproute2 \
        iputils-ping \
        procps \
    && rm -rf /var/lib/apt/lists/*

# Caddy (h1/h2/h3) and k6 — linux/amd64 and linux/arm64 (Apple Silicon)
RUN set -eux; \
    curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v2.11.4/caddy_2.11.4_linux_${TARGETARCH}.tar.gz" \
      | tar -xz -C /usr/local/bin caddy; \
    curl -fsSL "https://github.com/grafana/k6/releases/download/v1.8.1/k6-v1.8.1-linux-${TARGETARCH}.tar.gz" \
      | tar -xz --strip-components=1 -C /tmp; \
    mv /tmp/k6 /usr/local/bin/k6; \
    caddy version; \
    k6 version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/key_generate.py scripts/key_generate.py
RUN python scripts/key_generate.py

COPY . .

COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh netem.sh

EXPOSE 9443 9444
EXPOSE 9443/udp

ENTRYPOINT ["/docker-entrypoint.sh"]
