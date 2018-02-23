#!/bin/bash

mkdir ../build
python ../setup.py sdist
pip install -U --user -b ../build ../dist/*
rm -R ../dist
rm -R ../src/*.egg-info
rm -R ../build