#!/usr/bin/env bash

set -eu

rm -rf _build
rm -f api/*
better-apidoc \
    --separate \
    --no-toc \
    --templates _templates \
    -f -o api ../async2v
sphinx-build -b coverage . _build
sphinx-build -b html . _build
