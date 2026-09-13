// Regression test (Node) cho hàm THUẦN findInternalCandidatesFor() trong
// static/doi_chieu_ngan_hang.html (Kế Toán AI), theo báo cáo thật của người
// dùng kèm ảnh chụp màn hình: "kiểm tra lại phần gợi ý chuyển tiền nội bộ
// chưa đúng hãy chỉnh lại hiện gợi ý cho đúng" — GD TK VND "BAN 5500 USD
// CHO ACB TY GIA 26110" (+143.605.000đ) bị gợi ý khớp SAI với 2 GD hoàn
// toàn khác số tiền bên TK USD ("BAN 3000 USD..." / "BAN 12000 USD..."),
// trong khi GD ĐÚNG cùng số tiền ($5.500) lại không được gợi ý.
//
// Nguyên nhân: khi so khớp chéo tiền tệ (VD TK VND <-> TK USD, không thể so
// khớp đúng số tiền vì 1 bên VND 1 bên USD), code CŨ chỉ dựa vào % số TỪ
// trùng trong diễn giải (>=40%) — nhưng sao kê ghi các GD bán ngoại tệ theo
// 1 khuôn mẫu câu giống hệt nhau ("BÁN <số> USD CHO ACB TỶ GIÁ <số>"), nên
// 2 GD khác hẳn số tiền vẫn trùng phần lớn TỪ (chỉ khác đúng 2 con số) và
// vẫn vượt ngưỡng 40%, khiến gợi ý sai.
//
// Fix: thêm bước rút số tiền cụ thể nhúng trong diễn giải của chính GD đang
// xét (myDescAmts, qua extractDescAmounts) — nếu rút được số, số đó BẮT
// BUỘC phải khớp đúng (sai số <=0.5%) với số tiền THẬT của vế bên kia
// (oAmt) thì mới được coi là ứng viên hợp lệ.
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

const stopStart = html.indexOf('const STOP = new Set(');
if (stopStart < 0) throw new Error('Không tìm thấy STOP');
const stopEnd = html.indexOf(');', stopStart) + 2;
const stopSrc = html.slice(stopStart, stopEnd);

const normVNSrc = extractBraceBlock('function normVN(s) {');
const parseVNDateISrc = extractBraceBlock('const parseVNDateI = d => {');
const extractDescAmountsSrc = extractBraceBlock('const extractDescAmounts = desc => {');
const findInternalCandidatesForSrc = extractBraceBlock('const findInternalCandidatesFor = (txRow, accId, otherRowsPreloaded, debugOut) => {');

// Chạy trong 1 hàm bọc riêng (new Function) nhận co/activeTabAcc làm tham số — findInternalCandidatesFor
// đọc 2 biến này qua closure (không phải tham số của chính nó) trong file gốc, nên phải "giả lập" đúng
// scope đó thay vì eval() trực tiếp (const/let khai báo qua eval không lọt ra ngoài phạm vi eval).
const factory = new Function('co', 'activeTabAcc', `
${stopSrc}
${normVNSrc}
${parseVNDateISrc}
${extractDescAmountsSrc}
${findInternalCandidatesForSrc}
return findInternalCandidatesFor;
`);

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

function makeRow(id, debit, credit, date, desc, confirmed) {
  return { id, tx: { debit, credit, date, desc }, confirmed: confirmed || "" };
}

// ----- Test 1 (đúng ca thật đã báo, ảnh 1 & 3): GD TK VND "BAN 5500 USD
// CHO ACB TY GIA 26110" (+143.605.000đ, tiền vào) CHỈ được gợi ý đúng GD
// $5.500 bên TK USD — KHÔNG được gợi ý nhầm $3.000 hay $12.000. -----
{
  const co = { accounts: [{ id: 'usdAcc', currency: 'USD' }] };
  const activeTabAcc = { currency: 'VND' };
  const findInternalCandidatesFor = factory(co, activeTabAcc);

  const myRow = makeRow('vnd1', 0, 143605000, '14/01/2026', 'BAN 5500 USD CHO ACB TY GIA 26110');
  const uSai3000 = makeRow('u1', 3000, 0, '15/01/2026', 'BAN 3000 USD CHO ACB TY GIA 26100');
  const uSai12000 = makeRow('u2', 12000, 0, '16/01/2026', 'BAN 12000 USD CHO ACB TY GIA 26090');
  const uDung5500 = makeRow('u3', 5500, 0, '14/01/2026', 'BAN 5500 USD CHO ACB TY GIA 26110');

  const scored = findInternalCandidatesFor(myRow, 'usdAcc', [uSai3000, uSai12000, uDung5500]);
  const ids = scored.map(s => s.o.id);

  assert(!ids.includes('u1'), `KHÔNG được gợi ý GD $3.000 (khác hẳn số tiền) — got candidates: ${ids}`);
  assert(!ids.includes('u2'), `KHÔNG được gợi ý GD $12.000 (khác hẳn số tiền) — got candidates: ${ids}`);
  assert(ids.includes('u3'), `PHẢI gợi ý đúng GD $5.500 (cùng số tiền nhúng trong diễn giải) — got candidates: ${ids}`);
  console.log('PASS 1: GD "BAN 5500 USD..." chỉ gợi ý đúng GD $5.500 bên TK USD, không còn gợi ý nhầm $3.000/$12.000.');
}

