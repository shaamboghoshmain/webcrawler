#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
service/venv/bin/uvicorn service.main:app --host 127.0.0.1 --port 8000 --reload
