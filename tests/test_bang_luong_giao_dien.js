// Test giao diện "Bảng Lương" (Nhập Liệu -> Bảng Lương, chọn năm): chạy ĐÚNG code JS trong static/index.html với
// document/api giả lập. Yêu cầu người dùng: "làm thêm ô bảng lương và có thể chọn năm ví dụ năm 2025; 2026 để
// làm việc" + bảng theo file TỔNG HỢP (mỗi nhân viên 1 dòng / tháng).
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'index.html'), 'utf8');

// ---- 1: ô "Bảng Lương" nằm cạnh "Danh Sách Nhân Viên" trong màn Bảng Lương - BHXH ----
const iMo = html.indexOf('function moBangLuong(){');
const thanMo = html.slice(iMo, html.indexOf('function moDanhSachNhanVien', iMo));
assert(thanMo.includes('onclick="moDanhSachNhanVien()"') && thanMo.includes('onclick="moBangLuongNam()"'),
  'moBangLuong() phải có cả ô Danh Sách Nhân Viên lẫn ô Bảng Lương (gọi moBangLuongNam)');
assert(thanMo.includes('Bảng Lương</div>'), 'Ô mới phải có nhãn "Bảng Lương"');
console.log('PASS 1: ô "Bảng Lương" có cạnh ô "Danh Sách Nhân Viên".');

// ---- lấy khối JS Bảng Lương ra chạy trong sandbox ----
const b0 = html.indexOf('/* ----- BẢNG LƯƠNG (theo file TỔNG HỢP');
const b1 = html.indexOf('/* ----- KẾT NỐI MISA SME', b0);
assert(b0 > 0 && b1 > b0, 'Không tìm thấy khối JS Bảng Lương');
// `let` cấp trên cùng không thành thuộc tính của context vm -> đổi thành `var` (chỉ trong bản nạp của test) để test đọc/gán được trạng thái.
const khoiJs = html.slice(b0, b1).replace(/^let (bl\w+)/gm, 'var $1');

function taoMoiTruong(tuyChon = {}) {
  const goiApi = [], toasts = [], phanTu = {};
  const el = (id) => phanTu[id] || (phanTu[id] = { id, innerHTML: '', style: {}, dataset: {}, value: '', textContent: '',
    insertAdjacentHTML() {}, querySelector() { return null; }, querySelectorAll() { return []; } });
  const luuTru = {};
  const ctx = {
    current: 7, toast: (m, k) => toasts.push([m, k]),
    document: { getElementById: el, querySelectorAll: () => [] },
    localStorage: { getItem: (k) => luuTru[k] || null, setItem: (k, v) => { luuTru[k] = v; } },
    confirm: tuyChon.confirm || (() => true), prompt: tuyChon.prompt || (() => null),
    xkEsc: (s) => String(s == null ? '' : s).replace(/</g, '&lt;').replace(/>/g, '&gt;'),
    moBangLuong: () => { ctx.__daQuayLai = true; }, xuatFile: async () => {}, fetch: async () => ({ ok: true }),
    FormData: class { append() {} }, console,
    api: async (url, opts) => {
      goiApi.push([url, opts && opts.body ? JSON.parse(opts.body) : null]);
      return tuyChon.api ? tuyChon.api(url, opts) : {};
    },
  };
  ctx.window = ctx;
  return { ctx, goiApi, toasts, phanTu, luuTru };
}
const vm = require('vm');
function nap(tuyChon) {
  const m = taoMoiTruong(tuyChon);
  vm.createContext(m.ctx);
  vm.runInContext(khoiJs, m.ctx);
  return m;
}
const dongMau = (ma, ten, extra = {}) => Object.assign({ ma, ten, chuc_vu: '', luong_cb: 10000000, ngay_cong: 26, ngay_lam: '',
  tien_com: 730000, muc_xang: 1000000, di_lai: 0, pc_chuc_vu: 0, muc_dt: 1000000, trang_phuc: 400000, thuong_bh: 0,
  thuong_t13: 0, tang_ca: 0, so_npt: 0, ghi_chu: 'CK' }, extra);

