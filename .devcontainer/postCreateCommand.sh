#! /usr/bin/env bash

git config --global --add safe.directory /workspaces/$(basename $(pwd))


# Install Dependencies
pipx install poetry
poetry config virtualenvs.in-project true
poetry install

poetry run python -m ipykernel install --user --name=pyswap --display-name "Python (simplesoilprofile)"

# Install pre-commit hooks
poetry run pre-commit install --install-hooks

mkdir -p .logs
