VENV := $(shell echo $${VIRTUAL_ENV-.venv})
INSTALL_STAMP := $(VENV)/.install.stamp

$(INSTALL_STAMP): pyproject.toml poetry.lock
	python -m venv $(VENV)
	$(VENV)/bin/python -m pip install poetry
	$(VENV)/bin/python -m poetry install --no-root
	touch $(INSTALL_STAMP)

.PHONY: format
format: $(INSTALL_STAMP)
	$(VENV)/bin/python -m poetry run ruff check --fix *.py
	$(VENV)/bin/python -m poetry run ruff format *.py

.PHONY: lint
lint: $(INSTALL_STAMP)
	$(VENV)/bin/python -m poetry run ruff check *.py
	$(VENV)/bin/python -m poetry run ruff format --check *.py

.PHONY: start
start: $(INSTALL_STAMP)
	$(VENV)/bin/python -m poetry run python script.py

.PHONY: test
test: $(INSTALL_STAMP)
	$(VENV)/bin/python -m poetry run py.test test.py
