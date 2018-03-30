#!/usr/bin/env bash

sphinx-apidoc -f -o . ../
sphinx-build -b html . _build