# Setup

This document describes the setup of the repo itself and some common setup tasks between all three sub repos (not implemented yet).

For more detail, look at the setup files in the sub repos (not implemented yet).

## Requirements

- Python 3.12+
- Poetry 2.x

 For the full dependency list, see [pyproject.toml](pyproject.toml). 

## Installation

### Stable

> No stable release yet!

Once published, install using Poetry (advised) or pip.

It is strongly advised to pin the version below the next minor (`x.Y`) release, as minor bumps indicate major reworks that will most likely be breaking.

The examples below prescribe a version `0.1` and above, but under `0.2`.

**Poetry:**

```bash
poetry add "collector-core~=0.1"
```

**pip:**

```bash
pip install "collector-core~=0.1"
```


### Development

Clone the repository and install it with dev dependencies:

```bash
git clone https://codeberg.org/PaZuFa/pazufa-scraper-core.git
cd pazufa-collector-core
poetry install --with dev
```

Or install the latest development branch directly into another project:

**Poetry:**

```bash
poetry add "git+https://codeberg.org/PaZuFa/pazufa-scraper-core.git@develop"
```

**pip:**

```bash
pip install "git+https://codeberg.org/PaZuFa/pazufa-scraper-core.git@develop"
```

## CI Workflow

The project uses [Woodpecker CI](https://woodpecker-ci.org/) and runs on every push and pull request. The pipeline consists of four steps, with the last three running in parallel after setup:

| Step                    | What it does                                                        |
|-------------------------|---------------------------------------------------------------------|
| `setup`                 | Installs Poetry and all dependencies (including dev) into a `.venv` |
| `check-lock`            | Verifies the `poetry.lock` file is consistent with `pyproject.toml` |
| `format-and-type-check` | Runs `ruff format --check`, `ruff check`, and `mypy`                |
| `test`                  | Runs the test suite via `pytest`                                    |

All steps use `python:3.12-slim`. The virtualenv is created inside the project (`.venv/`) so later steps can use it directly without reinstalling.

## Usage

For usage documentation see the [wiki](https://wiki.pazufa.de/books/scraper-core).

## Known Issues

- **Some Poetry commands fail:**
  - Due to the dynamic description of dependencies in the pyproject.toml some Poetry commands like `poetry self show` sometimes do not acknowledge the `poetry.lock` file. This is a known Poetry issue and only cosmetic.
