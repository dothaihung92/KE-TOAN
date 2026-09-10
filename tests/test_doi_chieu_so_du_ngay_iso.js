// Regression test (Node) cho lỗi thật người dùng báo kèm 2 ảnh chụp màn
// hình: sau khi ghi đúng mã 112x riêng cho TK "1121-TCB-122334488" (Bảng
// cân đối tài khoản MISA đã hiện đúng cả 2 dòng "1121-MB-.../1121-TCB-..."),
// bấm "Đối chiếu số dư với MISA" ở tab TK đó lại báo lỗi "Chưa có giao dịch
// nào để xác định ngày cuối kỳ" dù tab đang có 365 giao dịch (79 tự động,
// 286 thủ công) — ảnh chụp dòng đầu tiên hiện ngày "2026-07-22".
//
// Nguyên nhân: dateRangeOfRows (doi_chieu_ngan_hang.html) trước đây tự so
// khớp r.tx.date với regex CHỈ nhận "dd/mm/yyyy" — TK này có giao dịch lưu
// ngày dạng "yyyy-mm-dd" (VD chuyển khoản nhanh qua QR), khiến MỌI dòng bị
// coi là "không đọc được ngày", nên tuNgay/denNgay đều rỗng dù có hàng trăm
// giao dịch thật.
//
// Fix: parseFlexVNDate (hàm mới, top-level) nhận diện phần nào là năm (4
// chữ số) để tự suy ra thứ tự dd/mm/yyyy hay yyyy/mm/dd, dùng trong
// dateRangeOfRows thay cho regex hẹp cũ.
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

eval(extractFn('parseFlexVNDate'));

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

// ----- Test 1 (đúng lỗi thật): ngày dạng "yyyy-mm-dd" (VD "2026-07-22" như ảnh chụp thật) PHẢI
// đọc được, KHÔNG được trả null như regex hẹp cũ. -----
{
  const p = parseFlexVNDate('2026-07-22');
  assert(p !== null, 'Ngày "2026-07-22" (yyyy-mm-dd, đúng ảnh chụp thật) PHẢI đọc được, không được trả null');
  assert(p.dd === 22 && p.mm === 7 && p.yyyy === 2026, `Phải đọc đúng dd=22 mm=7 yyyy=2026 — got ${JSON.stringify(p)}`);
  console.log('PASS 1: ngày "2026-07-22" (yyyy-mm-dd) đọc đúng dd/mm/yyyy, không còn bị coi là "không đọc được ngày".');
}

// ----- Test 2: hành vi CŨ (dd/mm/yyyy, đa số sao kê dán tay) vẫn phải đọc đúng như trước, không bị
// ảnh hưởng bởi fix này. -----
{
  const p = parseFlexVNDate('22/07/2026');
  assert(p !== null && p.dd === 22 && p.mm === 7 && p.yyyy === 2026, `"22/07/2026" phải đọc đúng như cũ — got ${JSON.stringify(p)}`);
  console.log('PASS 2: ngày "22/07/2026" (dd/mm/yyyy, hành vi cũ) vẫn đọc đúng như trước.');
}

// ----- Test 3: chuỗi rỗng/không hợp lệ vẫn trả null (không throw, không đoán bừa). -----
{
  assert(parseFlexVNDate('') === null, 'Chuỗi rỗng phải trả null');
  assert(parseFlexVNDate('abc') === null, 'Chuỗi không phải ngày phải trả null');
  assert(parseFlexVNDate('31/13/2026') === null, 'Tháng 13 không hợp lệ phải trả null');
  console.log('PASS 3: chuỗi rỗng/không hợp lệ vẫn trả null như cũ, không đoán bừa.');
}

console.log('\nTẤT CẢ TEST PASS');
