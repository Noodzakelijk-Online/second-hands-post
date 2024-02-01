#!/bin/bash

LOCK_FILE=/tmp/setup.lock

if [ -f "$LOCK_FILE" ]; then
    PID=$(cat $LOCK_FILE)
    if ps -p $PID > /dev/null; then
       echo "Stopping script..."
       kill $PID && rm $LOCK_FILE
    else
       echo "Process not running, but lock file exists. Cleaning up..."
       rm $LOCK_FILE
    fi
else
    echo "Script is not running."
fi
