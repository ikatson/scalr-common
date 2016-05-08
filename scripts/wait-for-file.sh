#!/bin/bash

TIMEOUT="${TIMEOUT:-1200}"
SLEEP="${SLEEP:-1}"
ELAPSED=0
FILE_TO_WAIT_FOR="${FILE_TO_WAIT_FOR:-$(echo "${1}")}"

while [[ ! -f "${FILE_TO_WAIT_FOR}" ]]; do
    sleep "${SLEEP}"
    ELAPSED=$(( ELAPSED + SLEEP ))
    if [[ "${ELAPSED}" -gt "${TIMEOUT}" ]]; then
        echo "Waited for ${ELAPSED} seconds, giving up"
        exit 1
    fi
done
