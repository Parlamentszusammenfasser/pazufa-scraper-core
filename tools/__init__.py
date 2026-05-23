"""Tools for pazufa_corelib.

YAML validator entry points — each can be run as a script or imported
from its own module:

- ``tools.yaml_validator_authors.yaml_validator_authors`` — validate a
  candidate author YAML file against the existing vocabulary.
- ``tools.yaml_validator_organizations.yaml_validator_organizations`` —
  validate a candidate organization YAML file against the existing vocabulary.
- ``tools.yaml_validator_tags.yaml_validator_tags`` — validate a candidate
  tag YAML file against the existing vocabulary.

Run from the CLI, e.g.::

    poetry run python -m tools.yaml_validator_authors candidate.yaml
    poetry run python -m tools.yaml_validator_organizations candidate.yaml
    poetry run python -m tools.yaml_validator_tags candidate.yaml

Or import the functions directly from their modules::

    from tools.yaml_validator_authors import yaml_validator_authors

See ``SETUP_NORMALIZATION.md`` (section "Validating New Files Before Merging")
for details on the checks, thresholds, and reference-file semantics.
"""
