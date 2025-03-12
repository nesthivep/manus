#!/bin/bash

# Activate the virtual environment
source .venv/bin/activate

# Add the project directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/home/rachitt/OpenManus

# Add the virtual environment's site-packages directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/home/rachitt/OpenManus/.venv/lib/python3.11/site-packages

echo "Environment set up for OpenManus!"
echo "PYTHONPATH is now: $PYTHONPATH" 