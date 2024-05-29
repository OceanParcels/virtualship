#!/bin/sh

# Runs all codetools and attempts to apply fixes wherever possible.
# Not suitable for the CI as that should not make any changes.

set -e

# Set working directory to the directory of this script.
cd "$(dirname "$0")"

PACKAGE=virtual_ship
TESTS=tests

echo "--------------"
echo "flake8"
echo "--------------"
flake8 ./$PACKAGE ./$TESTS
# darglint is ran as a plugin for flake8.

echo "--------------"
echo "pydocstyle"
echo "--------------"
pydocstyle ./$PACKAGE

echo "--------------"
echo "sort-all"
echo "--------------"
find ./$PACKAGE -type f -name '__init__.py' -print0 | xargs -0 sort-all

echo "--------------"
echo "black"
echo "--------------"
black ./$PACKAGE ./$TESTS

echo "--------------"
echo "isort"
echo "--------------"
isort ./$PACKAGE ./$TESTS

