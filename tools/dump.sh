#!/bin/bash

if [ -z "$1" ]; then
	echo "usage: dump.sh <database>"
	exit 2
fi

sqlite3 $1 "SELECT serialized FROM entities" | jq .
