FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libsqlite3-dev sqlite3 iputils-ping \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 sungrid && useradd -u 1000 -g 1000 -m -s /bin/bash sungrid

WORKDIR /app
COPY pyproject.toml ./
RUN pip install -e '.[dev]'

COPY --chown=sungrid:sungrid . .
RUN mkdir -p /data && chown sungrid:sungrid /data

USER sungrid
EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "sungrid.asgi:application"]
