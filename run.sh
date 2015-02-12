#!/usr/bin/env bash

if [ "$1" = "-d" ]
  then
  source ./environment.sh
  python run.py
else
  foreman start
fi
