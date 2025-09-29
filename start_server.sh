#!/bin/bash
# Start the Ankicraft web server

# Activate the virtual environment if it exists
if [ -f "/app/.venv/bin/activate" ]; then
    source /app/.venv/bin/activate
fi

# Run the Ankicraft web server
exec python -m ankicraft