import os
import sys
import shutil
import subprocess
from pathlib import Path

# ==============================================================================
# SKRIP BUILD PYINSTALLER - FASIH 3603 HELPER
# ==============================================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_CACHE = ROOT_DIR / "build" / "pyinstaller_cache"
SPEC_FILE = ROOT_DIR / "FASIH_3603_Helper.spec"

def build():
    print("========================================================")
    print("      Membangun Executable: FASIH 3603 Helper           ")
    print("========================================================")

    # Cek PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("[Error] PyInstaller belum terpasang. Jalankan: pip install pyinstaller")
        return

    # Bersihkan folder dist lama jika ada
    if (DIST_DIR / "FASIH_3603_Helper").exists():
        print("[Build] Membersihkan folder dist lama...")
        try:
            shutil.rmtree(DIST_DIR / "FASIH_3603_Helper")
        except Exception as e:
            print(f"[Warning] Gagal membersihkan dist: {e}")

    # Temukan path customtkinter untuk menyertakan aset warna/tema
    import customtkinter
    ctk_path = Path(customtkinter.__file__).parent

    # Deteksi folder DLL Conda (khusus Windows Conda/Anaconda)
    conda_lib_bin = Path(sys.prefix) / "Library" / "bin"
    if conda_lib_bin.exists():
        os.environ["PATH"] = str(conda_lib_bin) + os.pathsep + os.environ.get("PATH", "")

    # Parameter PyInstaller:
    # Menggunakan --onedir agar startup instan (< 1 detik) dan tidak sering kena false positive antivirus
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed", # Tanpa layar konsol hitam CMD
        "--name=FASIH_3603_Helper",
        f"--icon={str(ROOT_DIR / 'assets' / 'app_icon.ico')}",
        f"--add-data={str(ctk_path)};customtkinter",
        f"--add-data={str(ROOT_DIR / 'assets')};assets",
        f"--paths={str(conda_lib_bin)}" if conda_lib_bin.exists() else "",
        "--hidden-import=customtkinter",
        "--hidden-import=playwright",
        "--hidden-import=openpyxl",
        "--hidden-import=win32gui",
        "--hidden-import=win32con",
        "--hidden-import=win32process",
        "--hidden-import=psutil",
        "--hidden-import=modules.data_cleaning",
        "--hidden-import=modules.approve_se2026",
        f"--workpath={str(BUILD_CACHE)}",
        f"--distpath={str(DIST_DIR)}",
        str(ROOT_DIR / "main.py")
    ]
    cmd = [arg for arg in cmd if arg] # Bersihkan argumen kosong

    print("[Build] Menjalankan perintah PyInstaller...")
    res = subprocess.run(cmd)

    if res.returncode == 0:
        # Salin folder assets langsung ke dist/FASIH_3603_Helper/assets untuk kemudahan akses
        dist_assets = DIST_DIR / "FASIH_3603_Helper" / "assets"
        try:
            if dist_assets.exists():
                shutil.rmtree(dist_assets)
            shutil.copytree(ROOT_DIR / "assets", dist_assets)
        except Exception as e:
            print(f"[Warning] Gagal menyalin assets ke dist: {e}")

        # Salin skrip pembuat shortcut desktop ke dalam folder dist
        shortcut_script = ROOT_DIR / "Pasang_Shortcut_Desktop.bat"
        if shortcut_script.exists():
            try:
                shutil.copy2(shortcut_script, DIST_DIR / "FASIH_3603_Helper" / "Pasang_Shortcut_Desktop.bat")
            except Exception as e:
                print(f"[Warning] Gagal menyalin Pasang_Shortcut_Desktop.bat: {e}")

        # Pastikan DLL krusial Conda (terutama tcl/tk untuk _tkinter) selalu tersalin ke dist
        if conda_lib_bin.exists():
            target_internal = DIST_DIR / "FASIH_3603_Helper" / "_internal"
            target_root = DIST_DIR / "FASIH_3603_Helper"
            crucial_dlls = [
                "tcl86t.dll", "tk86t.dll", "libcrypto-3-x64.dll", "libssl-3-x64.dll",
                "libexpat.dll", "ffi.dll", "liblzma.dll", "libmpdec-4.dll", "libbz2.dll", "sqlite3.dll"
            ]
            for dll_name in crucial_dlls:
                src_dll = conda_lib_bin / dll_name
                if src_dll.exists():
                    try:
                        shutil.copy2(src_dll, target_internal / dll_name)
                        shutil.copy2(src_dll, target_root / dll_name)
                    except Exception as e:
                        print(f"[Warning] Gagal menyalin {dll_name}: {e}")

        print("\n========================================================")
        print("[SUKSES] BUILD BERHASIL!")
        print(f"Folder aplikasi: {DIST_DIR / 'FASIH_3603_Helper'}")
        print("Jalankan: FASIH_3603_Helper.exe di dalam folder tersebut.")
        print("========================================================")
    else:
        print(f"\n[Error] Build gagal dengan kode: {res.returncode}")

if __name__ == "__main__":
    build()
