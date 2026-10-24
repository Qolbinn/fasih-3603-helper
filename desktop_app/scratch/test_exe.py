import subprocess
import time
from pathlib import Path

exe_path = Path("dist/FASIH_3603_Helper/FASIH_3603_Helper.exe").resolve()
assert exe_path.exists(), f"Exe not found at {exe_path}"

print(f"Launching {exe_path.name}...")
proc = subprocess.Popen([str(exe_path)])
time.sleep(3.5)

poll = proc.poll()
if poll is not None:
    print(f"FAILED: Exe exited unexpectedly with code {poll}!")
    sys.exit(1)
else:
    print(f"SUCCESS: Exe is running smoothly (PID: {proc.pid})! Terminating test process...")
    proc.terminate()
    proc.kill()
    print("Process cleanly terminated. Build validation PASSED!")
