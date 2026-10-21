# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e

FROM python:3.15@sha256:4e324f579bdd7d0ce3cbae52e27bddeb316c9c23aa7563ac6a9811bbca55541b AS builder

WORKDIR /build

ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_NO_INPUT=on
ENV PIP_PREFER_BINARY=on
ENV PIP_PROGRESS_BAR=off

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN uv export --no-dev --no-editable | uv pip install --system --no-deps -r -

# pre-build the frontend for serving on `/` and on `/admin`, using a placeholder for
# the api url that is replaced at runtime (see `mex/admin/frontend.py`),
# the root build uses an empty frontend path, because `/` breaks the vite base url
ENV REFLEX_API_URL=http://mex-api-url-placeholder
RUN REFLEX_FRONTEND_PATH= reflex export --frontend-only --no-zip --no-ssr \
    && mkdir dist \
    && mv .web/build/client dist/root \
    && rm -rf .web
RUN REFLEX_FRONTEND_PATH=/admin reflex export --frontend-only --no-zip --no-ssr \
    && mv .web/build/client dist/admin \
    && rm -rf .web

FROM python:3.15-slim@sha256:f5b92f2a669a4c347044f29367f31983280b648250ca94dea66f98c53bc87e58

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

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.15/site-packages /usr/local/lib/python3.15/site-packages
COPY --from=builder /usr/local/bin/admin-api /usr/local/bin/admin-api
COPY --from=builder /usr/local/bin/admin-frontend /usr/local/bin/admin-frontend
COPY --from=builder --chown=10001 /build/assets assets
COPY --from=builder --chown=10001 /build/rxconfig.py rxconfig.py
COPY --from=builder --chown=10001 /build/dist dist

RUN chown 10001 /app

USER 10001

EXPOSE 8030
EXPOSE 8031

ENTRYPOINT [ "admin-frontend" ]
