// Regression test (Node) cho 2 yêu cầu người dùng gửi cùng lúc:
//   1) "Đồng thời hãy bỏ nhập từ file tờ khai đã nộp đi" — bỏ hẳn tính
//      năng "📄 Nhập từ file tờ khai đã nộp (XML)" (nút, input file ẩn,
//      hint, hàm nhapTuFileTKhai()) khỏi modal Thêm/Sửa công ty.
//   2) "Tên đăng nhập trang Thuế (thường là MST) hãy tự điền MST khi tra
//      cứu luôn" — ô "Tên đăng nhập trang Thuế" (#m_user) phải tự điền
//      bằng MST ngay khi bấm "🔍 Tự động điền"/tự động tra cứu (rời ô
//      MST), giống cách các ô Tên/Địa chỉ/Tên người ký đã tự điền — chỉ
//      điền khi ô đang TRỐNG (không ghi đè giá trị người dùng đã tự gõ),
//      và không phụ thuộc việc API tra cứu công ty có thành công hay
//      không (MST đã có sẵn ngay từ đầu, không cần đợi kết quả API).
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'index.html'), 'utf8');

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

// ----- Test 1: tính năng "Nhập từ file tờ khai đã nộp (XML)" đã bị bỏ hẳn. -----
{
  assert(!html.includes('nhapTuFileTKhai'),
    'Hàm nhapTuFileTKhai() phải được bỏ hẳn — theo yêu cầu "bỏ nhập từ file tờ khai đã nộp đi".');
  assert(!html.includes('m_tkhai_file'),
    'Input file ẩn #m_tkhai_file phải được bỏ khỏi modal Thêm/Sửa công ty.');
  assert(!html.includes('nhapTkhaiBtn') && !html.includes('Nhập từ file tờ khai đã nộp'),
    'Nút "📄 Nhập từ file tờ khai đã nộp (XML)" phải được bỏ khỏi modal Thêm/Sửa công ty.');
  assert(!html.includes('/api/import-tkhai-xml'),
    'Frontend không được gọi tới /api/import-tkhai-xml nữa (endpoint đã bị bỏ).');
  console.log('PASS 1: tính năng "Nhập từ file tờ khai đã nộp (XML)" đã được bỏ hẳn (nút/input/hint/hàm JS).');
}

// ----- Test 2: hàm traCuuDoanhNghiep() phải tự điền #m_user bằng MST khi ô đang trống. -----
{
  const m = html.match(/async function traCuuDoanhNghiep\(silent\)\{[\s\S]*?\n\}/);
  assert(m, 'Không tìm thấy hàm traCuuDoanhNghiep(silent) trong static/index.html');
  const than = m[0];
  assert(/m_user/.test(than),
    'Hàm traCuuDoanhNghiep() phải có thao tác với ô #m_user (tự điền MST) — theo yêu cầu người dùng.');
  // CHỈ điền khi ô đang trống — không ghi đè giá trị người dùng đã tự gõ,
  // đúng quy ước "chỉ điền ô trống" đã dùng cho Tên/Địa chỉ/Tên người ký.
  assert(/if\s*\(\s*!\s*(?:userEl|document\.getElementById\(['"]m_user['"]\))\.value\.trim\(\)\s*\)[\s\S]{0,40}=\s*mst/.test(than),
    `Phải CHỈ điền #m_user bằng biến mst khi ô đang trống (không ghi đè) — thân hàm: ${than}`);
  // Không phụ thuộc kết quả API (đặt TRƯỚC dòng "await api(" gọi tra cứu, không nằm trong khối xử lý info.*).
  const idxUser = than.search(/m_user/);
  const idxAwaitApi = than.indexOf('await api(');
  assert(idxUser !== -1 && idxAwaitApi !== -1 && idxUser < idxAwaitApi,
    'Việc tự điền #m_user bằng MST KHÔNG được phụ thuộc kết quả API tra cứu công ty — phải thực hiện '
    + 'trước khi gọi API (MST đã có sẵn, không cần đợi tra cứu công ty thành công).');
  console.log('PASS 2: traCuuDoanhNghiep() tự điền #m_user (Tên đăng nhập trang Thuế) bằng MST khi ô đang '
    + 'trống, thực hiện ngay khi tra cứu (không đợi/không phụ thuộc kết quả API).');
}

console.log('\nTẤT CẢ TEST PASS');
