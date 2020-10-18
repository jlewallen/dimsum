#!/bin/bash

sqlite3 $1 "SELECT serialized FROM entities" | jq .
