#!/bin/bash

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $dir

virtualenv -p python3 ~/venvs/register-publisher
source ~/venvs/register-publisher/bin/activate

pip install -r requirements.txt
