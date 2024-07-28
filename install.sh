#!/bin/bash

# Ensure script is being run as root
if [ "$(id -u)" != "0" ]; then
  echo "This script must be run as root" 1>&2
  exit 1
fi

INSTALL_DIR="/usr/local/bin"
SCRIPT_NAME="dins"
PIP_CMD="pip"
ARGCOMPLETE_CMD="activate-global-python-argcomplete"

# Install argcomplete
echo "Installing argcomplete..."
$PIP_CMD install argcomplete --break-system-packages
$ARGCOMPLETE_CMD --user

if [ $? -ne 0 ]; then
  echo "Error installing argcomplete. Aborting."
  exit 1
fi

# Copy main.py to INSTALL_DIR
echo "Installing dins..."
cp -f ./main.py "$INSTALL_DIR/$SCRIPT_NAME"

if [ $? -ne 0 ]; then
  echo "Error copying main.py to $INSTALL_DIR. Aborting."
  exit 1
fi

echo "Success! Installation completed."
