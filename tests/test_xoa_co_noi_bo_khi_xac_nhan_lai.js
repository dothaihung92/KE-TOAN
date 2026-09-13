// Regression test (Node) cho confirmRow()/overrideRow() trong static/doi_chieu_ngan_hang.html
// (Kế Toán AI), theo báo cáo thật của người dùng kèm ảnh chụp màn hình: mở popup "⇔ Chuyển tiền nội
// bộ" cho GD "BAN 5500 USD CHO ACB TY GIA 26110" (đúng GD cần khớp), danh sách chẩn đoán hiện đúng
// GD $5.500 cùng ngày/cùng diễn giải nhưng bị đánh dấu lý do loại là "đã xử lý" — trong khi người dùng
// xác nhận "phần mềm chưa hạch toán" GD đó (không hề có bút toán thật nào cho nó).
//
// Nguyên nhân: khi 1 dòng từng được đánh dấu "vế bên kia" của 1 GD chuyển khoản nội bộ (isInternal=
// true, confirmedHach="X", qua internalTransferRow()) — dù ĐÚNG hay do gợi ý SAI từ bug đã sửa trước
// đó — nếu sau này dòng đó lại được xử lý theo hướng KHÁC qua luồng xác nhận thường (bấm "Đúng"/
// "Không khớp"/gán hoá đơn qua confirmRow(), hoặc "[TM] Tiền Mặt"/gán MST qua overrideRow()), 2 hàm
// này copy nguyên `...r` rồi CHỈ ghi đè 1 vài field (confirmed/confirmedMST/...) — cờ isInternal/
// internalAccId/confirmedHach="X" CŨ vẫn còn nguyên. Hậu quả: findInternalCandidatesFor() vĩnh viễn
// loại dòng đó ra khỏi mọi gợi ý nội bộ sau này (coi là "đã xử lý"), dù nó không còn mang hạch toán
// nội bộ thật nào — đúng lỗi đã báo.
//
// Fix: confirmRow() (cả 2 nhánh Đúng/Không khớp) và overrideRow() nay LUÔN xoá isInternal/
// internalAccId/internalAccLabel/internalSkip khi xử lý 1 dòng qua luồng thường — 1 dòng đã được xử
// lý lại theo hướng khác thì không thể còn là placeholder "vế bên kia" của GD nội bộ cũ nữa.
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
function extractStatement(marker) {
  const start = html.indexOf(marker);
  if (start < 0) throw new Error('Không tìm thấy: ' + marker);
  const end = html.indexOf(';', start) + 1;
  return html.slice(start, end);
}

const getBestSrc = extractStatement('const getBest = r =>');
// confirmRow có nhiều dấu ';' lồng bên trong thân hàm (setRowsH(prev => prev.map(...))) nên phải
// dùng extractBraceBlock (đếm ngoặc {}) rồi tự thêm phần đuôi ")" + ";" còn thiếu (setRowsH(...)
// bọc ngoài prev.map({...})) thay vì dừng ở dấu ';' đầu tiên.
const confirmRowBody = extractBraceBlock('const confirmRow = (id, val, mst, name, loai, kw) => setRowsH(prev => prev.map(r => {');
// confirmRowBody hiện dừng ngay sau dấu "}" đóng của arrow "r => {...}" — cần thêm "));" để đóng
// prev.map(...) và setRowsH(...).
const confirmRowFull = confirmRowBody + '));';

const overrideRowBody = extractBraceBlock('const overrideRow = (id, mst, name, kw, hach) => {');

const factory = new Function('setRowsH', 'showToast', `
${getBestSrc}
${confirmRowFull}
${overrideRowBody}
return { confirmRow, overrideRow };
`);

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

function makeStaleInternalRow(id) {
  return {
    id,
    tx: { debit: 5500, credit: 0, date: '14/01/2026', desc: 'BAN 5500 USD CHO ACB TY GIA 26110', currency: 'USD' },
    confirmed: 'yes',
    confirmedMST: '',
    confirmedName: '⇔ Nội bộ – Nhận từ đ 1121 (VND)',
    confirmedHach: 'X',
    manualConfirm: true,
    isInternal: true,
    internalAccId: 'vndAcc',
    internalAccLabel: 'đ 1121',
    internalSkip: false,
  };
}

