@echo off
rem Use this script to create a new environment called "FAIRS"

call conda activate FAIRS && cd .. && pip install -e . --use-pep517
if errorlevel 1 (
    echo Failed to install the package in editable mode
    goto :eof
)

