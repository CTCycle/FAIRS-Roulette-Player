@echo off
copy "C:\Users\Thomas V\.gemini\antigravity\brain\7fa5e3bd-4e4d-408d-bd73-96df26114f2c\roulette_wheel_icon_1767350605605.png" "g:\Projects\Repository\FAIRS Roulette Player\FAIRS\client\public\roulette_wheel.png"
if %errorlevel% neq 0 (
    echo Copy failed with error %errorlevel%
) else (
    echo Copy successful
)
