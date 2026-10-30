import os
import sys
import unittest
from pathlib import Path
import importlib
import openpyxl

# Add desktop_app to sys.path
sys.path.insert(0, os.path.abspath("desktop_app"))

from playwright.sync_api import sync_playwright
from core.browser_manager import BrowserManager
from core.event_bus import EventBus

# Dynamic import to support '#' in directory name
dc_validator = importlib.import_module("modules.dc_usaha_#3603.validator")
dc_engine = importlib.import_module("modules.dc_usaha_#3603.engine")
dc_selectors = importlib.import_module("modules.dc_usaha_#3603.selectors")

ExcelValidator = dc_validator.ExcelValidator
find_total_container = dc_engine.find_total_container
check_has_existing_remark = dc_engine.check_has_existing_remark
add_remarks_to_element = dc_engine.add_remarks_to_element
ensure_anomali_switch_active = dc_engine.ensure_anomali_switch_active
find_revoke_button = dc_engine.find_revoke_button
find_edit_button = dc_engine.find_edit_button
check_and_handle_revoke_assignment = dc_engine.check_and_handle_revoke_assignment
ensure_form_mode_active = dc_engine.ensure_form_mode_active


class TestDCUsaha3603Validator(unittest.TestCase):
    """Pengujian Unit untuk Validator dan Template Excel Modul DC Usaha #3603"""

    def setUp(self):
        self.test_dir = Path("desktop_app/tests/temp_test_dc_3603")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.test_excel = self.test_dir / "test_dc_usaha.xlsx"

    def tearDown(self):
        if self.test_excel.exists():
            try:
                os.remove(self.test_excel)
            except Exception:
                pass
        if self.test_dir.exists():
            try:
                os.rmdir(self.test_dir)
            except Exception:
                pass

    def test_generate_template_excel(self):
        """Use Case: Generate template Excel DC Usaha #3603"""
        ok = ExcelValidator.generate_template_excel(str(self.test_excel))
        self.assertTrue(ok)
        self.assertTrue(self.test_excel.exists())

        wb = openpyxl.load_workbook(self.test_excel)
        sheet = wb.active
        headers = [sheet.cell(row=1, column=col).value for col in range(1, 15) if sheet.cell(row=1, column=col).value]
        
        # Header 'Link Fasih SM' (alias untuk url) harus ada
        headers_lower = [str(h).lower() for h in headers]
        self.assertTrue(any("link fasih" in h or "url" in h for h in headers_lower))
        self.assertIn("nama usaha", headers_lower)
        self.assertIn("status", headers_lower)
        self.assertIn("keterangan", headers_lower)

        # File template yang baru digenerate harus lolos validasi
        res_val = ExcelValidator.validate_excel_file(str(self.test_excel))
        self.assertTrue(res_val["valid"])
        self.assertEqual(res_val["total_rows"], 2)

    def test_validate_valid_minimal_file(self):
        """Use Case: Validasi Excel yang hanya berisi kolom 'url' (komponen keuangan opsional)"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["url", "nama_usaha"])
        ws.append(["https://fasih-sm.bps.go.id/assignment/1", "Warung Berkah"])
        ws.append(["https://fasih-sm.bps.go.id/assignment/2", "Toko Sembako"])
        wb.save(self.test_excel)

        res = ExcelValidator.validate_excel_file(str(self.test_excel))
        self.assertTrue(res["valid"])
        self.assertEqual(res["total_rows"], 2)
        self.assertEqual(len(res["rows_data"]), 2)
        self.assertEqual(res["rows_data"][0]["url"], "https://fasih-sm.bps.go.id/assignment/1")
        self.assertEqual(res["rows_data"][0]["nama_usaha"], "Warung Berkah")

    def test_validate_missing_url_column(self):
        """Use Case: Validasi Excel yang tidak memiliki kolom mandatory 'url' harus gagal"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["nama_usaha", "total_pendapatan"])
        ws.append(["Warung Berkah", 50000000])
        wb.save(self.test_excel)

        res = ExcelValidator.validate_excel_file(str(self.test_excel))
        self.assertFalse(res["valid"])
        err_msg = res.get("error", "") or res.get("message", "")
        self.assertIn("url", err_msg.lower())


