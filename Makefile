VERSION	?= minor
VIRTUAL_ENV ?= env

.PHONY: version
version:
	pip install bump2version
	bump2version $(VERSION)
	git checkout master
	git pull
	git merge develop
	git checkout develop
	git push origin develop master
	git push --tags

.PHONY: minor
minor:
	make version VERSION=minor

.PHONY: patch
patch:
	make version VERSION=patch

.PHONY: major
major:
	make version VERSION=major


.PHONY: clean
# target: clean - Display callable targets
clean:
	rm -rf build/ dist/ docs/_build *.egg-info
	find $(CURDIR) -name "*.py[co]" -delete
	find $(CURDIR) -name "*.orig" -delete
	find $(CURDIR)/$(MODULE) -name "__pycache__" | xargs rm -rf

$(VIRTUAL_ENV): setup.cfg
	@[ -d $(VIRTUAL_ENV) ] || python -m venv $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/pip install -e .[tests]
	@touch $(VIRTUAL_ENV)

.PHONY: test
test t: $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/pytest tests.py

.PHONY: mypy
mypy: $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/mypy aiopeewee

.PHONY: example
example: $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/pip install uvicorn asgi-tools
	@$(VIRTUAL_ENV)/bin/uvicorn --port 5000 example:app

