// Regression test (Node) cho handleRun() trong static/doi_chieu_ngan_hang.html
// (Kế Toán AI) — người dùng báo (kèm ảnh chụp màn hình): bấm THẲNG vào thẻ
// "Đối Chiếu Ngân Hàng" ở màn Nhập Liệu (KHÔNG qua nút "▶ Tiếp tục"), vào lại
// đúng Bước 1 với sao kê của tài khoản đang mở đã tự điền sẵn (khôi phục từ
// phiên cũ, "Nhận diện được 1827 giao dịch"), rồi bấm "🚀 Chạy AI đối chiếu" —
// "dữ liệu còn nguyên nhưng hạch toán đã gắn giao dịch mất hết phải làm lại
// từ đầu".
//
// Nguyên nhân: lưới an toàn "không ghi đè TK đã có dữ liệu" (đã có sẵn trong
// handleRun, dùng LS.get("session_"+co.id+"_"+acc.id)) CHỈ áp dụng cho các TK
// KHÁC tài khoản đang mở (if (acc.id !== activeAccountId)) — TK ĐANG MỞ (đúng
// ca thật gặp phải) hoàn toàn KHÔNG được kiểm tra, ghi đè mất sạch phần đã
// xác nhận (hạch toán đã gắn giao dịch) mà không hỏi gì cả.
//
// Fix: thêm kiểm tra NGAY ĐẦU handleRun() cho riêng TK đang mở — nếu đã có
// session với ít nhất 1 giao dịch ĐÃ XÁC NHẬN (confirmed === "yes"/"no"),
// hiện window.confirm() cảnh báo rõ sẽ ghi đè mất phần đã xác nhận, huỷ chạy
// nếu người dùng không đồng ý.

const fs = require('fs');
const path = require('path');
const assert = require('assert');
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

const handleRunBody = extractBraceBlock('const handleRun = () => {');

// handleRun tham chiếu nhiều biến/hàm ngoài phạm vi (co, activeAccountId, saokePer,
// saokeText, sk, dv, dr, apiKey, parseSaoke, LS, onProcess, onProcessAll) — factory
// nhận TẤT CẢ qua tham số, đúng cách đã dùng ở tests/test_xoa_co_noi_bo_khi_xac_nhan_lai.js
// cho confirmRow/overrideRow của CÙNG file này.
const factory = new Function(
  'co', 'activeAccountId', 'saokePer', 'saokeText', 'sk', 'dv', 'dr', 'apiKey',
  'parseSaoke', 'LS', 'onProcess', 'onProcessAll',
  `const handleRun = () => {
${handleRunBody.slice(handleRunBody.indexOf('{') + 1, -1)}
  };
  return handleRun;`
);

function assertThrows() {} // (không dùng, giữ chỗ cho rõ ý không cần try/catch riêng)

// parseSaoke thật rất phức tạp (đọc sao kê ngân hàng) — chỉ cần 1 stub trả về
// mảng độ dài > 0 khi text không rỗng, KHÔNG liên quan tới logic đang test
// (cảnh báo ghi đè) — test khác trong repo đã kiểm chứng parseSaoke thật riêng.
function fakeParseSaoke(text) {
  return text ? [{ desc: 'dong-gia-lap' }] : [];
}

function makeLS(store) {
  return { get: key => store[key], set: (key, val) => { store[key] = val; } };
}

// ===== Test 1 (QUAN TRỌNG — đúng bug thật): TK ĐANG MỞ đã có session với
// giao dịch ĐÃ XÁC NHẬN (confirmed="yes") — bấm "Chạy AI đối chiếu" PHẢI hiện
// window.confirm() cảnh báo TRƯỚC, và NẾU người dùng bấm Huỷ (confirm trả về
// false) thì KHÔNG được gọi onProcess/onProcessAll (không ghi đè gì cả). =====
{
  const co = { id: 'co1', accounts: [{ id: 'acc1', label: 'TK chính', currency: 'VND' }] };
  const store = {
    'session_co1_acc1': {
      results: [
        { id: 'r1', confirmed: 'yes', confirmedHach: '1121' },
        { id: 'r2', confirmed: 'no' },
        { id: 'r3', confirmed: false }, // dòng "pending", chưa xử lý
      ],
    },
  };
  const LS = makeLS(store);
  let daGoiOnProcess = false;
  let confirmCalls = [];
  global.window = { confirm: (msg) => { confirmCalls.push(msg); return false; } };
  const handleRun = factory(
    co, 'acc1', { acc1: 'sao-ke-cu-da-tu-dien-lai' }, '', [], [], [], '',
    fakeParseSaoke, LS,
    () => { daGoiOnProcess = true; },
    () => { daGoiOnProcess = true; });
  handleRun();
  assert.strictEqual(confirmCalls.length, 1,
    'Phải hiện ĐÚNG 1 lần window.confirm() cảnh báo trước khi chạy lại TK đang mở đã có giao dịch xác nhận — got ' + confirmCalls.length);
  assert.ok(/1\s*giao dịch|2\s*giao dịch/.test(confirmCalls[0]) || confirmCalls[0].includes('ĐÃ XÁC NHẬN'),
    'Nội dung cảnh báo phải nói rõ đã có giao dịch XÁC NHẬN sẽ bị mất — got: ' + confirmCalls[0]);
  assert.strictEqual(daGoiOnProcess, false,
    'Người dùng bấm Huỷ (confirm=false) -> TUYỆT ĐỐI KHÔNG được gọi onProcess/onProcessAll (không ghi đè gì) — đúng bug thật đã gặp (ghi đè mất hạch toán mà không hỏi).');
}
console.log('PASS 1: TK đang mở đã có giao dịch xác nhận -> hiện cảnh báo window.confirm(), Huỷ thì không ghi đè.');