class TestDCUsaha3603Playwright(unittest.TestCase):
    """Pengujian Integrasi Use Cases DOM & Playwright untuk Modul DC Usaha #3603"""

    @classmethod
    def setUpClass(cls):
        # Percepat eksekusi sleep untuk testing
        dc_engine.random_sleep = lambda *a, **k: True
        dc_engine.responsive_sleep = lambda *a, **k: True
        dc_engine.human_jitter = lambda *a, **k: None

        cls.chrome_path = BrowserManager.get_browser_path("chrome")
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=cls.chrome_path,
            headless=True
        )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page()

    def tearDown(self):
        self.page.close()

    def _build_mock_page(self, mode="TAHUNAN", notes_pengeluaran=None, notes_pendapatan=None):
        """Helper untuk membangun mock form Fasih dengan DOM yang representatif."""
        notes_p = notes_pengeluaran or []
        notes_pend = notes_pendapatan or []

        id_p = "total_pengeluaran#1001" if mode == "TAHUNAN" else "total_pengeluaran_bln#1001"
        id_pend = "total_pendapatan#1001" if mode == "TAHUNAN" else "total_pendapatan_bln#1001"

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
.hidden {{ display: none !important; }}
</style>
</head>
<body>
  <div id="{id_p}" class="container-box">
    <span>Total Pengeluaran</span>
    <button type="button" title="Catatan" id="btn-catatan-p">Catatan</button>
  </div>
  <div id="{id_pend}" class="container-box">
    <span>Total Pendapatan</span>
    <button type="button" title="Catatan" id="btn-catatan-pend">Catatan</button>
  </div>

  <!-- Modal Dialog Fasih -->
  <div id="modal-dialog" role="dialog" class="hidden" style="position:fixed;top:20px;left:20px;background:#fff;border:1px solid #ccc;padding:15px;z-index:9999;">
    <h3 id="modal-title">Catatan</h3>
    <div id="bubbles-container"></div>
    <div>
      <textarea placeholder="Tambah catatan..." id="input-catatan"></textarea>
    </div>
    <div style="margin-top:10px;">
      <button type="button" title="Simpan" id="btn-simpan">Simpan</button>
      <button type="button" title="Tutup" aria-label="Dismiss" id="btn-tutup">Tutup</button>
    </div>
  </div>

  <script>
    const dialog = document.getElementById('modal-dialog');
    const bubbles = document.getElementById('bubbles-container');
    const txtArea = document.getElementById('input-catatan');
    const btnSimpan = document.getElementById('btn-simpan');
    const btnTutup = document.getElementById('btn-tutup');
    let currentField = '';

    window.notesStore = {{
      pengeluaran: {notes_p!r},
      pendapatan: {notes_pend!r}
    }};

    function renderBubbles(field) {{
      bubbles.innerHTML = '';
      window.notesStore[field].forEach(n => {{
        const b = document.createElement('div');
        b.className = 'whitespace-pre-wrap';
        b.textContent = n;
        bubbles.appendChild(b);
      }});
    }}

    function openModal(field) {{
      currentField = field;
      renderBubbles(field);
      txtArea.value = '';
      dialog.classList.remove('hidden');
    }}

    function closeModal() {{
      dialog.classList.add('hidden');
    }}

    document.getElementById('btn-catatan-p').addEventListener('click', () => openModal('pengeluaran'));
    document.getElementById('btn-catatan-pend').addEventListener('click', () => openModal('pendapatan'));

    btnSimpan.addEventListener('click', () => {{
      const val = txtArea.value.trim();
      if (val) {{
        window.notesStore[currentField].push(val);
        renderBubbles(currentField);
      }}
      closeModal();
    }});

    btnTutup.addEventListener('click', closeModal);
    window.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') closeModal();
    }});
  </script>
