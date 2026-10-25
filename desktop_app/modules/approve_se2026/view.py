import customtkinter as ctk

class ApproveSE2026View(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=10)

        # Container scrollable agar responsif terhadap zoom / ukuran layar
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Header Card
        header_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color="#1e293b")
        header_card.pack(fill="x", pady=(0, 20), padx=10)

        badge_frame = ctk.CTkFrame(header_card, fg_color="transparent")
        badge_frame.pack(anchor="w", padx=24, pady=(20, 6))

        badge = ctk.CTkLabel(
            badge_frame,
            text="✨ MODUL SEGERA HADIR (SE 2026)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#0369a1",
            text_color="#e0f2fe",
            corner_radius=6,
            padx=10,
            pady=4
        )
        badge.pack(side="left")

        title = ctk.CTkLabel(
            header_card,
            text="✅ Modul Batch Approve SE 2026",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(anchor="w", padx=24, pady=(4, 6))

        desc = ctk.CTkLabel(
            header_card,
            text=(
                "Modul ini dirancang khusus untuk mempercepat proses verifikasi dan persetujuan (approval) "
                "dokumen hasil pencacahan dan data cleaning Sensus Ekonomi 2026 di Fasih secara massal dan terintegrasi."
            ),
            font=ctk.CTkFont(size=13),
            text_color="gray70",
            wraplength=760,
            justify="left"
        )
        desc.pack(anchor="w", padx=24, pady=(0, 20))

        # Planned Features Cards Grid
        features_label = ctk.CTkLabel(
            scroll,
            text="📋 Rencana Fitur Utama Modul Approval:",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        features_label.pack(anchor="w", padx=10, pady=(0, 10))

        features = [
            (
                "⚡ Batch Approve Otomatis",
                "Menyetujui puluhan hingga ratusan dokumen penugasan yang telah berstatus 'Clean' "
                "hanya dengan sekali klik tanpa perlu approval manual satu per satu."
            ),
            (
                "🛡️ Pra-Validasi Anomali & Galat",
                "Memeriksa kembali secara otomatis apakah masih terdapat galat atau catatan anomali yang belum terselesaikan "
                "sebelum aksi persetujuan dieksekusi."
            ),
            (
                "🎯 Filter Tingkat Petugas (PML / Koseka)",
                "Dukungan fleksibel untuk peran Pengawas Lapangan (PML) maupun Koordinator Sensus Kecamatan (Koseka) "
                "berdasarkan kewenangan akun SSO Fasih."
            ),
            (
                "📊 Rekapitulasi & Audit Log Approval",
                "Pencatatan riwayat persetujuan lengkap dengan ID penugasan, waktu eksekusi, serta ekspor laporan rekap ke format Excel."
            )
        ]

        grid_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=(0, 20))

        for idx, (f_title, f_desc) in enumerate(features):
            card = ctk.CTkFrame(grid_frame, corner_radius=10, fg_color="#0f172a", border_width=1, border_color="#334155")
            card.pack(fill="x", pady=6)

            ctk.CTkLabel(
                card,
                text=f_title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#38bdf8"
            ).pack(anchor="w", padx=16, pady=(12, 4))

            ctk.CTkLabel(
                card,
                text=f_desc,
                font=ctk.CTkFont(size=12),
                text_color="gray80",
                wraplength=740,
                justify="left"
            ).pack(anchor="w", padx=16, pady=(0, 12))

        # Info Box
        info_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#1e1b4b", border_width=1, border_color="#4338ca")
        info_card.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            info_card,
            text="ℹ️ Pemberitahuan Rilis",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#a5b4fc"
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            info_card,
            text=(
                "Fitur ini akan segera diaktifkan pada pembaruan FASIH 3603 Helper versi berikutnya seiring dengan jadwal tahapan "
                "pemeriksaan dan approval lapangan Sensus Ekonomi 2026. Pantau informasi pembaruan dari tim pengembang BPS Kab Tangerang."
            ),
            font=ctk.CTkFont(size=12),
            text_color="#c7d2fe",
            wraplength=740,
            justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 14))
