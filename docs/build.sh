#!/usr/bin/env bash

rm -rf _build
rm -f api/*
#sphinx-apidoc \
better-apidoc \
    --separate \
    --no-toc \
    --templates _templates \
    -f -o api ../async2v
sphinx-build -b html . _build
