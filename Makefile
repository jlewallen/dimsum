default: checks

checks:
	env/bin/mypy *.py --ignore-missing-imports

run:
	env/bin/python3 dimsum.py

env:
	echo

freeze:
	pip3 freeze > requirements.txt
