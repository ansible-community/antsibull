#!/bin/sh
if [ "$1" == "" ]; then
    echo "Syntax: $0 <version_number>"
    exit -1
fi
sed -i "s/^version = \".*\"$/version = \"$1\"/g" pyproject.toml
sed -i "s/^sphinx-antsibull-ext = \".*\"$/sphinx-antsibull-ext = \"==$1\"/g" pyproject.toml
sed -i "s/^version = \".*\"$/version = \"$1\"/g" sphinx-extension/pyproject.toml
