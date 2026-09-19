// Regression test (Node) cho static/doi_chieu_ngan_hang.html (Kế Toán AI) —
// người dùng yêu cầu: "thêm cột thông tin giao dịch này là của tài khoản NH
// nào và khi nhấn vào giao dịch đó phần mềm sẽ tự động quay lại đúng giao
// dịch thanh toán đã chọn bên ngoài. chức năng này áp dụng cho tờ khai XK
// và NK luôn".
//
// 3 phần: (1) mỗi lần gắn tờ khai vào 1 giao dịch NH (attachTokhai/
// attachTokhaiSplit), payment PHẢI lưu kèm accountId của tab đang mở lúc
// gắn — trước đây chỉ lưu {rowId, bankDate, bankAmt, bankRate, bankVND},
// rowId chỉ có ý nghĩa TRONG ĐÚNG phiên sao kê của 1 tài khoản nên không đủ
// để biết/nhảy về đúng tài khoản nếu người dùng đang xem tab KHÁC; (2) hàm
// thuần bankAccountLabel() suy tên tài khoản hiện trên cột mới, phân biệt
// đúng "chưa từng lưu accountId" (dữ liệu cũ, accId===undefined) với "tài
// khoản mặc định duy nhất" (accId===null, hợp lệ); (3) cột mới + nút nhảy
// về đúng giao dịch phải có mặt ở CẢ 2 bảng (Tờ khai XK và Tờ khai NK dùng
// chung 1 component ToKhaiModal, kind="XK"/"NK").
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'doi_chieu_ngan_hang.html'), 'utf8');

