#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Navigate to that directory
cd "$SCRIPT_DIR"

# Run the python script using the venv
./venv/bin/python newWebCrawl.py
