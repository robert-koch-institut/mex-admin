# syntax=docker/dockerfile:1

FROM python:3.14-trixie AS builder

WORKDIR /build

ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_NO_INPUT=on
ENV PIP_PREFER_BINARY=on
ENV PIP_PROGRESS_BAR=off

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN uv export --frozen --no-hashes --no-dev --output-file requirements.lock

RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.lock
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels --no-deps .


FROM python:3.14-slim-trixie

LABEL org.opencontainers.image.authors="mex@rki.de"
LABEL org.opencontainers.image.description="Metadata admin web application."
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.url="https://github.com/robert-koch-institut/mex-admin"
LABEL org.opencontainers.image.vendor="robert-koch-institut"

ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=1

ENV REFLEX_APP_NAME=mex
ENV REFLEX_FRONTEND_PORT=8030
ENV REFLEX_DEPLOY_URL=http://localhost:8030
ENV REFLEX_BACKEND_PORT=8031
ENV REFLEX_API_URL=http://localhost:8031
ENV REFLEX_TELEMETRY_ENABLED=False
ENV REFLEX_ENV_MODE=prod
ENV REFLEX_DIR=/app/reflex

WORKDIR /app

RUN apt-get update && apt-get install -y unzip curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/wheels /wheels

RUN pip install --no-cache-dir \
    --no-index \
    --find-links=/wheels \
    /wheels/*.whl \
    && rm -rf /wheels

RUN adduser \
    --disabled-password \
    --gecos "" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "10001" \
    mex

RUN chown mex:mex /app

COPY --chown=mex assets assets
COPY --chown=mex rxconfig.py rxconfig.py

USER mex

EXPOSE 8030
EXPOSE 8031

ENTRYPOINT [ "admin" ]
