// Regression test (Node) cho hàm THUẦN dongBoTaiKhoanNganHang() trong
// static/doi_chieu_ngan_hang.html (Kế Toán AI), theo yêu cầu người dùng
// "hãy thêm nút đồng bộ TK NH với misa khi nhấn vào phần mềm sẽ tự lấy
// thông tin tài khoản để nhập vào phần mềm luôn", và 2 lỗi thật đã báo
// ngay sau khi tính năng chạy lần đầu (kèm ảnh chụp màn hình):
//  1) "Mã hạch toán MISA phần mềm lấy sai số tài khoản số đúng chỉ có
//     1121" — công ty CHỈ có ĐÚNG 1 TK con "1121" trong Hệ thống tài
//     khoản MISA (không tách theo từng ngân hàng, xem ảnh "Hệ thống tài
//     khoản" chỉ có đúng 1 dòng "1121") nhưng phần mềm tự đoán hậu tố chữ
//     cái ra "1121-NG" (mã KHÔNG hề tồn tại trong MISA).
//  2) "tài khoản chính mặc định hãy bỏ đi không cần phải hiện vì đã có
//     thêm tài khoản rồi" — TK "TK chính" mặc định (rỗng, chưa gắn gì)
//     vẫn còn hiện cạnh TK thật vừa đồng bộ, gây thừa/rối.
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

const srcAll = ['suggestMisaAcct', 'dongBoTaiKhoanNganHang'].map(extractFn).join('\n');
eval(srcAll);

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

// ----- Test 1 (đúng lỗi thật): công ty CHỈ có đúng 1 TK con "1121" (đưa
// vào qua maTkVnd, xem _misa_danh_sach_tai_khoan_ngan_hang server.py) ->
// TK MỚI thêm PHẢI dùng đúng "1121", KHÔNG được tự đoán ra "1121-NG". -----
{
  const accounts = [{ id: 'main', label: 'TK chính', currency: 'VND' }];
  const dsMisa = [{ so_tk: '934594948', ten_ngan_hang: 'Ngân hàng TMCP Á Châu', inactive: false }];
  const { updated, soMoi } = dongBoTaiKhoanNganHang(accounts, dsMisa, '1121', null, () => false);
  assert(soMoi === 1, `phải thêm đúng 1 TK mới — got soMoi=${soMoi}`);
  const moi = updated.find(a => a.accountNo === '934594948');
  assert(moi, 'phải có TK mới với accountNo=934594948 — got ' + JSON.stringify(updated));
  assert(moi.misaAcct === '1121', `misaAcct PHẢI đúng '1121' (mã TK con THẬT duy nhất), KHÔNG được tự đoán '1121-NG' — got '${moi.misaAcct}'`);
  console.log('PASS 1: TK mới thêm dùng ĐÚNG mã hạch toán MISA thật (1121), không tự đoán sai thành 1121-NG.');
}

// ----- Test 2: TK ĐÃ CÓ SẴN trong danh sách (đã lỡ mang misaAcct SAI do
// đoán từ trước, vd '1121-NG') -> khi đồng bộ lại, PHẢI được SỬA về đúng
// mã thật '1121' (không giữ nguyên mã sai cũ). -----
{
  const accounts = [
    { id: 'main', label: 'TK chính', currency: 'VND' },
    { id: 'acc_1', label: 'Ngân hàng TMCP Á Châu 934594948', currency: 'VND', misaAcct: '1121-NG', bankName: 'Ngân hàng TMCP Á Châu', accountNo: '934594948' },
  ];
  const dsMisa = [{ so_tk: '934594948', ten_ngan_hang: 'Ngân hàng TMCP Á Châu', inactive: false }];
  const { updated, soMoi, soCapNhat } = dongBoTaiKhoanNganHang(accounts, dsMisa, '1121', null, () => false);
  assert(soMoi === 0, `TK đã có sẵn (khớp Số TK) không được thêm mới — got soMoi=${soMoi}`);
  assert(soCapNhat === 1, `phải đếm 1 TK được cập nhật (sửa mã sai) — got soCapNhat=${soCapNhat}`);
  const acc1 = updated.find(a => a.id === 'acc_1');
  assert(acc1.misaAcct === '1121', `mã hạch toán SAI cũ '1121-NG' PHẢI được sửa lại đúng '1121' khi đồng bộ lại — got '${acc1.misaAcct}'`);
  console.log('PASS 2: TK đã có sẵn với mã hạch toán SAI (đoán từ trước) được tự sửa đúng lại thành 1121 khi đồng bộ lại.');
}

