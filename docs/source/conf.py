# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'fedcal'
copyright = '2023, Adam Poulemanos'
author = 'Adam Poulemanos'
release = 'pre-alpha'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration


extensions: list[str] = [
    "autoapi.extension",
    "sphinx.ext.autodoc.typehints",
    "sphinx.ext.autosummary",
    "numpydoc",
]

autodoc_typehints = 'description'

templates_path: list[str] = ["_templates"]
exclude_patterns: list[Any] = []

autoapi_type = 'python'
autoapi_dirs = ['/home/uniquemarlin/Documents/dev/fedcal/fedcal/']
autoapi_options = ['members', 'show-inheritance']
autoapi_ignore = ["/home/uniquemarlin/anaconda3/envs/federal_calendar/lib/python3.11/site-packages/*"]
autoapi_python_use_implicit_namespaces = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme: str = "sphinx_rtd_theme"
html_static_path: list[str] = ["_static"]
