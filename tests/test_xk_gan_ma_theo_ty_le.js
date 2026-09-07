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
// thêm đvt nữa"): thêm điều kiện ĐVT phải khớp mới tự gán.
//
// ROUND 4 (theo yêu cầu người dùng, ĐẢO NGƯỢC round 3: "chỉnh lại gắn theo %
// không cần phải khớp đvt nữa mà chỉ cần gần giống tên và sau đó chọn đơn giá
// gần giống với tên hàng nhất đừng chêch lệch giá bán quá nhiều chỉ cho phép
// +- chêch lệch 30%"): BỎ hẳn điều kiện ĐVT — quay lại chỉ lọc theo % khớp
// tên như bản gốc.
//
// ROUND 5 (làm rõ lại theo yêu cầu người dùng: "không phải ưu tiên chọn mã
// có giá gần giá bán nhất mà ưu tiên khớp tên hàng sau đó mới dò đơn giá đc
// phép chệch lệch không quá 30%"): THỨ TỰ ƯU TIÊN VẪN LÀ % khớp tên (cao
// nhất trước, y hệt bản gốc, KHÔNG sắp lại theo độ lệch giá) — Đơn giá kho
// (r.gia) CHỈ dùng để LỌC BỎ mã lệch quá 30% so với Đơn giá bán (r.dgia) khi
// CẢ 2 giá đều biết, không dùng để đổi thứ tự ưu tiên giữa các mã còn lại.
//
// Test trích các hàm liên quan TỪ static/index.html (không stub thuật toán
// so khớp/điểm giống — dùng NGUYÊN VẸN xkManh/xkKichThuocKhop/xkMaNgoacKhop/
// xkDiemGiong/xkChuanTen/xkTinhGoiYTuoi thật, chỉ stub phần không liên quan
// tới thuật toán như toast/xkVeGrid) để xác nhận:
//  1) r.goi_y (dù có, dù điểm cao) bị BỎ QUA hoàn toàn — không dùng để gán.
//  2) Ứng viên tính TƯƠI từ xkTon (đúng tồn kho hiện tại) được dùng để gán,
//     y hệt điểm % mà modal "Gán mã hàng kho" tay sẽ hiển thị.
//  3) Dòng ĐÃ CÓ mã vẫn giữ nguyên vẹn (không đổi từ round 1).
//  4) Mã khớp TÊN 100% nhưng ĐVT khác hẳn KHÔNG còn bị chặn nữa (đảo ngược
//     round 3 — chỉ còn chặn theo giá, không phải theo ĐVT).
//  5) Mã lệch Đơn giá kho > 30% so với Đơn giá bán bị loại, dù tên khớp cao.
//  6) Giữa nhiều mã cùng đạt ngưỡng % và cùng trong khoảng ±30% giá, VẪN ưu
//     tiên gán mã có ĐIỂM % TÊN CAO NHẤT trước (KHÔNG sắp lại theo độ lệch
//     giá) — giá chỉ LỌC, không dùng để đổi thứ tự ưu tiên.
//  6b) Khi mã điểm % tên cao nhất bị LOẠI vì lệch giá > 30%, mã điểm thấp
//     hơn (nhưng còn trong 30%) mới được chọn — do bị lọc, không phải do ưu
//     tiên theo giá.
//  7) Thiếu dữ liệu giá (giá bán HOẶC giá kho) thì KHÔNG chặn/không đổi thứ
//     tự — an toàn với dữ liệu thiếu, giữ nguyên hành vi cũ.
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