(async () => {
  // ---- 2: định dạng số + dòng trống mặc định ----
  let m = nap();
  m.ctx.blTS = { ngay_cong_chuan: 26 };
  assert.strictEqual(m.ctx.blDinhDang(32500000), '32.500.000');
  assert.strictEqual(m.ctx.blDinhDang(26.5, true), '26,5');
  assert.strictEqual(m.ctx.blDinhDang('abc'), '');
  const trong = m.ctx.blDongTrong();
  assert(trong.ngay_cong === 0 && trong.ghi_chu === 'CK' && trong.luong_cb === 0 && trong.ngay_lam === '');
  console.log('PASS 2: định dạng số kiểu VN; dòng trống mặc định (công chuẩn 26, ghi chú CK).');

  // ---- 3: chọn NĂM — danh sách gồm các năm đã có dữ liệu + năm hiện tại ±1; nhớ năm đã chọn ----
  const namNay = new Date().getFullYear();
  m = nap({ api: (url) => ({ nam: 2025, tham_so: { ngay_cong_chuan: 26 }, thang: { '07': [dongMau('101', 'A')] }, cac_nam: [2025, 2024], cap_nhat: '' }) });
  m.ctx.blNam = 2025;
  await m.ctx.blTai();
  const opts = m.phanTu['blChonNam'].innerHTML;
  const cacNam = [...opts.matchAll(/value="(\d+)"/g)].map(x => +x[1]);
  for (const y of [2025, 2024, namNay - 1, namNay, namNay + 1]) assert(cacNam.includes(y), `Danh sách năm phải có ${y} — got ${cacNam}`);
  assert(cacNam.slice().sort((a, b) => b - a).join() === cacNam.join(), 'Năm phải sắp giảm dần');
  assert(/2025 ●/.test(opts) && !/>2026 ●/.test(opts) || namNay === 2025, 'Năm đã có dữ liệu đánh dấu ●');
  assert.strictEqual(m.luuTru['blNam'], '2025', 'Phải nhớ năm đang làm việc');
  assert(m.goiApi[0][0].includes('/api/bang-luong/7?nam=2025'));
  console.log('PASS 3: chọn năm (2025/2026...) — danh sách năm, đánh dấu năm có dữ liệu, nhớ năm đã chọn.');

  // ---- 4: đổi năm: đang có thay đổi CHƯA LƯU thì hỏi; đồng ý mới tải năm mới ----
  let hoi = 0;
  m = nap({ confirm: () => { hoi++; return false; }, api: () => ({ nam: 2026, tham_so: {}, thang: {}, cac_nam: [] }) });
  m.ctx.blNam = 2025; m.ctx.blBan = true;
  await m.ctx.blDoiNam('2026');
  assert.strictEqual(hoi, 1); assert.strictEqual(m.ctx.blNam, 2025, 'Không đồng ý -> ở lại năm cũ');
  assert.strictEqual(m.goiApi.length, 0, 'Không đồng ý -> không tải năm mới');
  m.ctx.blBan = false;
  await m.ctx.blDoiNam('2026');
  assert.strictEqual(m.ctx.blNam, 2026); assert.strictEqual(hoi, 1, 'Không có thay đổi chưa lưu thì không hỏi');
  await m.ctx.blDoiNam('1900');
  assert.strictEqual(m.ctx.blNam, 2026, 'Năm ngoài 2000-2100 bị bỏ qua');
  console.log('PASS 4: đổi năm hỏi lại khi còn thay đổi chưa lưu; năm sai bị bỏ qua.');

  // ---- 5: "➕ Năm khác": nhập năm hợp lệ -> chuyển sang; sai -> báo lỗi ----
  m = nap({ prompt: () => '2027', api: () => ({ nam: 2027, tham_so: {}, thang: {}, cac_nam: [] }) });
  m.ctx.blNam = 2026;
  await m.ctx.blNamKhac();
  assert.strictEqual(m.ctx.blNam, 2027);
  m = nap({ prompt: () => 'abc' }); m.ctx.blNam = 2026;
  await m.ctx.blNamKhac();
  assert.strictEqual(m.ctx.blNam, 2026); assert(m.toasts.some(([t, k]) => k === 'err' && /không hợp lệ/.test(t)));
  console.log('PASS 5: thêm năm khác (2027) và chặn năm không hợp lệ.');

  // ---- 6: nạp nhân viên KHÔNG tạo trùng (khớp theo mã); báo số đã thêm ----
  m = nap({ api: (url, o) => url.includes('tu-nhan-vien') ? { rows: [dongMau('101', 'A'), dongMau('102', 'B'), dongMau('', 'C')] }
    : { rows: JSON.parse(o.body).rows, tham_so: {} } });
  m.ctx.blNam = 2026; m.ctx.blThang = '09'; m.ctx.blTS = { ngay_cong_chuan: 26 };
  m.ctx.blDL = { '09': [dongMau('101', 'A cũ')] };
  await m.ctx.blNapNhanVien();
  const t9 = m.ctx.blDL['09'];
  assert.deepStrictEqual(t9.map(r => r.ma + ':' + r.ten), ['101:A cũ', '102:B', ':C'], 'Không đè dòng đã có, chỉ thêm người chưa có');
  assert(m.ctx.blBan === true);
  await m.ctx.blNapNhanVien();
  assert.strictEqual(m.ctx.blDL['09'].length, 3, 'Nạp lần 2 không thêm trùng');
  console.log('PASS 6: nạp từ Danh Sách Nhân Viên không tạo dòng trùng.');

  // ---- 7: sao chép từ tháng trước: nhảy qua tháng trống, giữ khoản cố định, đặt lại thưởng/T13/tăng ca ----
  m = nap({ api: (url, o) => ({ rows: (o && JSON.parse(o.body).rows) || [], tham_so: {} }) });
  m.ctx.blNam = 2026; m.ctx.blTS = {};
  m.ctx.blDL = { '03': [dongMau('101', 'A', { thuong_bh: 5, thuong_t13: 9, tang_ca: 7, so_npt: 2, ngay_lam: 20, tt_luong: 123 })] };
  m.ctx.blThang = '06';
  await m.ctx.blSaoChepThangTruoc();
  const r6 = m.ctx.blDL['06'][0];
  assert(r6.ma === '101' && r6.luong_cb === 10000000 && r6.so_npt === 2 && r6.muc_xang === 1000000, 'Giữ khoản cố định');
  assert(r6.thuong_bh === 0 && r6.thuong_t13 === 0 && r6.tang_ca === 0 && r6.ngay_lam === '', 'Khoản phát sinh đặt lại 0');
  assert(!('tt_luong' in r6), 'Không sao chép các cột do server tính');
  m.ctx.blThang = '02'; m.ctx.blDL = { '03': [dongMau('101', 'A')] };
  await m.ctx.blSaoChepThangTruoc();
  assert(m.toasts.some(([t, k]) => k === 'err' && /Không có tháng nào/.test(t)), 'Tháng đầu năm không có tháng trước');
  console.log('PASS 7: sao chép từ tháng trước (nhảy tháng trống, đặt lại thưởng/T13/tăng ca).');

  // ---- 8: lưu: chỉ gửi các trường NHẬP (không gửi cột tính), kèm tham số; xong hết cờ chưa lưu ----
  m = nap({ api: (url, o) => o && o.method === 'POST' ? { nam: 2025, tham_so: { ngay_cong_chuan: 26 }, thang: { '07': [dongMau('101', 'A', { tt_luong: 1 })] }, cac_nam: [2025] } : {} });
  m.ctx.blNam = 2025; m.ctx.blTS = { ngay_cong_chuan: 26, giam_tru_ban_than: 11000000 }; m.ctx.blBan = true;
  m.ctx.blDL = { '07': [dongMau('101', 'A', { tt_luong: 999, thue_tncn: 5 })], '08': [] };
  await m.ctx.blLuu();
  const [url, body] = m.goiApi.find(x => x[0].includes('/api/bang-luong/7?nam=2025'));
  assert(body.tham_so.giam_tru_ban_than === 11000000);
  assert(!('tt_luong' in body.thang['07'][0]) && !('thue_tncn' in body.thang['07'][0]), 'Không gửi cột do server tính');
  assert(body.thang['07'][0].ma === '101' && !('08' in body.thang), 'Tháng rỗng không gửi');
  assert.strictEqual(m.ctx.blBan, false);
  console.log('PASS 8: lưu chỉ gửi trường nhập + tham số, bỏ tháng rỗng, xóa cờ chưa lưu.');

  // ---- 9: sửa ô: chỉ khác định dạng hiển thị thì KHÔNG coi là thay đổi; gõ 32.500.000 thì tính lại ----
  m = nap({ api: (url, o) => { const b = JSON.parse(o.body); return { rows: b.rows.map(r => Object.assign({}, r, { luong_cb: 32500000 })), tham_so: {} }; } });
  m.ctx.blNam = 2026; m.ctx.blThang = '09'; m.ctx.blTS = {};
  m.ctx.blDL = { '09': [dongMau('101', 'A', { luong_cb: 32500000 })] };
  const td = (r, k, txt) => ({ dataset: { r: String(r), k }, textContent: txt });
  m.ctx.blSuaO(td(0, 'luong_cb', '32.500.000'));
  assert.strictEqual(m.ctx.blBan, false, 'Chỉ khác định dạng -> không đánh dấu chưa lưu');
  assert.strictEqual(m.goiApi.length, 0);
  m.ctx.blSuaO(td(0, 'luong_cb', '40.000.000'));
  assert.strictEqual(m.ctx.blBan, true);
  assert.strictEqual(m.goiApi.length, 1, 'Sửa số -> gọi server tính lại');
  assert.strictEqual(m.goiApi[0][1].rows[0].luong_cb, '40.000.000', 'Gửi nguyên chuỗi người dùng gõ, để server chuẩn hoá');
  console.log('PASS 9: sửa ô -> gửi chuỗi gõ tay cho server tính lại; không tính lại khi chỉ khác định dạng.');

  // ---- 10: vẽ bảng tháng: đủ cột như file, ô nhập có thể sửa, ô tính thì không, có dòng TỔNG CỘNG ----
  m = nap();
  m.ctx.blThang = '09';
  m.ctx.blDL = { '09': [dongMau('101', 'A', { luong: 10000000, thue_tncn: 100, kiem_tra: 100 }), dongMau('102', 'B', { luong: 5000000, thue_tncn: 50, kiem_tra: 999 })] };
  m.ctx.blVeBang();
  const bang = m.phanTu['blBangWrap'].innerHTML;
  for (const tieuDe of ['LƯƠNG', 'Họ và Tên', 'Thưởng bán hàng', 'Thưởng T13', 'Thuế TNCN', 'TT Lương (thực lãnh)', 'Chi phí lương', 'Thu nhập tính thuế', 'Giảm trừ người phụ thuộc'])
    assert(bang.toLowerCase().includes(tieuDe.toLowerCase()), 'Thiếu cột: ' + tieuDe);
  assert(/data-k="luong_cb"/.test(bang) && /data-k="thuong_bh"/.test(bang) && /data-k="so_npt"/.test(bang), 'Ô nhập sửa được');
  assert(!/data-k="thue_tncn"/.test(bang) && !/data-k="tt_luong"/.test(bang), 'Ô tính không sửa được');
  assert(/TỔNG CỘNG/.test(bang) && /15\.000\.000/.test(bang), 'Có dòng tổng (tiền lương 10tr + 5tr)');
  assert(/#fde2e2/.test(bang), 'Cột Kiểm tra lệch thuế >= 1đ phải tô đỏ');
  console.log('PASS 10: bảng tháng đủ cột theo file, ô nhập sửa được/ô tính chỉ đọc, dòng tổng, tô đỏ khi kiểm tra lệch.');

  // ---- 11: tab "Cả năm": tổng hợp theo nhân viên cộng đúng qua các tháng ----
  m = nap();
  m.ctx.blDL = { '07': [dongMau('101', 'A', { chi_phi_luong: 100, tt_luong: 80, thue_tncn: 10, bhxh_dn: 5, bhyt_dn: 1, bhtn_dn: 1, bh_duoc_tru: 4, tn_chiu_thue: 90 })],
    '08': [dongMau('101', 'A', { chi_phi_luong: 200, tt_luong: 160, thue_tncn: 20, bhxh_dn: 5, bhyt_dn: 1, bhtn_dn: 1, bh_duoc_tru: 4, tn_chiu_thue: 190 })] };
  m.ctx.blThang = 'nam'; m.ctx.blVeBang();
  const nam = m.phanTu['blBangWrap'].innerHTML;
  assert(/Tổng hợp theo nhân viên/.test(nam) && />300</.test(nam) && />240</.test(nam) && />30</.test(nam) && />280</.test(nam),
    'Tổng chi phí 300, thực lãnh 240, thuế 30, thu nhập chịu thuế 280 — got ' + nam.slice(0, 600));
  console.log('PASS 11: tab Cả năm cộng đúng theo từng nhân viên.');

  // ---- 12: tham số năm: áp dụng -> server chuẩn hoá -> tính lại mọi tháng đang có ----
  m = nap({ api: (url, o) => { const b = JSON.parse(o.body); return { rows: b.rows, tham_so: { ngay_cong_chuan: 26, giam_tru_ban_than: 15500000 } }; } });
  m.ctx.blNam = 2026; m.ctx.blThang = '09'; m.ctx.blTS = { ngay_cong_chuan: 26, giam_tru_ban_than: 11000000, he_so_tang_ca: 1.33, bh_dn: { bhxh: 17.5, bhyt: 3, bhtn: 1 }, bh_nld: { bhxh: 8, bhyt: 1.5, bhtn: 1 }, bac_thue: [[0, 5]] };
  m.ctx.blDL = { '03': [dongMau('101', 'A')], '09': [dongMau('102', 'B')] };
  m.ctx.document.getElementById('blThamSo').style.display = 'none';   // như HTML thật: khung tham số ẩn sẵn
  m.ctx.blMoThamSo();
  assert(/Tham số năm 2026/.test(m.phanTu['blThamSo'].innerHTML) && /kiểm tra và chỉnh lại cho năm 2026/.test(m.phanTu['blThamSo'].innerHTML));
  const gia = { blTsNgay: '26', blTsBt: '15500000', blTsNpt: '6200000', blTsHs: '1.33', blTsDx: '17.5', blTsDy: '3', blTsDt: '1', blTsNx: '8', blTsNy: '1.5', blTsNt: '1' };
  m.ctx.document.getElementById = (id) => (gia[id] !== undefined ? { value: gia[id] } : (m.phanTu[id] || (m.phanTu[id] = { style: {}, innerHTML: '', dataset: {} })));
  m.ctx.document.querySelectorAll = (sel) => sel.includes('blBacDong') ? [{ querySelector: (s) => ({ value: s.includes('Tu') ? '0' : '5' }) }] : [];
  await m.ctx.blApDungThamSo();
  assert.strictEqual(m.ctx.blTS.giam_tru_ban_than, 15500000, 'Dùng tham số server đã chuẩn hoá');
  assert.strictEqual(m.goiApi.filter(([u]) => u.includes('bang-luong-tinh')).length, 3, '1 lần chuẩn hoá + tính lại 2 tháng đang có dữ liệu');
  assert.strictEqual(m.ctx.blBan, true);
  console.log('PASS 12: áp dụng tham số năm -> chuẩn hoá -> tính lại các tháng, đánh dấu chưa lưu.');

  // ---- 13: ô tick "Đóng BHXH": có cột tick, dòng mới mặc định tick, bỏ tick -> lưu cờ + gọi server tính lại ----
  m = nap({ api: (url, o) => { const b = JSON.parse(o.body); return { rows: b.rows, tham_so: {} }; } });
  m.ctx.blTS = { ngay_cong_chuan: 26 };
  assert.strictEqual(m.ctx.blDongTrong().dong_bh, 1, 'Dòng mới mặc định có tick');
  m.ctx.blThang = '09'; m.ctx.blNam = 2026;
  m.ctx.blDL = { '09': [dongMau('101', 'A', { dong_bh: 1 }), dongMau('102', 'B', { dong_bh: 0 }), dongMau('103', 'C')] };
  m.ctx.blVeBang();
  const hb = m.phanTu['blBangWrap'].innerHTML;
  const tick = [...hb.matchAll(/<input type="checkbox"([^>]*)onchange="blDoiBH\((\d+),this\.checked\)"/g)];
  assert.strictEqual(tick.length, 3, 'Mỗi nhân viên 1 ô tick');
  assert(/checked/.test(tick[0][1]) && !/checked/.test(tick[1][1]) && /checked/.test(tick[2][1]), 'Tick theo dong_bh (thiếu = có tick)');
  assert(/Đóng BHXH/.test(hb), 'Có tiêu đề cột Đóng BHXH');
  m.ctx.blDoiBH(0, false);
  assert.strictEqual(m.ctx.blDL['09'][0].dong_bh, 0);
  assert.strictEqual(m.ctx.blBan, true);
  assert(m.goiApi.some(([u, b]) => u.includes('bang-luong-tinh') && b.rows[0].dong_bh === 0), 'Gửi cờ tick cho server tính lại');
  await m.ctx.blLuu(true);
  assert.strictEqual(m.goiApi[m.goiApi.length - 1][1].thang['09'][1].dong_bh, 0, 'Lưu gửi kèm dong_bh');
  console.log('PASS 13: ô tick Đóng BHXH — mặc định tick, bỏ tick -> tính lại, lưu kèm cờ.');

  // ---- 14: công chuẩn theo lịch: ô Ngày công/Tổng NC trống hiện giá trị đang dùng; gửi năm+tháng khi tính lại ----
  m = nap({ api: (url, o) => { const b = JSON.parse(o.body); return { rows: b.rows, tham_so: b.tham_so }; } });
  m.ctx.blNam = 2025; m.ctx.blThang = '01';
  m.ctx.blTS = { cong_chuan: { '01': 21, '07': 27 } };
  assert.strictEqual(m.ctx.blDongTrong().ngay_cong, 0, 'Dòng mới: ngày công 0 = theo lịch tháng');
  m.ctx.blDL = { '01': [dongMau('101', 'A', { ngay_cong: 0, ngay_lam: '', ngay_cong_hd: 21, ngay_lam_hd: 21 }),
                        dongMau('102', 'B', { ngay_cong: 24, ngay_lam: 20, ngay_cong_hd: 24, ngay_lam_hd: 20 })] };
  m.ctx.blVeBang();
  const b14 = m.phanTu['blBangWrap'].innerHTML;
  const oNgayCong = [...b14.matchAll(/data-k="ngay_cong"[^>]*>([^<]*)</g)].map(x => x[1]);
  const oTongNc = [...b14.matchAll(/data-k="ngay_lam"[^>]*>([^<]*)</g)].map(x => x[1]);
  assert.deepStrictEqual(oNgayCong, ['21', '24'], 'Hiện công chuẩn tháng khi để trống, giữ số nhập tay');
  assert.deepStrictEqual(oTongNc, ['21', '20']);
  m.ctx.blSuaO({ dataset: { r: '0', k: 'ngay_cong' }, textContent: '21' });
  assert.strictEqual(m.ctx.blBan, false, 'Gõ lại đúng số đang hiển thị -> không đổi/không tính lại');
  assert.strictEqual(m.goiApi.length, 0);
  m.ctx.blSuaO({ dataset: { r: '0', k: 'ngay_cong' }, textContent: '26' });
  assert.strictEqual(m.ctx.blBan, true);
  const goi = m.goiApi.find(([u]) => u.includes('bang-luong-tinh'))[1];
  assert.strictEqual(goi.nam, 2025); assert.strictEqual(goi.thang, '01');
  assert.strictEqual(goi.rows[0].ngay_cong, '26');
  // sao chép từ tháng trước: về "theo lịch" (ngay_cong = 0)
  m.ctx.blThang = '02'; m.ctx.blDL = { '01': [dongMau('101', 'A', { ngay_cong: 24 })] };
  await m.ctx.blSaoChepThangTruoc();
  assert.strictEqual(m.ctx.blDL['02'][0].ngay_cong, 0);
  // dòng thông tin tháng có công chuẩn
  m.ctx.blThang = '07'; m.phanTu['blInfo'] = { dataset: {}, style: {}, textContent: '' };
  m.ctx.blVeInfo();
  assert(/công chuẩn 27 ngày/.test(m.phanTu['blInfo'].textContent), m.phanTu['blInfo'].textContent);
  console.log('PASS 14: công chuẩn theo lịch — hiển thị, sửa tay, sao chép tháng, gửi năm/tháng khi tính lại.');

  // ---- 15: cột phụ cấp chỉ như Danh Sách Nhân Viên; cố định cột Mã NV + Họ tên; nạp NV cập nhật lương/phụ cấp ----
  m = nap();
  m.ctx.blThang = '09';
  m.ctx.blDL = { '09': [dongMau('101', 'A', { luong: 1, xang_xe: 500000, dien_thoai: 500000 })] };
  m.ctx.blVeBang();
  const b15 = m.phanTu['blBangWrap'].innerHTML;
  const tieuDe = [...b15.matchAll(/<th [^>]*>([^<]*)<\/th>/g)].map(x => x[1]);
  for (const c of ['Lương CB/Tháng', 'PC Tiền cơm', 'PC Xăng xe', 'PC Chức vụ', 'PC Điện thoại', 'PC Trang phục'])
    assert(tieuDe.includes(c), 'Phải có cột ' + c + ' — got ' + tieuDe.join('|'));
  for (const c of ['Mức xăng xe/tháng', 'Mức điện thoại/tháng', 'Hỗ trợ đi lại'])
    assert(!tieuDe.includes(c), 'Cột dư phải bị loại: ' + c);
  assert(!/data-k="muc_xang"/.test(b15) && !/data-k="di_lai"/.test(b15));
  // "Hỗ trợ đi lại" chỉ hiện khi dòng có giá trị (dữ liệu import cũ) — không giấu số đang tính vào thuế
  m.ctx.blDL = { '09': [dongMau('101', 'A', { di_lai: 300000 })] };
  m.ctx.blVeBang();
  assert(/data-k="di_lai"/.test(m.phanTu['blBangWrap'].innerHTML), 'Có giá trị đi lại -> vẫn hiện để không giấu số');
  // cố định 2 cột đầu
  const thMa = b15.match(/<th [^>]*>Mã NV<\/th>/)[0], thTen = b15.match(/<th [^>]*>Họ và Tên<\/th>/)[0];
  assert(/position:sticky;left:0/.test(thMa) && /position:sticky;left:60px/.test(thTen), 'Tiêu đề Mã NV/Họ tên cố định khi kéo ngang');
  assert(/data-k="ten"[^>]*position:sticky;left:60px/.test(b15) && /data-k="ma"[^>]*position:sticky;left:0/.test(b15), 'Ô dữ liệu Mã NV/Họ tên cố định');
  // nạp NV: người đã có -> cập nhật lương/phụ cấp theo danh sách; người mới -> thêm
  m = nap({ api: (url, o) => (url.includes('tu-nhan-vien')
    ? { rows: [dongMau('101', 'A', { luong_cb: 6000000, tien_com: 800000 }), dongMau('102', 'B')] }
    : { rows: JSON.parse(o.body).rows, tham_so: JSON.parse(o.body).tham_so }) });
  m.ctx.blNam = 2025; m.ctx.blThang = '09'; m.ctx.blTS = {};
  m.ctx.blDL = { '09': [dongMau('101', 'A', { luong_cb: 5310000, tien_com: 700000, thuong_bh: 123 })] };
  await m.ctx.blNapNhanVien();
  const r15 = m.ctx.blDL['09'];
  assert.strictEqual(r15.length, 2, 'Thêm người mới');
  assert.strictEqual(r15[0].luong_cb, 6000000); assert.strictEqual(r15[0].tien_com, 800000);
  assert.strictEqual(r15[0].thuong_bh, 123, 'Không đụng các khoản nhập riêng từng tháng');
  assert(/thêm 1 nhân viên, cập nhật lương\/phụ cấp .* 1 người/.test(m.toasts[m.toasts.length - 1][0]), m.toasts.join('|'));
  console.log('PASS 15: cột phụ cấp như Danh Sách Nhân Viên, cố định Mã NV + Họ tên, nạp NV cập nhật lương/phụ cấp.');

  console.log('\nALL DONE');
})().catch((e) => { console.error(e); process.exit(1); });