// ----- Test 3: công ty CÓ NHIỀU TK con 112x thật (tách theo ngân hàng,
// maTkVnd=null vì mơ hồ) -> KHÔNG có mã thật để dùng, phải rơi về
// suggestMisaAcct như cũ (không lỗi, không để trống). -----
{
  const accounts = [];
  const dsMisa = [{ so_tk: '11600294', ten_ngan_hang: 'Vietcombank', inactive: false }];
  const { updated, soMoi } = dongBoTaiKhoanNganHang(accounts, dsMisa, null, null, () => false);
  assert(soMoi === 1);
  const moi = updated[0];
  assert(moi.misaAcct && moi.misaAcct.startsWith('1121'), `không có mã thật (mơ hồ) thì vẫn phải rơi về suggestMisaAcct (bắt đầu '1121') — got '${moi.misaAcct}'`);
  console.log('PASS 3: không có mã hạch toán thật duy nhất (mơ hồ, nhiều TK con) -> vẫn dùng suggestMisaAcct như cũ, không lỗi.');
}

// ----- Test 4 (đúng lỗi thật thứ 2): TK "TK chính" mặc định TRỐNG (chưa
// gắn Số TK/Tên ngân hàng) PHẢI bị bỏ đi khi đã đồng bộ được TK thật từ
// MISA. -----
{
  const accounts = [{ id: 'main', label: 'TK chính', currency: 'VND' }];
  const dsMisa = [{ so_tk: '934594948', ten_ngan_hang: 'Ngân hàng TMCP Á Châu', inactive: false }];
  const { updated, soDaXoa } = dongBoTaiKhoanNganHang(accounts, dsMisa, '1121', null, () => false);
  assert(soDaXoa === 1, `phải đếm đúng 1 TK mặc định trống bị bỏ — got soDaXoa=${soDaXoa}`);
  assert(!updated.some(a => a.id === 'main'), 'TK "TK chính" mặc định trống PHẢI bị bỏ khỏi danh sách sau khi đồng bộ — got ' + JSON.stringify(updated));
  assert(updated.length === 1 && updated[0].accountNo === '934594948');
  console.log('PASS 4: TK "TK chính" mặc định trống bị bỏ đúng sau khi đồng bộ được TK thật từ MISA.');
}

// ----- Test 5: TK "TK chính" đã CÓ DỮ LIỆU SAO KÊ (coDuLieuSaoKe trả
// true) -> KHÔNG được bỏ (an toàn, tránh mất dữ liệu người dùng đã nhập)
// dù nhãn/accountNo trống giống hệt ca mặc định. -----
{
  const accounts = [{ id: 'main', label: 'TK chính', currency: 'VND' }];
  const dsMisa = [{ so_tk: '934594948', ten_ngan_hang: 'Ngân hàng TMCP Á Châu', inactive: false }];
  const { updated, soDaXoa } = dongBoTaiKhoanNganHang(accounts, dsMisa, '1121', null, a => a.id === 'main');
  assert(soDaXoa === 0, `TK có dữ liệu sao kê KHÔNG được đếm là đã xoá — got soDaXoa=${soDaXoa}`);
  assert(updated.some(a => a.id === 'main'), 'TK "TK chính" có dữ liệu sao kê PHẢI được GIỮ LẠI, không được xoá mất dữ liệu — got ' + JSON.stringify(updated));
  console.log('PASS 5: TK "TK chính" ĐÃ có dữ liệu sao kê được giữ nguyên, không bị xoá nhầm mất dữ liệu.');
}

// ----- Test 6: TK đã có tên/nhãn khác "TK chính" (người dùng tự đổi tên)
// dù rỗng accountNo/bankName -> KHÔNG bị coi là "mặc định trống", giữ
// nguyên (chỉ đúng nhãn "TK chính" y hệt mới coi là mặc định chưa dùng). -----
{
  const accounts = [{ id: 'x', label: 'Đang chờ nhập', currency: 'VND' }];
  const dsMisa = [{ so_tk: '934594948', ten_ngan_hang: 'Ngân hàng TMCP Á Châu', inactive: false }];
  const { updated, soDaXoa } = dongBoTaiKhoanNganHang(accounts, dsMisa, '1121', null, () => false);
  assert(soDaXoa === 0 && updated.some(a => a.id === 'x'), 'TK có nhãn KHÁC "TK chính" không được tự ý bỏ — got ' + JSON.stringify(updated));
  console.log('PASS 6: TK có nhãn khác "TK chính" (dù rỗng accountNo) không bị tự ý bỏ.');
}

