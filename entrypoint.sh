#!/usr/bin/env bash

./migrate.sh
uvicorn app:app --proxy-headers --host 0.0.0.0 --port 8800 --log-config=log_conf.yaml