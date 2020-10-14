SHELL := /bin/bash

default: checks

checks: env
	env/bin/mypy *.py --ignore-missing-imports

run:
	env/bin/python3 dimsum.py

test:
	rm -f fieldkit.sqlite3
	env/bin/python3 test.py

env:
	python3 -m venv env
	source env/bin/activate && pip3 install -r requirements.txt
	echo remember to source env/bin/activate

freeze:
	pip3 freeze > requirements.txt

web:
	cd web && yarn serve

dump:
	sqlite3 test.sqlite3 "SELECT * FROM entities"
	sqlite3 world.sqlite3 "SELECT * FROM entities"

image:
	docker build -t jlewallen/dimsum .

image-test:
	docker run --name mud --env-file .env --rm -p 5000:5000 jlewallen/dimsum

.PHONY: web
