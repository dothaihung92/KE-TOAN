// Regression test (Node) cho yêu cầu người dùng kèm 2 ảnh chụp màn hình:
// "Mật khẩu Dịch vụ công 1; 2 hãy ẩn lại không hiện ra" — 2 ô này trước
// đây là input type="text" (hiện chữ rõ ràng, khác hẳn ô "Mật khẩu trang
// Thuế" đã ẩn bằng type="password" + nút "👁 Hiện" từ trước).
//
// Đồng thời xác nhận ô "Thư mục lưu DỮ LIỆU công ty" (per-công ty, id
// "m_datadir") đã bị BỎ khỏi form sửa/thêm công ty — nay dùng CHUNG 1 thư
// mục cho tất cả công ty (xem test_thu_muc_du_lieu_chung.py), không còn
// cài đặt riêng từng công ty ở modal này nữa.
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'index.html'), 'utf8');

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

// ----- Test 1: input Mật khẩu Dịch vụ công 1/2 phải là type="password". -----
{
  const m1 = html.match(/<input id="m_dvc1"[^>]*>/);
  const m2 = html.match(/<input id="m_dvc2"[^>]*>/);
  assert(m1, 'Không tìm thấy input #m_dvc1 trong static/index.html');
  assert(m2, 'Không tìm thấy input #m_dvc2 trong static/index.html');
  assert(/type="password"/.test(m1[0]), `#m_dvc1 phải là type="password" (ẩn mật khẩu) — got: ${m1[0]}`);
  assert(/type="password"/.test(m2[0]), `#m_dvc2 phải là type="password" (ẩn mật khẩu) — got: ${m2[0]}`);
  console.log('PASS 1: Mật khẩu Dịch vụ công 1/2 đã là type="password" (ẩn), đúng yêu cầu "hãy ẩn lại không hiện ra".');
}

// ----- Test 2: phải có nút "👁 Hiện" riêng cho từng ô (giống ô Mật khẩu trang Thuế) để vẫn xem lại được khi cần. -----
{
  assert(html.includes('toggleDvc1Pass()') && html.includes('function toggleDvc1Pass()'),
    'Phải có hàm toggleDvc1Pass() cho nút "👁 Hiện" của Mật khẩu Dịch vụ công 1');
  assert(html.includes('toggleDvc2Pass()') && html.includes('function toggleDvc2Pass()'),
    'Phải có hàm toggleDvc2Pass() cho nút "👁 Hiện" của Mật khẩu Dịch vụ công 2');
  console.log('PASS 2: có nút "👁 Hiện" riêng cho cả 2 ô mật khẩu Dịch vụ công (vẫn xem lại được khi cần, không chỉ ẩn cứng).');
}

// ----- Test 3: ô "Thư mục lưu DỮ LIỆU công ty" theo TỪNG công ty (id m_datadir) đã bị bỏ khỏi modal -- nay dùng thư mục CHUNG. -----
{
  assert(!html.includes('id="m_datadir"'), (
    'Ô "Thư mục lưu DỮ LIỆU công ty" theo TỪNG công ty (m_datadir) phải được bỏ khỏi modal Thêm/Sửa công ty '
    + '— nay đã gộp thành 1 thư mục CHUNG cho tất cả công ty (nút "📂 Thư mục dữ liệu chung").'));
  assert(html.includes('moGlobalDataDirModal()'), 'Phải có nút mở modal Thư mục dữ liệu chung (moGlobalDataDirModal)');
  assert(html.includes("api('/api/settings/global-data-dir')"), 'Phải gọi đúng API GET thư mục dữ liệu chung khi mở modal');
  console.log('PASS 3: ô thư mục dữ liệu riêng từng công ty đã được thay bằng 1 thư mục CHUNG duy nhất cho tất cả công ty.');
}

console.log('\nTẤT CẢ TEST PASS');
