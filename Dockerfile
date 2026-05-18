# STAGE 1: Builder
FROM python:3.13-alpine AS builder
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir aiomysql pymysql

# STAGE 2: Production
FROM python:3.13-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Forçamos o Python a olhar para a pasta src como a raiz do código
    PYTHONPATH="/app/src"

RUN apk add --no-cache curl && rm -rf /var/cache/apk/*
RUN addgroup -g 1001 appuser && adduser -D -u 1001 -G appuser appuser && \
    mkdir -p /app/logs && chown -R appuser:appuser /app

# O segredo está aqui: vamos trabalhar DIRETO na src
WORKDIR /app
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
COPY --chown=appuser:appuser . /app

WORKDIR /app/src
USER appuser

# Healthcheck ajustado para a porta interna
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f https://localhost:4443/health --insecure || exit 1

EXPOSE 4443/tcp
EXPOSE 4443/udp

# Comandos simplificados: como o WORKDIR já é /app/src, não precisa repetir "src/..."
ENTRYPOINT ["hypercorn", "--certfile", "cert/cert.pem", "--keyfile", "cert/ecc-key.pem"]
CMD ["--bind", "0.0.0.0:4443", "--quic-bind", "0.0.0.0:4443", "main:app"]