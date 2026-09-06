// Regression test (Node) cho lỗi thật vừa báo (kèm 2 ảnh chụp màn hình Kế
// Toán AI, màn "Xác nhận kết quả"): sau khi bấm chọn 1 gợi ý "Khớp tên"
// (đổ thông tin MST/Tên/Hạch toán vào khung "Đã chọn N dòng" phía trên
// dùng cho thao tác hàng loạt) rồi bấm Enter (= xác nhận "Đúng" cho ĐÚNG 1
// dòng đang focus, KHÔNG phải xác nhận hàng loạt vì không có dòng nào
// được tick chọn — "Đã chọn 0 dòng"), khung thông tin phía trên (MST/Tên/
// TK) KHÔNG được xoá — vẫn giữ nguyên dữ liệu CŨ của dòng vừa xử lý xong,
// dễ gây hiểu lầm/áp nhầm cho thao tác hàng loạt sau đó.
//
// Nguyên nhân: hàm clearBulkPreview() đã được viết SẴN đúng cho tình
// huống này (xem chú thích gốc tại chỗ định nghĩa: "tự xoá đi khi không
// có dòng nào đang thật sự được chọn hàng loạt") nhưng CHƯA được gọi ở
// nhánh phím Enter/N xác nhận ĐƠN 1 dòng (chỉ được gọi ở saveSingle/
// saveBatch/nút Huỷ sửa của từng dòng) — bấm Enter đi qua đường
// confirmRow() trực tiếp, bỏ sót không gọi clearBulkPreview().
//
// Test trích ĐÚNG hàm xử lý phím (handler) từ static/doi_chieu_ngan_hang.html
// (không viết lại logic), stub tối thiểu các biến/hàm khác trong closure
// mà nhánh "Enter" (bulkSelected rỗng) cần tới, xác nhận: confirmRow VẪN
// được gọi đúng (không phá vỡ hành vi xác nhận đơn dòng cũ) VÀ
// clearBulkPreview() PHẢI được gọi ngay sau đó.
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'doi_chieu_ngan_hang.html'), 'utf8');