// ----- Test 7 (đúng lỗi thật MỚI, ảnh Hệ thống tài khoản MISA có 2 mã con
// "11221"/"11222" cùng dưới "1122"): "hãy lấy số tài khoản trong misa để
// gắn chứ phần mềm không tự gắn tài khoản đúng 11221" — công ty có NHIỀU
// TK ngoại tệ dùng NHIỀU mã con 1122x KHÁC NHAU -> maTkUsd (mức công ty)
// = null (mơ hồ), nhưng mỗi dòng dsMisa nay có field "ma_hach_toan" RIÊNG
// (học từ lịch sử Thu/Chi tiền gửi thật của ĐÚNG BankAccountID, xem server.
// py) -> TK MỚI thêm PHẢI ưu tiên dùng ĐÚNG mã riêng đó, tự đặt luôn
// currency="USD" (vì mã học được là 1122x), KHÔNG rơi về suggestMisaAcct. -----
{
  const accounts = [];
  const dsMisa = [
    { so_tk: '24449247', ten_ngan_hang: 'Ngân hàng TMCP Á Châu', inactive: false, ma_hach_toan: '11221' },
    { so_tk: '362698698', ten_ngan_hang: 'Ngân hàng TMCP Á Châu', inactive: false, ma_hach_toan: '11222' },
  ];
  const { updated, soMoi } = dongBoTaiKhoanNganHang(accounts, dsMisa, null, null, () => false);
  assert(soMoi === 2, `phải thêm đúng 2 TK mới — got soMoi=${soMoi}`);
  const tk1 = updated.find(a => a.accountNo === '24449247');
  const tk2 = updated.find(a => a.accountNo === '362698698');
  assert(tk1.misaAcct === '11221' && tk1.currency === 'USD', (
    `TK '24449247' PHẢI dùng ĐÚNG mã riêng '11221' học từ lịch sử thật (KHÔNG rơi về suggestMisaAcct chung `
    + `'1122'), và tự đặt currency='USD' — got misaAcct='${tk1.misaAcct}', currency='${tk1.currency}'`));
  assert(tk2.misaAcct === '11222' && tk2.currency === 'USD', (
    `TK '362698698' PHẢI dùng ĐÚNG mã riêng '11222', KHÔNG lẫn sang '11221' của TK khác — got `
    + `misaAcct='${tk2.misaAcct}', currency='${tk2.currency}'`));
  console.log("PASS 7: TK MỚI thêm ưu tiên đúng 'ma_hach_toan' RIÊNG học từ lịch sử thật (11221/11222), không còn gắn nhầm/rơi về đoán chung, tự đặt currency=USD đúng.");
}

// ----- Test 8: TK ĐÃ CÓ SẴN (misaAcct SAI cũ, vd '1121' của VND do nhầm)
// -> khi đồng bộ lại, ma_hach_toan riêng của dòng dsMisa PHẢI ưu tiên sửa
// đúng lại, kể cả maTkVnd/maTkUsd mức công ty đều null (mơ hồ). -----
{
  const accounts = [
    { id: 'acc1', label: 'USD', currency: 'USD', misaAcct: '1121', accountNo: '24449247' },
  ];
  const dsMisa = [
    { so_tk: '24449247', ten_ngan_hang: 'Ngân hàng TMCP Á Châu', inactive: false, ma_hach_toan: '11221' },
  ];
  const { updated, soCapNhat } = dongBoTaiKhoanNganHang(accounts, dsMisa, null, null, () => false);
  assert(soCapNhat === 1, `phải đếm 1 TK được cập nhật — got soCapNhat=${soCapNhat}`);
  const acc1 = updated.find(a => a.id === 'acc1');
  assert(acc1.misaAcct === '11221', (
    `misaAcct SAI cũ '1121' PHẢI được sửa đúng lại thành '11221' (ưu tiên ma_hach_toan riêng của TK, dù `
    + `maTkVnd/maTkUsd mức công ty đều mơ hồ/null) — got '${acc1.misaAcct}'`));
  console.log("PASS 8: TK đã có sẵn với misaAcct sai cũ được ưu tiên sửa đúng theo 'ma_hach_toan' riêng học từ lịch sử thật, dù không có mã chung ở mức công ty.");
}

console.log('\nTẤT CẢ TEST PASS');
