#!/bin/bash
# Test script to run the email digest in the correct virtual environment

# Change to the project directory
cd "$(dirname "$0")/.."

# Activate the virtual environment
source venv/bin/activate

# Run the digest script with test parameters
python scripts/send_digest.py --recipients andrew.maguire@undp.org --days 14 --test

# Deactivate the virtual environment
deactivate