// ----- Test 1 (đúng ca thật đã báo): dòng đang bị KẸT ở trạng thái isInternal=true/confirmedHach="X"
// (placeholder "vế bên kia" cũ, không còn hạch toán thật) — bấm "✓ Đúng" (confirmRow) phải XOÁ sạch
// isInternal để dòng không còn bị coi là "đã xử lý" vĩnh viễn trong gợi ý nội bộ nữa. -----
{
  let rows = [makeStaleInternalRow('u1')];
  const setRowsH = updater => { rows = updater(rows); };
  const { confirmRow } = factory(setRowsH, () => {});

  confirmRow('u1', 'yes', '', '', '', '');
  const r = rows.find(x => x.id === 'u1');
  assert(r.isInternal === false, `isInternal PHẢI về false sau khi xác nhận lại qua confirmRow — got ${r.isInternal}`);
  assert(!r.internalAccId, `internalAccId PHẢI được xoá — got ${r.internalAccId}`);
  assert(r.confirmedHach !== 'X', `confirmedHach KHÔNG được còn là placeholder "X" — got '${r.confirmedHach}'`);
  console.log('PASS 1: confirmRow("yes") xoá sạch cờ isInternal/internalAccId/confirmedHach="X" cũ — dòng không còn kẹt "đã xử lý" nội bộ.');
}

// ----- Test 2: bấm "X Không khớp" (confirmRow val="no") cũng phải xoá isInternal tương tự. -----
{
  let rows = [makeStaleInternalRow('u2')];
  const setRowsH = updater => { rows = updater(rows); };
  const { confirmRow } = factory(setRowsH, () => {});

  confirmRow('u2', 'no', null, null, null, '');
  const r = rows.find(x => x.id === 'u2');
  assert(r.isInternal === false, `isInternal PHẢI về false sau "Không khớp" — got ${r.isInternal}`);
  assert(!r.internalAccId, `internalAccId PHẢI được xoá — got ${r.internalAccId}`);
  console.log('PASS 2: confirmRow("no") cũng xoá sạch cờ isInternal cũ.');
}

// ----- Test 3: bấm "[TM] Tiền Mặt" (overrideRow) cũng phải xoá isInternal tương tự. -----
{
  let rows = [makeStaleInternalRow('u3')];
  const setRowsH = updater => { rows = updater(rows); };
  const { overrideRow } = factory(setRowsH, () => {});

  overrideRow('u3', '', 'Tiền mặt', '', '1111');
  const r = rows.find(x => x.id === 'u3');
  assert(r.isInternal === false, `isInternal PHẢI về false sau "[TM] Tiền Mặt" — got ${r.isInternal}`);
  assert(!r.internalAccId, `internalAccId PHẢI được xoá — got ${r.internalAccId}`);
  console.log('PASS 3: overrideRow() ("[TM] Tiền Mặt") cũng xoá sạch cờ isInternal cũ.');
}

// ----- Test 4 (không hồi quy): dòng BÌNH THƯỜNG (chưa từng là internal) xác nhận qua confirmRow vẫn
// ra đúng kết quả như cũ — không bị ảnh hưởng bởi việc thêm bước xoá isInternal. -----
{
  let rows = [{
    id: 'u4',
    tx: { debit: 0, credit: 5000000, date: '01/02/2026', desc: 'THANH TOAN HOA DON ABC', currency: 'VND' },
    confirmed: '',
  }];
  const setRowsH = updater => { rows = updater(rows); };
  const { confirmRow } = factory(setRowsH, () => {});

  confirmRow('u4', 'yes', '0311111222', 'Công ty ABC', 'DAURA', '');
  const r = rows.find(x => x.id === 'u4');
  assert(r.confirmed === 'yes' && r.confirmedMST === '0311111222' && r.confirmedName === 'Công ty ABC',
    `Dòng bình thường xác nhận qua confirmRow vẫn phải ra đúng MST/tên như cũ — got confirmed=${r.confirmed}, mst=${r.confirmedMST}, name=${r.confirmedName}`);
  assert(r.isInternal === false, 'Dòng bình thường (chưa từng internal) vẫn phải có isInternal=false sau xác nhận.');
  console.log('PASS 4: dòng bình thường (chưa từng internal) xác nhận qua confirmRow vẫn đúng như cũ — không hồi quy.');
}

console.log(process.exitCode ? 'CÓ TEST FAIL' : 'TẤT CẢ TEST PASS');
