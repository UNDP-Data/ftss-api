#!/bin/bash
# Script to run the direct email test in the correct virtual environment

# Change to the project directory
cd "$(dirname "$0")/.."

# Activate the virtual environment
source venv/bin/activate

# Run the direct test script
python scripts/test_email_direct.py andrew.maguire@undp.org

# Deactivate the virtual environment
deactivate