// ===== Test 2 (không hồi quy — QUAN TRỌNG): người dùng bấm ĐỒNG Ý ở hộp
// confirm (confirm=true) -> handleRun PHẢI tiếp tục chạy bình thường (vẫn gọi
// onProcess), không bị chặn vĩnh viễn — cảnh báo chỉ để XÁC NHẬN LẠI Ý ĐỊNH,
// không phải khoá cứng tính năng "chạy lại". =====
{
  const co = { id: 'co1', accounts: [{ id: 'acc1', label: 'TK chính', currency: 'VND' }] };
  const store = {
    'session_co1_acc1': { results: [{ id: 'r1', confirmed: 'yes', confirmedHach: '1121' }] },
  };
  const LS = makeLS(store);
  let daGoiOnProcess = false;
  global.window = { confirm: () => true };
  const handleRun = factory(
    co, 'acc1', { acc1: 'sao-ke-cu' }, '', [], [], [], '',
    fakeParseSaoke, LS,
    () => { daGoiOnProcess = true; },
    () => { daGoiOnProcess = true; });
  handleRun();
  assert.strictEqual(daGoiOnProcess, true,
    'Bấm Đồng ý (confirm=true) ở hộp cảnh báo -> PHẢI tiếp tục chạy đối chiếu bình thường (gọi onProcess), không bị chặn vĩnh viễn.');
}
console.log('PASS 2: bấm Đồng ý ở hộp cảnh báo -> vẫn chạy đối chiếu bình thường, không bị khoá cứng.');

// ===== Test 3 (không hồi quy — QUAN TRỌNG): TK đang mở CHƯA có session nào
// (lần đầu dán sao kê, hoặc có session nhưng CHƯA xác nhận dòng nào — toàn bộ
// confirmed=false) -> KHÔNG được hiện cảnh báo (không có gì để mất), chạy
// bình thường ngay, không làm phiền người dùng vô ích. =====
{
  const co = { id: 'co1', accounts: [{ id: 'acc1', label: 'TK chính', currency: 'VND' }] };
  // Ca A: chưa từng có session nào
  {
    const LS = makeLS({});
    let confirmCalls = 0, daGoiOnProcess = false;
    global.window = { confirm: () => { confirmCalls++; return true; } };
    const handleRun = factory(
      co, 'acc1', { acc1: 'sao-ke-moi' }, '', [], [], [], '',
      fakeParseSaoke, LS, () => { daGoiOnProcess = true; }, () => { daGoiOnProcess = true; });
    handleRun();
    assert.strictEqual(confirmCalls, 0, 'Chưa từng có session nào cho TK đang mở -> KHÔNG được hiện cảnh báo.');
    assert.strictEqual(daGoiOnProcess, true, 'Phải chạy đối chiếu bình thường ngay.');
  }
  // Ca B: có session nhưng CHƯA xác nhận dòng nào (toàn bộ confirmed=false)
  {
    const LS = makeLS({ 'session_co1_acc1': { results: [{ id: 'r1', confirmed: false }, { id: 'r2', confirmed: false }] } });
    let confirmCalls = 0, daGoiOnProcess = false;
    global.window = { confirm: () => { confirmCalls++; return true; } };
    const handleRun = factory(
      co, 'acc1', { acc1: 'sao-ke-cu-chua-xac-nhan' }, '', [], [], [], '',
      fakeParseSaoke, LS, () => { daGoiOnProcess = true; }, () => { daGoiOnProcess = true; });
    handleRun();
    assert.strictEqual(confirmCalls, 0, 'Session có nhưng CHƯA xác nhận dòng nào (toàn bộ pending) -> không có gì để mất, KHÔNG được hiện cảnh báo.');
    assert.strictEqual(daGoiOnProcess, true, 'Phải chạy đối chiếu bình thường ngay.');
  }
}
console.log('PASS 3: TK đang mở chưa có session/chưa xác nhận dòng nào -> không hiện cảnh báo vô ích, chạy bình thường ngay.');

console.log('\nALL DONE');
