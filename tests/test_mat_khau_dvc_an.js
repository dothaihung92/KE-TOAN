// Regression test (Node) cho yêu cầu người dùng kèm 2 ảnh chụp màn hình:
// "Mật khẩu Dịch vụ công 1; 2 hãy ẩn lại không hiện ra" — 2 ô này trước
// đây là input type="text" (hiện chữ rõ ràng, khác hẳn ô "Mật khẩu trang
// Thuế" đã ẩn bằng type="password" + nút "👁 Hiện" từ trước).
//
// Đồng thời xác nhận ô "Thư mục lưu DỮ LIỆU công ty" theo TỪNG công ty (id
// "m_datadir") đã bị BỎ khỏi form sửa/thêm công ty — dữ liệu công ty nay
// TỰ ĐỘNG nằm trong thư mục con "DU LIEU CTY" ngay trong "Thư mục lưu
// file XML/PDF" (xem test_thu_muc_du_lieu_chung.py). Nút "📂 Thư mục dữ
// liệu chung" toàn app (thử nghiệm ở bản trước) cũng đã bị BỎ theo yêu cầu
// người dùng "không cần dùng tới nữa". Và ô "TK Nợ mặc định" cũng đã bị bỏ
// theo yêu cầu người dùng "hãy bỏ dòng TK Nợ mặc định".
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

// ----- Test 3: ô "Thư mục lưu DỮ LIỆU công ty" theo TỪNG công ty (id m_datadir) đã bị bỏ khỏi modal — dữ liệu công ty nay tự động nằm cạnh Thư mục lưu file XML/PDF, không cấu hình gì thêm. -----
{
  assert(!html.includes('id="m_datadir"'), (
    'Ô "Thư mục lưu DỮ LIỆU công ty" theo TỪNG công ty (m_datadir) phải được bỏ khỏi modal Thêm/Sửa công ty '
    + '— dữ liệu công ty nay tự động nằm trong thư mục con "DU LIEU CTY" cạnh Thư mục lưu file XML/PDF.'));
  console.log('PASS 3: ô thư mục dữ liệu riêng từng công ty đã được bỏ — dữ liệu tự động nằm cạnh Thư mục lưu file XML/PDF.');
}

// ----- Test 4 (đúng yêu cầu "bỏ thư mục dữ liệu chung đi vì không cần dùng tới nữa"): nút/modal "Thư mục dữ liệu chung" toàn app đã bị bỏ hẳn. -----
{
  assert(!html.includes('moGlobalDataDirModal') && !html.includes('globalDataDirModal')
    && !html.includes('luuGlobalDataDir') && !html.includes('/api/settings/global-data-dir'), (
    'Nút/modal "📂 Thư mục dữ liệu chung" (toàn app) phải được bỏ hẳn theo yêu cầu người dùng '
    + '"bỏ thư mục dữ liệu chung đi vì không cần dùng tới nữa".'));
  console.log('PASS 4: nút/modal "Thư mục dữ liệu chung" toàn app đã được bỏ hẳn.');
}

// ----- Test 5 (đúng yêu cầu "hãy bỏ dòng TK Nợ mặc định"): ô "TK Nợ mặc định" đã bị bỏ khỏi modal Thêm/Sửa công ty. -----
{
  assert(!html.includes('id="m_no_mac_dinh"') && !html.includes('TK Nợ mặc định'), (
    'Ô "TK Nợ mặc định" phải được bỏ khỏi modal Thêm/Sửa công ty theo yêu cầu người dùng '
    + '"hãy bỏ dòng TK Nợ mặc định".'));
  console.log('PASS 5: ô "TK Nợ mặc định" đã được bỏ khỏi modal Thêm/Sửa công ty.');
}

console.log('\nTẤT CẢ TEST PASS');
