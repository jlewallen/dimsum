FROM python:3.9-slim AS python-venv-image

RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc
RUN python -m venv /app/venv
# Make sure we use the virtualenv:
ENV PATH="/app/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM node:16 AS build-nodejs-image

WORKDIR /app
COPY src/web /app/src/web/
COPY src/web/src/config.ts.prod /app/src/web/src/config.ts
RUN cd src/web && yarn install && npx browserslist@latest --update-db && yarn run build

FROM python:3.9-slim

RUN apt-get update && apt-get install -y --no-install-recommends nginx && apt-get clean

WORKDIR /app

ENV PATH="/app/venv/bin:$PATH"

COPY tools/nginx.conf /app
COPY --from=python-venv-image /app/venv /app/venv
COPY --from=build-nodejs-image /app/src/web/dist /app/static
COPY src/dimsum /app
COPY logging.json /app
COPY dimsum.conf /app
COPY ssh_host_key /app
COPY ssh_host_key.pub /app

ADD ./tools/startup.sh /app/startup.sh
RUN chmod u+x /app/startup.sh

ENTRYPOINT [ "/app/startup.sh" ]