const FN_NAMES = ['xkChuanTen', 'xkManh', 'xkMaNgoacGop', 'xkMaNgoacKhop', 'xkKichThuocTrich',
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

// ----- ROUND 4 (đảo ngược round 3, theo yêu cầu người dùng "không cần phải
// khớp đvt nữa"): Test 4 — mã TÊN khớp 100% nhưng ĐVT khác hẳn (Thùng vs M2)
// KHÔNG còn bị chặn — chỉ chặn theo giá (test sau), không phải theo ĐVT. -----
{
  const tenBan = 'Sơn chống thấm ABC';
  const xkRowsInput = [{ sl: 5, tt: 500000, ten_sp: tenBan, dvt: 'Thùng', ma: '', goi_y: [] }];  // KHÔNG có dgia
  const xkTonInput = [{ ma: 'SCT01', ten: tenBan, dvt: 'M2', gia: 100000, ton: 100 }];
  const { xkRows } = runWith(xkRowsInput, xkTonInput, 90);
  assert(xkRows.length === 1 && xkRows[0].ma === 'SCT01',
    'Mã "SCT01" khớp TÊN 100% — ĐVT khác (Thùng/M2) KHÔNG còn bị chặn (đảo ngược round 3) — được ' + JSON.stringify(xkRows));
  console.log('PASS 4: mã khớp tên 100% dù ĐVT khác (Thùng vs M2) vẫn ĐƯỢC gán — điều kiện ĐVT đã bỏ theo yêu cầu mới.');
}

// ----- Test 5 (theo yêu cầu người dùng "đừng chêch lệch giá bán quá nhiều
// chỉ cho phép +- chêch lệch 30%"): mã khớp TÊN 100% nhưng Đơn giá kho lệch
// > 30% so với Đơn giá bán -> PHẢI bị loại, không tự gán nhầm hàng khác. -----
{
  const tenBan = 'Bồn cầu AC-989VN/BW1';
  const xkRowsInput = [{ sl: 3, tt: 14100000, ten_sp: tenBan, dgia: 4700000, ma: '', goi_y: [] }];
  const xkTonInput = [{ ma: 'BC-LECH', ten: tenBan, dvt: 'Bộ', gia: 6500000, ton: 100 }];  // lệch 38% > 30%
  const { xkRows } = runWith(xkRowsInput, xkTonInput, 90);
  assert(xkRows.length === 1 && !xkRows[0].ma,
    'Mã "BC-LECH" khớp TÊN 100% nhưng Đơn giá kho (6.500.000) lệch 38% so Đơn giá bán (4.700.000) — vượt '
    + '30% cho phép — PHẢI bị loại, không tự gán — được ' + JSON.stringify(xkRows));
  console.log('PASS 5: mã khớp tên 100% nhưng lệch giá > 30% so với giá bán bị loại đúng, không tự gán nhầm hàng khác.');
}

// ----- Test 6: nhiều mã CÙNG đạt ngưỡng % tên và CÙNG trong khoảng ±30% giá
// -> VẪN ưu tiên gán mã có ĐIỂM % TÊN CAO NHẤT trước (giá chỉ lọc, không
// dùng để sắp lại thứ tự ưu tiên) — theo yêu cầu làm rõ lại của người dùng. -----
{
  const tenBan = 'Bồn cầu AC-989VN/BW1';
  const tenGanDung = 'Bồn cầu AC-989VN/BW1 hàng nhập khẩu chính hãng';   // tên dài hơn -> điểm % thấp hơn 1.0
  const xkChuanTenTest = eval('(' + extractFn(html, 'xkChuanTen') + ')');
  const diemGiongTest = eval('(' + extractFn(html, 'xkDiemGiong') + ')');
  const diemGanDung = diemGiongTest(xkChuanTenTest(tenBan), xkChuanTenTest(tenGanDung));
  const nguong = Math.max(1, Math.floor(diemGanDung * 100) - 5);   // đủ thấp để CẢ 2 mã cùng đạt ngưỡng
  const xkRowsInput = [{ sl: 2, tt: 9400000, ten_sp: tenBan, dgia: 4700000, ma: '', goi_y: [] }];
  const xkTonInput = [
    // Điểm % tên CAO NHẤT (khớp tuyệt đối 100%), giá lệch ~23% (vẫn <= 30%,
    // KHÔNG bị lọc).
    { ma: 'BC-DIEM-CAO-GIA-XA', ten: tenBan, dvt: 'Bộ', gia: 5800000, ton: 100 },
    // Điểm % tên THẤP HƠN (tên dài hơn), giá rất gần (~1%) nhưng KHÔNG được
    // ưu tiên chỉ vì giá gần hơn — điểm tên vẫn quyết định thứ tự.
    { ma: 'BC-DIEM-THAP-GIA-GAN', ten: tenGanDung, dvt: 'Bộ', gia: 4650000, ton: 100 },
  ];
  const { xkRows } = runWith(xkRowsInput, xkTonInput, nguong);
  assert(xkRows.length === 1 && xkRows[0].ma === 'BC-DIEM-CAO-GIA-XA',
    `Phải ưu tiên gán mã có ĐIỂM % TÊN CAO NHẤT (BC-DIEM-CAO-GIA-XA, khớp tuyệt đối, giá lệch ~23% `
    + `vẫn trong 30%) — KHÔNG được ưu tiên mã điểm tên thấp hơn chỉ vì giá gần hơn (BC-DIEM-THAP-GIA-GAN) `
    + `— được ${JSON.stringify(xkRows)}`);
  console.log('PASS 6: giữa nhiều mã cùng đạt ngưỡng % và cùng trong 30% giá, vẫn ưu tiên đúng mã điểm % tên cao nhất, giá không dùng để sắp lại thứ tự.');
}

// ----- Test 6b: khi mã điểm % tên CAO NHẤT bị LOẠI vì lệch giá > 30%, mã
// điểm thấp hơn (còn trong 30%) mới được chọn — do bị LỌC, không phải do ưu
// tiên theo giá. -----
{
  const tenBan = 'Bồn cầu AC-989VN/BW1';
  const tenGanDung = 'Bồn cầu AC-989VN/BW1 hàng nhập khẩu chính hãng';
  const xkChuanTenTest = eval('(' + extractFn(html, 'xkChuanTen') + ')');
  const diemGiongTest = eval('(' + extractFn(html, 'xkDiemGiong') + ')');
  const diemGanDung = diemGiongTest(xkChuanTenTest(tenBan), xkChuanTenTest(tenGanDung));
  const nguong = Math.max(1, Math.floor(diemGanDung * 100) - 5);
  const xkRowsInput = [{ sl: 2, tt: 9400000, ten_sp: tenBan, dgia: 4700000, ma: '', goi_y: [] }];
  const xkTonInput = [
    // Điểm % tên CAO NHẤT nhưng giá lệch 38% (> 30%) -> PHẢI bị loại.
    { ma: 'BC-DIEM-CAO-GIA-LOAI', ten: tenBan, dvt: 'Bộ', gia: 6500000, ton: 100 },
    // Điểm % tên thấp hơn, giá lệch ~1% (trong 30%) -> mã còn lại duy nhất.
    { ma: 'BC-DIEM-THAP-GIA-ON', ten: tenGanDung, dvt: 'Bộ', gia: 4650000, ton: 100 },
  ];
  const { xkRows } = runWith(xkRowsInput, xkTonInput, nguong);
  assert(xkRows.length === 1 && xkRows[0].ma === 'BC-DIEM-THAP-GIA-ON',
    `Mã điểm % tên cao nhất (BC-DIEM-CAO-GIA-LOAI) lệch giá 38% > 30% phải bị LỌC BỎ, còn lại `
    + `BC-DIEM-THAP-GIA-ON (trong 30%) được chọn — được ${JSON.stringify(xkRows)}`);
  console.log('PASS 6b: mã điểm % tên cao nhất bị loại do lệch giá > 30%, mã còn lại (trong 30%) mới được chọn.');
}

// ----- Test 7: THIẾU dữ liệu giá (giá bán HOẶC giá kho) -> KHÔNG chặn/không
// đổi thứ tự — an toàn với dữ liệu thiếu, giữ nguyên hành vi cũ theo % tên. -----
{
  const tenBan = 'Sơn chống thấm XYZ';
  // 7a: dòng bán KHÔNG có dgia (giá bán) -> không lọc/không sắp lại theo giá.
  const xkRowsInputA = [{ sl: 5, tt: 500000, ten_sp: tenBan, ma: '', goi_y: [] }];
  const xkTonInputA = [{ ma: 'SXY01', ten: tenBan, dvt: 'Thùng', gia: 999999999, ton: 100 }];  // giá kho "vô lý" cũng không sao vì không có giá bán để so
  const { xkRows: xkRowsA } = runWith(xkRowsInputA, xkTonInputA, 90);
  assert(xkRowsA.length === 1 && xkRowsA[0].ma === 'SXY01',
    'Thiếu Đơn giá bán (r.dgia) thì KHÔNG được chặn/lọc theo giá, vẫn gán bình thường theo % tên — được ' + JSON.stringify(xkRowsA));

  // 7b: có dgia nhưng mã tồn kho THIẾU giá kho (gia=0/rỗng) -> không bị chặn.
  const xkRowsInputB = [{ sl: 5, tt: 500000, ten_sp: tenBan, dgia: 4700000, ma: '', goi_y: [] }];
  const xkTonInputB = [{ ma: 'SXY02', ten: tenBan, dvt: 'Thùng', gia: 0, ton: 100 }];
  const { xkRows: xkRowsB } = runWith(xkRowsInputB, xkTonInputB, 90);
  assert(xkRowsB.length === 1 && xkRowsB[0].ma === 'SXY02',
    'Mã tồn kho thiếu Đơn giá kho (chưa rõ để so) KHÔNG được chặn — được ' + JSON.stringify(xkRowsB));
  console.log('PASS 7: thiếu dữ liệu giá (giá bán hoặc giá kho) ở 1 trong 2 bên không chặn/không đổi thứ tự, an toàn với dữ liệu thiếu.');
}

console.log('\nTẤT CẢ TEST PASS');
