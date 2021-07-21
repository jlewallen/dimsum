FROM python:3.9-slim AS python-venv-image

RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc
RUN python -m venv /app/venv
# Make sure we use the virtualenv:
ENV PATH="/app/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN ls -alh /app

FROM node:16 AS build-nodejs-image

WORKDIR /app
COPY src/web /app/src/web/
RUN cd src/web && npm install && npm run build
RUN ls -alh /app
RUN ls -alh /app/src
RUN ls -alh /app/src/web/dist

FROM bash

WORKDIR /app

ENV PATH="/app/venv/bin:$PATH"

COPY --from=python-venv-image /app/venv /app/venv
COPY --from=build-nodejs-image /app/src/web/dist /app/static
COPY src/dimsum /app

RUN ls -alh /app

CMD [ "python", "/app/src/dimsum/cli.py" ]
