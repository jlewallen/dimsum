SHELL := /bin/bash

default: checks test

uvicorn:
	uvicorn --app-dir src/dimsum --log-config `pwd`/logging.json --reload --factory dimsum:app

checks: env
	env/bin/mypy src/dimsum --ignore-missing-imports

clean:
	rm -rf env
	rm -rf src/web/node_modules

test: env
	rm -f test*.sqlite3
	env/bin/coverage run -m pytest src/dimsum/test_*.py

coverage: test
	env/bin/coverage html

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

gqlgen:
	cd src/web && npm run gqlgen

src/web/src/config:
	cp src/web/src/config.ts.dev src/web/src/config.ts

src/web/node_modules:
	cd src/web && yarn install

web: src/web/node_modules src/web/src/config
	cd src/web && yarn serve --port 8082

wiki:
	./ds load-wiki --directory docs  --user jlewallen --database world.sqlite3

graph:
	rm -rf gen
	mkdir -p gen
	for m in *.sqlite3; do                                                     \
	n=`basename $$m .sqlite3`;                                                 \
	env/bin/python3 src/dimsum/cli.py export --path $$m | jq . > gen/$$n.json; \
	env/bin/python3 src/dimsum/cli.py graph --path $$m --output gen/$$n.dot;   \
	dot -T png gen/$$n.dot > gen/$$n.png;                                      \
	done

.PHONY: web