function extractFn(name) {
  const marker = 'function ' + name + '(';
  const start = html.indexOf(marker);
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

function assert(cond, msg) {
  if (!cond) throw new Error('THẤT BẠI: ' + msg);
}

// ===== Phần 1: bankAccountLabel() — hàm thuần, test bằng cách gọi thật =====
eval(extractFn('xayMapRowIdSangAccountId'));
eval(extractFn('timAccountIdTheoRowIdCu'));
eval(extractFn('bankAccountLabel'));

const accounts = [
  { id: 'acc-vnd', label: '1121 VND', currency: 'VND', bankName: 'ACB' },
  { id: 'acc-usd', label: 'USD 362698698', currency: 'USD' },
];

assert(bankAccountLabel(accounts, 'acc-vnd') === 'ACB',
  'Tài khoản có "Tên ngân hàng" (bankName, VD "ACB") thì PHẢI ưu tiên hiện đúng tên đó — người dùng yêu ' +
  'cầu rõ "hãy lấy theo Tên ngân hàng đã nhập từ tk NH", không phải nhãn tab kỹ thuật.');
assert(bankAccountLabel(accounts, 'acc-usd') === 'USD 362698698',
  'Tài khoản CHƯA nhập Tên ngân hàng thì tạm hiện nhãn tab (acc.label) để không bỏ trống.');
assert(bankAccountLabel(accounts, undefined) === '(cũ)',
  'accId===undefined mà không truyền/không dò được qua oldAccountMap vẫn phải hiện "(cũ)", không được ' +
  'ném lỗi hay đoán bừa.');
assert(bankAccountLabel(accounts, null) === '?',
  'accId===null nhưng KHÔNG có tài khoản nào trong danh sách mang id null thì phải hiện "?" (không tìm ' +
  'thấy), khác hẳn trường hợp thật "chỉ có 1 TK mặc định, accounts=[{id:null,...}]".');
const mot_tk_mac_dinh = [{ id: null, label: 'TK chính', currency: 'VND' }];
assert(bankAccountLabel(mot_tk_mac_dinh, null) === 'TK chính',
  'Công ty chỉ có 1 tài khoản mặc định (id=null hợp lệ) thì accId===null phải ra đúng nhãn "TK chính".');
assert(bankAccountLabel(accounts, 'khong-ton-tai') === '?',
  'accId không khớp tài khoản nào trong danh sách (VD tài khoản đã bị xoá) phải hiện "?", không được lỗi.');
assert(bankAccountLabel(null, 'acc-vnd') === '?',
  'accounts=null/rỗng (chưa truyền prop) không được làm chết hàm — phải trả "?" an toàn.');
console.log('PASS 1: bankAccountLabel() phân biệt đúng "(cũ)" / accId hợp lệ (ưu tiên bankName) / không tìm thấy / rỗng.');

// ===== Phần 1b (QUAN TRỌNG — ĐÚNG CA THẬT người dùng báo: cột "Tài khoản NH"
// hiện "(cũ)" cho MỌI dòng dữ liệu có sẵn): payment CŨ (accountId===undefined)
// vẫn phải dò lại được tài khoản thật qua oldAccountMap (rowId -> accountId,
// dựng từ sao kê đã lưu của TỪNG tài khoản — xem xayMapRowIdSangAccountId). =====
const oldMap = xayMapRowIdSangAccountId([
  { accountId: 'acc-vnd', results: [{ id: 'row-1' }, { id: 'row-2' }] },
  { accountId: undefined, results: [{ id: 'row-3' }] }, // session cũ chưa từng lưu accountId -> mặc định null
]);
assert(oldMap['row-1'] === 'acc-vnd' && oldMap['row-2'] === 'acc-vnd',
  'xayMapRowIdSangAccountId() phải gộp mọi rowId trong .results của 1 session về đúng accountId của session đó.');
assert(oldMap['row-3'] === null,
  'Session cũ (accountId===undefined, lưu từ trước khi hỗ trợ nhiều tài khoản) phải quy về null (tài ' +
  'khoản mặc định) trong map — undefined trong map nghĩa là "chưa dò được", khác hẳn null "đã dò ra, là TK mặc định".');
assert(!('row-khong-co' in oldMap), 'rowId không có trong bất kỳ session nào thì không được có mặt trong map.');

assert(timAccountIdTheoRowIdCu([{ accountId: 'acc-vnd', results: [{ id: 'row-1' }] }], 'row-1') === 'acc-vnd',
  'timAccountIdTheoRowIdCu() phải tìm đúng session chứa rowId rồi trả về accountId của session đó.');
assert(timAccountIdTheoRowIdCu([{ accountId: 'acc-vnd', results: [{ id: 'row-1' }] }], 'row-khac') === undefined,
  'rowId không khớp session nào thì phải trả undefined (không dò ra), không phải null hay lỗi.');
assert(timAccountIdTheoRowIdCu([], 'row-1') === undefined && timAccountIdTheoRowIdCu(null, 'row-1') === undefined,
  'Không có session nào (mảng rỗng/null) không được làm chết hàm.');

assert(bankAccountLabel(accounts, undefined, 'row-1', oldMap) === 'ACB',
  'payment CŨ (accountId===undefined) nhưng dò được qua oldAccountMap (đúng ca thật người dùng báo: mọi ' +
  'dòng dữ liệu có sẵn đều hiện "(cũ)") PHẢI hiện đúng Tên ngân hàng đã dò lại, không được hiện "(cũ)" nữa.');
assert(bankAccountLabel(accounts, undefined, 'row-khong-co-trong-map', oldMap) === '(cũ)',
  'rowId không có trong oldAccountMap (thật sự không dò ra được, VD sao kê gốc đã bị xoá) thì vẫn hiện ' +
  '"(cũ)" như cũ, không được đoán bừa.');
console.log('PASS 1b: payment cũ dò lại được đúng tên ngân hàng qua oldAccountMap thay vì luôn hiện "(cũ)".');

// ===== Phần 2 (QUAN TRỌNG — đúng ca thật, kiểm tra qua mã nguồn): payment
// PHẢI lưu accountId = tab đang mở (activeTabAccId) lúc gắn tờ khai, ở CẢ
// đường gắn thường (attachTokhai) lẫn gối đầu (attachTokhaiSplit). =====
function braceBlockOf(marker) {
  const start = html.indexOf(marker);
  assert(start >= 0, 'Không tìm thấy: ' + marker);
  let i = html.indexOf('{', start);
  let depth = 0, end = -1;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  assert(end >= 0, 'Không tìm được dấu } khớp cho: ' + marker);
  return html.slice(start, end);
}

const attachTokhaiSrc = braceBlockOf('const attachTokhai = (kind, rowId, tokhaiId) => {');
assert(/newPayments\s*=\s*\[\.\.\.existingPayments,\s*\{\s*rowId,\s*accountId:\s*activeTabAccId/.test(attachTokhaiSrc),
  'attachTokhai() phải lưu accountId: activeTabAccId ngay trong object payment mới tạo — thiếu trường ' +
  'này thì không biết/không nhảy về được đúng tài khoản của giao dịch đã gắn.');

const attachTokhaiSplitSrc = braceBlockOf('const attachTokhaiSplit = (kind, rowId, allocations) => {');
assert(/newPayments\s*=\s*\[\.\.\.existingPayments,\s*\{\s*rowId,\s*accountId:\s*activeTabAccId/.test(attachTokhaiSplitSrc),
  'attachTokhaiSplit() (thanh toán "gối đầu") cũng phải lưu accountId: activeTabAccId — nếu chỉ sửa ' +
  'attachTokhai() mà bỏ sót đường gối đầu thì các tờ khai gắn qua "⤵ Gối đầu" vẫn thiếu tài khoản.');
console.log('PASS 2: cả attachTokhai() và attachTokhaiSplit() đều lưu accountId của tab đang mở.');

// ===== Phần 3 (đúng ca thật): ToKhaiModal (dùng CHUNG cho cả tờ khai XK và
// NK — phân biệt bằng prop kind) phải nhận accounts + onJumpToPayment, có
// cột "Tài khoản NH" trong bảng, và nút trong cột đó gọi onJumpToPayment
// kèm đúng accountId/rowId của TỪNG lần thanh toán. =====
const modalSigIdx = html.indexOf('function ToKhaiModal({');
assert(modalSigIdx >= 0, 'Không tìm thấy function ToKhaiModal(...).');
// Tìm đúng dấu ")" đóng danh sách tham số huỷ cấu trúc (không phải "{" đầu
// tiên sau đó — "{" đó là CHÍNH thẻ mở object huỷ cấu trúc tham số, khớp
// với "}" đóng tham số chứ chưa phải thân hàm).
const modalParamCloseParen = html.indexOf(') {', modalSigIdx);
assert(modalParamCloseParen >= 0, 'Không tìm được ") {" kết thúc danh sách tham số của ToKhaiModal.');
const modalSig = html.slice(modalSigIdx, modalParamCloseParen);
assert(/\baccounts\b/.test(modalSig) && /\bonJumpToPayment\b/.test(modalSig),
  'ToKhaiModal phải nhận thêm 2 prop: accounts (để suy tên tài khoản) và onJumpToPayment (để nhảy về ' +
  'đúng giao dịch) — dùng chung cho cả kind="XK" và kind="NK".');

// Lấy THÂN HÀM (bắt đầu từ đúng "{" mở thân hàm, sau ") {" ở trên) — brace
// block bắt từ "function ToKhaiModal({" sẽ dừng SỚM ở "}" đóng tham số huỷ
// cấu trúc (vì "{" đầu tiên gặp được lại chính là "{" mở tham số đó).
let bi = modalParamCloseParen + 2, depth = 0, modalBodyEnd = -1;
for (; bi < html.length; bi++) {
  if (html[bi] === '{') depth++;
  else if (html[bi] === '}') { depth--; if (depth === 0) { modalBodyEnd = bi + 1; break; } }
}
assert(modalBodyEnd >= 0, 'Không tìm được dấu } khớp cho thân hàm ToKhaiModal.');
const modalBody = html.slice(modalSigIdx, modalBodyEnd);
assert(/"Tài khoản NH"/.test(modalBody),
  'Bảng Tờ khai (dùng chung cho XK/NK) phải có cột tiêu đề "Tài khoản NH".');
assert(/onJumpToPayment\s*&&\s*onJumpToPayment\(p\.accountId,\s*p\.rowId\)/.test(modalBody),
  'Nút trong cột "Tài khoản NH" phải gọi onJumpToPayment(p.accountId, p.rowId) — đúng accountId/rowId ' +
  'của TỪNG lần thanh toán (1 tờ khai có thể có nhiều lần thanh toán khác tài khoản/khác ngày).');
assert(/xayMapRowIdSangAccountId\(/.test(modalBody),
  'ToKhaiModal phải dò lại accountId cho payment CŨ qua xayMapRowIdSangAccountId (quét sao kê đã lưu) — ' +
  'nếu không, cột "Tài khoản NH" sẽ luôn hiện "(cũ)" cho mọi dòng dữ liệu có từ trước, đúng lỗi người dùng báo.');
assert(/accountLabel\(p\.accountId,\s*p\.rowId\)/.test(modalBody),
  'Chỗ hiện tên tài khoản phải gọi accountLabel(p.accountId, p.rowId) — truyền cả rowId để dò qua ' +
  'oldAccountMap khi accountId===undefined.');
console.log('PASS 3: ToKhaiModal (dùng chung XK/NK) có cột "Tài khoản NH" (dò lại được payment cũ) với nút nhảy về đúng giao dịch.');

// ===== Phần 4 (không hồi quy — cả 2 nơi gọi ToKhaiModal, cho XK VÀ NK, đều
// phải truyền accounts/onJumpToPayment — không được chỉ sửa 1 bên). =====
const callSites = [...html.matchAll(/React\.createElement\(ToKhaiModal,\s*\{([\s\S]*?)\n\s*\}\)/g)];
assert(callSites.length === 2, `Phải có đúng 2 chỗ gọi ToKhaiModal (kind="NK" và kind="XK"), tìm thấy ${callSites.length}.`);
callSites.forEach((m, idx) => {
  const block = m[1];
  const kindMatch = block.match(/kind:\s*"(NK|XK)"/);
  const kind = kindMatch ? kindMatch[1] : `(#${idx})`;
  assert(/accounts:\s*allAccounts/.test(block),
    `Chỗ gọi ToKhaiModal cho kind="${kind}" phải truyền accounts: allAccounts.`);
  assert(/onJumpToPayment:\s*jumpToPayment/.test(block),
    `Chỗ gọi ToKhaiModal cho kind="${kind}" phải truyền onJumpToPayment: jumpToPayment — thiếu ở 1 bên ` +
    `(XK hoặc NK) thì tính năng chỉ hoạt động cho đúng 1 loại tờ khai, khác yêu cầu "áp dụng cho tờ ` +
    `khai XK và NK luôn".`);
});
console.log('PASS 4: cả 2 chỗ gọi ToKhaiModal (kind="NK" và kind="XK") đều truyền accounts/onJumpToPayment.');

// ===== Phần 5 (không hồi quy — hành vi nhảy về đúng giao dịch): jumpToPayment
// phải đổi tab khi payment thuộc tài khoản khác tab đang mở, và phải bỏ mọi
// bộ lọc đang áp (nếu không, giao dịch cần tới có thể đang bị lọc ẩn). =====
const jumpFnSrc = braceBlockOf('const jumpToPayment = (accountId, rowId) => {');
assert(/setFilter\("all"\)/.test(jumpFnSrc) && /setSearch\(""\)/.test(jumpFnSrc),
  'jumpToPayment() phải bỏ bộ lọc/ô tìm kiếm đang áp trước khi tìm dòng cần nhảy tới — nếu không, dòng ' +
  'đó có thể đang bị lọc ẩn (VD đang lọc "Chưa xử lý" nhưng giao dịch đã xác nhận rồi) và sẽ báo nhầm ' +
  '"không tìm thấy" dù dữ liệu vẫn còn nguyên.');
assert(/targetAccountId\s*=\s*accountId/.test(jumpFnSrc) &&
       /targetAccountId\s*===\s*undefined/.test(jumpFnSrc) &&
       /resolveOldAccountId\(rowId\)/.test(jumpFnSrc),
  'jumpToPayment() phải gọi resolveOldAccountId(rowId) để dò lại accountId khi payment CŨ ' +
  '(accountId===undefined) — nếu không, payment cũ sẽ luôn tìm trong tab ĐANG MỞ thay vì đổi sang đúng ' +
  'tab thật, đúng lỗi người dùng báo (nhấn vào báo "Không tìm thấy giao dịch ngân hàng này").');
assert(/switchTab\(targetAccountId\)/.test(jumpFnSrc),
  'jumpToPayment() phải đổi tab theo targetAccountId (accountId gốc, hoặc đã dò lại qua ' +
  'resolveOldAccountId nếu là payment cũ) — đây là chỗ THỰC SỰ "quay lại đúng tài khoản" mà người dùng yêu cầu.');

// ===== Phần 5b (ĐÚNG CA THẬT: nhấn vào payment CŨ không nhảy đúng nơi): phải
// có sẵn resolveOldAccountId() dò accountId qua toàn bộ sao kê đã lưu của
// công ty (getSessionIndex + timAccountIdTheoRowIdCu), dùng khi payment
// không có accountId lưu sẵn. =====
const resolveOldSrc = braceBlockOf('const resolveOldAccountId = rowId => {');
assert(/getSessionIndex\(co\.id\)/.test(resolveOldSrc),
  'resolveOldAccountId() phải quét TOÀN BỘ session đã lưu của công ty (getSessionIndex(co.id)), không ' +
  'chỉ tab đang mở — payment cũ có thể thuộc BẤT KỲ tài khoản nào.');
assert(/timAccountIdTheoRowIdCu\(/.test(resolveOldSrc),
  'resolveOldAccountId() phải dùng timAccountIdTheoRowIdCu() để dò rowId trong các session đã đọc.');
console.log('PASS 5: jumpToPayment() dò lại accountId cho payment cũ (resolveOldAccountId) rồi mới đổi tab, và bỏ bộ lọc trước khi tìm dòng cần nhảy tới.');

console.log('\nALL DONE');
