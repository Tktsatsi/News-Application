# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
import django

BASE_DIR = os.path.abspath("..")
sys.path.insert(0, BASE_DIR)

# Path to the Django project folder (News_app)
DJANGO_PROJECT_DIR = os.path.abspath("../News_app")
sys.path.insert(0, DJANGO_PROJECT_DIR)

os.environ["DJANGO_SETTINGS_MODULE"] = "news_project.settings"
django.setup()

project = 'News-application'
copyright = '2025, Tshidiso Tsatsi'
author = 'Tshidiso Tsatsi'
release = '00.00.01'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon"
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
