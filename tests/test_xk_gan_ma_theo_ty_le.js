// Regression test (Node) cho tính năng nút "🎯 Gán theo %: ≥90/80/70/60/50%"
// ở màn Xuất Kho, theo yêu cầu người dùng: "thêm nút dò mã mã hàng tự động
// với tỷ lệ khớp 90%; 80%; 70%; 60%; 50%... mặt hàng nào đã gắn mã rồi thì
// không cần phải chạy lại chỉ chạy các dòng chưa gắn mã hàng thôi."
//
// ROUND 2 (fix lỗi thật vừa báo lại): dòng "Gạch ốp lát 40*40 cm" bấm nút
// "≥60%" KHÔNG gán được gì, dù bấm đúp mở bảng "Gán mã hàng kho" TAY lại
// hiện rõ ràng nhiều mã "Khớp 67%"/"Khớp 64%" còn tồn hàng trăm (vd MH288
// còn 390). Nguyên nhân: round 1 dùng r.goi_y (field lưu SẴN từ server lúc
// Dò mã hàng tự động/import lần đầu — CHỈ có đúng 1 ứng viên, đã hết sạch
// tồn từ lâu) thay vì tính lại "tươi" theo tồn kho HIỆN TẠI như modal tay
// vẫn làm (xkTinhGoiYTuoi — xem chú thích gốc ở xkMoGan). Fix: dùng đúng
// xkTinhGoiYTuoi(r) (cùng nguồn "Khớp XX%" với modal tay) thay vì r.goi_y.
//
// ROUND 3 (theo yêu cầu người dùng "hãy chỉnh lại dò theo % hãy so khớp
// thêm đvt nữa"): chỉ so khớp TÊN không đủ an toàn — 1 mã TÊN giống hệt
// nhưng bán/tồn theo ĐƠN VỊ khác hẳn (vd "M2" thay vì "Thùng") vẫn có thể bị
// tự gán nhầm dù điểm % rất cao, làm sai cả tồn kho lẫn giá vốn (Số lượng/
// Đơn giá 2 đơn vị không tương đương). Nay "Gán theo %" THÊM điều kiện ĐVT
// phải khớp (sau chuẩn hoá — xem xkChuanDvt) mới tự gán; ĐVT thiếu ở 1 bên
// (không rõ để so) thì KHÔNG chặn, vẫn gán bình thường như trước.
//
// Test trích các hàm liên quan TỪ static/index.html (không stub thuật toán
// so khớp/điểm giống — dùng NGUYÊN VẸN xkManh/xkKichThuocKhop/xkMaNgoacKhop/
// xkDiemGiong/xkChuanTen/xkChuanDvt/xkTinhGoiYTuoi thật, chỉ stub phần
// không liên quan tới thuật toán như toast/xkVeGrid) để xác nhận:
//  1) r.goi_y (dù có, dù điểm cao) bị BỎ QUA hoàn toàn — không dùng để gán.
//  2) Ứng viên tính TƯƠI từ xkTon (đúng tồn kho hiện tại) được dùng để gán,
//     y hệt điểm % mà modal "Gán mã hàng kho" tay sẽ hiển thị.
//  3) Dòng ĐÃ CÓ mã vẫn giữ nguyên vẹn (không đổi từ round 1).
//  4) Mã khớp TÊN đủ % nhưng ĐVT khác hẳn bị loại, không tự gán nhầm đơn vị.
//  5) ĐVT thiếu ở 1 bên không chặn gán (an toàn với dữ liệu thiếu).
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

const FN_NAMES = ['xkChuanTen', 'xkChuanDvt', 'xkManh', 'xkMaNgoacGop', 'xkMaNgoacKhop', 'xkKichThuocTrich',
                   'xkKichThuocKhop', 'xkDiemGiong', 'xkTinhGoiYTuoi', 'xkGanMaTheoTyLe'];
const srcAll = FN_NAMES.map(n => extractFn(html, n)).join('\n');

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

const XK_DO_DAI_TOI_THIEU_MANH = 6;   // hằng số dùng bởi xkManh() — xem static/index.html

function runWith(xkRowsInput, xkTonInput, pct) {
  var xkRows = xkRowsInput;
  var xkTon = xkTonInput;
  var toastCalls = [];
  function toast(msg, kind) { toastCalls.push({ msg, kind }); }
  function xkTuNlRows() {}
  function xkVeGrid(moRong) {}
  function xkTonAnToan(t) { return (t.ton_kho_min != null && t.ton_kho_min !== '') ? t.ton_kho_min : t.ton; }

  eval(srcAll);
  xkGanMaTheoTyLe(pct);
  return { xkRows, toastCalls };
}

