#!/bin/bash

# This script sets up a Python virtual environment and installs the required packages.
# It should be run from the backend directory.
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install flask flask-cors