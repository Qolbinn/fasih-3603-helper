# PyInstaller runtime hook: runs before any application module is imported
import sys

# Explicitly block numpy and optional scientific libraries in the frozen application.
# This guarantees that openpyxl and other libraries never attempt to import host/system
# numpy installations that might be corrupted or incompatible (e.g. NumPy 2.x alias removals).
for _mod in ("numpy", "scipy", "pandas", "matplotlib"):
    sys.modules[_mod] = None
