@echo off
rem Use this script to install packages in developer mode

call conda activate FAIRS && cd .. && pip install -e .
if errorlevel 1 (
    echo Failed to install the package in editable mode
    goto :eof
)

