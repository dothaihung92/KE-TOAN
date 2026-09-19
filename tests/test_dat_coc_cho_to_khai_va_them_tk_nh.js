// Regression test (Node) cho static/doi_chieu_ngan_hang.html (Kế Toán AI) — 3 yêu cầu tiếp theo:
//
// 1) "thêm nút đặt cọc chờ tờ khai": khi GD ngân hàng là khoản đặt cọc trả/thu TRƯỚC KHI có tờ khai
//    hải quan (VD đặt cọc cho NCC nước ngoài), người dùng cần hạch toán công nợ + mã KH/NCC NGAY (để
//    import MISA trừ công nợ trước), đồng thời tự động tạo 1 dòng tờ khai "placeholder" đã gắn sẵn
//    giao dịch này — sau này có tờ khai thật chỉ cần sửa lại đúng dòng đó (không mất liên kết).
// 2) "nút hiển thị số lệnh còn treo đặt cọc": đếm số dòng tờ khai placeholder (chưa có Số tờ khai
//    nhưng đã gắn giao dịch) còn treo, và TỰ ĐỘNG hết đếm ngay khi dòng đó được bổ sung Số tờ khai
//    thật (không cần code "gỡ" riêng — chỉ cần đếm lại đúng điều kiện mỗi lần).
// 3) "+ Thêm tài khoản Ngân Hàng" ngay tại màn Xác nhận kết quả — trước đây phải quay lại Bước 1.
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'doi_chieu_ngan_hang.html'), 'utf8');

