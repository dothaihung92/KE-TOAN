// Regression test (Node, KHÔNG phải Python — đây là lỗi ở static/index.html,
// phần JS phía trình duyệt): người dùng báo "khi tôi chọn 1 mã mà sẽ bị tách
// dòng, khi chọn xong phần mềm sẽ bỏ lọc hiển thị... không có hiện lọc như
// trước" — nghĩa là sau khi chọn 1 mã ở modal "Gán mã hàng kho" khiến dòng đó
// bị TÁCH làm 2 (do không đủ tồn), bộ lọc "chỉ hiện dòng chưa gán Mã hàng
// kho" (nlSnapTrong, xem nlLocDong) hiện SAI/THIẾU dòng.
//
// Nguyên nhân: nlSnapTrong lưu CHỈ SỐ (index) các dòng "trống" tại thời điểm
// bật lọc. Khi xkChonMa() tách 1 dòng thành 2 (xkRows.splice(idx+1,0,dongThieu)),
// MỌI dòng đứng SAU dòng bị tách đều dịch lên +1 chỉ số — nhưng trước fix,
// xkChonMa() gọi xkVeGrid() KHÔNG truyền moRong nên xkRemapChiSoSauTach()
// không chạy, nlSnapTrong vẫn giữ chỉ số CŨ -> bộ lọc lệch, hiện sai dòng.
//
// Test này trích đúng 2 hàm liên quan (xkMoRongDonGian, xkRemapChiSoSauTach)
// từ static/index.html rồi gọi trực tiếp với 1 kịch bản tách dòng đơn giản,
// xác nhận nlSnapTrong được dịch lại ĐÚNG theo chỉ số MỚI.
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

const srcMoRong = extractFn(html, 'xkMoRongDonGian');
const srcRemap = extractFn(html, 'xkRemapChiSoSauTach');

// biến toàn cục mà xkRemapChiSoSauTach dùng (nlChon, nlSnapTrong) — khai báo
// bằng var (không const/let) để eval() phía dưới ghi đè được vào scope này.
var nlChon = null;
var nlSnapTrong = {};

eval(srcMoRong);
eval(srcRemap);

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

// Kịch bản: bảng có 5 dòng (chỉ số 0..4). Bộ lọc "chỉ hiện dòng chưa gán"
// đang ghim đúng các dòng {1, 3} (nlSnapTrong[ci] = Set{1,3}) — 2 dòng còn
// trống Mã hàng kho ở cột ci=8 (số cột không quan trọng với test này).
// Người dùng chọn 1 mã cho dòng 1 -> dòng 1 bị TÁCH thành 2 dòng (do thiếu
// tồn): dòng 1 cũ (đã gán mã) + 1 dòng MỚI chèn ngay sau (vẫn trống).
const ci = 8;
nlSnapTrong[ci] = new Set([1, 3]);

const soDongCuTruocTach = 5;   // bảng cũ có 5 dòng trước khi tách
const idxCuBiTach = 1;         // dòng bị tách là dòng chỉ số 1
const soDongMoi = 2;           // tách thành 2 dòng

const moRong = xkMoRongDonGian(soDongCuTruocTach, idxCuBiTach, soDongMoi);
// moRong[0] không đổi vị trí (đứng TRƯỚC dòng bị tách)
assert(moRong[0].batDau === 0 && moRong[0].soDong === 1, 'Dòng 0 (trước dòng bị tách) phải giữ nguyên vị trí — got ' + JSON.stringify(moRong[0]));
// moRong[1] (dòng bị tách) -> nở thành 2 dòng MỚI tại đúng vị trí cũ
assert(moRong[1].batDau === 1 && moRong[1].soDong === 2, 'Dòng 1 (bị tách) phải nở thành 2 dòng bắt đầu tại vị trí 1 — got ' + JSON.stringify(moRong[1]));
// moRong[2], moRong[3], moRong[4] (đứng SAU dòng bị tách) phải dịch xuống +1
assert(moRong[2].batDau === 3 && moRong[2].soDong === 1, 'Dòng 2 (sau dòng bị tách) phải dịch xuống vị trí mới 3 — got ' + JSON.stringify(moRong[2]));
assert(moRong[3].batDau === 4 && moRong[3].soDong === 1, 'Dòng 3 (sau dòng bị tách, ĐANG bị bộ lọc ghim) phải dịch xuống vị trí mới 4 — got ' + JSON.stringify(moRong[3]));
assert(moRong[4].batDau === 5 && moRong[4].soDong === 1, 'Dòng 4 (sau dòng bị tách) phải dịch xuống vị trí mới 5 — got ' + JSON.stringify(moRong[4]));

xkRemapChiSoSauTach(moRong);

const ketQua = Array.from(nlSnapTrong[ci]).sort((a, b) => a - b);
// dòng 1 (cũ, đang ghim) nở thành 2 dòng mới {1, 2} -> CẢ 2 đều phải được ghim
// tiếp (giữ hiển thị để dễ theo dõi vừa tách ra sao — xem chú thích gốc);
// dòng 3 (cũ, đang ghim) dịch xuống vị trí mới 4.
assert(JSON.stringify(ketQua) === JSON.stringify([1, 2, 4]),
  'Sau khi tách dòng 1 thành 2 dòng {1,2} và dòng 3 dịch xuống 4, bộ lọc "chưa gán" đang ghim PHẢI trở thành {1,2,4} '
  + '(không được giữ nguyên chỉ số CŨ {1,3} — sẽ trỏ NHẦM sang dòng khác/mất dòng sau khi tách) — được ' + JSON.stringify(ketQua));

console.log('PASS: xkMoRongDonGian/xkRemapChiSoSauTach dịch đúng bộ lọc "chưa gán" (nlSnapTrong) theo chỉ số MỚI sau khi 1 dòng bị tách làm 2 — không còn hiện sai/thiếu dòng như báo cáo thật ("chọn 1 mã mà sẽ bị tách dòng... phần mềm sẽ bỏ lọc hiển thị... không có hiện lọc như trước").');
