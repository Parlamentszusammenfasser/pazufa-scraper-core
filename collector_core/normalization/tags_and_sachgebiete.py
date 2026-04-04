from pathlib import Path
import json
import yaml
import numpy as np
from ..tags_and_sachgebiete_model import Tag, Sachgebiet, TagFile, SachgebietFile, BaseTagFile

GLOBAL_TAGS_PATH = "global_tags.yaml"
SACHGEBIETE_PATH = "sachgebiete.yaml"

# =====================================================================
# private helper functions
# =====================================================================


def _load_global_tags() -> list[dict]:
    tags_list = {}

    




def _load_sachgebiete() -> list[dict]:
    pass


def _load_local_tags() -> list[dict]:
    pass


# =====================================================================
# Public lifetime functions
# =====================================================================


def generate_tags_npy():
    pass


def generate_sachgebiete_npy():
    pass


# =====================================================================
# Public action functions
# =====================================================================


def get_tags_json():
    pass


def get_tags_npy():
    pass


def get_sachgebiete_json():
    pass


def get_sachgebiete_npy():
    pass


def check_tags():
    # optional give local path to tags.npy for faster checks
    pass
