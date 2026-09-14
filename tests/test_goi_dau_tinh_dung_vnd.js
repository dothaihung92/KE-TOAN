// Regression test (Node) cho rowAmountVND() trong static/doi_chieu_ngan_hang.html (Kế Toán AI),
// theo báo cáo thật của người dùng: "Chỉnh lại chức năng gối đầu phần mềm không chuyển qua VNĐ mà
// lấy USD để tính" — khi "gối đầu" (1 GD ngân hàng chia tiền cho NHIỀU tờ khai), phần biến
// "remainingVND"/"splitRemainingVND" từng lấy THẲNG số tiền GD gốc (VD $9,172.54 nếu GD ở TK USD)
// gán luôn là "VND" mà KHÔNG hề quy đổi qua tỷ giá — cùng gốc lỗi với "Fix: gắn tờ khai với GD từ
// TK ngoại tệ tính SAI chênh lệch" đã sửa trước đó (computeBankPayment), nhưng lần này ở luồng
// "gối đầu" (handlePickSplit/splitRemainingVND), không phải luồng gắn 1 tờ khai đơn lẻ.
//
// Fix: thêm rowAmountVND(row) — dùng CHUNG cho cả computeBankPayment lẫn handlePickSplit/
// splitRemainingVND — quy đổi ĐÚNG ra VND khi GD đang ở TK ngoại tệ (nhân với row.tyGia, tỷ giá VCB
// người dùng đã tự nhập), lấy thẳng số tiền khi GD đã ở TK VND (không đổi hành vi cũ).
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'doi_chieu_ngan_hang.html'), 'utf8');

function extractBraceBlock(marker) {
  const start = html.indexOf(marker);
  if (start < 0) throw new Error('Không tìm thấy: ' + marker);
  let i = html.indexOf('{', start);
  let depth = 0, end = -1;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  if (end < 0) throw new Error('Không tìm được dấu } khớp cho: ' + marker);
  return html.slice(start, end);
}

const rowAmountVNDSrc = extractBraceBlock('function rowAmountVND(row) {');
const rowAmountVND = new Function(`${rowAmountVNDSrc}\nreturn rowAmountVND;`)();

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

// ----- Test 1 (đúng ca thật đã báo): GD ở TK USD, có tỷ giá VCB đã nhập — PHẢI quy đổi ra VND
// đúng bằng số ngoại tệ × tỷ giá, KHÔNG được trả thẳng số ngoại tệ. -----
{
  const row = { tx: { debit: 0, credit: 9172.54, currency: 'USD' }, tyGia: 26391 };
  const vnd = rowAmountVND(row);
  assert(vnd === Math.round(9172.54 * 26391), `PHẢI quy đổi đúng ra VND (9172.54 × 26391) — got ${vnd}, expected ${Math.round(9172.54 * 26391)}`);
  assert(vnd !== 9172.54, 'TUYỆT ĐỐI không được trả thẳng số USD (9172.54) làm số VND — đúng lỗi thật đã báo');
  console.log('PASS 1: GD ở TK USD có tỷ giá VCB — rowAmountVND() quy đổi đúng ra VND, không còn lấy thẳng số USD.');
}

// ----- Test 2: GD ở TK USD nhưng CHƯA có tỷ giá — trả về số ngoại tệ gốc (không quy đổi được), để
// nơi gọi tự cảnh báo, không được throw lỗi/crash. -----
{
  const row = { tx: { debit: 0, credit: 9172.54, currency: 'USD' }, tyGia: 0 };
  const vnd = rowAmountVND(row);
  assert(vnd === 9172.54, `Chưa có tỷ giá thì tạm trả số ngoại tệ gốc (để nơi gọi cảnh báo) — got ${vnd}`);
  console.log('PASS 2: GD ở TK USD chưa có tỷ giá — không crash, trả về số gốc để nơi gọi tự cảnh báo.');
}

// ----- Test 3 (không hồi quy): GD ở TK VND — lấy thẳng số tiền như hành vi cũ, không bị ảnh hưởng. -----
{
  const row = { tx: { debit: 0, credit: 195000000, currency: 'VND' } };
  const vnd = rowAmountVND(row);
  assert(vnd === 195000000, `GD ở TK VND vẫn phải lấy thẳng số tiền như cũ — got ${vnd}`);
  console.log('PASS 3: GD ở TK VND (hành vi cũ) không bị ảnh hưởng bởi fix.');
}

// ----- Test 4: GD debit (tiền ra) cũng phải quy đổi đúng như GD credit (tiền vào). -----
{
  const row = { tx: { debit: 5000, credit: 0, currency: 'USD' }, tyGia: 26100 };
  const vnd = rowAmountVND(row);
  assert(vnd === Math.round(5000 * 26100), `GD tiền ra (debit) ở TK USD vẫn phải quy đổi đúng — got ${vnd}`);
  console.log('PASS 4: GD tiền ra (debit) ở TK USD cũng quy đổi đúng ra VND.');
}

console.log(process.exitCode ? 'CÓ TEST FAIL' : 'TẤT CẢ TEST PASS');