// ----- Test 1: r.goi_y (stale, hết tồn) BỊ BỎ QUA — dùng ứng viên TƯƠI từ
// xkTon (còn tồn) thay thế — đúng ca thật "Gạch ốp lát 40*40 cm". -----
{
  const tenBan = 'Gạch ốp lát 40*40 cm';
  const xkRowsInput = [
    { sl: 164.29, tt: 18893350, ten_sp: tenBan, ma: '',
      // r.goi_y CŨ (từ lúc Dò mã hàng tự động lần đầu) — điểm rất cao
      // nhưng mã đó GIỜ đã hết sạch tồn — PHẢI bị bỏ qua hoàn toàn.
      goi_y: [{ ma: 'MA-CU-HET-HANG', diem: 0.99, ten: tenBan, dvt: 'Thùng', gia: 115000 }] },
  ];
  const xkTonInput = [
    // vẫn còn trong tồn kho (mã cũ đã dùng hết, KHÔNG có trong xkTon nữa —
    // mô phỏng đúng ca thật: mã r.goi_y trỏ tới không còn/không đủ tồn).
    { ma: 'MH288', ten: 'Gạch 40 x 40', dvt: 'Thùng', gia: 115605, ton: 390 },
    { ma: 'MH143', ten: 'Gạch PR.40.40_A1', dvt: 'Thùng', gia: 73080, ton: 41 },
  ];
  // Tính điểm THẬT (giống hệt thuật toán modal tay) để biết chính xác ngưỡng
  // nào ứng viên MH288 đạt được, không đoán mò con số.
  const xkChuanTenTest = eval('(' + extractFn(html, 'xkChuanTen') + ')');
  const diemGiongTest = eval('(' + extractFn(html, 'xkDiemGiong') + ')');
  const diemMH288 = diemGiongTest(xkChuanTenTest(tenBan), xkChuanTenTest('Gạch 40 x 40'));
  const nguongDuoi = Math.max(1, Math.floor(diemMH288 * 100) - 5);   // chắc chắn ĐẠT
  const nguongTren = Math.min(99, Math.ceil(diemMH288 * 100) + 20);  // chắc chắn KHÔNG đạt

  const kqDat = runWith(xkRowsInput, xkTonInput, nguongDuoi);
  const ganDuoc = kqDat.xkRows.find(r => r.ma === 'MH288');
  assert(ganDuoc, `Ngưỡng ${nguongDuoi}% (dưới điểm thật ${Math.round(diemMH288*100)}% của MH288) PHẢI gán được MH288 (tính TƯƠI từ xkTon, KHÔNG dùng r.goi_y đã hết tồn) — got ${JSON.stringify(kqDat.xkRows)}`);
  assert(!kqDat.xkRows.some(r => r.ma === 'MA-CU-HET-HANG'),
    'KHÔNG được dùng mã "MA-CU-HET-HANG" từ r.goi_y (stale, đã hết tồn) — chỉ dùng ứng viên tính tươi từ xkTon');

  const kqKhongDat = runWith(xkRowsInput, xkTonInput, nguongTren);
  assert(!kqKhongDat.xkRows.some(r => r.ma), `Ngưỡng ${nguongTren}% (trên điểm thật ${Math.round(diemMH288*100)}% của MH288) KHÔNG được gán gì — got ${JSON.stringify(kqKhongDat.xkRows)}`);

  console.log(`PASS 1: điểm thật MH288="${Math.round(diemMH288*100)}%" — dùng đúng ứng viên tính TƯƠI từ tồn kho hiện tại (KHÔNG dùng r.goi_y lỗi thời đã hết tồn), đúng ca thật "Gạch ốp lát 40*40 cm" vừa báo lại.`);
}

