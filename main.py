import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import customtkinter as ctk

from config import (
    APP_NAME, APP_VERSION, APP_SUBTITLE, APP_AUTHOR,
    USER_APPDATA_DIR, LOGS_DIR, AUDIT_DIR,
    APP_ICON_ICO, APP_LOGO_PNG, APP_LOGO_36, APP_LOGO_64
)
from core.logger import logger
from core.event_bus import EventBus
from core.browser_manager import BrowserManager
from modules.data_cleaning.view import DataCleaningView
from modules.approve_se2026.view import ApproveSE2026View

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class Fasih3603App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION} - {APP_AUTHOR}")
        self.geometry("1120x740")
        self.minsize(980, 640)

        # Set Window and Taskbar Icon
        try:
            if APP_ICON_ICO.exists():
                self.iconbitmap(str(APP_ICON_ICO))
            if APP_LOGO_PNG.exists():
                self._app_icon_photo = tk.PhotoImage(file=str(APP_LOGO_PNG))
                self.iconphoto(True, self._app_icon_photo)
        except Exception:
            pass

        self.event_bus = EventBus()
        self.current_view = None
        self.zoom_level = 1.0

        self._build_main_layout()
        self._start_browser_status_monitor()
        self.bind("<Return>", self._on_global_enter)
        self.protocol("WM_DELETE_WINDOW", self._on_window_closing)

    def _build_main_layout(self):
        # 1. Top Bar: Header & Chrome CDP Launcher & Zoom
        self.top_bar = ctk.CTkFrame(self, height=55, corner_radius=0, fg_color="#1e293b")
        self.top_bar.pack(side="top", fill="x")

        # Title & Version with Minimalist Rebranded Logo
        title_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=8)

        try:
            if APP_LOGO_36.exists():
                self.logo_top_img = tk.PhotoImage(file=str(APP_LOGO_36))
                lbl_logo = tk.Label(title_box, image=self.logo_top_img, bg="#1e293b", bd=0)
                lbl_logo.pack(side="left", padx=(0, 10))
        except Exception:
            pass

        lbl_app = ctk.CTkLabel(title_box, text=APP_NAME, font=ctk.CTkFont(size=16, weight="bold"))
        lbl_app.pack(side="left", padx=(0, 8))

        lbl_ver = ctk.CTkLabel(title_box, text=f"v{APP_VERSION}", font=ctk.CTkFont(size=11), text_color="#c084fc", fg_color="#0f172a", corner_radius=6, padx=6, pady=2)
        lbl_ver.pack(side="left")

        # Chrome CDP Launcher Control (Kanan Atas)
        chrome_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        chrome_box.pack(side="right", padx=16, pady=8)

        self.lbl_browser_status = ctk.CTkLabel(
            chrome_box,
            text="🔴 Chrome Belum Aktif",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f87171"
        )
        self.lbl_browser_status.pack(side="left", padx=(0, 12))

        self.btn_launch_chrome = ctk.CTkButton(
            chrome_box,
            text="🚀 Buka Browser Fasih",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            width=150,
            command=self._launch_chrome_action
        )
        self.btn_launch_chrome.pack(side="left")

        # Zoom Controls (Di sebelah kiri Chrome Launcher)
        zoom_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        zoom_box.pack(side="right", padx=(0, 16), pady=8)

        ctk.CTkLabel(zoom_box, text="🔍 Zoom:", font=ctk.CTkFont(size=11), text_color="gray70").pack(side="left", padx=(0, 4))

        self.btn_zoom_out = ctk.CTkButton(
            zoom_box,
            text="➖",
            width=28,
            height=28,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            command=self._zoom_out
        )
        self.btn_zoom_out.pack(side="left", padx=2)

        self.lbl_zoom = ctk.CTkLabel(
            zoom_box,
            text="100%",
            width=48,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#c084fc"
        )
        self.lbl_zoom.pack(side="left", padx=2)

        self.btn_zoom_in = ctk.CTkButton(
            zoom_box,
            text="➕",
            width=28,
            height=28,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            command=self._zoom_in
        )
        self.btn_zoom_in.pack(side="left", padx=2)

        # 2. Main Body: Sidebar (Kiri) & View Container (Kanan)
        self.body_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.body_frame.pack(side="top", fill="both", expand=True)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self.body_frame, width=220, corner_radius=0, fg_color="#0f172a")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Sidebar Brand Badge
        brand_card = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_card.pack(fill="x", padx=16, pady=(16, 12))

        try:
            if APP_LOGO_64.exists():
                self.logo_side_img = tk.PhotoImage(file=str(APP_LOGO_64))
                lbl_side_logo = tk.Label(brand_card, image=self.logo_side_img, bg="#0f172a", bd=0)
                lbl_side_logo.pack(anchor="w", pady=(0, 6))
        except Exception:
            pass

        ctk.CTkLabel(brand_card, text=APP_NAME, font=ctk.CTkFont(size=14, weight="bold"), text_color="#f8fafc").pack(anchor="w")
        ctk.CTkLabel(brand_card, text="BPS KABUPATEN TANGERANG", font=ctk.CTkFont(size=9, weight="bold"), text_color="#c084fc").pack(anchor="w", pady=(1, 0))

        # Divider line
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#1e293b").pack(fill="x", padx=16, pady=(10, 14))

        ctk.CTkLabel(self.sidebar, text="MENU MODUL", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray50").pack(anchor="w", padx=16, pady=(0, 8))

        self.nav_buttons = {}
        self._add_nav_item("beranda", "🏠 Beranda & Panduan", self._show_home_view)
        self._add_nav_item("cleaning", "🧹 Data Cleaning SE2026", self._show_cleaning_view)
        self._add_nav_item("approve", "✅ Approve SE 2026 (Soon)", self._show_approve_view)
        self._add_nav_item("pengaturan", "⚙️ Pengaturan & Info", self._show_settings_view)

        # Sidebar Footer
        side_footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        side_footer.pack(side="bottom", fill="x", padx=12, pady=12)
        ctk.CTkLabel(side_footer, text=APP_SUBTITLE, font=ctk.CTkFont(size=10), text_color="gray40", justify="center", wraplength=190).pack()

        # View Container
        self.container = ctk.CTkFrame(self.body_frame, corner_radius=0, fg_color="transparent")
        self.container.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Modul views cache
        self.view_cleaning = DataCleaningView(self.container, self.event_bus)
        self.view_approve = ApproveSE2026View(self.container)
        self.view_home = self._create_home_view()
        self.view_settings = self._create_settings_view()

        # Default buka Data Cleaning
        self._show_cleaning_view()

    def _add_nav_item(self, key, label, cmd):
        btn = ctk.CTkButton(
            self.sidebar,
            text=label,
            font=ctk.CTkFont(size=12),
            anchor="w",
            height=38,
            fg_color="transparent",
            text_color="gray80",
            hover_color="#1e293b",
            command=cmd
        )
        btn.pack(fill="x", padx=8, pady=2)
        self.nav_buttons[key] = btn

    def _set_active_nav(self, active_key):
        for k, btn in self.nav_buttons.items():
            if k == active_key:
                btn.configure(fg_color="#7c3aed", text_color="white", font=ctk.CTkFont(size=12, weight="bold"))
            else:
                btn.configure(fg_color="transparent", text_color="gray80", font=ctk.CTkFont(size=12))

    def _switch_view(self, new_view, nav_key):
        if self.current_view:
            self.current_view.pack_forget()
        self.current_view = new_view
        self.current_view.pack(fill="both", expand=True)
        self._set_active_nav(nav_key)

    def _show_cleaning_view(self):
        self._switch_view(self.view_cleaning, "cleaning")

    def _show_approve_view(self):
        self._switch_view(self.view_approve, "approve")

    def _show_home_view(self):
        self._switch_view(self.view_home, "beranda")

    def _show_settings_view(self):
        self._switch_view(self.view_settings, "pengaturan")

    def _create_home_view(self):
        frame = ctk.CTkFrame(self.container, corner_radius=10)

        # Header Selamat Datang dengan Brand Logo
        head_box = ctk.CTkFrame(frame, fg_color="transparent")
        head_box.pack(fill="x", padx=25, pady=(20, 16))

        try:
            if APP_LOGO_64.exists():
                self.logo_home_img = tk.PhotoImage(file=str(APP_LOGO_64))
                lbl_h_logo = tk.Label(head_box, image=self.logo_home_img, bg="#2b2b2b", bd=0)
                lbl_h_logo.pack(side="left", padx=(0, 16))
        except Exception:
            pass

        head_text = ctk.CTkFrame(head_box, fg_color="transparent")
        head_text.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(head_text, text=f"Selamat Datang di {APP_NAME}!", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(head_text, text=f"{APP_SUBTITLE} - Dikembangkan untuk mempermudah operasional rekan kerja BPS.", font=ctk.CTkFont(size=13), text_color="gray70").pack(anchor="w")

        # Panduan 3 Langkah
        box_guide = ctk.CTkFrame(frame, corner_radius=8, fg_color="#1e293b")
        box_guide.pack(fill="x", padx=25, pady=10)

        ctk.CTkLabel(box_guide, text="📖 Panduan Singkat Penggunaan:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=16, pady=(14, 8))

        steps = [
            ("Langkah 1", "Klik tombol '🚀 Buka Browser Fasih' di kanan atas. Chrome akan terbuka."),
            ("Langkah 2", "Lakukan login SSO BPS + OTP di jendela Chrome tersebut sampai masuk dashboard Fasih."),
            ("Langkah 3", "Buka menu 'Data Cleaning SE2026', pilih file Excel 'flag_clean.xlsx' yang sudah disiapkan."),
            ("Langkah 4", "Klik 'Mulai Otomasi'. Bot akan memeriksa dan membersihkan data baris demi baris secara otomatis!")
        ]

        for s_title, s_desc in steps:
            s_row = ctk.CTkFrame(box_guide, fg_color="transparent")
            s_row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(s_row, text=f"{s_title}:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#c084fc", width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(s_row, text=s_desc, font=ctk.CTkFont(size=12), text_color="gray80").pack(side="left")

        ctk.CTkFrame(box_guide, height=10, fg_color="transparent").pack()

        # Tombol aksi langsung
        btn_box = ctk.CTkFrame(frame, fg_color="transparent")
        btn_box.pack(fill="x", padx=25, pady=20)

        ctk.CTkButton(
            btn_box,
            text="🧹 Buka Modul Data Cleaning Sekarang",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=42,
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            command=self._show_cleaning_view
        ).pack(side="left")

        return frame

    def _create_settings_view(self):
        frame = ctk.CTkFrame(self.container, corner_radius=10)

        ctk.CTkLabel(frame, text="⚙️ Pengaturan & Informasi Sistem", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=25, pady=(20, 15))

        # Folder Data
        box_dirs = ctk.CTkFrame(frame, corner_radius=8, fg_color="#1e293b")
        box_dirs.pack(fill="x", padx=25, pady=10)

        ctk.CTkLabel(box_dirs, text="Lokasi Data & Berkas Aplikasi:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=16, pady=(12, 6))

        dirs = [
            ("Folder Data Pengguna", USER_APPDATA_DIR),
            ("Folder Berkas Log", LOGS_DIR),
            ("Folder Jejak Audit", AUDIT_DIR)
        ]

        for label, pth in dirs:
            r = ctk.CTkFrame(box_dirs, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(r, text=f"{label}:", width=160, anchor="w", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
            ctk.CTkLabel(r, text=str(pth), font=ctk.CTkFont(size=11), text_color="gray70").pack(side="left", padx=(0, 10))
            ctk.CTkButton(r, text="Buka", width=60, height=24, command=lambda p=pth: os.startfile(str(p))).pack(side="right")

        ctk.CTkFrame(box_dirs, height=10, fg_color="transparent").pack()

        # Tema Tampilan
        box_theme = ctk.CTkFrame(frame, corner_radius=8, fg_color="#1e293b")
        box_theme.pack(fill="x", padx=25, pady=10)
        ctk.CTkLabel(box_theme, text="Preferensi Tampilan:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=16, pady=(12, 6))

        t_row = ctk.CTkFrame(box_theme, fg_color="transparent")
        t_row.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(t_row, text="Tema Warna:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))

        def change_theme(new_theme):
            ctk.set_appearance_mode(new_theme)

        theme_om = ctk.CTkOptionMenu(t_row, values=["Dark", "Light", "System"], command=change_theme)
        theme_om.pack(side="left")

        return frame

    def _zoom_in(self):
        if self.zoom_level < 1.45:
            self.zoom_level = round(self.zoom_level + 0.1, 1)
            self._apply_zoom()

    def _zoom_out(self):
        if self.zoom_level > 0.85:
            self.zoom_level = round(self.zoom_level - 0.1, 1)
            self._apply_zoom()

    def _apply_zoom(self):
        self.lbl_zoom.configure(text=f"{int(round(self.zoom_level * 100))}%")
        ctk.set_widget_scaling(self.zoom_level)

    def _on_global_enter(self, event=None):
        if hasattr(self, "view_cleaning") and self.current_view == self.view_cleaning:
            self.view_cleaning._on_enter_pressed(event)

    def _launch_chrome_action(self):
        self.lbl_browser_status.configure(text="🟡 Membuka...", text_color="#f59e0b")
        self.update_idletasks()
        success, msg = BrowserManager.launch_browser()
        if not success:
            messagebox.showerror("Peluncuran Browser Gagal", msg)
            self.lbl_browser_status.configure(text="🔴 Chrome Belum Aktif", text_color="#f87171")
        else:
            self.lbl_browser_status.configure(text="🟢 Browser Aktif", text_color="#34d399")

    def _start_browser_status_monitor(self):
        def monitor():
            while True:
                active, name = BrowserManager.is_cdp_running(timeout=1.0)
                if active:
                    self.lbl_browser_status.configure(
                        text=f"🟢 Terhubung ({name})",
                        text_color="#34d399"
                    )
                else:
                    self.lbl_browser_status.configure(
                        text="🔴 Chrome Belum Aktif",
                        text_color="#f87171"
                    )
                threading.Event().wait(3.0)

        t = threading.Thread(target=monitor, daemon=True)
        t.start()

    def _on_window_closing(self):
        # Periksa apakah proses otomasi sedang berjalan
        from core.event_bus import EngineState
        if self.event_bus.get_state() in [EngineState.RUNNING, EngineState.PAUSED]:
            ans = messagebox.askyesno(
                "Otomasi Sedang Berjalan",
                "⚠️ Otomasi saat ini sedang berjalan!\n\n"
                "Apakah Anda yakin ingin menghentikan otomasi dan keluar dari aplikasi?\n\n"
                "ℹ️ Catatan: Data baris yang telah selesai diproses sudah tersimpan secara otomatis dan aman di file Excel Anda.",
                icon="warning"
            )
            if not ans:
                return

            self.event_bus.request_stop()
            logger.warning("Aplikasi ditutup oleh pengguna. Menghentikan engine otomasi...")
            self.after(300, self.destroy)
        else:
            self.destroy()

if __name__ == "__main__":
    app = Fasih3603App()
    app.mainloop()
