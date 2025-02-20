from __future__ import annotations

import importlib.metadata

project = "Virtual Ship Parcels"
copyright = "2024, Emma Daniëls"
author = "Emma Daniëls"
version = release = importlib.metadata.version("virtualship")

extensions = [
    "myst_parser",
    "nbsphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    # "sphinx_autodoc_typehints",# https://github.com/OceanParcels/virtualship/pull/125#issuecomment-2668766302
    "sphinx_copybutton",
]

source_suffix = [".rst", ".md"]
exclude_patterns = [
    "_build",
    "**.ipynb_checkpoints",
    "Thumbs.db",
    ".DS_Store",
    ".env",
    ".venv",
]

html_theme = "pydata_sphinx_theme"

html_theme_options = {
    "logo": {
        "text": "Virtual Ship Parcels",
        "image_light": "virtual_ship_logo_no_text.png",
        "image_dark": "virtual_ship_logo_inverted_no_text.png",
    },
    "use_edit_page_button": True,
    "github_url": "https://github.com/OceanParcels/virtualship",
    "icon_links": [
        {
            "name": "Conda Forge",
            "url": "https://anaconda.org/conda-forge/virtualship",  # required
            "icon": "fa-solid fa-box",
            "type": "fontawesome",
        }
    ],
}
html_context = {
    "github_user": "OceanParcels",
    "github_repo": "virtualship",
    "github_version": "main",
    "doc_path": "docs",
}
html_show_sourcelink = False
html_static_path = ["_static"]

myst_enable_extensions = [
    "colon_fence",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

nitpick_ignore = [
    ("py:class", "_io.StringIO"),
    ("py:class", "_io.BytesIO"),
]

always_document_param_types = True

nbsphinx_thumbnails = {
    "user-guide/assignments/Research_proposal_intro": "user-guide/_images/MFPtimeline.jpg",
    "user-guide/assignments/Research_Proposal_only": "user-guide/_images/MFP.jpg",
    "user-guide/assignments/Virtualship_research_proposal": "user-guide/_images/AnnaWeber.jpeg",
    "user-guide/assignments/sciencecommunication_assignment": "user-guide/_images/marine_ss.jpg",
    "user-guide/assignments/Sail_the_ship": "user-guide/_images/vessel.jpg",
}
