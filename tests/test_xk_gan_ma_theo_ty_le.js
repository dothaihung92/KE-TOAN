// Regression test (Node) cho tính năng MỚI theo yêu cầu người dùng: "thêm
// nút dò mã mã hàng tự động với tỷ lệ khớp 90%; 80%; 70%; 60%; 50%... mặt
// hàng nào đã gắn mã rồi thì không cần phải chạy lại chỉ chạy các dòng chưa
// gắn mã hàng thôi."
//
// Test trích hàm xkGanMaTheoTyLe() từ static/index.html, mô phỏng tối thiểu
// các hàm/biến phụ thuộc (xkRows, xkTon, xkTonAnToan, xkTuNlRows, xkVeGrid,
// toast) rồi gọi trực tiếp với các ngưỡng khác nhau, xác nhận:
//  1) Dòng ĐÃ CÓ mã giữ NGUYÊN VẸN (không đụng, dù gợi ý khác điểm cao hơn).
//  2) Dòng TRỐNG mã CHỈ được gán khi gợi ý điểm cao nhất đạt ĐÚNG ngưỡng.
//  3) Gán đúng, tự tách dòng khi mã gợi ý không đủ tồn cho cả số lượng cần.
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

const srcFn = extractFn(html, 'xkGanMaTheoTyLe');

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

function runWith(xkRowsInput, xkTonInput, pct) {
  var xkRows = xkRowsInput;
  var xkTon = xkTonInput;
  var toastCalls = [];
  function toast(msg, kind) { toastCalls.push({ msg, kind }); }
  function xkTuNlRows() {}          // no-op: xkRows đã ở đúng dạng object sẵn trong test
  function xkVeGrid(moRong) {}      // no-op: chỉ cần xác nhận nội dung xkRows sau khi hàm chạy xong
  function xkTonAnToan(t) { return (t.ton_kho_min != null && t.ton_kho_min !== '') ? t.ton_kho_min : t.ton; }

  eval(srcFn);
  xkGanMaTheoTyLe(pct);
  return { xkRows, toastCalls };
}

// ----- Test 1: dòng ĐÃ CÓ mã giữ nguyên vẹn, không chạy lại -----
{
  const xkRowsInput = [
    { sl: 5, tt: 500000, ten_sp: 'Hàng A', ma: 'MA-CU', goi_y: [{ ma: 'MA-KHAC', diem: 0.99 }] },
  ];
  const xkTonInput = [
    { ma: 'MA-CU', ten: 'Hàng A', dvt: 'Cái', gia: 100000, ton: 100 },
    { ma: 'MA-KHAC', ten: 'Hàng A bản khác', dvt: 'Cái', gia: 90000, ton: 100 },
  ];
  const { xkRows } = runWith(xkRowsInput, xkTonInput, 50);
  assert(xkRows.length === 1 && xkRows[0].ma === 'MA-CU',
    'Dòng đã có mã "MA-CU" phải giữ NGUYÊN, KHÔNG được đổi sang gợi ý khác dù điểm cao hơn — được ' + JSON.stringify(xkRows));
  console.log('PASS 1: dòng đã có mã giữ nguyên vẹn, không chạy lại.');
}

// ----- Test 2: dòng trống mã chỉ gán khi đạt ĐÚNG ngưỡng -----
{
  const xkRowsInput = [
    { sl: 5, tt: 500000, ten_sp: 'Hàng B', ma: '', goi_y: [{ ma: 'MB', diem: 0.75 }] },
  ];
  const xkTonInput = [{ ma: 'MB', ten: 'Hàng B', dvt: 'Cái', gia: 100000, ton: 100 }];

  const kq90 = runWith(xkRowsInput, xkTonInput, 90);
  assert(kq90.xkRows.length === 1 && !kq90.xkRows[0].ma,
    'Gợi ý điểm 75% KHÔNG đạt ngưỡng 90% -> dòng phải VẪN TRỐNG mã — được ' + JSON.stringify(kq90.xkRows));

  const kq70 = runWith(xkRowsInput, xkTonInput, 70);
  assert(kq70.xkRows.length === 1 && kq70.xkRows[0].ma === 'MB' && kq70.xkRows[0].sl === 5,
    'Gợi ý điểm 75% ĐẠT ngưỡng 70% -> dòng phải được gán mã "MB", đủ nguyên SL=5 — được ' + JSON.stringify(kq70.xkRows));
  console.log('PASS 2: chỉ gán khi gợi ý đạt đúng ngưỡng phần trăm, không gán khi dưới ngưỡng.');
}

// ----- Test 3: tự tách dòng khi mã gợi ý không đủ tồn -----
{
  const xkRowsInput = [
    { sl: 10, tt: 1000000, ten_sp: 'Hàng C', ma: '', goi_y: [{ ma: 'MC', diem: 0.95 }] },
  ];
  const xkTonInput = [{ ma: 'MC', ten: 'Hàng C', dvt: 'Cái', gia: 100000, ton: 6 }];   // chỉ còn 6, cần 10
  const { xkRows } = runWith(xkRowsInput, xkTonInput, 90);
  assert(xkRows.length === 2, 'Phải tách thành 2 dòng (6 gán được + 4 còn thiếu) — được ' + JSON.stringify(xkRows));
  const ganDuoc = xkRows.find(r => r.ma === 'MC');
  const conThieu = xkRows.find(r => !r.ma);
  assert(ganDuoc && ganDuoc.sl === 6, 'Dòng gán được phải đúng SL=6 (hết tồn) — được ' + JSON.stringify(ganDuoc));
  assert(conThieu && conThieu.sl === 4, 'Dòng còn thiếu phải đúng SL=4 (10-6), vẫn trống mã để xử lý tiếp — được ' + JSON.stringify(conThieu));
  assert(ganDuoc.sl + conThieu.sl === 10, 'Tổng SL sau tách phải bảo toàn đúng 10 — được ' + (ganDuoc.sl + conThieu.sl));
  console.log('PASS 3: tự tách dòng đúng khi mã gợi ý không đủ tồn cho cả số lượng cần, bảo toàn tổng SL.');
}

console.log('\nTẤT CẢ TEST PASS');