// ----- Test 2: dòng ĐÃ CÓ mã vẫn giữ nguyên vẹn (không đổi từ round 1) -----
{
  const xkRowsInput = [
    { sl: 5, tt: 500000, ten_sp: 'Hàng A', ma: 'MA-CU', goi_y: [] },
  ];
  const xkTonInput = [
    { ma: 'MA-CU', ten: 'Hàng A', dvt: 'Cái', gia: 100000, ton: 100 },
    { ma: 'MA-KHAC', ten: 'Hàng A phiên bản khác', dvt: 'Cái', gia: 90000, ton: 100 },
  ];
  const { xkRows } = runWith(xkRowsInput, xkTonInput, 10);
  assert(xkRows.length === 1 && xkRows[0].ma === 'MA-CU',
    'Dòng đã có mã "MA-CU" phải giữ NGUYÊN, không đụng tới — được ' + JSON.stringify(xkRows));
  console.log('PASS 2: dòng đã có mã giữ nguyên vẹn, không chạy lại.');
}

// ----- Test 3: tự tách dòng khi mã tính tươi đạt ngưỡng nhưng không đủ tồn -----
{
  const tenBan = 'Hàng C mẫu XYZ';
  const xkRowsInput = [{ sl: 10, tt: 1000000, ten_sp: tenBan, ma: '', goi_y: [] }];
  const xkTonInput = [{ ma: 'MC', ten: tenBan, dvt: 'Cái', gia: 100000, ton: 6 }];  // khớp 100%, chỉ còn 6, cần 10
  const { xkRows } = runWith(xkRowsInput, xkTonInput, 90);
  assert(xkRows.length === 2, 'Phải tách thành 2 dòng (6 gán được + 4 còn thiếu) — được ' + JSON.stringify(xkRows));
  const ganDuoc = xkRows.find(r => r.ma === 'MC');
  const conThieu = xkRows.find(r => !r.ma);
  assert(ganDuoc && ganDuoc.sl === 6, 'Dòng gán được phải đúng SL=6 (hết tồn) — được ' + JSON.stringify(ganDuoc));
  assert(conThieu && conThieu.sl === 4, 'Dòng còn thiếu phải đúng SL=4 (10-6) — được ' + JSON.stringify(conThieu));
  console.log('PASS 3: tự tách dòng đúng khi mã tính tươi đạt ngưỡng nhưng không đủ tồn, bảo toàn tổng SL.');
}

// ----- ROUND 3 (theo yêu cầu người dùng "dò theo % hãy so khớp thêm đvt
// nữa"): Test 4 — mã TÊN khớp 100% nhưng ĐVT khác hẳn (Thùng vs M2) -> PHẢI
// bị loại, KHÔNG tự gán dù điểm tên rất cao và còn thừa tồn. -----
{
  const tenBan = 'Sơn chống thấm ABC';
  const xkRowsInput = [{ sl: 5, tt: 500000, ten_sp: tenBan, dvt: 'Thùng', ma: '', goi_y: [] }];
  const xkTonInput = [{ ma: 'SCT01', ten: tenBan, dvt: 'M2', gia: 100000, ton: 100 }];
  const { xkRows } = runWith(xkRowsInput, xkTonInput, 90);
  assert(xkRows.length === 1 && !xkRows[0].ma,
    'Mã "SCT01" khớp TÊN 100% nhưng ĐVT khác (Thùng/M2) PHẢI bị loại, không tự gán — được ' + JSON.stringify(xkRows));
  console.log('PASS 4: mã khớp tên 100% nhưng ĐVT khác (Thùng vs M2) bị loại đúng, không tự gán nhầm đơn vị.');
}

// ----- Test 5: ĐVT THIẾU ở 1 trong 2 bên (không rõ để so) -> KHÔNG loại,
// vẫn gán bình thường theo % tên như trước (an toàn, không chặn nhầm chỉ vì
// thiếu dữ liệu ĐVT). -----
{
  const tenBan = 'Sơn chống thấm XYZ';
  const xkRowsInput = [{ sl: 5, tt: 500000, ten_sp: tenBan, dvt: 'Thùng', ma: '', goi_y: [] }];
  const xkTonInput = [{ ma: 'SXY01', ten: tenBan, dvt: '', gia: 100000, ton: 100 }];  // ĐVT tồn kho rỗng/chưa có
  const { xkRows } = runWith(xkRowsInput, xkTonInput, 90);
  assert(xkRows.length === 1 && xkRows[0].ma === 'SXY01',
    'ĐVT tồn kho rỗng (không rõ để so) KHÔNG được chặn gán — được ' + JSON.stringify(xkRows));
  console.log('PASS 5: ĐVT thiếu ở 1 bên không chặn gán, vẫn gán bình thường theo % tên như trước.');
}

console.log('\nTẤT CẢ TEST PASS');
