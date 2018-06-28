RST_DOCS_DIR=docs/rst

.PHONY: clean clean-test clean-pyc clean-build docs help \
	dev/bumpversion-path dev/bumpversion-minor dev/bumpversion-major
.DEFAULT_GOAL := help

# This doesn't evaluate until it's called. The -D argument is the
# directory of the target file ($@), kinda like `dirname`.
MANPAGES ?= $(patsubst %.rst.in,%,$(wildcard ./docs/man/man1/mazer*.1.rst.in))
ifneq ($(shell which rst2man 2>/dev/null),)
RST2MAN = rst2man $< $@
else ifneq ($(shell which rst2man.py 2>/dev/null),)
RST2MAN = rst2man.py $< $@
else
RST2MAN = @echo "ERROR: rst2man from docutils command is not installed but is required to build $(MANPAGES)" && exit 1
endif
GENERATE_CLI = docs/bin/generate_man.py

# Regenerate %.1.rst if %.1.rst.in has been modified more
# recently than %.1.rst.
%.1.rst: %.1.rst.in
	sed "s/%VERSION%/$(VERSION)/" $< > $@
	rm $<

# Regenerate %.1 if %.1.rst or ansible_galaxy/__init__.py (where __version__ is defined)
# has been modified more recently than %.1. (Implicitly runs the %.1.rst recipe)
%.1: %.1.rst ansible_galaxy/__init__.py
	$(RST2MAN)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

lint: ## check style with flake8
	flake8 ansible_galaxy_cli ansible_galaxy tests

test: ## run tests quickly with the default Python
	py.test

test-all: ## run tests on every Python version with tox
	tox

coverage: ## check code coverage quickly with the default Python
	coverage run --source ansible_galaxy_cli -m pytest
	coverage report -m
	coverage html

docs: ## generate Sphinx HTML documentation, including API docs
	rm -f $(RST_DOCS_DIR)/ansible_galaxy_cli.rst
	rm -f $(RST_DOCS_DIR)/modules.rst
	sphinx-apidoc -o $(RST_DOCS_DIR) ansible_galaxy_cli
	$(MAKE) -C $(RST_DOCS_DIR) clean
	$(MAKE) -C $(RST_DOCS_DIR) html

.PHONY: generate_rst
generate_man_rst: ansible_galaxy_cli/cli/*.py
	mkdir -p ./docs/man/man1/ ; \
	PYTHONPATH=./lib $(GENERATE_CLI) --template-file=docs/templates/man.j2 --output-dir=docs/man/man1/ --output-format man ansible_galaxy_cli/cli/*.py

man: generate_man_rst
	$(MAKE) $(MANPAGES)

dev/bumpversion-patch:
	bumpversion --verbose patch

dev/bumpversion-minor:
	bumpversion --verbose minor

dev/bumpversion-major:
	bumpversion --verbose major

dev/release: dist ## package and upload a release
	twine upload dist/*

dev/dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install
