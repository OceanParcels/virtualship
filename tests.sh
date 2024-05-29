#!/bin/sh

# Runs the tests and creates a code coverage report.

pytest --cov=virtual_ship --cov-report=html tests