// ----- Test 2 (ảnh 2, dòng thứ 2): GD TK VND "BAN 5000 USD CHO ACB TY GIA
// 26100" (+130.500.000đ) cũng KHÔNG được gợi ý nhầm GD $3.000. -----
{
  const co = { accounts: [{ id: 'usdAcc', currency: 'USD' }] };
  const activeTabAcc = { currency: 'VND' };
  const findInternalCandidatesFor = factory(co, activeTabAcc);

  const myRow = makeRow('vnd2', 0, 130500000, '15/01/2026', 'BAN 5000 USD CHO ACB TY GIA 26100');
  const uSai3000 = makeRow('u1', 3000, 0, '15/01/2026', 'BAN 3000 USD CHO ACB TY GIA 26100');
  const uDung5000 = makeRow('u4', 5000, 0, '15/01/2026', 'BAN 5000 USD CHO ACB TY GIA 26100');

  const scored = findInternalCandidatesFor(myRow, 'usdAcc', [uSai3000, uDung5000]);
  const ids = scored.map(s => s.o.id);

  assert(!ids.includes('u1'), `KHÔNG được gợi ý GD $3.000 cho GD $5.000 — got candidates: ${ids}`);
  assert(ids.includes('u4'), `PHẢI gợi ý đúng GD $5.000 — got candidates: ${ids}`);
  console.log('PASS 2: GD "BAN 5000 USD..." không còn bị gợi ý nhầm GD $3.000 cùng khuôn mẫu câu.');
}

// ----- Test 3 (không hồi quy): diễn giải KHÔNG có số tiền nhúng sẵn (VD
// "CHUYEN KHOAN NOI BO QUA ACB") thì vẫn giữ nguyên hành vi CŨ — so khớp
// theo % từ trùng (vì không có số để đối chiếu chặt hơn), không bị chặn. -----
{
  const co = { accounts: [{ id: 'usdAcc', currency: 'USD' }] };
  const activeTabAcc = { currency: 'VND' };
  const findInternalCandidatesFor = factory(co, activeTabAcc);

  const myRow = makeRow('vnd3', 0, 26000000, '20/01/2026', 'CHUYEN KHOAN NOI BO QUA ACB');
  const uMatch = makeRow('u5', 1000, 0, '20/01/2026', 'CHUYEN KHOAN NOI BO QUA ACB');

  const scored = findInternalCandidatesFor(myRow, 'usdAcc', [uMatch]);
  const ids = scored.map(s => s.o.id);
  assert(ids.includes('u5'), `Diễn giải không có số tiền cụ thể vẫn phải gợi ý theo % từ trùng như cũ — got candidates: ${ids}`);
  console.log('PASS 3: diễn giải không nhúng số tiền cụ thể vẫn gợi ý bình thường theo % từ trùng (không hồi quy).');
}

// ----- Test 4 (chẩn đoán mới thêm): khi truyền debugOut, hàm PHẢI ghi lại đúng lý do loại từng GD
// bị loại — dùng để hiện chi tiết trong modal khi người dùng báo "vẫn không thấy gợi ý" nhưng không
// rõ vì sao (VD báo cáo thật: TK kia CÓ dữ liệu nhưng vẫn hiện "không tìm thấy GD nào khớp"). Đảm bảo
// debugOut không làm thay đổi kết quả thật (candidates) khi có/không truyền vào. -----
{
  const co = { accounts: [{ id: 'usdAcc', currency: 'USD' }] };
  const activeTabAcc = { currency: 'VND' };
  const findInternalCandidatesFor = factory(co, activeTabAcc);

  const myRow = makeRow('vnd4', 0, 143605000, '14/01/2026', 'BAN 5500 USD CHO ACB TY GIA 26110');
  const uSai3000 = makeRow('u1', 3000, 0, '14/01/2026', 'BAN 3000 USD CHO ACB TY GIA 26100');
  const uDaXuLy = makeRow('u6', 5500, 0, '14/01/2026', 'BAN 5500 USD CHO ACB TY GIA 26110', 'yes');
  uDaXuLy.isInternal = true;

  const debugOut = {};
  const scored = findInternalCandidatesFor(myRow, 'usdAcc', [uSai3000, uDaXuLy], debugOut);
  assert(scored.length === 0, `Ca này cố tình không có ứng viên hợp lệ nào — got: ${scored.map(s=>s.o.id)}`);
  assert(debugOut.saiSoTienNhung === 1, `debugOut phải ghi nhận đúng 1 GD bị loại do diễn giải giống nhưng sai số tiền (u1) — got saiSoTienNhung=${debugOut.saiSoTienNhung}`);
  assert(debugOut.daXuLy === 1, `debugOut phải ghi nhận đúng 1 GD bị loại do đã xử lý (u6, isInternal=true) — got daXuLy=${debugOut.daXuLy}`);

  // Không truyền debugOut vẫn phải ra kết quả giống hệt (không bị ảnh hưởng bởi việc thêm tham số mới)
  const scoredNoDebug = findInternalCandidatesFor(myRow, 'usdAcc', [uSai3000, uDaXuLy]);
  assert(scoredNoDebug.length === scored.length, 'Không truyền debugOut vẫn phải ra cùng kết quả như có truyền');
  console.log('PASS 4: debugOut ghi đúng lý do loại từng GD (phục vụ chẩn đoán), không ảnh hưởng kết quả thật.');
}

console.log(process.exitCode ? 'CÓ TEST FAIL' : 'TẤT CẢ TEST PASS');
