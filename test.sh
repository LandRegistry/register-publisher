#!/usr/bin/env bash

source ./environment-test.sh
py.test --cov application  --cov-report term-missing -v tests