# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/stable/config

import os.path

root = os.path.dirname(__file__)

project = 'async2v'
copyright = '2018, Thomas Reifenberger'
author = 'Thomas Reifenberger'

# The short X.Y version
version = ''
# The full version, including alpha/beta/rc tags
release = ''

extensions = [
    'sphinx.ext.autosummary',
    'sphinx.ext.autodoc',
    'sphinx_autodoc_typehints',
    'sphinx.ext.coverage',
]

templates_path = ['_templates']

master_doc = 'index'

language = None
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = ['_static']
htmlhelp_basename = 'async2vdoc'


def run_apidoc(_):
    import better_apidoc
    better_apidoc.main([
        'better-apidoc',
        '--no-toc',
        '--templates', os.path.join(root, '_templates'),
        '--force',
        '--separate',
        '--output-dir', os.path.join(root, 'api'),
        os.path.join(root, '..', 'async2v'),
    ])


autodoc_member_order = 'bysource'
add_module_names = False
default_role = 'any'
autodoc_default_flags = ['members', 'show-inheritance']


def setup(app):
    app.connect('builder-inited', run_apidoc)
