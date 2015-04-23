#!/usr/bin/env bash

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $dir

source ~/venvs/register-publisher/bin/activate
source ./environment-test.sh

mkdir -p logs
> logs/debug.log
> logs/errors.log

py.test --junitxml=TEST-register-publisher.xml --cov application --cov-report term-missing -v tests "$@"

