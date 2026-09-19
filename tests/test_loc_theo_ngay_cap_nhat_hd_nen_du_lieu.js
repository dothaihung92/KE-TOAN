// Regression test (Node) cho static/doi_chieu_ngan_hang.html (Kế Toán AI) — 5 việc từ yêu cầu:
// "thêm nút chọn thời gian giao dịch từ ngày đến ngày ... vì tôi muốn sẽ luôn làm tiếp tục sao kê
// chứ không phải làm xong rồi xoá làm tiếp dữ liệu mới", cùng 4 điều chỉnh đi kèm:
// 1) nút "cập nhật dữ liệu hoá đơn đầu vào đầu ra" ngay tại màn Xác nhận kết quả
// 2) Xuất/Import UNT/UNC vào MISA chỉ theo ĐÚNG khoảng ngày đã chọn, không xuất hết
// 3) "Thêm sao kê": dữ liệu đã có thì giữ nguyên (không thêm trùng), dữ liệu mới mới được thêm
// 4) nén dữ liệu lưu trữ (LocalStorage/IndexedDB) để giảm dung lượng khi lưu giữ mãi mãi nhiều công ty
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'doi_chieu_ngan_hang.html'), 'utf8');

function assert(cond, msg) {
  if (!cond) throw new Error('THẤT BẠI: ' + msg);
}

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

function braceBlockOf(marker, fromIdx) {
  const start = html.indexOf(marker, fromIdx || 0);
  assert(start >= 0, 'Không tìm thấy: ' + marker);
  let i = html.indexOf('{', start);
  let depth = 0, end = -1;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  assert(end >= 0, 'Không tìm được dấu } khớp cho: ' + marker);
  return { src: html.slice(start, end), start, end };
}

// ===== Phần 1: ngayVNThanhISO()/ngayTrongKhoang() — hàm thuần lọc theo khoảng ngày =====
eval(extractFn('ngayVNThanhISO'));
eval(extractFn('ngayTrongKhoang'));

assert(ngayVNThanhISO('14/01/2026') === '2026-01-14', 'Phải quy đúng ngày VN (dd/mm/yyyy) về ISO (yyyy-mm-dd).');
assert(ngayVNThanhISO('05/01/2026 08:59:05') === '2026-01-05', 'Phải bỏ phần giờ nếu sao kê ghi kèm giờ.');
assert(ngayVNThanhISO('') === '' && ngayVNThanhISO(undefined) === '', 'Ngày rỗng/undefined phải trả rỗng, không lỗi.');
assert(ngayVNThanhISO('abc') === '', 'Chuỗi không phải ngày hợp lệ phải trả rỗng.');

assert(ngayTrongKhoang('14/01/2026', '', '') === true, 'Không chọn khoảng ngày (from/to rỗng) thì KHÔNG lọc bỏ dòng nào.');
assert(ngayTrongKhoang('14/01/2026', '2026-01-01', '2026-01-31') === true, 'Ngày nằm TRONG khoảng phải giữ lại.');
assert(ngayTrongKhoang('14/01/2026', '2026-02-01', '2026-02-28') === false, 'Ngày nằm NGOÀI khoảng phải lọc bỏ.');
assert(ngayTrongKhoang('01/01/2026', '2026-01-01', '') === true, 'Chỉ chọn "Từ ngày" (để trống "Đến ngày") vẫn phải hoạt động đúng (không giới hạn phía trên).');
assert(ngayTrongKhoang('31/12/2025', '2026-01-01', '') === false, 'Ngày trước "Từ ngày" phải bị loại dù "Đến ngày" để trống.');
assert(ngayTrongKhoang('', '2026-01-01', '2026-01-31') === true,
  'Ngày không đọc được (dữ liệu lỗi hiếm gặp) KHÔNG được lọc bỏ oan — an toàn hơn ẩn mất giao dịch khi có bộ lọc ngày.');
