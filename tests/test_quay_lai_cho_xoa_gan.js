// Regression test (Node) cho unlinkRow() trong static/doi_chieu_ngan_hang.html (Kế Toán AI), theo
// 2 yêu cầu của người dùng:
//   1. "khi đã bỏ chọn giao dịch thanh toán thì giao dịch đó hãy quay lại mục chờ chưa xử lý" — bỏ
//      gắn 1 lần thanh toán khỏi tờ khai (nút ✕ cạnh mỗi payment) phải đưa GD ngân hàng tương ứng về
//      lại "Chờ", không được để nó kẹt ở trạng thái "đã xác nhận" dù không còn payment nào trỏ tới.
//   2. "Hãy thêm nút quay lại mục chờ xoá thông tin đã gắn vào giao dịch để nhập lại" — 1 nút chung
//      trên MỌI dòng đã xác nhận (dù gắn sai MST/hoá đơn/tờ khai/nội bộ/tiền mặt...) để xoá sạch và
//      đưa về "Chờ", nhập lại từ đầu.
//
// unlinkRow(id) phải: (a) xoá sạch các trường xác nhận trên dòng ngân hàng (confirmed, confirmedMST,
// confirmedHach, confirmedToKhaiId, isInternal...) về trạng thái "Chờ" ban đầu, và (b) quét + xoá
// ĐÚNG payment đang trỏ rowId này khỏi CẢ tờ khai NK lẫn XK (không dựa vào 1 field "kind" lưu sẵn trên
// dòng, vì dòng không lưu kèm biết chắc thuộc danh sách NK hay XK).
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

const tkPaymentsSrc = extractBraceBlock('function tkPayments(tk) {');
const unlinkRowSrc = extractBraceBlock('const unlinkRow = (id) => {');

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

function makeConfirmedRow(id, extra) {
  return Object.assign({
    id,
    tx: { debit: 0, credit: 5000000, date: '01/02/2026', desc: 'TT HD', currency: 'VND' },
    confirmed: 'yes',
    confirmedMST: '0311111222',
    confirmedName: 'Công ty ABC',
    confirmedLoai: 'DAURA',
    confirmedHach: '131',
    confirmedInvId: 'inv1',
    confirmedToKhaiId: 'tk1',
    manualConfirm: true,
    manualKw: 'ABC',
    isInternal: false,
  }, extra || {});
}

// ----- Test 1 (đúng yêu cầu #2): nút "↩ Quay lại chờ" — xoá sạch mọi thông tin đã gắn trên 1 dòng
// đã xác nhận, đưa confirmed về "" (Chờ). -----
{
  let rows = [makeConfirmedRow('r1')];
  const tokhaiXK = [{ id: 'tk1', toKhaiSo: 'TK001', payments: [{ rowId: 'r1', bankVND: 5000000 }] }];
  const tokhaiNK = [];
  const toasts = [];
  const factory = new Function('tokhaiListOf', 'saveTokhaiListOf', 'setRowsH', 'showToast', `
    ${tkPaymentsSrc}
    ${unlinkRowSrc}
    return unlinkRow;
  `);
  const setRowsH = updater => { rows = updater(rows); };
  let savedXK = null;
  const unlinkRow = factory(
    kind => kind === 'XK' ? tokhaiXK : tokhaiNK,
    kind => (next => { if (kind === 'XK') savedXK = next; }),
    setRowsH,
    msg => toasts.push(msg)
  );
  unlinkRow('r1');
  const r = rows.find(x => x.id === 'r1');
  assert(r.confirmed === '', `confirmed PHẢI về "" (Chờ) — got '${r.confirmed}'`);
  assert(r.confirmedMST === '' && r.confirmedName === '' && r.confirmedHach === '', 'confirmedMST/Name/Hach PHẢI xoá sạch');
  assert(r.confirmedToKhaiId === undefined, 'confirmedToKhaiId PHẢI xoá');
  assert(!r.manualConfirm, 'manualConfirm PHẢI về false');
  assert(savedXK && savedXK.find(t => t.id === 'tk1').payments.length === 0, `Payment trỏ r1 PHẢI bị xoá khỏi tờ khai XK — got ${JSON.stringify(savedXK)}`);
  assert(toasts.length === 1, 'Phải có đúng 1 toast báo đã đưa về Chờ');
  console.log('PASS 1: "↩ Quay lại chờ" xoá sạch thông tin đã gắn (kể cả payment tờ khai), đưa dòng về "Chờ".');
}

// ----- Test 2 (đúng yêu cầu #1): bỏ gắn payment ở bảng Tờ khai phải đưa dòng ngân hàng về Chờ. Mô
// phỏng removePayment() gọi onUnlinkRow(rowId) sau khi đã xoá payment khỏi tk.payments — kiểm tra
// unlinkRow vẫn hoạt động đúng dù payment đã bị xoá trước đó ở phía gọi (idempotent). -----
{
  let rows = [makeConfirmedRow('r2', { confirmedToKhaiId: 'tk2' })];
  const tokhaiNK = [{ id: 'tk2', toKhaiSo: 'TK002', payments: [] }]; // payment đã bị removePayment() xoá trước đó
  const tokhaiXK = [];
  const factory = new Function('tokhaiListOf', 'saveTokhaiListOf', 'setRowsH', 'showToast', `
    ${tkPaymentsSrc}
    ${unlinkRowSrc}
    return unlinkRow;
  `);
  const setRowsH = updater => { rows = updater(rows); };
  const unlinkRow = factory(kind => kind === 'XK' ? tokhaiXK : tokhaiNK, () => () => {}, setRowsH, () => {});
  unlinkRow('r2');
  const r = rows.find(x => x.id === 'r2');
  assert(r.confirmed === '', `Dòng ngân hàng PHẢI quay về "Chờ" sau khi bỏ gắn payment — got '${r.confirmed}'`);
  console.log('PASS 2: bỏ gắn payment (removePayment) → dòng ngân hàng tương ứng quay lại "Chờ" đúng như yêu cầu.');
}

// ----- Test 3 (không hồi quy): dòng KHÁC (không phải id đang unlink) không bị đụng tới. -----
{
  let rows = [makeConfirmedRow('r3'), makeConfirmedRow('r4')];
  const tokhaiXK = [];
  const tokhaiNK = [];
  const factory = new Function('tokhaiListOf', 'saveTokhaiListOf', 'setRowsH', 'showToast', `
    ${tkPaymentsSrc}
    ${unlinkRowSrc}
    return unlinkRow;
  `);
  const setRowsH = updater => { rows = updater(rows); };
  const unlinkRow = factory(kind => kind === 'XK' ? tokhaiXK : tokhaiNK, () => () => {}, setRowsH, () => {});
  unlinkRow('r3');
  const r3 = rows.find(x => x.id === 'r3'), r4 = rows.find(x => x.id === 'r4');
  assert(r3.confirmed === '', 'r3 phải về Chờ');
  assert(r4.confirmed === 'yes' && r4.confirmedMST === '0311111222', 'r4 (dòng khác) KHÔNG được bị đụng tới');
  console.log('PASS 3: chỉ đúng dòng được chọn bị reset, các dòng khác giữ nguyên (không hồi quy).');
}

console.log(process.exitCode ? 'CÓ TEST FAIL' : 'TẤT CẢ TEST PASS');
