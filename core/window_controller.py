import os
import sys
import ctypes

try:
    import win32gui
    import win32con
    import win32process
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

from config import DEFAULT_CDP_PORT, APP_NAME

class WindowController:
    @staticmethod
    def get_cdp_pids():
        """
        Mengidentifikasi PID proses browser (Chrome / Edge) yang membuka port CDP 9222
        atau menggunakan flag remote-debugging / chrome_profile khusus Fasih Helper.
        """
        pids = set()
        if not HAS_WIN32:
            return pids

        # 1. Cari melalui command line proses
        try:
            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    name = (p.info.get('name') or '').lower()
                    if 'chrome' not in name and 'edge' not in name:
                        continue
                    cmdline = " ".join(p.info.get('cmdline') or [])
                    if f"--remote-debugging-port={DEFAULT_CDP_PORT}" in cmdline or "chrome_profile" in cmdline:
                        pids.add(p.info['pid'])
                        # Sertakan juga child processes jika ada
                        try:
                            for child in p.children(recursive=True):
                                pids.add(child.pid)
                        except Exception:
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass

        # 2. Cari melalui koneksi listening port jika belum ketemu
        if not pids:
            try:
                for conn in psutil.net_connections(kind='tcp'):
                    if conn.laddr.port == DEFAULT_CDP_PORT and conn.status == psutil.CONN_LISTEN:
                        if conn.pid:
                            pids.add(conn.pid)
                            try:
                                proc = psutil.Process(conn.pid)
                                for child in proc.children(recursive=True):
                                    pids.add(child.pid)
                            except Exception:
                                pass
            except Exception:
                pass

        return pids

    @classmethod
    def find_browser_windows(cls):
        """
        Mencari handle jendela (HWND) HANYA untuk browser CDP Fasih.
        Sangat terisolasi: TIDAK AKAN PERNAH menyentuh aplikasi desktop FASIH 3603 Helper
        dan TIDAK AKAN PERNAH menyentuh instance Google Chrome pribadi pengguna.
        """
        if not HAS_WIN32:
            return []

        cdp_pids = cls.get_cdp_pids()
        current_pid = os.getpid()

        hwnds = []
        def enum_cb(hwnd, extra):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True

                # Pastikan bukan jendela diri sendiri (Desktop App)
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                except Exception:
                    return True

                if pid == current_pid:
                    return True  # JANGAN PERNAH sentuh aplikasi desktop!

                title = win32gui.GetWindowText(hwnd).strip()
                if not title:
                    return True

                # Jika judul mengandung nama aplikasi desktop, lewati
                if APP_NAME.lower() in title.lower():
                    return True

                # Skenario 1: Jika CDP PID terdeteksi (akurasi mutlak)
                if cdp_pids:
                    if pid in cdp_pids:
                        hwnds.append((hwnd, title))
                else:
                    # Skenario 2: Fallback jika PID tidak bisa dibaca (misal batasan permission)
                    # Wajib spesifik mengandung 'fasih' di judul DAN browser Chrome/Edge,
                    # BUKAN sekadar 'google chrome' generik milik user lain!
                    t_lower = title.lower()
                    if "fasih" in t_lower and any(b in t_lower for b in ["chrome", "edge"]):
                        hwnds.append((hwnd, title))
            except Exception:
                pass

            return True

        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass
        return hwnds

    @classmethod
    def minimize_browser(cls):
        """
        Meminimalkan jendela browser CDP ke taskbar / background.
        Hanya berlaku untuk browser CDP, tidak menyentuh Chrome pribadi pengguna.
        """
        if not HAS_WIN32:
            return False

        windows = cls.find_browser_windows()
        success = False
        for hwnd, title in windows:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                success = True
            except Exception:
                pass
        return success

    @classmethod
    def restore_and_focus_browser(cls):
        """
        Menampilkan dan memfokuskan jendela browser CDP ke depan layar.
        TIDAK AKAN me-restore (mengecilkan) jendela jika jendela sudah maximized.
        """
        if not HAS_WIN32:
            return False

        windows = cls.find_browser_windows()
        if not windows:
            return False

        user32 = ctypes.windll.user32
        success = False
        for hwnd, title in windows:
            try:
                # Cek apakah jendela sedang diminimalkan ke taskbar
                is_minimized = win32gui.IsIconic(hwnd)

                if is_minimized:
                    # Jika sedang diminimalkan, pulihkan ke ukuran sebelumnya
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                else:
                    # Jika jendela sudah terbuka/tampil, JANGAN panggil SW_RESTORE karena akan meng-unmaximize jendela!
                    # Cukup tampilkan tanpa mengubah ukuran
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

                # Bawa ke depan layar
                try:
                    win32gui.BringWindowToTop(hwnd)
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass

                success = True
            except Exception:
                pass
        return success
