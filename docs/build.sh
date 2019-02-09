#!/usr/bin/env bash

set -eu

rm -rf _build
rm -f api/*
sphinx-build -b coverage . _build
sphinx-build -b html . _build
