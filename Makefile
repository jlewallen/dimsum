SHELL := /bin/bash

default: checks test

checks: env
	env/bin/mypy *.py --ignore-missing-imports

clean:
	rm -rf env
	rm -rf web/node_modules

run:
	env/bin/python3 dimsum.py

test: env
	rm -f test*.sqlite3
	env/bin/python3 -m pytest test_*.py

prettier: env
	python3 -m black .

env:
	python3 -m venv env
	source env/bin/activate && pip3 install -r requirements.txt
	echo remember to source env/bin/activate

freeze:
	pip3 freeze > requirements.txt

web/src/config:
	cp web/src/config.ts.dev web/src/config.ts

web/node_modules:
	cd web && yarn install

web: web/node_modules web/src/config
	cd web && yarn serve

image:
	docker build -t jlewallen/dimsum .

image-test:
	docker run --name mud --env-file .env --rm -p 5000:5000 -v `pwd`/world.sqlite3:/app/world.sqlite3 jlewallen/dimsum

prod-image:
	cp web/src/config.ts.prod web/src/config.ts
	docker build -t jlewallen/dimsum .

prod-server:
	docker run --name mud --env-file .env --rm -p 5000:5000 -v `pwd`/world.sqlite3:/app/world.sqlite3 -d jlewallen/dimsum

.PHONY: web
