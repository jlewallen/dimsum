default: checks

checks:
	env/bin/mypy *.py

run:
	env/bin/python3 dimsum.py

env:
	echo

freeze:
	pip3 freeze > requirements.txt
