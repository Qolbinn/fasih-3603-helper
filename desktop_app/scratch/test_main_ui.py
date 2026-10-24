import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import Fasih3603App

print("Initializing Fasih3603App...")
app = Fasih3603App()
app.withdraw() # Jangan tampilkan window saat testing

print("Testing view switches...")
app._show_home_view()
assert app.current_view == app.view_home
print("   Home view OK!")

app._show_kbli_pmm_view()
assert app.current_view == app.view_kbli_pmm
print("   Switched to KBLI PMM View successfully!")

app._show_kbli_sembako_view()
assert app.current_view == app.view_kbli_sembako
print("   Switched to KBLI Sembako View successfully!")

app._show_remark_kbli_view()
assert app.current_view == app.view_remark_kbli
print("   Switched to Remark KBLI View successfully!")

app._show_kbli_pmm_view()
assert app.current_view == app.view_kbli_pmm

print("Testing zoom functionality...")
app._zoom_in()
app._zoom_out()
app.zoom_level = 1.0
app._apply_zoom()
print("   Zoom operations OK!")

app.destroy()
print("\nALL MAIN UI TESTS PASSED SUCCESSFULLY!")
