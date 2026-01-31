#!/bin/bash
# Check if python venv exists
if [ ! -d "service/venv" ]; then
    echo "Python venv not found. Please run setup first."
    exit 1
fi

# Trap SIGINT to kill background processes
trap "kill 0" SIGINT

# Start Python API in background
echo "Starting Python Service..."
export PYTHONPATH=$PYTHONPATH:$(pwd)
service/venv/bin/uvicorn service.main:app --host 127.0.0.1 --port 8000 &
PID=$!

# Wait for API to be ready
echo "Waiting for API to be ready..."
sleep 2

# Start Electron App (in dev mode matching API port)
echo "Starting Electron App..."
cd app
npm run electron:dev

# When Electron closes, kill Python servce
kill $PID
