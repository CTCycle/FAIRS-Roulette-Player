@echo off
rem Use this script to create a new environment called "TokenExp"

echo STEP 1: Creation of TokenExp environment
call conda create -n TokenExp python=3.10 -y
if errorlevel 1 (
    echo Failed to create the environment TokenExp
    goto :eof
)

rem If present, activate the environment
call conda activate TokenExp

rem Install additional packages with pip
echo STEP 2: Install python libraries and packages
call pip install numpy pandas seaborn transformers datasets matplotlib 
if errorlevel 1 (
    echo Failed to install Python libraries.
    goto :eof
)


rem Print the list of dependencies installed in the environment
echo List of installed dependencies
call conda list

set/p<nul =Press any key to exit... & pause>nul
