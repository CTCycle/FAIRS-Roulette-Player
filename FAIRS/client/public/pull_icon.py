import shutil
import os
import sys

source = r"C:\Users\Thomas V\.gemini\antigravity\brain\7fa5e3bd-4e4d-408d-bd73-96df26114f2c\roulette_wheel_icon_1767350605605.png"
dest = "roulette_wheel.png"
log_file = "copy_log.txt"

with open(log_file, "w") as f:
    f.write(f"Starting copy from {source}\n")
    try:
        if not os.path.exists(source):
            f.write(f"Error: Source not found at {source}\n")
        else:
            shutil.copy(source, dest)
            f.write("Success: File copied.\n")
            if os.path.exists(dest):
                f.write(f"Verified: {dest} exists.\n")
            else:
                f.write(f"Error: {dest} not found after copy.\n")
    except Exception as e:
        f.write(f"Exception: {e}\n")