function assert(cond, msg) {
  if (!cond) throw new Error('THẤT BẠI: ' + msg);
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

// ===== Phần 1 (QUAN TRỌNG — đúng yêu cầu): datCocChoToKhai() phải hạch toán công nợ + mã đối tượng
// NGAY trên dòng GD, VÀ tự tạo tờ khai placeholder đã gắn sẵn payment. =====
const datCocSrc = braceBlockOf('const datCocChoToKhai = (kind, rowId, mst, name, hach) => {');
assert(/toKhaiSo:\s*""/.test(datCocSrc.src),
  'Tờ khai tự tạo phải để trống Số tờ khai (toKhaiSo: "") — đây chính là dấu hiệu nhận biết "placeholder chưa có tờ khai thật".');
assert(/ghiChu:\s*"Đặt cọc — chờ tờ khai"/.test(datCocSrc.src),
  'Phải ghi chú rõ "Đặt cọc — chờ tờ khai" trên tờ khai tự tạo để người dùng không nhầm là tờ khai thật.');
assert(/maDoiTuong:\s*\(mst \|\| ""\)\.trim\(\)/.test(datCocSrc.src) && /nhaCungCap:\s*\(name \|\| ""\)\.trim\(\)/.test(datCocSrc.src),
  'Phải điền mã đối tượng (maDoiTuong) và tên (nhaCungCap) ngay từ khi tạo — đây là ĐÚNG YÊU CẦU "hạch ' +
  'toán công nợ và mã khách hàng để import vào misa trước".');
assert(/payments:\s*\[\{\s*rowId,\s*accountId:\s*activeTabAccId/.test(datCocSrc.src),
  'Tờ khai tự tạo phải gắn sẵn payment (rowId + accountId) của đúng giao dịch ngân hàng vừa đặt cọc.');
assert(/saveTokhaiListOf\(kind\)\(\[\.\.\.tokhaiListOf\(kind\), tkWithPayment\]\)/.test(datCocSrc.src),
  'Phải lưu tờ khai placeholder (đã gắn payment) vào đúng danh sách theo kind (NK/XK) TRONG 1 lần lưu ' +
  '— tránh race giữa "tạo tờ khai" và "gắn payment" là 2 thao tác tách rời.');
assert(/confirmed:\s*"yes"/.test(datCocSrc.src) &&
       /confirmedMST:\s*newTk\.maDoiTuong \|\| r\.confirmedMST/.test(datCocSrc.src) &&
       /confirmedHach:\s*hach \|\| r\.confirmedHach \|\| defaultHachOf\(kind\)/.test(datCocSrc.src),
  'Dòng giao dịch ngân hàng phải được XÁC NHẬN NGAY với đúng hạch toán (131/331) + MST đối tượng — để ' +
  'import UNT/UNC vào MISA trừ công nợ trước, đúng yêu cầu "hạch toán công nợ và mã khách hàng... trước".');
console.log('PASS 1: datCocChoToKhai() hạch toán công nợ + mã đối tượng ngay, và tự tạo tờ khai placeholder gắn sẵn giao dịch.');

// ===== Phần 2 (không hồi quy — nơi gọi phải nối dây đủ): ConfirmRow phải nhận onDatCocChoToKhai và
// có 2 nút gọi submitDatCoc("NK")/submitDatCoc("XK") dùng ĐÚNG MST/Tên/Hạch toán đang gõ trong form. =====
assert(/onDatCocChoToKhai: datCocChoToKhai,/.test(html),
  'Nơi tạo từng ConfirmRow phải truyền onDatCocChoToKhai: datCocChoToKhai.');
const confirmRowSig = html.slice(html.indexOf('function ConfirmRow({'), html.indexOf('function ConfirmRow({') + 500);
assert(/\bonDatCocChoToKhai\b/.test(confirmRowSig), 'ConfirmRow phải nhận thêm prop onDatCocChoToKhai.');
const submitDatCocSrc = braceBlockOf('const submitDatCoc = kind => {');
assert(/onDatCocChoToKhai\(kind, r\.id, editMST, editName, editHach\)/.test(submitDatCocSrc.src),
  'submitDatCoc() phải gọi onDatCocChoToKhai với đúng MST/Tên/Hạch toán người dùng vừa gõ trong form ' +
  '"Nhập khác" — tái dùng ĐÚNG dữ liệu đã nhập, không bắt gõ lại ở chỗ khác.');
assert(/onClick: \(\) => submitDatCoc\("NK"\)/.test(html) && /onClick: \(\) => submitDatCoc\("XK"\)/.test(html),
  'Phải có đủ 2 nút gọi submitDatCoc cho CẢ "NK" và "XK" — thiếu 1 bên thì tính năng chỉ dùng được cho ' +
  '1 chiều hàng hoá (chỉ nhập HOẶC chỉ xuất).');
console.log('PASS 2: ConfirmRow có 2 nút "Đặt cọc chờ tờ khai NK/XK" dùng đúng dữ liệu đang gõ trong form.');

// ===== Phần 3 (đúng ca thật, "nút hiển thị số lệnh còn treo đặt cọc"): đếm đúng điều kiện placeholder
// còn treo cho CẢ NK và XK, và hiện thành nút riêng bên cạnh nút "Tờ Khai NK/XK". =====
assert(/const pendingDepositNK = tokhaiList\.filter\(t => !t\.toKhaiSo && tkPayments\(t\)\.length > 0\)\.length;/.test(html),
  'Phải đếm đúng số tờ khai NK placeholder còn treo (chưa có Số tờ khai NHƯNG đã gắn giao dịch).');
assert(/const pendingDepositXK = tokhaiXKList\.filter\(t => !t\.toKhaiSo && tkPayments\(t\)\.length > 0\)\.length;/.test(html),
  'Phải đếm đúng số tờ khai XK placeholder còn treo.');
assert(/pendingDepositNK > 0 &&[\s\S]{0,600}Đặt cọc NK chờ: " \+ pendingDepositNK/.test(html),
  'Phải hiện nút riêng "Đặt cọc NK chờ: N" khi còn ≥1 lệnh treo.');
assert(/pendingDepositXK > 0 &&[\s\S]{0,600}Đặt cọc XK chờ: " \+ pendingDepositXK/.test(html),
  'Phải hiện nút riêng "Đặt cọc XK chờ: N" khi còn ≥1 lệnh treo.');
console.log('PASS 3: có nút riêng hiện đúng số lệnh đặt cọc NK/XK còn treo tờ khai.');

// ===== Phần 4 (đúng ca thật, "auto hết hiện khi đã gắn tờ khai rồi"): điều kiện đếm dùng !t.toKhaiSo
// — kiểm tra logic thuần bằng dữ liệu giả lập để chắc chắn không lệ thuộc React/DOM. =====
function demPendingDeposit(list) {
  const tkPaymentsLite = tk => (tk.payments || []);
  return list.filter(t => !t.toKhaiSo && tkPaymentsLite(t).length > 0).length;
}
const dsGiaLap = [
  { id: 1, toKhaiSo: "", payments: [{ rowId: "r1" }] },      // đang treo
  { id: 2, toKhaiSo: "12345/NK/2026", payments: [{ rowId: "r2" }] }, // đã có tờ khai thật -> KHÔNG tính
  { id: 3, toKhaiSo: "", payments: [] },                       // chưa gắn GD nào -> KHÔNG tính (không phải placeholder đặt cọc)
];
assert(demPendingDeposit(dsGiaLap) === 1,
  'Chỉ đếm đúng 1 dòng (id=1): chưa có Số tờ khai NHƯNG đã gắn giao dịch. Dòng id=2 đã có tờ khai thật ' +
  '(dù còn payments) không được tính — đúng hành vi "tự động không còn hiện khi đã gắn vào tờ khai". ' +
  'Dòng id=3 không có payments cũng không tính vì không phải khoản đặt cọc thật.');
console.log('PASS 4: điều kiện đếm tự động rụng khỏi danh sách ngay khi tờ khai được bổ sung Số tờ khai thật.');

// ===== Phần 5 (QUAN TRỌNG — đúng yêu cầu "thêm nút thêm tài khoản Ngân Hàng"): ConfirmScreen phải có
// sẵn nút + form thêm tài khoản NGAY TẠI màn hình, không cần quay lại Bước 1. =====
const addAccSrc = braceBlockOf('const addAccountInline = () => {');
assert(/saveCoAccounts\(co\.id, \[\.\.\.allAccounts, newAcc\]\)/.test(addAccSrc.src),
  'addAccountInline() phải gọi saveCoAccounts với danh sách tài khoản đã thêm mới — lưu trực tiếp, ' +
  'không cần rời màn hình Xác nhận kết quả.');
assert(/switchTab\(newAcc\.id\)/.test(addAccSrc.src),
  'Sau khi thêm, phải tự chuyển sang tab tài khoản MỚI luôn để người dùng dán sao kê tiếp ngay — đúng ' +
  'yêu cầu "tiếp tục làm dữ liệu không cần phải quay ra bên ngoài".');
assert(/🏦 \+ Thêm TK NH/.test(html) || /"🏦 \+ Th\\u00eam TK NH"/.test(html),
  'Phải có nút "🏦 + Thêm TK NH" hiện trên thanh công cụ của màn Xác nhận kết quả.');
assert(/onClick:\(\)=>setAddAccMode\(m=>!m\)/.test(html),
  'Nút thêm TK NH phải bật/tắt được form thêm tài khoản (addAccMode) ngay tại chỗ.');
console.log('PASS 5: có nút "+ Thêm TK NH" ngay tại màn Xác nhận kết quả, thêm xong tự chuyển sang tab mới.');

console.log('\nALL DONE');