console.log('PASS 1: ngayVNThanhISO()/ngayTrongKhoang() lọc đúng khoảng ngày, không lọc oan khi để trống hoặc không đọc được ngày.');

// ===== Phần 2 (QUAN TRỌNG — đúng yêu cầu): bộ lọc hiển thị (filtered) phải cộng dồn thêm điều kiện
// khoảng ngày, và phải hiện CẢ giao dịch đã xử lý lẫn chưa xử lý trong khoảng đó (không lọc theo
// trạng thái xác nhận — chỉ lọc theo ngày). =====
const filteredSrc = braceBlockOf('const filtered = rows.filter(r => {');
assert(/if \(!ngayTrongKhoang\(r\.tx\.date, dateFrom, dateTo\)\) return false;/.test(filteredSrc.src),
  'filtered (danh sách hiện trên màn hình) phải cộng thêm điều kiện lọc theo khoảng ngày (dateFrom/dateTo).');
assert(!/dateFrom.*confirmed|confirmed.*dateFrom/.test(filteredSrc.src),
  'Điều kiện lọc ngày không được gắn kèm điều kiện trạng thái xác nhận — phải hiện CẢ giao dịch đã xử ' +
  'lý lẫn chưa xử lý trong khoảng ngày đó, đúng yêu cầu.');
console.log('PASS 2: bộ lọc hiển thị cộng dồn đúng khoảng ngày, hiện cả giao dịch đã xử lý lẫn chưa xử lý.');

// ===== Phần 3 (QUAN TRỌNG — đúng yêu cầu #2): Xuất/Import UNT/UNC phải dùng ĐÚNG phạm vi theo
// khoảng ngày đang chọn (rowsForExport), KHÔNG xuất hết toàn bộ rows khi có chọn khoảng ngày; Xuất
// Excel thì KHÔNG bị đổi (không nằm trong yêu cầu, vẫn xuất như cũ để không gây bất ngờ). =====
const rowsForExportSrc = braceBlockOf('const rowsForExport = (dateFrom || dateTo)');
assert(/rows\.filter\(r => ngayTrongKhoang\(r\.tx\.date, dateFrom, dateTo\)\)/.test(html.slice(rowsForExportSrc.start, rowsForExportSrc.start + 300)),
  'rowsForExport phải lọc rows theo đúng khoảng ngày khi có chọn (dateFrom || dateTo).');
