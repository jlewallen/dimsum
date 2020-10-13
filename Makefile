default: checks

checks:
	env/bin/mypy *.py --ignore-missing-imports

run:
	env/bin/python3 dimsum.py

test:
	rm -f fieldkit.sqlite3
	env/bin/python3 test.py

env:
	echo

freeze:
	pip3 freeze > requirements.txt

web:
	cd web && yarn serve

dump:
	sqlite3 test.sqlite3 "SELECT * FROM entities"
	sqlite3 world.sqlite3 "SELECT * FROM entities"

.PHONY: web
