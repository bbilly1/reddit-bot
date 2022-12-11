#!/bin/bash
# run inside the container

printf "===============\n run redditbot\n===============\n"

while true; do
    echo "[exec]: start now $(date)"
    python main.py
    echo "[exec]: run completed"
    sleep 3600
done

##
exit 0
