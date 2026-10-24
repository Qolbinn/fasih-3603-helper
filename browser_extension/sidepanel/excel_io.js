// ==============================================================================
// FASIH 3603 HELPER - EXCEL I/O & VALIDATOR (SHEETJS ENGINE)
// ==============================================================================

window.ExcelIO = {
  currentWorkbook: null,
  currentSheetName: null,
  currentFileName: null,
  normalizedRows: [],
  headerMap: {}, // canonicalKey -> originalHeaderName

  // 1. Baca dan validasi file Excel
  async parseExcelFile(file, moduleId) {
    const config = window.MODULES_CONFIG[moduleId];
    if (!config) throw new Error(`Konfigurasi modul '${moduleId}' tidak ditemukan`);

    const data = await file.arrayBuffer();
    const workbook = XLSX.read(data, { type: "array" });
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];

    // Konversi sheet ke array of objects (raw row data)
    const rawRows = XLSX.utils.sheet_to_json(sheet, { defval: "" });

    if (rawRows.length === 0) {
      throw new Error("File Excel kosong atau tidak memiliki baris data!");
    }

    // Ekstrak nama kolom asli dari baris pertama
    const headers = Object.keys(rawRows[0]).map((h) => String(h).trim());

    // Petakan kolom berdasarkan alias
    const headerMap = {};
    for (const [canonicalKey, aliases] of Object.entries(config.columnAliases)) {
      for (const h of headers) {
        const cleanH = h.toLowerCase().trim();
        if (aliases.includes(cleanH)) {
          headerMap[canonicalKey] = h;
          break;
        }
      }
    }

    // Periksa kolom wajib (mandatory keys)
    const missingKeys = [];
    for (const mKey of config.mandatoryKeys) {
      if (!headerMap[mKey]) {
        missingKeys.push(mKey);
      }
    }

    if (missingKeys.length > 0) {
      throw new Error(
        `Kolom wajib tidak ditemukan di Excel: [${missingKeys.join(", ")}]. Silakan gunakan tombol 'Unduh Template' untuk format resmi.`
      );
    }

    // Normalisasi baris data
    const normalizedRows = [];
    let doneCount = 0;
    let pendingCount = 0;

    for (let i = 0; i < rawRows.length; i++) {
      const raw = rawRows[i];
      const norm = {
        _rowIndex: i + 2, // 1-indexed Excel row (header baris 1)
        _raw: raw
      };

      for (const [canonicalKey, originalCol] of Object.entries(headerMap)) {
        norm[canonicalKey] = raw[originalCol] !== undefined ? String(raw[originalCol]).trim() : "";
      }

      // Salin juga kolom raw dengan key lowercase agar mudah diakses
      for (const [rawK, rawV] of Object.entries(raw)) {
        const cleanK = rawK.toLowerCase().trim();
        if (norm[cleanK] === undefined) {
          norm[cleanK] = rawV !== undefined ? String(rawV).trim() : "";
        }
      }

      // Khusus NIK R27: Kumpulkan semua kolom target NIK (nik_1, nik_2, dll)
      if (moduleId === "cleaning_nik_r27") {
        const nikList = [];
        for (const [colName, val] of Object.entries(raw)) {
          const cleanCol = colName.toLowerCase().trim();
          if (/^nik(?:_|\s*)?(\d+)?$/i.test(cleanCol) && cleanCol !== "total_nik" && cleanCol !== "total nik") {
            const cleanVal = String(val).trim();
            if (cleanVal) nikList.push(cleanVal);
          }
        }
        norm.target_niks = nikList;
        norm.nik_list = nikList;
      }

      // Evaluasi status eksekusi awal
      const st = (norm.status || "").toUpperCase();
      if (st === "SELESAI" || st === "SUCCESS" || st === "BERHASIL" || st === "SUKSES") {
        norm._isDone = true;
        doneCount++;
      } else {
        norm._isDone = false;
        pendingCount++;
      }

      normalizedRows.push(norm);
    }

    this.currentWorkbook = workbook;
    this.currentSheetName = sheetName;
    this.currentFileName = file.name;
    this.normalizedRows = normalizedRows;
    this.headerMap = headerMap;

    return {
      totalRows: normalizedRows.length,
      doneRows: doneCount,
      pendingRows: pendingCount,
      rows: normalizedRows
    };
  },

  // 2. Perbarui baris di memori
  updateRowResult(rowIndex, status, keterangan) {
    const row = this.normalizedRows.find((r) => r._rowIndex === rowIndex);
    if (row) {
      row.status = status;
      row.keterangan = keterangan;
      row._isDone = status === "SELESAI";

      // Tulis juga ke raw sheet workbook
      const sheet = this.currentWorkbook.Sheets[this.currentSheetName];
      const statusCol = this.headerMap.status || "status_eksekusi";
      const ketCol = this.headerMap.keterangan || "catatan_eksekusi";

      // Cari kolom huruf di sheet
      const range = XLSX.utils.decode_range(sheet["!ref"]);
      let statusColIdx = -1;
      let ketColIdx = -1;

      for (let C = range.s.c; C <= range.e.c; ++C) {
        const cell = sheet[XLSX.utils.encode_cell({ r: 0, c: C })];
        if (cell) {
          const val = String(cell.v).toLowerCase().trim();
          if (val === statusCol.toLowerCase()) statusColIdx = C;
          if (val === ketCol.toLowerCase()) ketColIdx = C;
        }
      }

      // Jika belum ada header status/keterangan, buat kolom baru di ujung kanan
      if (statusColIdx === -1) {
        statusColIdx = range.e.c + 1;
        range.e.c = statusColIdx;
        sheet[XLSX.utils.encode_cell({ r: 0, c: statusColIdx })] = { t: "s", v: "status_eksekusi" };
      }
      if (ketColIdx === -1) {
        ketColIdx = range.e.c + 1;
        range.e.c = ketColIdx;
        sheet[XLSX.utils.encode_cell({ r: 0, c: ketColIdx })] = { t: "s", v: "catatan_eksekusi" };
      }

      sheet["!ref"] = XLSX.utils.encode_range(range);

      // Tulis nilai ke sel baris
      const rIdx = rowIndex - 1; // 0-indexed untuk SheetJS
      sheet[XLSX.utils.encode_cell({ r: rIdx, c: statusColIdx })] = { t: "s", v: status };
      sheet[XLSX.utils.encode_cell({ r: rIdx, c: ketColIdx })] = { t: "s", v: keterangan };
    }
  },

  // 3. Unduh file Excel hasil pembaruan
  downloadUpdatedExcel(filenamePrefix = "HASIL_") {
    if (!this.currentWorkbook) throw new Error("Belum ada file Excel yang diproses");

    const outData = XLSX.write(this.currentWorkbook, { bookType: "xlsx", type: "array" });
    const blob = new Blob([outData], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });

    const originalName = this.currentFileName || "data.xlsx";
    const downloadName = originalName.startsWith("HASIL_") ? originalName : `${filenamePrefix}${originalName}`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = downloadName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  // 4. Unduh Template Resmi
  downloadTemplate(moduleId) {
    const config = window.MODULES_CONFIG[moduleId];
    if (!config) throw new Error(`Konfigurasi modul '${moduleId}' tidak ditemukan`);

    const ws = XLSX.utils.json_to_sheet(config.sampleData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Sheet1");

    const outData = XLSX.write(wb, { bookType: "xlsx", type: "array" });
    const blob = new Blob([outData], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Template_${config.name.replace(/[^a-zA-Z0-9]/g, "_")}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
};
