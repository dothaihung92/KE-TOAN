// Regression test (Node, KHÔNG phải Python — lỗi ở static/index.html, phần
// JS phía trình duyệt): người dùng yêu cầu "khi chọn ô và nhấn shift và nút
// lên xuống qua lại sẽ tô xanh giống như trong excel" — trước fix, hàm
// nlPhimO() xử lý mũi tên KHÔNG kiểm tra e.shiftKey, luôn RESET vùng chọn về
// đúng 1 ô mới (r1=c1=r2=c2=ô mới) — Shift+mũi tên không có tác dụng mở
// rộng vùng chọn như Excel (mất luôn cả góc neo ban đầu).
//
// Test này trích hàm nlPhimO() từ static/index.html, mô phỏng DOM tối
// thiểu (document.querySelector trả về 1 "td" giả, chỉ cần .focus()/.blur()
// là no-op) và các hàm phụ thuộc khác (nlUndo/nlRedo/nlFillDown/...) dạng
// stub, gọi trực tiếp với sự kiện bàn phím giả lập ArrowRight có/không giữ
// Shift, xác nhận nlChon mở rộng đúng khi giữ Shift (giữ nguyên góc neo
// r1/c1, chỉ dời r2/c2) và reset về 1 ô khi KHÔNG giữ Shift.
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'index.html'), 'utf8');

function extractFn(src, name) {
  const marker = 'function ' + name + '(';
  const start = src.indexOf(marker);
  if (start < 0) throw new Error('Không tìm thấy hàm ' + name);
  let i = src.indexOf('{', start);
  let depth = 0, end = -1;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  if (end < 0) throw new Error('Không tìm được dấu } khớp cho hàm ' + name);
  return src.slice(start, end);
}

const srcPhimO = extractFn(html, 'nlPhimO');

// ----- mock DOM + globals mà nlPhimO() cần -----
var nlChon = null;
var nhapLieuLoaiHienTai = 'in';
var nlHeader = ['A', 'B', 'C', 'D'];
var nlRows = [[], [], []];
var highlightCalls = 0;
function nlCapNhatHighlight() { highlightCalls++; }
function nlUndo() {} function nlRedo() {} function nlFillDown() {} function nlFillRight() {}
function nlBatFilter() {} function quayLaiChonBangKe() {} function nlXoaHighlight() {}
function nlLocDong() { return nlRows.map((r, idx) => ({ row: r, idx })); }
function xkFillDown() {} function xkTuNlRows() {} function xkMoGan() {}

function fakeTd(r, c) {
  return { dataset: { r: String(r), c: String(c) }, textContent: '', blur() {}, focus() {} };
}
var document = {
  querySelector(sel) {
    // sel dạng: td[data-r="R"][data-c="C"]
    const m = sel.match(/data-r="(-?\d+)"\]\[data-c="(-?\d+)"/);
    if (!m) return null;
    return fakeTd(+m[1], +m[2]);
  }
};

eval(srcPhimO);

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}
function mkEvent(key, shiftKey) {
  return { key, shiftKey: !!shiftKey, ctrlKey: false, metaKey: false, altKey: false, preventDefault() {} };
}

// Bắt đầu: người dùng đã bấm chuột vào ô (2,2) -> nlChon neo tại đó (mô
// phỏng đúng hành vi nlMouseDown, không cần gọi lại hàm đó trong test này).
nlChon = { r1: 2, c1: 2, r2: 2, c2: 2 };

// Bấm Shift+ArrowRight từ ô (2,2) -> phải MỞ RỘNG vùng chọn sang (2,3), giữ
// nguyên góc neo (2,2) — KHÔNG được reset về đúng 1 ô (2,3).
nlPhimO(mkEvent('ArrowRight', true), fakeTd(2, 2));
assert(nlChon.r1 === 2 && nlChon.c1 === 2 && nlChon.r2 === 2 && nlChon.c2 === 3,
  'Shift+ArrowRight lần 1 phải mở rộng vùng chọn thành r1=2,c1=2,r2=2,c2=3 (giữ nguyên góc neo) — được ' + JSON.stringify(nlChon));

// Bấm TIẾP Shift+ArrowRight từ ô (2,3) (ô đang "hoạt động" sau lần mở rộng
// trước) -> vùng chọn phải mở rộng tiếp sang (2,4), góc neo (2,2) vẫn giữ
// nguyên — giống hệt cách Excel mở rộng dần theo từng lần giữ Shift.
nlPhimO(mkEvent('ArrowRight', true), fakeTd(2, 3));
assert(nlChon.r1 === 2 && nlChon.c1 === 2 && nlChon.r2 === 2 && nlChon.c2 === 4,
  'Shift+ArrowRight lần 2 (liên tiếp) phải mở rộng tiếp thành r2=2,c2=4, góc neo r1=2,c1=2 KHÔNG đổi — được ' + JSON.stringify(nlChon));

// Bấm ArrowRight KHÔNG giữ Shift -> phải RESET vùng chọn về đúng 1 ô mới
// (giống Excel: bỏ vùng chọn cũ, chọn lại đúng 1 ô khi không giữ Shift).
nlPhimO(mkEvent('ArrowRight', false), fakeTd(2, 4));
assert(nlChon.r1 === 2 && nlChon.c1 === 5 && nlChon.r2 === 2 && nlChon.c2 === 5,
  'ArrowRight (không giữ Shift) phải reset vùng chọn về đúng 1 ô mới (2,5) — được ' + JSON.stringify(nlChon));

console.log('PASS: Shift+mũi tên mở rộng vùng chọn giữ nguyên góc neo (giống Excel), mũi tên thường (không '
  + 'giữ Shift) vẫn reset về đúng 1 ô như trước — đúng yêu cầu người dùng.');
