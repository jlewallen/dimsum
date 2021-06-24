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

server:
	uvicorn --app-dir src/dimsum --log-config logging.yml --reload dimsum:app

graph:
	+@for m in *.sqlite3; do                                               \
	n=`basename $$m .sqlite3`;                                             \
	rm -f $n.json;                                                         \
	env/bin/python3 src/dimsum/cli.py export --path $$m | jq . > $$n.json; \
	env/bin/python3 src/dimsum/cli.py graph --path $$m;                    \
	dot -T png $$n.dot > $$n.png;                                          \
	done

.PHONY: web
