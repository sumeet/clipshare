#!/bin/bash

# Restarts the client when it dies unexpectedly. If it exits cleanly, then we
# exit.
until python3 client.py
do :
done
