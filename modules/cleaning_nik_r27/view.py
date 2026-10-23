import os
import sys
import re
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

from config import LOGS_DIR
from core.logger import logger
from core.event_bus import EventBus, EngineState
from modules.cleaning_nik_r27.validator import ExcelNIKR27Validator
from modules.cleaning_nik_r27.engine import CleaningNIKR27Engine

class CleaningNIKR27View(ctk.CTkFrame):
    """
    Antarmuka pengguna (View) untuk modul Data Cleaning NIK R27 R27 SE2026.
    Konsisten 100% dengan tata letak, estetika, dan fungsionalitas modul Data Cleaning & Remark KBLI.
    """
    def __init__(self, master, event_bus: EventBus = None):
        super().__init__(master, corner_radius=10)
        self.event_bus = event_bus or EventBus()

        self.current_excel_path = None
        self.validated_data = None
        self.tree_item_map = {}
        self.worker_thread = None
        self.log_font_size = 11
        self.current_stats = {"total": 0, "done": 0, "error": 0, "pending": 0}
        self.log_queue = queue.Queue()

        self._build_ui()
        self._setup_event_listener()

    def _build_ui(self):
        # 1. Panel Atas: Input File & Kontrol
        header_frame = ctk.CTkFrame(self, corner_radius=8)
        header_frame.pack(fill="x", padx=10, pady=8)

        # Baris 1: File Picker & Status Template
        file_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        file_row.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(file_row, text="File Excel:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        self.entry_file = ctk.CTkEntry(file_row, placeholder_text="Pilih file Excel Data Cleaning NIK R27 R27 R27...", width=400)
        self.entry_file.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_file.bind("<Return>", lambda e: self._on_file_entry_return())

        btn_browse = ctk.CTkButton(file_row, text="📂 Pilih File", width=100, command=self._browse_file)
        btn_browse.pack(side="left", padx=(0, 6))

        btn_download = ctk.CTkButton(
            file_row,
            text="📥 Unduh Template",
            width=135,
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._download_template
        )
        btn_download.pack(side="left")

        # Label Validasi Template
        self.lbl_validation = ctk.CTkLabel(
            header_frame,
            text="Silakan pilih file Excel terlebih dahulu untuk memvalidasi template.",
            font=ctk.CTkFont(size=11),
            text_color="gray70"
        )
        self.lbl_validation.pack(anchor="w", padx=12, pady=(0, 6))

        # Baris 2: Pengaturan Mode Submit & Chrome
        opt_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        opt_row.pack(fill="x", padx=10, pady=(2, 4))

        self.mode_var = ctk.StringVar(value="prod")
        ctk.CTkLabel(opt_row, text="Opsi Submit:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        self.rad_prod = ctk.CTkRadioButton(opt_row, text="Mode Automasi", variable=self.mode_var, value="prod")
        self.rad_prod.pack(side="left", padx=(0, 15))
        self.rad_debug = ctk.CTkRadioButton(opt_row, text="Mode Debug/Review", variable=self.mode_var, value="debug")
        self.rad_debug.pack(side="left", padx=(0, 20))

        self.cb_minimize = ctk.CTkCheckBox(opt_row, text="Minimalkan Chrome Otomatis saat Berjalan")
        self.cb_minimize.pack(side="left", padx=(0, 10))
        self.cb_minimize.select()

        # Multi-worker selector
        ctk.CTkLabel(opt_row, text="⚡ Worker:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(15, 6))
        self.worker_opt = ctk.CTkOptionMenu(
            opt_row,
            values=["1 Worker", "2 Worker (Disarankan)", "3 Worker", "4 Worker", "5 Worker"],
            width=180,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1e293b",
            button_color="#334155",
            button_hover_color="#475569"
        )
        self.worker_opt.set("2 Worker (Disarankan)")
        self.worker_opt.pack(side="left", padx=(0, 10))

        # Baris 2b: Pengaturan Rentang Baris Eksekusi
        range_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        range_row.pack(fill="x", padx=10, pady=(2, 4))

        self.range_var = ctk.StringVar(value="all")
        ctk.CTkLabel(range_row, text="Rentang Target:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        self.rad_range_all = ctk.CTkRadioButton(
            range_row,
            text="Semua Baris (Default)",
            variable=self.range_var,
            value="all",
            command=self._toggle_range_inputs
        )
        self.rad_range_all.pack(side="left", padx=(0, 15))

        self.rad_range_custom = ctk.CTkRadioButton(
            range_row,
            text="Batasi Baris:",
            variable=self.range_var,
            value="custom",
            command=self._toggle_range_inputs
        )
        self.rad_range_custom.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(range_row, text="Dari:", font=ctk.CTkFont(size=11), text_color="gray70").pack(side="left", padx=(0, 4))
        self.entry_start_row = ctk.CTkEntry(range_row, width=55, placeholder_text="2", state="disabled")
        self.entry_start_row.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(range_row, text="s.d.", font=ctk.CTkFont(size=11), text_color="gray70").pack(side="left", padx=(0, 4))
        self.entry_end_row = ctk.CTkEntry(range_row, width=55, placeholder_text="Akhir", state="disabled")
        self.entry_end_row.pack(side="left", padx=(0, 10))

        self.lbl_range_hint = ctk.CTkLabel(
            range_row,
            text="(Contoh: Dari 2 s.d. 3 untuk menguji baris tertentu)",
            font=ctk.CTkFont(size=11),
            text_color="gray60"
        )
        self.lbl_range_hint.pack(side="left")

        # Baris 2c: Pengaturan Metode Autentikasi / Login Fasih
        auth_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        auth_row.pack(fill="x", padx=10, pady=(2, 4))

        self.auth_mode_var = ctk.StringVar(value="manual")
        ctk.CTkLabel(auth_row, text="Metode Login:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        self.rad_auth_manual = ctk.CTkRadioButton(
            auth_row,
            text="Login Manual (Sesi Chrome)",
            variable=self.auth_mode_var,
            value="manual",
            command=self._toggle_auth_inputs
        )
        self.rad_auth_manual.pack(side="left", padx=(0, 15))

        self.rad_auth_auto = ctk.CTkRadioButton(
            auth_row,
            text="Auto Login (Khusus Non-OTP)",
            variable=self.auth_mode_var,
            value="auto",
            command=self._toggle_auth_inputs
        )
        self.rad_auth_auto.pack(side="left", padx=(0, 15))

        # Sub-frame Kredensial SSO (User & Pass)
        self.creds_frame = ctk.CTkFrame(auth_row, fg_color="#1e293b", corner_radius=6, border_width=1, border_color="#334155")
        
        ctk.CTkLabel(self.creds_frame, text="User SSO:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(side="left", padx=(8, 4), pady=2)
        self.entry_sso_user = ctk.CTkEntry(self.creds_frame, width=130, height=26, placeholder_text="username SSO")
        self.entry_sso_user.pack(side="left", padx=(0, 8), pady=2)

        ctk.CTkLabel(self.creds_frame, text="Pass SSO:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(side="left", padx=(0, 4), pady=2)
        self.entry_sso_pass = ctk.CTkEntry(self.creds_frame, width=130, height=26, placeholder_text="password SSO", show="*")
        self.entry_sso_pass.pack(side="left", padx=(0, 6), pady=2)

        self.btn_toggle_pass = ctk.CTkButton(
            self.creds_frame,
            text="👁",
            width=28,
            height=24,
            fg_color="#334155",
            hover_color="#475569",
            command=self._toggle_show_password
        )
        self.btn_toggle_pass.pack(side="left", padx=(0, 6), pady=2)

        # Baris 3: Tombol Aksi
        btn_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(6, 10))

        self.btn_start = ctk.CTkButton(btn_row, text="▶️ Mulai Otomasi", fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(weight="bold"), command=self._start_automation)
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_pause = ctk.CTkButton(btn_row, text="⏸️ Jeda", fg_color="#f59e0b", hover_color="#d97706", width=140, state="disabled", command=self._toggle_pause)
        self.btn_pause.pack(side="left", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(btn_row, text="⏹️ Berhenti Aman", fg_color="#ef4444", hover_color="#dc2626", width=130, state="disabled", command=self._stop_automation)
        self.btn_stop.pack(side="left", padx=(0, 8))

        self.btn_confirm_submit = ctk.CTkButton(
            btn_row,
            text="✅ Konfirmasi Submit & Lanjut (Enter)",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            width=250,
            state="disabled",
            font=ctk.CTkFont(weight="bold"),
            command=self._confirm_submit_action
        )
        self.btn_confirm_submit.pack(side="left", padx=(0, 8))

        self.btn_confirm_auth = ctk.CTkButton(
            btn_row,
            text="🟢 Saya Sudah Login (Lanjutkan)",
            fg_color="#059669",
            hover_color="#047857",
            width=220,
            state="normal",
            font=ctk.CTkFont(weight="bold"),
            command=self._confirm_auth_action
        )
        # self.btn_confirm_auth disembunyikan secara default, hanya ditampilkan saat sesi auth_waiting

        # 2. Main Content: 2 Tabs
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tab_stats = self.tabview.add("📊 Live Statistik & Rekap Data")
        self.tab_logs = self.tabview.add("💻 Log Terminal")

        self._build_tab_stats()
        self._build_tab_logs()

    def _build_tab_stats(self):
        # Kartu Ringkasan Metrik Dashboard
        cards_frame = ctk.CTkFrame(self.tab_stats, fg_color="transparent")
        cards_frame.pack(fill="x", padx=4, pady=(4, 8))

        self.card_total = self._create_metric_card(cards_frame, "📋", "Total Sasaran", "0", "Baris Target", "#38bdf8")
        self.card_done = self._create_metric_card(cards_frame, "✅", "Berhasil (SUKSES)", "0", "Sukses Tersimpan", "#34d399")
        self.card_error = self._create_metric_card(cards_frame, "❌", "Gagal (Galat)", "0", "Perlu Review", "#f87171")
        self.card_pending = self._create_metric_card(cards_frame, "⏳", "Sisa Antrean", "0", "Menunggu Proses", "#fbbf24")

        # Progress Bar & Info Baris Aktif Card
        prog_frame = ctk.CTkFrame(self.tab_stats, fg_color="#1e293b", corner_radius=8, border_width=1, border_color="#334155")
        prog_frame.pack(fill="x", padx=4, pady=(0, 8))

        prog_top = ctk.CTkFrame(prog_frame, fg_color="transparent")
        prog_top.pack(fill="x", padx=12, pady=(8, 4))

        self.lbl_active_row = ctk.CTkLabel(
            prog_top,
            text="Status: Menunggu file Excel dan perintah mulai...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f8fafc"
        )
        self.lbl_active_row.pack(side="left")

        self.lbl_prog_pct = ctk.CTkLabel(
            prog_top,
            text="0% (0/0)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_prog_pct.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(prog_frame, height=10, progress_color="#0284c7")
        self.progress_bar.pack(fill="x", padx=12, pady=(0, 10))
        self.progress_bar.set(0)

        # Container Tabel Data Live (Dark Card dengan Border)
        table_container = ctk.CTkFrame(self.tab_stats, fg_color="#1e293b", corner_radius=8, border_width=1, border_color="#334155")
        table_container.pack(fill="both", expand=True, padx=4, pady=0)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "FasihNIKR27.Treeview",
            background="#1e293b",
            foreground="#f1f5f9",
            fieldbackground="#1e293b",
            rowheight=30,
            font=("Segoe UI", 10),
            borderwidth=0
        )
        style.configure(
            "FasihNIKR27.Treeview.Heading",
            background="#0f172a",
            foreground="#38bdf8",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=[8, 8]
        )
        style.map(
            "FasihNIKR27.Treeview",
            background=[("selected", "#0284c7")],
            foreground=[("selected", "#ffffff")]
        )
        style.map(
            "FasihNIKR27.Treeview.Heading",
            background=[("active", "#1e293b")],
            foreground=[("active", "#7dd3fc")]
        )
        style.configure(
            "FasihNIK.Vertical.TScrollbar",
            gripcount=0,
            background="#334155",
            darkcolor="#1e293b",
            lightcolor="#1e293b",
            troughcolor="#0f172a",
            bordercolor="#0f172a",
            arrowcolor="#94a3b8"
        )

        columns = ("no", "baris", "url", "total_nik", "nik_list", "status", "ket")
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="FasihNIKR27.Treeview"
        )

        self.tree.heading("no", text="No")
        self.tree.heading("baris", text="Baris")
        self.tree.heading("url", text="Link Fasih Penugasan")
        self.tree.heading("total_nik", text="Total NIK")
        self.tree.heading("nik_list", text="Daftar Target NIK")
        self.tree.heading("status", text="Status")
        self.tree.heading("ket", text="Keterangan")

        self.tree.column("no", width=45, anchor="center")
        self.tree.column("baris", width=55, anchor="center")
        self.tree.column("url", width=220, anchor="w")
        self.tree.column("total_nik", width=85, anchor="center")
        self.tree.column("nik_list", width=240, anchor="w")
        self.tree.column("status", width=105, anchor="center")
        self.tree.column("ket", width=340, anchor="w")

        # Tags pewarnaan status baris
        self.tree.tag_configure("even", background="#1e293b")
        self.tree.tag_configure("odd", background="#182234")
        self.tree.tag_configure("tag_done", foreground="#34d399")
        self.tree.tag_configure("tag_gagal", foreground="#f87171")
        self.tree.tag_configure("tag_dihentikan", foreground="#fbbf24")
        self.tree.tag_configure("tag_proses", foreground="#38bdf8")
        self.tree.tag_configure("tag_belum", foreground="#94a3b8")

        vsb = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview, style="FasihNIK.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

    def _create_metric_card(self, parent, icon, title, initial_value, subtitle, color):
        card = ctk.CTkFrame(
            parent,
            corner_radius=10,
            fg_color="#1e293b",
            border_width=1,
            border_color="#334155",
            height=75
        )
        card.pack(side="left", fill="x", expand=True, padx=4)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 2))

        ctk.CTkLabel(header, text=icon, font=ctk.CTkFont(size=14)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(side="left")

        val_frame = ctk.CTkFrame(card, fg_color="transparent")
        val_frame.pack(fill="x", padx=12, pady=(0, 8))

        lbl_val = ctk.CTkLabel(val_frame, text=initial_value, font=ctk.CTkFont(size=22, weight="bold"), text_color=color)
        lbl_val.pack(side="left")

        ctk.CTkLabel(val_frame, text=f"• {subtitle}", font=ctk.CTkFont(size=10), text_color="#64748b").pack(side="left", padx=(8, 0), pady=(4, 0))

        return lbl_val

    def _build_tab_logs(self):
        # Action Bar Log
        log_action_bar = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        log_action_bar.pack(fill="x", padx=4, pady=4)

        # Kiri: Auto-scroll & Zoom Controls
        left_ctrl = ctk.CTkFrame(log_action_bar, fg_color="transparent")
        left_ctrl.pack(side="left")

        self.cb_autoscroll = ctk.CTkCheckBox(left_ctrl, text="Auto-scroll ke bawah", font=ctk.CTkFont(size=11))
        self.cb_autoscroll.pack(side="left", padx=(4, 12))
        self.cb_autoscroll.select()

        # Zoom Controls Box
        zoom_frame = ctk.CTkFrame(left_ctrl, fg_color="#1e293b", corner_radius=6, border_width=1, border_color="#334155")
        zoom_frame.pack(side="left", padx=4)

        ctk.CTkLabel(zoom_frame, text="🔍 Font Log:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(side="left", padx=(8, 4), pady=2)

        btn_zoom_out = ctk.CTkButton(
            zoom_frame,
            text="➖ A-",
            width=38,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            command=self._zoom_out_log
        )
        btn_zoom_out.pack(side="left", padx=2, pady=2)

        self.lbl_log_font = ctk.CTkLabel(
            zoom_frame,
            text=f"{self.log_font_size} pt",
            width=46,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_log_font.pack(side="left", padx=2, pady=2)

        btn_zoom_in = ctk.CTkButton(
            zoom_frame,
            text="➕ A+",
            width=38,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            command=self._zoom_in_log
        )
        btn_zoom_in.pack(side="left", padx=2, pady=2)

        btn_zoom_reset = ctk.CTkButton(
            zoom_frame,
            text="Reset",
            width=46,
            height=26,
            font=ctk.CTkFont(size=10),
            fg_color="transparent",
            hover_color="#334155",
            text_color="gray70",
            command=self._reset_log_font
        )
        btn_zoom_reset.pack(side="left", padx=(2, 6), pady=2)

        # Kanan: Aksi (Folder, Bersihkan, Salin)
        btn_copy = ctk.CTkButton(log_action_bar, text="📋 Salin Log", width=95, font=ctk.CTkFont(size=11), command=self._copy_logs)
        btn_copy.pack(side="right", padx=4)

        btn_clear = ctk.CTkButton(log_action_bar, text="🧹 Bersihkan", width=90, font=ctk.CTkFont(size=11), fg_color="#475569", hover_color="#334155", command=self._clear_logs)
        btn_clear.pack(side="right", padx=4)

        btn_open_folder = ctk.CTkButton(log_action_bar, text="📁 Buka Folder Log", width=125, font=ctk.CTkFont(size=11), command=self._open_log_folder)
        btn_open_folder.pack(side="right", padx=4)

        # Console Frame Container
        console_container = ctk.CTkFrame(self.tab_logs, corner_radius=8, fg_color="#090d16", border_width=1, border_color="#334155")
        console_container.pack(fill="both", expand=True, padx=4, pady=4)

        # Mini header status bar di atas console
        term_header = ctk.CTkFrame(console_container, height=26, fg_color="#0f172a", corner_radius=0)
        term_header.pack(fill="x")
        ctk.CTkLabel(
            term_header,
            text="● Live Terminal Console (UTF-8) — Gunakan tombol A+/A- atau Ctrl+Scroll untuk zoom ukuran tulisan",
            font=ctk.CTkFont(size=10),
            text_color="#64748b"
        ).pack(side="left", padx=10, pady=2)

        # Mini Live Status Dashboard Worker
        self.worker_dashboard_frame = ctk.CTkFrame(console_container, fg_color="#0b1324", height=32, corner_radius=0)
        self.worker_dashboard_frame.pack(fill="x", padx=0, pady=(0, 2))

        ctk.CTkLabel(
            self.worker_dashboard_frame,
            text="⚡ Status Worker:",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#94a3b8"
        ).pack(side="left", padx=(10, 6), pady=4)

        self.worker_badge_colors = {
            1: "#38bdf8", # Sky blue
            2: "#a78bfa", # Violet
            3: "#fb923c", # Orange
            4: "#f472b6", # Pink
            5: "#34d399", # Emerald
        }
        self.worker_badges = {}
        for i in range(1, 6):
            b_frame = ctk.CTkFrame(
                self.worker_dashboard_frame,
                fg_color="#1e293b",
                corner_radius=4,
                border_width=1,
                border_color="#334155"
            )
            lbl = ctk.CTkLabel(
                b_frame,
                text=f"W-{i}: ⏸️ Menunggu",
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                text_color="#94a3b8"
            )
            lbl.pack(padx=8, pady=2)
            self.worker_badges[i] = {"frame": b_frame, "label": lbl}
            if i <= 2:
                b_frame.pack(side="left", padx=4, pady=3)

        # Log Text Box
        self.log_text = tk.Text(
            console_container,
            bg="#090d16",
            fg="#e2e8f0",
            insertbackground="#38bdf8",
            selectbackground="#0284c7",
            font=("Consolas", self.log_font_size),
            wrap="word",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=10
        )
        log_scroll = ttk.Scrollbar(console_container, orient="vertical", command=self.log_text.yview, style="FasihNIK.Vertical.TScrollbar")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        # Shortcut zoom dengan mousewheel
        self.log_text.bind("<Control-MouseWheel>", self._on_log_mousewheel)

        # Warna tag log dengan kontras tinggi
        self.log_text.tag_config("INFO", foreground="#38bdf8")
        self.log_text.tag_config("BOT", foreground="#f8fafc")
        self.log_text.tag_config("SUCCESS", foreground="#34d399", font=("Consolas", self.log_font_size, "bold"))
        self.log_text.tag_config("REMARKS", foreground="#6ee7b7")
        self.log_text.tag_config("WARNING", foreground="#fbbf24")
        self.log_text.tag_config("ERROR", foreground="#f87171", font=("Consolas", self.log_font_size, "bold"))
        self.log_text.tag_config("DEBUG", foreground="#c084fc")

        # Warna tag worker [W-1] s.d. [W-5]
        self.log_text.tag_config("W1", foreground="#38bdf8", font=("Consolas", self.log_font_size, "bold"))
        self.log_text.tag_config("W2", foreground="#a78bfa", font=("Consolas", self.log_font_size, "bold"))
        self.log_text.tag_config("W3", foreground="#fb923c", font=("Consolas", self.log_font_size, "bold"))
        self.log_text.tag_config("W4", foreground="#f472b6", font=("Consolas", self.log_font_size, "bold"))
        self.log_text.tag_config("W5", foreground="#34d399", font=("Consolas", self.log_font_size, "bold"))

    def _zoom_in_log(self):
        if self.log_font_size < 22:
            self.log_font_size += 1
            self._apply_log_font()

    def _zoom_out_log(self):
        if self.log_font_size > 8:
            self.log_font_size -= 1
            self._apply_log_font()

    def _reset_log_font(self):
        self.log_font_size = 11
        self._apply_log_font()

    def _apply_log_font(self):
        self.lbl_log_font.configure(text=f"{self.log_font_size} pt")
        self.log_text.configure(font=("Consolas", self.log_font_size))
        self.log_text.tag_config("SUCCESS", font=("Consolas", self.log_font_size, "bold"))
        self.log_text.tag_config("ERROR", font=("Consolas", self.log_font_size, "bold"))
        for i in range(1, 6):
            self.log_text.tag_config(f"W{i}", font=("Consolas", self.log_font_size, "bold"))

    def _on_log_mousewheel(self, event):
        if event.delta > 0:
            self._zoom_in_log()
        elif event.delta < 0:
            self._zoom_out_log()
        return "break"

    def _setup_event_listener(self):
        logger.register_callback(self._on_log_emitted)
        self.after(100, self._process_event_bus)

    def _on_log_emitted(self, level, message, time_str):
        self.log_queue.put((level, message, time_str))

    def _browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Pilih File Excel Data Cleaning NIK R27 R27",
            filetypes=[("Excel Files", "*.xlsx *.xlsm"), ("All Files", "*.*")]
        )
        if file_path:
            self.entry_file.delete(0, "end")
            self.entry_file.insert(0, file_path)
            self._load_and_validate_file(file_path)

    def _on_file_entry_return(self):
        pth = self.entry_file.get().strip().strip('"').strip("'")
        if pth:
            self._load_and_validate_file(pth)

    def _download_template(self):
        dest_path = filedialog.asksaveasfilename(
            title="Simpan Template Data Cleaning NIK R27 R27",
            defaultextension=".xlsx",
            initialfile="Template_Data_Cleaning_NIK_R27_SE2026.xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        )
        if not dest_path:
            return

        try:
            ExcelNIKR27Validator.generate_template_excel(dest_path)
            ans = messagebox.askyesno(
                "Unduh Template Berhasil",
                f"Template Excel Data Cleaning NIK R27 R27 berhasil disimpan ke:\n{dest_path}\n\n"
                "Apakah Anda ingin langsung membuka file tersebut sekarang?"
            )
            if ans:
                os.startfile(dest_path)
        except Exception as e:
            messagebox.showerror("Gagal Membuat Template", f"Terjadi kesalahan saat membuat template: {e}")

    def _load_and_validate_file(self, file_path):
        self.current_excel_path = file_path
        filename = Path(file_path).name

        self.lbl_validation.configure(text="Sedang memvalidasi template Excel...", text_color="#f59e0b")
        self.update_idletasks()

        res = ExcelNIKR27Validator.validate_excel_file(file_path)
        self.validated_data = res

        if not res["valid"]:
            self.lbl_validation.configure(
                text=f"❌ {res['error']}",
                text_color="#f87171"
            )
            self.btn_start.configure(state="disabled")
            messagebox.showerror("Validasi Template Gagal", f"File '{filename}' tidak memenuhi template:\n\n{res['error']}")
            return

        # Template valid
        if self.event_bus.get_state() != EngineState.RUNNING:
            self.btn_start.configure(state="normal")
            self.btn_pause.configure(state="disabled", text="⏸️ Jeda")
            self.btn_stop.configure(state="disabled")

        if res.get("file_locked"):
            self.lbl_validation.configure(
                text=f"⚠️ Template Valid ({res['total_rows']} baris: {res['pending_rows']} belum, {res['done_rows']} selesai) - Tutup file di Excel sebelum Mulai.",
                text_color="#f59e0b"
            )
        else:
            self.lbl_validation.configure(
                text=f"✅ Template Valid ({filename}): Total {res['total_rows']} baris ({res['done_rows']} selesai, {res['pending_rows']} siap diproses).",
                text_color="#10b981"
            )

        total = res["total_rows"]
        done = res["done_rows"]
        pending = res["pending_rows"]

        self.current_stats["total"] = total
        self.current_stats["done"] = done
        self.current_stats["pending"] = pending
        self.current_stats["error"] = 0

        self.card_total.configure(text=str(total))
        self.card_done.configure(text=str(done))
        self.card_pending.configure(text=str(pending))
        self.card_error.configure(text="0")
        self.lbl_prog_pct.configure(text=f"0% (0/{total})")

        self._populate_table_preview(res)
        logger.info(f"File Excel NIK berhasil divalidasi: {filename} (Total: {total}, Sisa: {pending})")

    def _populate_table_preview(self, res):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_map.clear()

        for i, row in enumerate(res["rows_data"]):
            status_str = str(row.get("status") or "").strip().upper()
            status_tag = "tag_belum"
            if "SUKSES" in status_str or "DONE" in status_str:
                status_tag = "tag_done"
            elif "GAGAL" in status_str:
                status_tag = "tag_gagal"
            elif "DIHENTIKAN" in status_str or "DILEWATI" in status_str:
                status_tag = "tag_dihentikan"

            stripe_tag = "even" if i % 2 == 0 else "odd"

            r_num = row.get("row_idx", row.get("_row_num", i + 2))
            url_str = str(row.get("url") or "").strip()
            url_display = url_str[:35] + "..." if len(url_str) > 35 else url_str
            niks = row.get("nik_list", [])
            total_n = row.get("total_nik", len(niks))
            if niks:
                if len(niks) <= 2:
                    nik_display = f"{', '.join(niks)} ({len(niks)} NIK)"
                else:
                    nik_display = f"{', '.join(niks[:2])}... ({len(niks)} NIK)"
            else:
                nik_display = "Kosong"

            item_id = self.tree.insert("", "end", values=(
                i + 1,
                r_num,
                url_display,
                total_n,
                nik_display,
                row.get("status") or "⏳ BELUM",
                row.get("keterangan") or ""
            ), tags=(stripe_tag, status_tag))
            self.tree_item_map[r_num] = item_id

    def _toggle_range_inputs(self):
        if self.range_var.get() == "custom":
            self.entry_start_row.configure(state="normal")
            self.entry_end_row.configure(state="normal")
            if not self.entry_start_row.get().strip():
                self.entry_start_row.insert(0, "2")
            self.entry_start_row.focus()
        else:
            self.entry_start_row.configure(state="disabled")
            self.entry_end_row.configure(state="disabled")

    def _toggle_auth_inputs(self):
        if self.auth_mode_var.get() == "auto":
            self.creds_frame.pack(side="left", padx=(0, 10))
            self.entry_sso_user.focus()
        else:
            self.creds_frame.pack_forget()

    def _toggle_show_password(self):
        if self.entry_sso_pass.cget("show") == "*":
            self.entry_sso_pass.configure(show="")
            self.btn_toggle_pass.configure(text="🔒")
        else:
            self.entry_sso_pass.configure(show="*")
            self.btn_toggle_pass.configure(text="👁")

    def _start_automation(self):
        if not self.current_excel_path or not self.validated_data or not self.validated_data.get("valid"):
            messagebox.showwarning("Perhatian", "Silakan pilih file Excel dengan template yang valid terlebih dahulu.")
            return

        if ExcelNIKR27Validator.is_file_locked(self.current_excel_path):
            messagebox.showwarning(
                "File Excel Terbuka",
                "File Excel saat ini sedang dibuka di aplikasi Microsoft Excel.\n\n"
                "Harap tutup file Excel tersebut terlebih dahulu agar bot dapat menulis hasil eksekusi secara aman."
            )
            return

        # Validasi Kredensial jika memilih Auto Login
        auth_mode = self.auth_mode_var.get()
        sso_username = self.entry_sso_user.get().strip() if hasattr(self, "entry_sso_user") else ""
        sso_password = self.entry_sso_pass.get().strip() if hasattr(self, "entry_sso_pass") else ""

        if auth_mode == "auto":
            if not sso_username or not sso_password:
                messagebox.showwarning(
                    "Kredensial Belum Diisi",
                    "Anda memilih mode 'Auto Login (Khusus Non-OTP)'.\n\n"
                    "Silakan masukkan Username dan Password SSO BPS terlebih dahulu."
                )
                if not sso_username:
                    self.entry_sso_user.focus()
                else:
                    self.entry_sso_pass.focus()
                return

        row_start = 2
        row_end = None
        if self.range_var.get() == "custom":
            start_str = self.entry_start_row.get().strip()
            end_str = self.entry_end_row.get().strip()
            if start_str:
                try:
                    row_start = max(2, int(start_str))
                except ValueError:
                    messagebox.showwarning("Rentang Tidak Valid", "Nilai 'Dari Baris' harus berupa angka (minimal 2).")
                    return
            if end_str:
                try:
                    row_end = int(end_str)
                    if row_end < row_start:
                        messagebox.showwarning("Rentang Tidak Valid", "Nilai 's.d. Baris' harus lebih besar atau sama dengan baris awal.")
                        return
                except ValueError:
                    messagebox.showwarning("Rentang Tidak Valid", "Nilai 's.d. Baris' harus berupa angka.")
                    return

        debug_review = (self.mode_var.get() == "debug")
        auto_minimize = bool(self.cb_minimize.get())

        raw_w = self.worker_opt.get()
        try:
            num_workers = int(raw_w.split()[0])
        except Exception:
            num_workers = 2

        # Atur visibilitas badge worker di dashboard
        for i in range(1, 6):
            if i <= num_workers:
                self.worker_badges[i]["frame"].pack(side="left", padx=4, pady=3)
                self.worker_badges[i]["label"].configure(text=f"W-{i}: ⏸️ Menunggu", text_color="#94a3b8")
                self.worker_badges[i]["frame"].configure(border_color="#334155")
            else:
                self.worker_badges[i]["frame"].pack_forget()

        config_opts = {
            "debug_review_submit": debug_review,
            "auto_minimize": auto_minimize,
            "row_start": row_start,
            "row_end": row_end,
            "num_workers": num_workers,
            "auth_mode": auth_mode,
            "sso_username": sso_username,
            "sso_password": sso_password
        }

        self.event_bus.reset_controls()
        engine = CleaningNIKR27Engine(self.current_excel_path, self.event_bus, config_opts)

        self.btn_start.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸️ Jeda", fg_color="#f59e0b", hover_color="#d97706")
        self.btn_stop.configure(state="normal")
        self.btn_confirm_submit.configure(state="disabled")
        if self.btn_confirm_auth.winfo_manager() == "pack":
            self.btn_confirm_auth.pack_forget()

        self.worker_thread = threading.Thread(target=engine.run, daemon=True, name="CleaningNIK-EngineThread")
        self.worker_thread.start()

    def _on_enter_pressed(self, event=None):
        if self.btn_confirm_auth.winfo_manager() == "pack":
            self._confirm_auth_action()
        elif self.event_bus.is_waiting_confirm_submit():
            self._confirm_submit_action()

    def _toggle_pause(self):
        if self.event_bus.is_paused():
            self.event_bus.request_resume()
            self.btn_pause.configure(text="⏸️ Jeda", fg_color="#f59e0b", hover_color="#d97706")
            self.lbl_active_row.configure(text="▶️ Melanjutkan otomasi...")
        else:
            self.event_bus.request_pause()
            self.btn_pause.configure(text="▶️ Lanjutkan Otomasi", fg_color="#10b981", hover_color="#059669")

    def _stop_automation(self):
        confirm = messagebox.askyesno(
            "Konfirmasi Hentikan",
            "Apakah Anda yakin ingin menghentikan otomasi?\n"
            "Worker yang sedang berjalan akan menyelesaikan baris saat ini dengan aman lalu berhenti."
        )
        if confirm:
            self.lbl_active_row.configure(text="⏹️ Mengirim sinyal berhenti aman...")
            self.event_bus.request_stop()
            self.btn_stop.configure(state="disabled")

    def _confirm_submit_action(self):
        self.btn_confirm_submit.configure(state="disabled")
        self.event_bus.confirm_submit()

    def _confirm_auth_action(self):
        if self.btn_confirm_auth.winfo_manager() == "pack":
            self.btn_confirm_auth.pack_forget()
        self.lbl_active_row.configure(text="🟢 Mengonfirmasi status login ke browser...")
        self.event_bus.confirm_auth()

    def _process_event_bus(self):
        """Memproses event queue dan log terminal dari background worker thread ke UI."""
        # 1. Flush antrean log ke log_text secara thread-safe pada UI main thread
        logs_drained = 0
        autoscroll = self.cb_autoscroll.get()
        while not self.log_queue.empty() and logs_drained < 100:
            try:
                level, message, time_str = self.log_queue.get_nowait()
                m = re.match(r"^(.*?)(\[W-([1-5])\])\s*(.*)$", message)
                if m:
                    pre, tag_text, w_num, post = m.groups()
                    if pre:
                        self.log_text.insert("end", f"[{time_str}] [{level}] {pre}", level)
                    else:
                        self.log_text.insert("end", f"[{time_str}] [{level}] ", level)
                    self.log_text.insert("end", f"{tag_text} ", f"W{w_num}")
                    self.log_text.insert("end", f"{post}\n", level)
                else:
                    formatted = f"[{time_str}] [{level}] {message}\n"
                    self.log_text.insert("end", formatted, level)
                logs_drained += 1
            except queue.Empty:
                break

        if logs_drained > 0 and autoscroll:
            self.log_text.see("end")

        # 2. Proses event bus reguler
        events = self.event_bus.poll_events()
        for ev_type, payload in events:
            if ev_type == "row_started":
                r_idx = payload["row_idx"]
                w_id = payload.get("worker_id")
                w_info = f"[W-{w_id}] " if w_id else ""
                url_short = payload.get("url", "")
                if len(url_short) > 30:
                    url_short = url_short[:30] + "..."
                self.lbl_active_row.configure(text=f"🔄 {w_info}Sedang memproses Baris {r_idx}: {url_short}")
                if r_idx in self.tree_item_map:
                    item_id = self.tree_item_map[r_idx]
                    vals = list(self.tree.item(item_id, "values"))
                    vals[5] = f"🔄 PROSES (W{w_id})" if w_id else "🔄 PROSES"
                    old_tags = list(self.tree.item(item_id, "tags"))
                    stripe_tag = "odd" if "odd" in old_tags else "even"
                    self.tree.item(item_id, values=vals, tags=(stripe_tag, "tag_proses"))
                    self.tree.see(item_id)

            elif ev_type == "worker_status_updated":
                w_id = payload.get("worker_id")
                st = payload.get("status")
                r_idx = payload.get("row_idx")
                nama = payload.get("nama_usaha", "")
                if w_id and w_id in self.worker_badges:
                    b_info = self.worker_badges[w_id]
                    w_color = self.worker_badge_colors.get(w_id, "#38bdf8")
                    if st == "BUSY":
                        short_nama = (nama[:13] + "..") if len(nama) > 13 else nama
                        b_info["label"].configure(text=f"W-{w_id}: 🔄 B{r_idx} {short_nama}", text_color=w_color)
                        b_info["frame"].configure(border_color=w_color)
                    elif st == "IDLE":
                        b_info["label"].configure(text=f"W-{w_id}: ⏸️ Siap", text_color="#94a3b8")
                        b_info["frame"].configure(border_color="#334155")
                    elif st == "DONE":
                        b_info["label"].configure(text=f"W-{w_id}: ✅ Selesai", text_color="#10b981")
                        b_info["frame"].configure(border_color="#10b981")
                    elif st == "ERROR":
                        b_info["label"].configure(text=f"W-{w_id}: ❌ Error", text_color="#f87171")
                        b_info["frame"].configure(border_color="#f87171")

            elif ev_type == "row_completed":
                r_idx = payload["row_idx"]
                status = payload["status"]
                ket = payload.get("keterangan", "")
                if r_idx in self.tree_item_map:
                    item_id = self.tree_item_map[r_idx]
                    vals = list(self.tree.item(item_id, "values"))
                    old_tags = list(self.tree.item(item_id, "tags"))
                    stripe_tag = "odd" if "odd" in old_tags else "even"
                    if "SUKSES" in status or "DONE" in status:
                        vals[5] = "✅ SUKSES"
                        new_status_tag = "tag_done"
                        self.current_stats["done"] += 1
                        self.current_stats["pending"] = max(0, self.current_stats["pending"] - 1)
                    elif "DIHENTIKAN" in status:
                        vals[5] = "⏹️ DIHENTIKAN"
                        new_status_tag = "tag_dihentikan"
                    elif "DILEWATI" in status:
                        vals[5] = "⏭️ DILEWATI"
                        new_status_tag = "tag_dihentikan"
                        self.current_stats["pending"] = max(0, self.current_stats["pending"] - 1)
                    else:
                        vals[5] = "❌ GAGAL"
                        new_status_tag = "tag_gagal"
                        self.current_stats["error"] += 1
                        self.current_stats["pending"] = max(0, self.current_stats["pending"] - 1)

                    vals[6] = ket
                    self.tree.item(item_id, values=vals, tags=(stripe_tag, new_status_tag))

                    # Update live kartu metrik
                    self.card_done.configure(text=str(self.current_stats["done"]))
                    self.card_error.configure(text=str(self.current_stats["error"]))
                    self.card_pending.configure(text=str(self.current_stats["pending"]))

            elif ev_type == "waiting_confirm_submit":
                r_idx = payload["row_idx"]
                nama = payload.get("nama_usaha", "")
                self.btn_confirm_submit.configure(state="normal", text="✅ Konfirmasi Submit & Lanjut (Enter)")
                self.lbl_active_row.configure(text=f"🔍 [Review] Baris {r_idx} [{nama}]: Silakan periksa rincian NIK di Chrome, lalu klik konfirmasi atau tekan ENTER.")

            elif ev_type == "progress_updated":
                curr = payload["current"]
                total = payload["total"]
                pct = curr / float(total) if total > 0 else 0
                self.progress_bar.set(pct)
                pct_str = f"{int(round(pct * 100))}% ({curr}/{total})"
                self.lbl_prog_pct.configure(text=pct_str)

            elif ev_type == "auth_waiting":
                msg = payload.get("message", "Silakan login SSO BPS & OTP di jendela Google Chrome.")
                is_mid = payload.get("is_midrun", False)
                r_idx = payload.get("row_idx")
                if is_mid and r_idx:
                    self.lbl_active_row.configure(text=f"🔑 [Sesi Habis di Baris {r_idx}] {msg}")
                    self.btn_confirm_auth.configure(text="🟢 Saya Sudah Login Kembali")
                else:
                    self.lbl_active_row.configure(text=f"🔑 [Login SSO Diperlukan] {msg}")
                    self.btn_confirm_auth.configure(text="🟢 Saya Sudah Login (Lanjutkan)")
                if self.btn_confirm_auth.winfo_manager() != "pack":
                    self.btn_confirm_auth.pack(side="left", padx=(0, 8))

            elif ev_type == "auth_success":
                if self.btn_confirm_auth.winfo_manager() == "pack":
                    self.btn_confirm_auth.pack_forget()
                is_mid = payload.get("is_midrun", False)
                r_idx = payload.get("row_idx")
                if is_mid and r_idx:
                    self.lbl_active_row.configure(text=f"🟢 Sesi pulih! Memuat ulang Baris {r_idx}...")
                else:
                    self.lbl_active_row.configure(text="🟢 Login SSO Fasih aktif. Memulai pemrosesan data NIK...")

            elif ev_type == "auth_required":
                messagebox.showwarning("Perhatian SSO", payload.get("message", "Login SSO Diperlukan."))

            elif ev_type == "all_completed":
                if self.btn_confirm_auth.winfo_manager() == "pack":
                    self.btn_confirm_auth.pack_forget()
                self.btn_start.configure(state="normal")
                self.btn_pause.configure(state="disabled", text="⏸️ Jeda", fg_color="#f59e0b")
                self.btn_stop.configure(state="disabled")
                self.btn_confirm_submit.configure(state="disabled", text="✅ Konfirmasi Submit & Lanjut (Enter)")
                for i in range(1, 6):
                    if i in self.worker_badges:
                        self.worker_badges[i]["label"].configure(text=f"W-{i}: ✅ Selesai", text_color="#10b981")
                        self.worker_badges[i]["frame"].configure(border_color="#10b981")
                was_stopped = payload.get("was_stopped", False)
                if was_stopped:
                    self.lbl_active_row.configure(text="⏹️ Otomasi Data Cleaning NIK R27 R27 telah dihentikan pengguna.")
                    messagebox.showinfo(
                        "Otomasi Dihentikan",
                        f"Otomasi Cleaning NIK R27 dihentikan secara aman.\n- Berhasil: {payload['done']}\n- Gagal: {payload['error']}\n- Dilewati: {payload['skipped']}"
                    )
                else:
                    self.lbl_active_row.configure(text="🏁 Seluruh proses otomasi Data Cleaning NIK R27 R27 telah selesai!")
                    messagebox.showinfo(
                        "Otomasi Selesai",
                        f"Otomasi Cleaning NIK R27 selesai!\n- Berhasil: {payload['done']}\n- Gagal: {payload['error']}\n- Dilewati: {payload['skipped']}"
                    )

        self.after(100, self._process_event_bus)

    def _copy_logs(self):
        txt = self.log_text.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(txt)
        messagebox.showinfo("Salin Log", "Seluruh teks log berhasil disalin ke clipboard.")

    def _clear_logs(self):
        self.log_text.delete("1.0", "end")

    def _open_log_folder(self):
        os.startfile(str(LOGS_DIR))