assert(/exportUNT\(rowsForExport,/.test(html), 'Nút "Xuất UNT" phải dùng rowsForExport (đã lọc theo ngày), không dùng thẳng rows.');
assert(/exportUNC\(rowsForExport,/.test(html), 'Nút "Xuất UNC" phải dùng rowsForExport.');
assert(/previewThuChiVaoMisa\(rowsForExport, "unt"/.test(html), '"Import UNT vào MISA" phải dùng rowsForExport.');
assert(/previewThuChiVaoMisa\(rowsForExport, "unc"/.test(html), '"Import UNC vào MISA" phải dùng rowsForExport.');
assert(/exportExcel\(rows,co&&co\.name/.test(html),
  '"Xuất Excel" KHÔNG nằm trong yêu cầu thu hẹp theo ngày — vẫn phải xuất đủ rows như trước, không đổi hành vi ngoài ý muốn.');
console.log('PASS 3: Xuất/Import UNT/UNC dùng đúng phạm vi theo khoảng ngày đã chọn; Xuất Excel không bị ảnh hưởng.');

// ===== Phần 4 (đúng yêu cầu #3): "Thêm sao kê" (addMoreSaoke) phải GIỮ NGUYÊN dữ liệu đã có (không
// thêm trùng) và chỉ thêm dữ liệu MỚI — đồng thời phải BÁO RÕ cho người dùng biết đã giữ nguyên bao
// nhiêu / thêm mới bao nhiêu, để yên tâm dán chồng lấn nhiều đợt không bị nhân đôi giao dịch. =====
const addMoreSaokeSrc = braceBlockOf('const addMoreSaoke = async () => {');
assert(/const existKeys = new Set\(rows\.map\(keyOf\)\);/.test(addMoreSaokeSrc.src) &&
       /const uniqueNew = newResults\.filter\(nr => !existKeys\.has\(keyOf\(nr\)\)\);/.test(addMoreSaokeSrc.src),
  'Phải khớp theo nội dung giao dịch (ngày+diễn giải+số tiền) để biết dòng nào ĐÃ CÓ SẴN — giữ nguyên ' +
  'dòng cũ (không đụng trạng thái đã xác nhận), chỉ dòng chưa có mới được thêm mới.');
assert(/const soDaCoSan = newResults\.length - uniqueNew\.length;/.test(addMoreSaokeSrc.src),
  'Phải đếm được số giao dịch đã có sẵn (bị bỏ qua vì đã trùng) để báo rõ cho người dùng.');
assert(/soDaCoSan > 0 \? " \(" \+ soDaCoSan \+ " giao dịch đã có sẵn/.test(addMoreSaokeSrc.src),
  'Toast báo kết quả phải nói rõ có bao nhiêu giao dịch đã có sẵn (giữ nguyên) — không chỉ báo số mới ' +
  'thêm, để người dùng an tâm dán chồng lấn dữ liệu không bị nhân đôi.');
console.log('PASS 4: "Thêm sao kê" giữ nguyên dữ liệu đã có (không thêm trùng), chỉ thêm dữ liệu mới, và báo rõ cả 2 số cho người dùng.');

// ===== Phần 5 (QUAN TRỌNG — đúng yêu cầu #1): nút "Cập nhật hoá đơn" phải lấy lại hoá đơn mới nhất
// từ /api/dcnh/hoa-don rồi đẩy invDV/invDR mới lên để tự đối chiếu lại với sao kê. =====
const capNhatSrc = braceBlockOf('const capNhatHoaDon = async () => {');
assert(/fetch\("\/api\/dcnh\/hoa-don\?"/.test(capNhatSrc.src),
  'capNhatHoaDon() phải gọi đúng API cầu nối /api/dcnh/hoa-don (đã có sẵn, lấy hoá đơn đã tra cứu từ phần mềm chính).');
assert(/saveCoInvoices\(co\.id, dv, dr\)/.test(capNhatSrc.src),
  'Phải lưu lại hoá đơn mới vào bộ nhớ dùng chung của công ty (saveCoInvoices).');
assert(/onUpdateInvoices\(dv, dr\)/.test(capNhatSrc.src),
  'Phải gọi onUpdateInvoices để đẩy invDV/invDR mới lên component cha — nếu không, dữ liệu hoá đơn mới ' +
  'chỉ nằm trong bộ nhớ mà KHÔNG kích hoạt lại việc đối chiếu (rematchPending) với sao kê đang xem.');
console.log('PASS 5: nút "Cập nhật hoá đơn" lấy hoá đơn mới nhất và đẩy lên để tự đối chiếu lại với sao kê.');

// ===== Phần 5b (không hồi quy — nối dây đủ 2 đầu): App phải truyền onUpdateInvoices cho ConfirmScreen,
// và hàm đó phải thật sự cập nhật processData (nguồn của prop invDV/invDR truyền vào ConfirmScreen). =====
assert(/onUpdateInvoices: \(dv, dr\) => setProcessData\(prev => \(\{\.\.\.\(prev\|\|\{\}\), invDV: dv, invDR: dr\}\)\)/.test(html),
  'App phải truyền onUpdateInvoices cho ConfirmScreen, và hàm này phải cập nhật processData.invDV/invDR ' +
  '— đúng nguồn dữ liệu mà prop invDV/invDR của ConfirmScreen đang lấy.');
const confirmScreenSig = html.slice(html.indexOf('function ConfirmScreen({'), html.indexOf('function ConfirmScreen({') + 400);
assert(/\bonUpdateInvoices\b/.test(confirmScreenSig), 'ConfirmScreen phải nhận thêm prop onUpdateInvoices.');
console.log('PASS 5b: đã nối dây đủ App -> ConfirmScreen cho onUpdateInvoices, cập nhật đúng nguồn processData.');

// ===== Phần 6 (QUAN TRỌNG — đúng yêu cầu #4): dữ liệu lưu trữ (LS) phải được NÉN lại trước khi lưu,
// và VẪN đọc được dữ liệu CŨ đã lưu từ trước khi có nén (không mất dữ liệu người dùng khi lên bản mới)
// — test bằng cách giả lập window.LZString (nén/giải nén thật của LZString không chạy được ngoài
// trình duyệt, nhưng LOGIC chọn nén/không nén + phân biệt cũ/mới thì test được không cần thư viện thật). =====
const lsSrcEnd = html.indexOf('// ── Lưu dữ liệu ra FILE TRÊN MÁY TÍNH');
const lsSrc = html.slice(html.indexOf('const LS_LZ_PREFIX'), lsSrcEnd);
const lzCalls = [];
const mockWindow = {
  LZString: {
    compressToBase64: s => { lzCalls.push('c:' + s); return 'B64(' + s + ')'; },
    decompressFromBase64: s => { lzCalls.push('d:' + s); const m = /^B64\((.*)\)$/.exec(s); return m ? m[1] : null; }
  }
};
const mockIDBKV = { put: () => {}, del: () => {} };
// Trong trình duyệt, <script src="...lz-string..."> gắn LZString làm biến TOÀN CỤC (dùng được cả
// trần lẫn qua window.LZString) — code gốc gọi trần "LZString...." (chỉ DÒ qua "window.LZString" ở
// điều kiện bật/tắt nén). Truyền LZString làm tham số riêng để khớp đúng cách gọi đó.
const LS = new Function('window', 'IDBKV', 'LZString', lsSrc + '\nreturn LS;')(mockWindow, mockIDBKV, mockWindow.LZString);

const obj = { results: [{ id: 1, tx: { date: '01/01/2026', desc: 'test', debit: 1000 } }], accountId: null };
LS.set('session_test1', obj);
assert(LS.__mem['session_test1'].indexOf('~LZ~') === 0,
  'Giá trị lưu MỚI phải được nén (có tiền tố "~LZ~") — không nén thì không tiết kiệm được dung lượng như yêu cầu.');
const doc = LS.get('session_test1');
assert(doc && doc.results && doc.results[0].tx.desc === 'test' && doc.accountId === null,
  'Đọc lại dữ liệu vừa nén phải ra ĐÚNG dữ liệu gốc (không méo/mất dữ liệu qua vòng nén/giải nén).');
assert(lzCalls.some(c => c.startsWith('c:')) && lzCalls.some(c => c.startsWith('d:')),
  'Phải thật sự có gọi nén lúc lưu (compressToBase64) và giải nén lúc đọc (decompressFromBase64).');

// Dữ liệu CŨ (lưu từ bản TRƯỚC KHI có nén) là JSON thuần, không có tiền tố "~LZ~" — vẫn phải đọc
// được, không được coi là hỏng/mất chỉ vì thiếu tiền tố.
LS.__mem['session_cu'] = JSON.stringify({ results: [{ id: 2 }], accountId: 'acc1' });
const docCu = LS.get('session_cu');
assert(docCu && docCu.accountId === 'acc1' && docCu.results[0].id === 2,
  'Dữ liệu CŨ (JSON thuần, lưu từ trước khi có nén, không có tiền tố "~LZ~") vẫn phải đọc được đúng ' +
  '— đây là ĐÚNG YÊU CẦU không được mất dữ liệu người dùng đã lưu từ trước khi nâng cấp lên bản có nén.');
console.log('PASS 6: dữ liệu lưu mới được nén lại, đọc ra đúng dữ liệu gốc, và vẫn đọc được dữ liệu cũ chưa nén từ trước.');

console.log('\nALL DONE');
