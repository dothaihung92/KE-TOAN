// Regression test (Node) cho lỗi thật người dùng báo kèm 2 ảnh chụp màn
// hình "Kế Toán AI": dòng giao dịch đã bấm "🔀 Tách BHXH" (tách thành 3
// khoản 3383/3384/3386 — bảo hiểm phải nộp cho cơ quan BHXH, KHÔNG PHẢI
// công nợ 131/331 với 1 đối tượng cụ thể) vẫn bị modal "Import chi tiền
// (UNC) vào MISA" báo "THIẾU MST (hạch toán 131/331) — cần bấm "Chọn HĐ"/
// sửa tay MST cho các dòng này trước" và bị LOẠI KHỎI danh sách import,
// dù dòng đó không hề hạch toán 131/331 thật sự.
//
// Nguyên nhân: nút "🔀 BHXH ✓" (bhxhRow) chỉ bật cờ r.isBhxh=true, KHÔNG hề
// đổi r.confirmedHach (vẫn giữ giá trị MẶC ĐỊNH "331" gán từ lúc xác nhận
// dòng, vì BHXH luôn là giao dịch Tiền ra). buildThuChiGiaoDich (dựng danh
// sách giao dịch để import UNT/UNC vào MISA) kiểm tra "!mst && (hach==='131'
// || hach==='331')" TRƯỚC khi tới đoạn xử lý r.isBhxh (tách 3383/3384/3386)
// — dòng BHXH (không có MST, đúng bản chất vì không phải công nợ với 1
// khách/NCC cụ thể) bị chặn nhầm ở bước kiểm tra MST, không bao giờ tới
// được đoạn tách 3383/3384/3386.
//
// Fix: buildThuChiGiaoDich (dòng "if (!r.isBhxh && !mst && ...)") và
// isMissingMstRow (badge cảnh báo trên màn xác nhận) đều bỏ qua dòng
// r.isBhxh khi kiểm tra "thiếu MST hạch toán 131/331".
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'doi_chieu_ngan_hang.html'), 'utf8');

function extractFn(name) {
  const markers = ['async function ' + name + '(', 'function ' + name + '('];
  let marker = null, start = -1;
  for (const m of markers) {
    const i = html.indexOf(m);
    if (i >= 0) { marker = m; start = i; break; }
  }
  if (start < 0) throw new Error('Không tìm thấy hàm ' + name);
  let i = html.indexOf('{', start);
  let depth = 0, end = -1;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  if (end < 0) throw new Error('Không tìm được dấu } khớp cho hàm ' + name);
  return html.slice(start, end);
}

function extractConst(name) {
  const marker = 'const ' + name + ' =';
  const start = html.indexOf(marker);
  if (start < 0) throw new Error('Không tìm thấy const ' + name);
  const end = html.indexOf(';', start);
  return html.slice(start, end + 1);
}

const srcAll = [
  extractConst('RUT_NOP_TIEN_MAT_RE'),
  extractFn('normVN'),
  extractFn('buildVoucherNo'),
  extractFn('convertUsdRowsToVnd'),
  extractFn('buildThuChiGiaoDich'),
].join('\n');
eval(srcAll);

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

async function main() {
  // ----- Test 1 (đúng lỗi thật đã báo): dòng "Tách BHXH" (isBhxh=true) —
  // confirmedHach vẫn ở mặc định "331" (chưa từng bị đổi bởi nút BHXH ✓),
  // KHÔNG có confirmedMST — PHẢI tạo được 3 dòng giao dịch 3383/3384/3386,
  // KHÔNG được rơi vào boQuaThieuMst. -----
  {
    const rows = [{
      id: 'r1', confirmed: 'yes', confirmedHach: '331', confirmedMST: '', confirmedName: '',
      isBhxh: true, tx: { date: '16/03/2026', debit: 3000000, credit: 0, desc: 'DONG BHXH T3.2026', currency: 'VND' },
    }];
    const { giaoDich, boQuaThieuMst } = await buildThuChiGiaoDich(rows, 'unc', [], 'MB', '123334488', null);
    assert(boQuaThieuMst.soLuong === 0, (
      `Dòng đã "Tách BHXH" KHÔNG được rơi vào boQuaThieuMst (đúng lỗi thật: modal báo "THIẾU MST (hạch `
      + `toán 131/331)" cho dòng BHXH dù dòng đó không hạch toán 131/331 thật) — got soLuong=${boQuaThieuMst.soLuong}, danhSach=${JSON.stringify(boQuaThieuMst.danhSach)}`));
    assert(giaoDich.length === 3, `Phải tách đúng 3 dòng giao dịch (3383/3384/3386) — got ${giaoDich.length}: ${JSON.stringify(giaoDich)}`);
    const tkSet = new Set(giaoDich.map(g => g.tk_doi_ung));
    assert(tkSet.has('3383') && tkSet.has('3384') && tkSet.has('3386'), (
      `Phải có đủ 3 TK 3383 (BHXH)/3384 (BHYT)/3386 (BHTN) — got ${JSON.stringify([...tkSet])}`));
    const tongTien = giaoDich.reduce((s, g) => s + g.so_tien, 0);
    assert(tongTien === 3000000, `Tổng 3 dòng tách phải = đúng số tiền gốc 3.000.000đ — got ${tongTien}`);
    console.log('PASS 1: dòng đã "Tách BHXH" (confirmedHach vẫn ở mặc định 331, không có MST) được tạo đúng 3 dòng giao dịch 3383/3384/3386, KHÔNG còn bị chặn nhầm ở bước kiểm tra "thiếu MST hạch toán 131/331".');
  }

  // ----- Test 2: dòng BÌNH THƯỜNG (không phải BHXH) hạch toán 331 mà THIẾU
  // MST thật sự -> VẪN PHẢI bị chặn/báo thiếu MST như cũ (không phá vỡ hành
  // vi cảnh báo hợp lệ ban đầu). -----
  {
    const rows = [{
      id: 'r2', confirmed: 'yes', confirmedHach: '331', confirmedMST: '', confirmedName: '',
      isBhxh: false, tx: { date: '16/03/2026', debit: 5000000, credit: 0, desc: 'CHUYEN KHOAN NCC ABC', currency: 'VND' },
    }];
    const { giaoDich, boQuaThieuMst } = await buildThuChiGiaoDich(rows, 'unc', [], 'MB', '123334488', null);
    assert(boQuaThieuMst.soLuong === 1 && giaoDich.length === 0, (
      `Dòng THƯỜNG (không phải BHXH) hạch toán 331 thiếu MST vẫn PHẢI bị chặn như cũ — got `
      + `boQuaThieuMst.soLuong=${boQuaThieuMst.soLuong}, giaoDich.length=${giaoDich.length}`));
    console.log('PASS 2: dòng bình thường (không "Tách BHXH") hạch toán 131/331 thiếu MST thật sự vẫn bị chặn/báo đúng như cũ, không bị ảnh hưởng bởi fix này.');
  }
}

main().then(() => console.log('\nTẤT CẢ TEST PASS')).catch(e => { console.error(e); process.exitCode = 1; });
