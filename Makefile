SHELL := /bin/bash

default: checks test

checks: env
	env/bin/mypy src/dimsum/*.py --ignore-missing-imports

clean:
	rm -rf env
	rm -rf src/web/node_modules

run:
	env/bin/python3 src/dimsum/dimsum.py

test: env
	rm -f test*.sqlite3
	env/bin/python3 -m pytest src/dimsum/test_*.py

prettier: env
	python3 -m black .

env:
	python3 -m venv env
	source env/bin/activate && pip3 install -r requirements.txt
	echo
	echo remember to source env/bin/activate
	echo

freeze:
	pip3 freeze > requirements.txt

src/web/src/config:
	cp src/web/src/config.ts.dev src/web/src/config.ts

src/web/node_modules:
	cd src/web && yarn install

web: src/web/node_modules src/web/src/config
	cd src/web && yarn serve

image:
	docker build -t jlewallen/dimsum .

image-test:
	docker run --name mud --env-file .env --rm -p 5000:5000 -v `pwd`/world.sqlite3:/app/world.sqlite3 jlewallen/dimsum

prod-image:
	cp src/web/src/config.ts.prod src/web/src/config.ts
	docker build -t jlewallen/dimsum .

prod-server:
	docker run --name mud --env-file .env --rm -p 5000:5000 -v `pwd`/world.sqlite3:/app/world.sqlite3 -d jlewallen/dimsum

graph:
	env/bin/python3 src/dimsum/dump.py world.sqlite3
	jq . world.json > world-pretty.json && mv world-pretty.json world.json
	dot -T png world.dot > world.png
	env/bin/python3 src/dimsum/dump.py test.sqlite3
	jq . test.json > test-pretty.json && mv test-pretty.json test.json
	dot -T png test.dot > test.png

.PHONY: web
