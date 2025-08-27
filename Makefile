.PHONY: help install lint format type test cov build release

help:
	@echo "Common tasks:\n  install, lint, format, type, test, cov, build, release"

install:
	python -m pip install -U pip
	pip install -e .[dev]
	pre-commit install

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .
	ruff format .
	echo "Formatted."

type:
	mypy src

test:
	pytest

cov:
	coverage run -m pytest && coverage report -m

build:
	python -m build

release:
	@echo "Tagging and pushing tag for release..."
	@git tag -a v$$(python -c 'import importlib; print(importlib.import_module("biox").__version__)') -m "Release"
	@git push --tags
