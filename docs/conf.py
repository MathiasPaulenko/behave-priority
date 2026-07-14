"""Sphinx configuration for behave-priority documentation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path("..").resolve()))

project = "behave-priority"
copyright = "2024, behave-priority contributors"
author = "behave-priority contributors"
release = "0.1.0"
version = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = "behave-priority"
html_theme_options = {
    "source_repository": "https://github.com/MathiasPaulenko/behave-priority",
    "source_branch": "main",
    "source_directory": "docs/",
}

todo_include_todos = True

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "exclude-members": "__weakref__",
}

autosummary_generate = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "behave": ("https://behave.readthedocs.io/en/stable", None),
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = True
