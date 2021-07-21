#!/bin/bash

PATH=/app/venv/bin:$PATH

nginx -c /app/nginx.conf &

pushd /app
python cli.py --no-colors server --unix-socket /tmp/uvicorn.sock "$@"
popd
