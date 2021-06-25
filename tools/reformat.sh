#!/bin/bash

for a in *.json; do
	cat $a | jq . > "$a-temp"
	mv -f "$a-temp" $a
done
