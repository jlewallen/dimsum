default: checks

checks:
	env/bin/mypy *.py --ignore-missing-imports

run:
	env/bin/python3 dimsum.py

test:
	env/bin/python3 test.py

env:
	echo

freeze:
	pip3 freeze > requirements.txt

dump:
	sqlite3 test.sqlite3 "SELECT * FROM entities"