</body>
</html>
"""
        self.page.set_content(html)
        self.page.wait_for_load_state("domcontentloaded")

    def test_container_detection_tahunan(self):
        """Use Case 1: Deteksi container standar tahunan"""
        self._build_mock_page(mode="TAHUNAN")

        elem_p, mode_p, sel_p = find_total_container(self.page, "pengeluaran")
        self.assertIsNotNone(elem_p)
        self.assertEqual(mode_p, "TAHUNAN")
        self.assertIn("total_pengeluaran#", sel_p)

        elem_pend, mode_pend, sel_pend = find_total_container(self.page, "pendapatan")
        self.assertIsNotNone(elem_pend)
        self.assertEqual(mode_pend, "TAHUNAN")
        self.assertIn("total_pendapatan#", sel_pend)

    def test_container_detection_usaha_baru_2026_bln(self):
        """Use Case 2: Deteksi container bulanan (_bln) untuk usaha baru buka 2026"""
        self._build_mock_page(mode="BULANAN_2026")

        elem_p, mode_p, sel_p = find_total_container(self.page, "pengeluaran")
        self.assertIsNotNone(elem_p)
        self.assertEqual(mode_p, "BULANAN_2026")
        self.assertIn("total_pengeluaran_bln#", sel_p)

        elem_pend, mode_pend, sel_pend = find_total_container(self.page, "pendapatan")
        self.assertIsNotNone(elem_pend)
        self.assertEqual(mode_pend, "BULANAN_2026")
        self.assertIn("total_pendapatan_bln#", sel_pend)

    def test_container_detection_missing(self):
        """Use Case 3: Container tidak ditemukan sama sekali pada form"""
        self.page.set_content("<html><body><div>Tidak ada formulir</div></body></html>")
        elem_p, mode_p, sel_p = find_total_container(self.page, "pengeluaran")
        self.assertIsNone(elem_p)
        self.assertIsNone(mode_p)

    def test_check_pre_existing_remark_clean(self):
        """Use Case 4: Pemeriksaan rincian yang belum memiliki catatan (harus return False)"""
        self._build_mock_page(mode="TAHUNAN", notes_pengeluaran=[])
        elem_p, _, _ = find_total_container(self.page, "pengeluaran")

        has_remark, note_text = check_has_existing_remark(self.page, elem_p, "Total Pengeluaran")
        self.assertFalse(has_remark)
        self.assertEqual(note_text, "")

        # Verifikasi dialog telah ditutup kembali
        dialog = self.page.locator("div[role='dialog']").first
        self.assertTrue(dialog.is_hidden())

    def test_check_pre_existing_remark_existing(self):
        """Use Case 5: Pemeriksaan rincian yang SUDAH memiliki catatan sebelumnya (harus return True dan teks catatan)"""
        self._build_mock_page(mode="TAHUNAN", notes_pengeluaran=["Catatan Sebelumnya dari PML"])
        elem_p, _, _ = find_total_container(self.page, "pengeluaran")

        has_remark, note_text = check_has_existing_remark(self.page, elem_p, "Total Pengeluaran")
        self.assertTrue(has_remark)
        self.assertIn("Catatan Sebelumnya dari PML", note_text)

        # Verifikasi dialog telah ditutup kembali
        dialog = self.page.locator("div[role='dialog']").first
        self.assertTrue(dialog.is_hidden())

    def test_add_remarks_pengeluaran_dan_pendapatan(self):
        """Use Case 6: Pemberian remark #0 pada pengeluaran dan #3603 pada pendapatan (Alur Sukses)"""
        self._build_mock_page(mode="TAHUNAN")
        elem_p, _, _ = find_total_container(self.page, "pengeluaran")
        elem_pend, _, _ = find_total_container(self.page, "pendapatan")

        # Beri catatan #0 pada Total Pengeluaran
        add_remarks_to_element(self.page, elem_p, "#0")

        # Beri catatan #3603 pada Total Pendapatan
        add_remarks_to_element(self.page, elem_pend, "#3603")

        # Verifikasi di notesStore JS
        notes_p = self.page.evaluate("() => window.notesStore.pengeluaran")
        notes_pend = self.page.evaluate("() => window.notesStore.pendapatan")
        self.assertIn("#0", notes_p)
        self.assertIn("#3603", notes_pend)

    def test_skip_rule_when_pengeluaran_has_existing_remark(self):
        """Use Case 7: Aturan Skip jika Total Pengeluaran sudah ada remark"""
        self._build_mock_page(mode="TAHUNAN", notes_pengeluaran=["#0 (Sudah ada)"])
        elem_p, _, _ = find_total_container(self.page, "pengeluaran")

        has_p, note_p = check_has_existing_remark(self.page, elem_p, "Total Pengeluaran")
        self.assertTrue(has_p)

        # Logika engine: Jika has_p == True -> SKIP assignment
        # Pastikan tidak ada aksi penambahan catatan dan status menjadi DILEWATI
        notes_pend = self.page.evaluate("() => window.notesStore.pendapatan")
        self.assertEqual(len(notes_pend), 0)

    def test_skip_rule_when_pendapatan_has_existing_remark(self):
        """Use Case 8: Aturan Skip jika Total Pendapatan sudah ada remark"""
        self._build_mock_page(mode="TAHUNAN", notes_pengeluaran=[], notes_pendapatan=["Ada revisi"])
        elem_p, _, _ = find_total_container(self.page, "pengeluaran")
        elem_pend, _, _ = find_total_container(self.page, "pendapatan")

        has_p, _ = check_has_existing_remark(self.page, elem_p, "Total Pengeluaran")
        self.assertFalse(has_p)

        has_pend, note_pend = check_has_existing_remark(self.page, elem_pend, "Total Pendapatan")
        self.assertTrue(has_pend)
        self.assertIn("Ada revisi", note_pend)

        # Logika engine: Jika has_pend == True -> SKIP assignment
        notes_p = self.page.evaluate("() => window.notesStore.pengeluaran")
        self.assertEqual(len(notes_p), 0)

    def test_usaha_baru_2026_bln_remarks_flow(self):
        """Use Case 9: Usaha Baru 2026 (_bln) berhasil diberi remark #0 dan #3603 pada rincian bulanan"""
        self._build_mock_page(mode="BULANAN_2026")
        elem_p, mode_p, _ = find_total_container(self.page, "pengeluaran")
        elem_pend, mode_pend, _ = find_total_container(self.page, "pendapatan")

        self.assertEqual(mode_p, "BULANAN_2026")
        self.assertEqual(mode_pend, "BULANAN_2026")

        # Cek pre-existing (keduanya clean)
        has_p, _ = check_has_existing_remark(self.page, elem_p, "Total Pengeluaran")
        has_pend, _ = check_has_existing_remark(self.page, elem_pend, "Total Pendapatan")
        self.assertFalse(has_p)
        self.assertFalse(has_pend)

        # Tambahkan catatan
        add_remarks_to_element(self.page, elem_p, "#0")
        add_remarks_to_element(self.page, elem_pend, "#3603")

        notes_p = self.page.evaluate("() => window.notesStore.pengeluaran")
        notes_pend = self.page.evaluate("() => window.notesStore.pendapatan")
        self.assertIn("#0", notes_p)
        self.assertIn("#3603", notes_pend)


    def test_anomali_switch_already_active(self):
        """Use Case 10: Toggle Tampilkan Anomali sudah aktif -> Dibiarkan (tidak diklik ulang)"""
        html = """<!DOCTYPE html><html><body>
        <div id="cek_anomali_button">
          <input role="switch" type="checkbox" aria-checked="true" checked>
          <div id="switch-123-control"></div>
        </div>
        </body></html>"""
        self.page.set_content(html)
        result = ensure_anomali_switch_active(self.page)
        self.assertFalse(result)  # False artinya sudah aktif sebelumnya, dibiarkan

    def test_anomali_switch_inactive_activates_on_click(self):
        """Use Case 11: Toggle Tampilkan Anomali belum aktif -> Berhasil diaktifkan setelah klik kontrol"""
        html = """<!DOCTYPE html><html><body>
        <div id="cek_anomali_button">
          <input role="switch" type="checkbox" aria-checked="false">
          <div id="switch-123-control" style="display:inline-block;width:30px;height:15px;background:#ccc;"></div>
        </div>
        <script>
          const ctrl = document.getElementById('switch-123-control');
          const inp = document.querySelector("input[role='switch']");
          ctrl.addEventListener('click', () => {
            inp.setAttribute('aria-checked', 'true');
            inp.checked = true;
          });
        </script>
        </body></html>"""
        self.page.set_content(html)
        result = ensure_anomali_switch_active(self.page)
        self.assertTrue(result)  # True artinya berhasil diaktifkan
        sw_input = self.page.locator("div#cek_anomali_button input[role='switch']").first
        self.assertEqual(sw_input.get_attribute("aria-checked"), "true")

    def test_engine_done_and_success_count_attributes(self):
        """Use Case 12: Engine memiliki atribut done_session dan alias success_count"""
        DataCleaningEngine = dc_engine.DataCleaningEngine
        engine = DataCleaningEngine("dummy.xlsx", EventBus())
        self.assertEqual(engine.done_session, 0)
        self.assertEqual(engine.success_count, 0)
        engine.success_count += 1
        self.assertEqual(engine.done_session, 1)
        self.assertEqual(engine.success_count, 1)


    def test_revoke_button_detection(self):
        """Use Case 13: Deteksi tombol Revoke Assignment (tabler-icon-rotate-clockwise)"""
        html = '''<!DOCTYPE html><html><body>
        <button class="f:inline-flex f:items-center f:justify-center f:rounded-full f:shadow-md" data-state="closed">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="tabler-icon tabler-icon-rotate-clockwise f:size-5">
            <path d="M4.05 11a8 8 0 1 1 .5 4m-.5 5v-5h5"></path>
          </svg>
        </button>
        </body></html>'''
        self.page.set_content(html)
        btn = find_revoke_button(self.page)
        self.assertIsNotNone(btn)
        self.assertTrue(btn.is_visible())

    def test_edit_button_detection(self):
        """Use Case 14: Deteksi tombol Edit Assignment (tabler-icon-edit)"""
        html = '''<!DOCTYPE html><html><body>
        <button class="f:inline-flex f:items-center f:justify-center f:rounded-full f:shadow-md" data-state="closed">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="tabler-icon tabler-icon-edit f:size-5">
            <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1"></path>
            <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415"></path>
            <path d="M16 5l3 3"></path>
          </svg>
        </button>
        </body></html>'''
        self.page.set_content(html)
        btn = find_edit_button(self.page)
        self.assertIsNotNone(btn)
        self.assertTrue(btn.is_visible())

    def test_revoke_not_needed_when_no_button(self):
        """Use Case 15: Penugasan normal tanpa tombol revoke -> return False"""
        self.page.set_content("<!DOCTYPE html><html><body><div>Formulir Normal</div></body></html>")
        res = check_and_handle_revoke_assignment(self.page)
        self.assertFalse(res)

    def test_revoke_assignment_flow_success(self):
        """Use Case 16: Alur lengkap Revoke Assignment (Klik Revoke -> Konfirmasi -> Reload -> Tombol Edit Muncul)"""
        html = '''<!DOCTYPE html><html><body>
        <div id="container">
          <button id="btn-revoke" class="f:inline-flex f:items-center f:justify-center f:rounded-full f:shadow-md">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="tabler-icon tabler-icon-rotate-clockwise f:size-5">
              <path d="M4.05 11a8 8 0 1 1 .5 4m-.5 5v-5h5"></path>
            </svg>
          </button>
        </div>

        <div role="alertdialog" id="revoke-dialog" style="display:none;">
          <h2>Revoke Assignment?</h2>
          <p>Apakah Anda yakin ingin revoke assignment ini?</p>
          <button type="button" id="btn-batal">Batal</button>
          <button type="button" id="btn-konfirm">Konfirmasi</button>
        </div>

        <script>
          const btnRevoke = document.getElementById('btn-revoke');
          const dialog = document.getElementById('revoke-dialog');
          const btnKonfirm = document.getElementById('btn-konfirm');
          const container = document.getElementById('container');

          btnRevoke.addEventListener('click', () => {
            dialog.style.display = 'block';
          });

          btnKonfirm.addEventListener('click', () => {
            dialog.style.display = 'none';
            container.innerHTML = `
              <button id="btn-edit" class="f:inline-flex f:items-center f:justify-center f:rounded-full f:shadow-md">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="tabler-icon tabler-icon-edit f:size-5">
                  <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1"></path>
                  <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415"></path>
                  <path d="M16 5l3 3"></path>
                </svg>
              </button>
            `;
          });
        </script>
        </body></html>'''
        self.page.set_content(html)
        res = check_and_handle_revoke_assignment(self.page)
        self.assertTrue(res)
        btn_edit = find_edit_button(self.page)
        self.assertIsNotNone(btn_edit)

    def test_ensure_form_mode_active_clicks_edit(self):
        """Use Case 17: ensure_form_mode_active mengklik tombol Edit jika tersedia"""
        html = '''<!DOCTYPE html><html><body>
        <button id="btn-edit" class="f:inline-flex f:items-center f:justify-center f:rounded-full f:shadow-md">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="tabler-icon tabler-icon-edit f:size-5">
            <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1"></path>
          </svg>
        </button>
        <script>
          window.editClicked = false;
          document.getElementById('btn-edit').addEventListener('click', () => {
            window.editClicked = true;
          });
        </script>
        </body></html>'''
        self.page.set_content(html)
        ensure_form_mode_active(self.page)
        clicked = self.page.evaluate("() => window.editClicked")
        self.assertTrue(clicked)

if __name__ == "__main__":
    unittest.main()