function extractHandlerBody() {
  const marker = 'const handler = e => {';
  const start = html.indexOf(marker);
  if (start < 0) throw new Error('Không tìm thấy "const handler = e => {"');
  const braceStart = html.indexOf('{', start);
  let depth = 0, end = -1;
  for (let i = braceStart; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  if (end < 0) throw new Error('Không tìm được dấu } khớp cho handler');
  return html.slice(braceStart, end);   // gồm cả { ... }
}

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

function runHandler(evt, { bulkSelectedSize, hasFocusedRow }) {
  const calls = [];
  // ----- stub tối thiểu mọi biến/hàm mà handler() tham chiếu -----
  const filtered = hasFocusedRow ? [{ id: 'row-1' }] : [];
  let showCount = 20;
  const SHOW_STEP = 20;
  const setShowCount = () => {};
  const showToast = () => {};
  const searchInputRef = { current: null };
  const handleSaveAndLearn = () => {};
  const pickerFor = null;
  const closePicker = () => {};
  const bulkForm = { mst: '', ten_cty: '', hach: '', kw: '' };
  const bulkSelected = { size: bulkSelectedSize };
  const clearBulkSelection = () => {};
  const search = '';
  const setSearch = () => {};
  const assignSelected = () => {};
  const openPicker = () => {};
  const focusIdx = 0;
  const overrideRow = () => {};
  const toggleBulkSelectAll = () => {};
  const undo = () => {};
  const redo = () => {};
  const bulkConfirmSelected = () => { calls.push('bulkConfirmSelected'); };
  const confirmRow = (...args) => { calls.push('confirmRow:' + args[1]); };
  const clearBulkPreview = () => { calls.push('clearBulkPreview'); };
  const setFocusIdx = () => {};
  const keyboardNavRef = { current: false };
  const window_ = { dispatchEvent: () => {} };
  const CustomEvent_ = function () {};

  const body = extractHandlerBody();
  // đổi tên window/CustomEvent trong thân hàm để không đụng globalThis thật (Node có window nếu chạy
  // trong môi trường khác, cẩn thận không lẫn) — thay bằng biến cục bộ đã stub ở trên.
  const fn = new Function(
    'e', 'filtered', 'showCount', 'SHOW_STEP', 'setShowCount', 'showToast', 'searchInputRef',
    'handleSaveAndLearn', 'pickerFor', 'closePicker', 'bulkForm', 'bulkSelected', 'clearBulkSelection',
    'search', 'setSearch', 'assignSelected', 'openPicker', 'focusIdx', 'overrideRow',
    'toggleBulkSelectAll', 'undo', 'redo', 'bulkConfirmSelected', 'confirmRow', 'clearBulkPreview',
    'setFocusIdx', 'keyboardNavRef', 'window', 'CustomEvent',
    body
  );
  fn(evt, filtered, showCount, SHOW_STEP, setShowCount, showToast, searchInputRef,
     handleSaveAndLearn, pickerFor, closePicker, bulkForm, bulkSelected, clearBulkSelection,
     search, setSearch, assignSelected, openPicker, focusIdx, overrideRow,
     toggleBulkSelectAll, undo, redo, bulkConfirmSelected, confirmRow, clearBulkPreview,
     setFocusIdx, keyboardNavRef, window_, CustomEvent_);
  return calls;
}

// ----- Test 1 (đúng ca lỗi thật): "Đã chọn 0 dòng" (bulkSelected rỗng) +
// có dòng đang focus + bấm Enter -> PHẢI xác nhận "yes" cho đúng dòng đó
// VÀ PHẢI xoá khung thông tin phía trên (clearBulkPreview). -----
{
  const evt = { key: 'Enter', preventDefault() {}, target: { tagName: 'DIV' } };
  const calls = runHandler(evt, { bulkSelectedSize: 0, hasFocusedRow: true });
  assert(calls.includes('confirmRow:yes'), 'Enter với 0 dòng tick chọn phải xác nhận "yes" cho dòng đang focus — được ' + JSON.stringify(calls));
  assert(calls.includes('clearBulkPreview'), 'Enter PHẢI gọi clearBulkPreview() ngay sau khi xác nhận đơn dòng — khung "Đã chọn N dòng" phía trên phải được xoá, không giữ nguyên dữ liệu cũ — được ' + JSON.stringify(calls));
  console.log('PASS 1: bấm Enter xác nhận đơn dòng (0 dòng tick chọn) — clearBulkPreview() được gọi đúng, khung thông tin phía trên được xoá.');
}

// ----- Test 2: phím "N" (Không khớp) cho đơn dòng cũng PHẢI xoá khung —
// cùng lỗi/cùng nguyên tắc như Enter. -----
{
  const evt = { key: 'n', preventDefault() {}, target: { tagName: 'DIV' } };
  const calls = runHandler(evt, { bulkSelectedSize: 0, hasFocusedRow: true });
  assert(calls.includes('confirmRow:no'), 'phím N phải xác nhận "no" cho dòng đang focus — được ' + JSON.stringify(calls));
  assert(calls.includes('clearBulkPreview'), 'phím N PHẢI gọi clearBulkPreview() — được ' + JSON.stringify(calls));
  console.log('PASS 2: bấm phím N (Không khớp) đơn dòng — clearBulkPreview() được gọi đúng.');
}

// ----- Test 3: CÓ dòng đang tick chọn hàng loạt (bulkSelected.size >= 1)
// -> Enter phải đi theo nhánh bulkConfirmSelected() (KHÔNG phải confirmRow
// đơn dòng) — hành vi hàng loạt vẫn giữ nguyên như cũ, không bị đổi. -----
{
  const evt = { key: 'Enter', preventDefault() {}, target: { tagName: 'DIV' } };
  const calls = runHandler(evt, { bulkSelectedSize: 3, hasFocusedRow: true });
  assert(calls.includes('bulkConfirmSelected'), 'có dòng tick chọn hàng loạt thì Enter phải gọi bulkConfirmSelected() — được ' + JSON.stringify(calls));
  assert(!calls.some(c => c.startsWith('confirmRow')), 'KHÔNG được gọi confirmRow() đơn dòng khi đang có dòng tick chọn hàng loạt — được ' + JSON.stringify(calls));
  console.log('PASS 3: có dòng tick chọn hàng loạt — Enter vẫn đi đúng nhánh bulkConfirmSelected(), không đổi hành vi cũ.');
}

console.log('\nTẤT CẢ TEST PASS');
