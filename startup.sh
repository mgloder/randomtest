#!/bin/bash

# Ensure dependencies are installed
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Start the Chainlit application
python -m chainlit run app.py --host 0.0.0.0 --port 8000