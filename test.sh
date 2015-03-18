#!/usr/bin/env bash

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $dir

source ~/venvs/register-publisher/bin/activate
source ./environment-test.sh

py.test --junitxml=TEST-register-publisher.xml --cov application --cov-report term-missing -v tests
