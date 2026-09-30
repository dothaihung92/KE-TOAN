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
  m.ctx.blDL = { '09': [dongMau('101', 'A', { di_lai: 300000, tt_di_lai: 300000 })] };
  m.ctx.blVeBang();
  assert(/>Hỗ trợ đi lại</.test(m.phanTu['blBangWrap'].innerHTML), 'Có giá trị đi lại -> vẫn hiện để không giấu số');
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
  assert(/thêm 1 nhân viên, cập nhật lương\/phụ cấp\/đóng BHXH .* 1 người/.test(m.toasts[m.toasts.length - 1][0]), m.toasts.join('|'));
  console.log('PASS 15: cột phụ cấp như Danh Sách Nhân Viên, cố định Mã NV + Họ tên, nạp NV cập nhật lương/phụ cấp.');

  // ---- 16: thuế TNCN thay đổi giữa năm (từ 7/2026): khung tham số có mục riêng, áp dụng gửi đúng, dòng thông tin báo ----
  const moi = { tu_thang: 7, giam_tru_ban_than: 15500000, giam_tru_npt: 6200000, bac_thue: [[0, 5], [10000000, 10], [30000000, 20], [60000000, 30], [100000000, 35]] };
  m = nap({ api: (url, o) => { const b = JSON.parse(o.body); return { rows: b.rows, tham_so: b.tham_so }; } });
  m.ctx.blNam = 2026; m.ctx.blThang = '08';
  m.ctx.blTS = { ngay_cong_chuan: 26, giam_tru_ban_than: 11000000, giam_tru_npt: 4400000, he_so_tang_ca: 1.33, bh_dn: { bhxh: 17.5, bhyt: 3, bhtn: 1 }, bh_nld: { bhxh: 8, bhyt: 1.5, bhtn: 1 }, bac_thue: [[0, 5]], thue_moi: moi };
  m.ctx.document.getElementById('blThamSo').style.display = 'none';
  m.ctx.blMoThamSo();
  const ph = m.phanTu['blThamSo'].innerHTML;
  assert(/Thuế TNCN thay đổi giữa năm/.test(ph) && /id="blMoiBat" checked/.test(ph) && /15\.500\.000/.test(ph) && /6\.200\.000/.test(ph), 'Có mục thuế thay đổi giữa năm, đã tick sẵn với bộ mới');
  assert((ph.match(/class="blBacDong"/g) || []).length === 1 + 5, 'Bậc thuế cũ (1) + bộ mới 5 bậc');
  m.phanTu['blInfo'] = { dataset: {}, style: {}, textContent: '' }; m.ctx.blVeInfo();
  assert(/thuế TNCN theo quy định mới \(từ tháng 7: giảm trừ 15\.500\.000\/6\.200\.000, 5 bậc\)/.test(m.phanTu['blInfo'].textContent), m.phanTu['blInfo'].textContent);
  m.ctx.blThang = '05'; m.ctx.blVeInfo();
  assert(!/quy định mới/.test(m.phanTu['blInfo'].textContent), 'Tháng trước 7 không báo thuế mới');
  // áp dụng: tick bật -> gửi thue_moi; bỏ tick -> gửi null
  const gia2 = { blTsBt: '11000000', blTsNpt: '4400000', blTsHs: '1.33', blTsDx: '17.5', blTsDy: '3', blTsDt: '1', blTsNx: '8', blTsNy: '1.5', blTsNt: '1',
    blMoiTu: '7', blMoiBt: '15500000', blMoiNpt: '6200000' };
  let bat = true;
  m.ctx.document.getElementById = (id) => (id === 'blMoiBat' ? { checked: bat } : gia2[id] !== undefined ? { value: gia2[id] } : (m.phanTu[id] || (m.phanTu[id] = { style: {}, innerHTML: '', dataset: {} })));
  m.ctx.document.querySelectorAll = (sel) => sel.includes('blBacMoi') ? [{ querySelector: (q) => ({ value: q.includes('Tu') ? '0' : '5' }) }]
    : sel.includes('blBacDong') ? [{ querySelector: (q) => ({ value: q.includes('Tu') ? '0' : '5' }) }] : [];
  await m.ctx.blApDungThamSo();
  const g1 = m.goiApi.find(([u]) => u.includes('bang-luong-tinh'))[1];
  assert.deepStrictEqual(JSON.parse(JSON.stringify(g1.tham_so.thue_moi)), { tu_thang: '7', giam_tru_ban_than: '15500000', giam_tru_npt: '6200000', bac_thue: [['0', '5']] });
  bat = false; m.goiApi.length = 0;
  await m.ctx.blApDungThamSo();
  assert.strictEqual(m.goiApi.find(([u]) => u.includes('bang-luong-tinh'))[1].tham_so.thue_moi, null, 'Bỏ tick -> không đổi giữa năm');
  console.log('PASS 16: mục thuế TNCN thay đổi giữa năm (từ 7/2026) trong tham số năm + dòng thông tin theo tháng.');

  // ---- 17: bấm tên người lao động -> chuyển sang Danh Sách Nhân Viên, viền ĐỎ dòng của người đó; có nút quay lại ----
  m = nap();
  let moNv = [];
  m.ctx.moDanhSachNhanVien = (giu) => moNv.push(giu);
  m.ctx.blNam = 2026; m.ctx.blThang = '02'; m.ctx.blTS = {};
  m.ctx.blDL = { '02': [dongMau('101', 'Trần A'), dongMau('', 'Lê C'), dongMau('', '')] };
  m.ctx.blVeBang();
  const tdTen = m.phanTu['blBangWrap'].innerHTML.match(/<td [^>]*data-k="ten"[^>]*>/g);
  assert(/onclick="blMoNvCuaNguoi\(0\)"/.test(tdTen[0]) && !/contenteditable/.test(tdTen[0]), 'Dòng có người: ô tên bấm được -> mở Danh Sách Nhân Viên');
  assert(/onclick="blMoNvCuaNguoi\(1\)"/.test(tdTen[1]), 'Dòng chỉ có tên (không mã) vẫn bấm được');
  assert(/contenteditable/.test(tdTen[2]) && !/blMoNvCuaNguoi/.test(tdTen[2]), 'Dòng trống (thêm tay): ô tên gõ được');
  await m.ctx.blMoNvCuaNguoi(0);
  assert.deepStrictEqual(moNv, [true], 'Chuyển sang màn Danh Sách Nhân Viên');
  assert.deepStrictEqual(JSON.parse(JSON.stringify(m.ctx.nvTuBl)), { thang: '02', ma: '101', ten: 'Trần A' });
  // có thay đổi chưa lưu: hỏi, OK -> lưu rồi chuyển; Hủy -> ở lại
  m = nap({ confirm: () => false, api: async () => ({}) });
  moNv = []; m.ctx.moDanhSachNhanVien = (g) => moNv.push(g);
  m.ctx.blNam = 2026; m.ctx.blThang = '02'; m.ctx.blDL = { '02': [dongMau('101', 'Trần A')] }; m.ctx.blBan = true;
  await m.ctx.blMoNvCuaNguoi(0);
  assert.strictEqual(moNv.length, 0, 'Hủy -> ở lại Bảng Lương, không mất dữ liệu'); assert.strictEqual(m.goiApi.length, 0);
  m = nap({ confirm: () => true, api: async (u, o) => ({ tham_so: {}, thang: JSON.parse(o.body).thang, cac_nam: [2026] }) });
  moNv = []; m.ctx.moDanhSachNhanVien = (g) => moNv.push(g);
  m.ctx.blNam = 2026; m.ctx.blThang = '02'; m.ctx.blDL = { '02': [dongMau('101', 'Trần A')] }; m.ctx.blBan = true;
  await m.ctx.blMoNvCuaNguoi(0);
  assert.strictEqual(moNv.length, 1); assert(m.goiApi.some(([u]) => u.includes('/api/bang-luong/7?nam=2026')), 'OK -> lưu bảng lương trước khi chuyển');

  // --- phía Danh Sách Nhân Viên: chạy ĐÚNG code veGridNhanVien trong index.html ---
  const n0 = html.indexOf('const NV_COT_TICK='), n1 = html.indexOf('function nvSuaO(', n0);
  const nvJs = html.slice(n0, n1);
  const nvEnv = { nvHeader: ['STT', 'Mã NV', 'Họ và tên', 'Lương Cơ bản'], nvFilters: {}, nvChon: null, nvEsc: (x) => String(x), nvTuBl: null,
    nvRows: [[1, '101', 'Trần A', 5000000], [2, '102', 'Nguyễn B', 6000000], [3, '', 'Lê C', 4000000]],
    nvRowsLoc: () => [0, 1, 2], console };
  const nvEls = { nvTableWrap: { innerHTML: '' }, nvTuBl: { innerHTML: '' } };
  nvEnv.document = { getElementById: (id) => nvEls[id], querySelector: () => ({ scrollIntoView() { nvEnv.__cuon = (nvEnv.__cuon || 0) + 1; } }) };
  nvEnv.moBangLuongNam = (t) => { nvEnv.__ve = t; };
  vm.createContext(nvEnv);
  vm.runInContext(nvJs + '\nvar nvSuaOCuoi;', nvEnv);
  vm.runInContext('nvTuBl=null;veGridNhanVien()', nvEnv);
  assert(!/d00000/.test(nvEls.nvTableWrap.innerHTML) && nvEls.nvTuBl.innerHTML === '', 'Mở từ menu thường: không viền đỏ');
  vm.runInContext("nvTuBl={thang:'02',ma:'102',ten:'Nguyễn B'};veGridNhanVien()", nvEnv);
  const tr = nvEls.nvTableWrap.innerHTML.split('<tr').filter((x) => /data-r=/.test(x));
  assert(!/d00000/.test(tr[0]) && /data-nvsel="1"/.test(tr[1]) && /inset 0 2px 0 #d00000/.test(tr[1]) && !/d00000/.test(tr[2]), 'Chỉ dòng của Nguyễn B (Mã 102) viền đỏ');
  assert(/Người lao động đang chọn: <b>Nguyễn B<\/b>/.test(nvEls.nvTuBl.innerHTML) && /Quay lại Bảng Lương \(tháng 2\)/.test(nvEls.nvTuBl.innerHTML));
  assert.strictEqual(nvEnv.__cuon, 1, 'Tự cuộn tới dòng được chọn');
  vm.runInContext('veGridNhanVien()', nvEnv);
  assert.strictEqual(nvEnv.__cuon, 1, 'Lọc/vẽ lại không cuộn lại');
  // không có mã -> khớp theo tên; không thấy -> báo
  vm.runInContext("nvTuBl={thang:'02',ma:'',ten:'Lê C'};veGridNhanVien()", nvEnv);
  assert(/data-nvsel="1"/.test(nvEls.nvTableWrap.innerHTML.split('<tr').filter((x) => /data-r=/.test(x))[2]));
  vm.runInContext("nvTuBl={thang:'02',ma:'999',ten:'Không có'};veGridNhanVien()", nvEnv);
  assert(!/data-nvsel/.test(nvEls.nvTableWrap.innerHTML) && /Không thấy <b>Không có<\/b>/.test(nvEls.nvTuBl.innerHTML));
  vm.runInContext('nvVeBangLuong()', nvEnv);
  assert.strictEqual(nvEnv.__ve, '02'); assert.strictEqual(vm.runInContext('nvTuBl', nvEnv), null);
  console.log('PASS 17: bấm tên -> mở Danh Sách Nhân Viên, viền đỏ dòng người đó (theo mã, không có mã theo tên), nút quay lại đúng tháng.');

  // ---- 18: mọi phụ cấp tính theo ngày đi làm: cột PC là số đã tính (chỉ đọc); nút "Mức phụ cấp" hiện cột MỨC để sửa ----
  m = nap();
  m.ctx.blThang = '09'; m.ctx.blNam = 2026; m.ctx.blTS = {};
  m.ctx.blDL = { '09': [dongMau('101', 'A', { ngay_lam: 13, tt_tien_com: 365000, xang_xe: 500000, tt_pc_chuc_vu: 250000, dien_thoai: 500000, tt_trang_phuc: 200000 })] };
  m.ctx.blVeBang();
  let b18 = m.phanTu['blBangWrap'].innerHTML;
  for (const k of ['tt_tien_com', 'tt_pc_chuc_vu', 'tt_trang_phuc']) assert(b18.includes('>' + ({ tt_tien_com: 'PC Tiền cơm', tt_pc_chuc_vu: 'PC Chức vụ', tt_trang_phuc: 'PC Trang phục' })[k] + '<'), 'Cột PC đã tính: ' + k);
  assert(!/data-k="tien_com"/.test(b18) && !/data-k="pc_chuc_vu"/.test(b18) && !/data-k="trang_phuc"/.test(b18), 'Mặc định ẩn cột mức');
  assert(/365\.000/.test(b18) && /250\.000/.test(b18) && /200\.000/.test(b18), 'Hiện số phụ cấp đã tính theo ngày làm');
  m.ctx.blDoiHienMuc();
  b18 = m.phanTu['blBangWrap'].innerHTML;
  for (const k of ['tien_com', 'muc_xang', 'di_lai', 'pc_chuc_vu', 'muc_dt', 'trang_phuc']) assert(new RegExp('data-k="' + k + '"').test(b18), 'Bấm nút -> hiện cột mức ' + k);
  assert(!/data-k="tt_tien_com"/.test(b18), 'Cột đã tính vẫn chỉ đọc');
  m.ctx.blDoiHienMuc();
  assert(!/data-k="tien_com"/.test(m.phanTu['blBangWrap'].innerHTML), 'Bấm lần nữa -> ẩn lại');
  console.log('PASS 18: phụ cấp theo ngày đi làm — cột PC đã tính (chỉ đọc), nút "✎ Mức phụ cấp" hiện/ẩn cột mức.');

  // ---- 19: nút "Chi phí lương cả năm": nhập khoảng tháng + tổng -> gọi server -> xem trước -> áp dụng vào bảng ----
  const khKq = { thang: { '10': [dongMau('2', 'NV2', { ngay_lam_hd: 27, dong_bh: 1, thuong_bh: 200000, tang_ca: 200000, chi_phi_luong: 8333333, thue_tncn: 0 })],
                          '11': [dongMau('2', 'NV2', { ngay_lam_hd: 13, dong_bh: 0, thoi_vu: true, chi_phi_luong: 4000000, thue_tncn: 300000 })] },
    tom_tat: { so_nguoi: 2, day_du: 1, thoi_vu: 1, so_thang: 2, tong_chi_phi: 12333333, muc_tieu: 12333333, da_co_ngoai: 0, can_them: 12333333,
      tong_thuong_bh: 200000, tong_tang_ca: 200000, tong_thue: 300000, canh_bao: ['Tháng 11: thử cảnh báo'] } };
  m = nap({ api: async (url, o) => (url.includes('ke-hoach') ? khKq : { rows: JSON.parse(o.body).rows, tham_so: {} }) });
  m.ctx.blNam = 2025; m.ctx.blThang = '01'; m.ctx.blTS = {};
  m.ctx.blDL = { '03': [dongMau('9', 'Có sẵn', { chi_phi_luong: 1000000 })] };
  const khGia = { blKhTu: '10', blKhDen: '11', blKhTien: '50.000.000', blKhTc: '40' };
  m.ctx.document.getElementById = (id) => (khGia[id] !== undefined ? { value: khGia[id] } : (m.phanTu[id] || (m.phanTu[id] = { style: {}, innerHTML: '', dataset: {} })));
  m.ctx.blMoKeHoach();
  assert(/Chi phí lương cả năm 2025/.test(m.phanTu['blKeHoach'].innerHTML) && /giữ nguyên theo Danh Sách Nhân Viên/.test(m.phanTu['blKeHoach'].innerHTML) && /dưới 14 ngày/.test(m.phanTu['blKeHoach'].innerHTML));
  await m.ctx.blTinhKeHoach();
  const goiKh = m.goiApi.find(([u]) => u.includes('/ke-hoach'))[1];
  assert.strictEqual(goiKh.nam, 2025); assert.strictEqual(goiKh.tu_thang, 10); assert.strictEqual(goiKh.den_thang, 11);
  assert.strictEqual(goiKh.muc_tieu, '50.000.000'); assert.strictEqual(goiKh.ty_le_tang_ca, '40');
  assert.strictEqual(goiKh.da_co_ngoai, 0, 'Áp dụng xóa dữ liệu cũ cả năm -> không trừ các tháng đã có');
  const kqHtml = m.phanTu['blKhKq'].innerHTML;
  assert(/cần <b[^>]*>2 người<\/b>/.test(kqHtml) && /1 người đủ công có BHXH, 1 người làm dưới 14 ngày không BHXH/.test(kqHtml) && /thử cảnh báo/.test(kqHtml) && /Áp dụng \(xóa dữ liệu cũ cả năm/.test(kqHtml) && /toàn bộ dữ liệu đã nhập của năm này sẽ bị xóa/.test(m.phanTu['blKeHoach'].innerHTML));
  assert(/không BHXH/.test(kqHtml) && /12\.333\.333/.test(kqHtml));
  // áp dụng: hỏi xác nhận, XÓA dữ liệu cũ của cả năm (kể cả tháng 3) rồi nhập lại tháng 10–11
  let hoiKh = 0; m.ctx.confirm = (msg) => { hoiKh++; assert(/XÓA toàn bộ dữ liệu đã nhập của năm 2025 \(tháng 3\)/.test(msg), msg); return true; };
  await m.ctx.blApDungKeHoach();
  assert.strictEqual(hoiKh, 1, 'Có dữ liệu cũ -> hỏi xác nhận'); assert.strictEqual(m.ctx.blDL['03'], undefined, 'Dữ liệu cũ của cả năm bị xóa');
  assert.deepStrictEqual(Object.keys(m.ctx.blDL).sort(), ['10', '11']);
  assert.strictEqual(m.ctx.blDL['10'][0].chi_phi_luong, 8333333); assert.strictEqual(m.ctx.blDL['11'][0].dong_bh, 0);
  assert.strictEqual(m.ctx.blBan, true); assert.strictEqual(m.ctx.blThang, '10');
  // khoảng tháng sai / thiếu tiền -> báo lỗi, không gọi server
  m.goiApi.length = 0; khGia.blKhTu = '11'; khGia.blKhDen = '10';
  await m.ctx.blTinhKeHoach(); assert.strictEqual(m.goiApi.length, 0);
  khGia.blKhTu = '10'; khGia.blKhTien = ''; await m.ctx.blTinhKeHoach(); assert.strictEqual(m.goiApi.length, 0);
  // thông tin tháng: cảnh báo không đóng BHXH nhưng làm >= 14 ngày, và số người thời vụ
  m.ctx.blThang = '10'; m.phanTu['blInfo'] = { dataset: {}, style: {}, textContent: '' };
  m.ctx.blDL = { '10': [dongMau('1', 'A', { canh_bao_bh: true }), dongMau('2', 'B', { thoi_vu: true })] }; m.ctx.blVeInfo();
  assert(/1 người không đóng BHXH nhưng làm từ 14 ngày/.test(m.phanTu['blInfo'].textContent) && /1 người làm dưới 14 ngày không BHXH \(khấu trừ 10% thuế TNCN\)/.test(m.phanTu['blInfo'].textContent));
  console.log('PASS 19: nút "Chi phí lương cả năm" — nhập tháng + tổng, xem trước, áp dụng, cảnh báo BHXH <14 ngày.');

  // ---- 20: Danh Sách Nhân Viên: cột tick "Đóng BHXH" (+ Tháng/Năm vào làm), số hiện 5.310.000; bảng lương tự tick theo đó ----
  const q0 = html.indexOf('const NV_COT_TICK='), q1 = html.indexOf('async function nvLuu(', q0);
  const env2 = { nvHeader: ['STT', 'Mã NV', 'Họ và tên', 'Tháng/Năm vào làm', 'Chức vụ', 'Lương Cơ bản', 'PC Tiền cơm'], nvFilters: {}, nvChon: null, nvTuBl: null,
    nvEsc: (x) => String(x), nvRows: [[1, '2', 'Trần A', '10/2024', 'KD', 5310000, '700000'], [2, '3', 'Lê B', '', 'KD', '5.310.000', 700000]], console };
  env2.nvRowsLoc = () => env2.nvRows.map((_, i) => i);
  const els2 = { nvTableWrap: { innerHTML: '' }, nvTuBl: { innerHTML: '' } };
  env2.document = { getElementById: (id) => els2[id], querySelector: () => null };
  vm.createContext(env2); vm.runInContext(html.slice(q0, q1), env2);
  vm.runInContext('nvThemCotTick()', env2);          // danh sách lưu từ trước chưa có cột
  assert.deepStrictEqual(JSON.parse(JSON.stringify(env2.nvHeader)), ['STT', 'Mã NV', 'Họ và tên', 'Tháng/Năm vào làm', 'Đóng BHXH', 'Chức vụ', 'Lương Cơ bản', 'PC Tiền cơm'], 'Cột mới ngay sau Tháng/Năm vào làm');
  assert.deepStrictEqual(env2.nvRows.map((r) => r[4]), ['x', 'x'], 'Người cũ được tick sẵn (giữ hành vi cũ)');
  assert.strictEqual(env2.nvRows[0].length, env2.nvHeader.length);
  vm.runInContext('nvThemCotTick()', env2); assert.strictEqual(env2.nvHeader.length, 8, 'Không thêm cột lần 2');
  vm.runInContext('veGridNhanVien()', env2);
  const g2 = els2.nvTableWrap.innerHTML;
  assert.strictEqual((g2.match(/type="checkbox"/g) || []).length, 2, 'Mỗi nhân viên 1 ô tick');
  assert(/5\.310\.000/.test(g2) && /700\.000/.test(g2) && !/>5310000</.test(g2) && !/>700000</.test(g2), 'Lương + phụ cấp hiện dạng 5.310.000');
  vm.runInContext('nvDoiTick(1,4,false)', env2); assert.strictEqual(env2.nvRows[1][4], '');
  vm.runInContext('nvDoiTick(1,4,true)', env2); assert.strictEqual(env2.nvRows[1][4], 'x');
  assert.deepStrictEqual(['x', '1', 1, 'có', '', 0, 'không', null].map((v) => vm.runInContext('nvCoTick', env2)(v)), [true, true, true, true, false, false, false, false]);
  const td20 = { dataset: { r: '0', c: '6' }, textContent: '1500000', };
  vm.runInContext('nvSuaO', env2)(td20);
  assert.strictEqual(env2.nvRows[0][6], '1.500.000'); assert.strictEqual(td20.textContent, '1.500.000', 'Gõ 1500000 -> 1.500.000');
  const tdTen2 = { dataset: { r: '0', c: '2' }, textContent: ' Trần A2 ' }; vm.runInContext('nvSuaO', env2)(tdTen2);
  assert.strictEqual(env2.nvRows[0][2], 'Trần A2', 'Cột chữ giữ nguyên');
  vm.runInContext('nvThemDong()', env2);
  assert.strictEqual(env2.nvRows[env2.nvRows.length - 1][4], 'x', 'Dòng mới mặc định tick');
  // bảng lương: nạp từ Danh Sách Nhân Viên gửi tháng và đồng bộ ô đóng BHXH (người làm dưới 14 ngày giữ không đóng)
  m = nap({ api: (url, o) => (url.includes('tu-nhan-vien')
    ? { rows: [dongMau('101', 'A', { dong_bh: 0 }), dongMau('102', 'B', { dong_bh: 1 }), dongMau('103', 'C', { dong_bh: 1 })] }
    : { rows: JSON.parse(o.body).rows, tham_so: JSON.parse(o.body).tham_so }) });
  m.ctx.blNam = 2024; m.ctx.blThang = '10'; m.ctx.blTS = {};
  m.ctx.blDL = { '10': [dongMau('101', 'A', { dong_bh: 1 }), dongMau('102', 'B', { dong_bh: 0, thoi_vu: true, ngay_lam: 5 }), dongMau('103', 'C', { dong_bh: 1 })] };
  await m.ctx.blNapNhanVien();
  assert(m.goiApi[0][0].includes('thang=10'), 'Gửi tháng đang xem: ' + m.goiApi[0][0]);
  const d20 = m.ctx.blDL['10'];
  assert.strictEqual(d20[0].dong_bh, 0, 'Bỏ tick trong danh sách -> bảng lương không đóng BHXH');
  assert.strictEqual(d20[1].dong_bh, 0, 'Người thời vụ (<14 ngày) giữ nguyên không đóng');
  assert.strictEqual(d20[2].dong_bh, 1);
  // ô nhập tiền hiện dấu chấm
  const inp = { value: '120000000' }; m.ctx.blDangTien(inp); assert.strictEqual(inp.value, '120.000.000');
  inp.value = '12abc'; m.ctx.blDangTien(inp); assert.strictEqual(inp.value, '12'); inp.value = ''; m.ctx.blDangTien(inp); assert.strictEqual(inp.value, '');
  m.ctx.blTS = { ngay_cong_chuan: 26, giam_tru_ban_than: 11000000, giam_tru_npt: 4400000, he_so_tang_ca: 1.33, nguong_khau_tru_10: 2000000, bh_dn: { bhxh: 17.5, bhyt: 3, bhtn: 1 }, bh_nld: { bhxh: 8, bhyt: 1.5, bhtn: 1 }, bac_thue: [[0, 5], [10000000, 10]], thue_moi: null };
  m.ctx.document.getElementById('blThamSo').style.display = 'none'; m.ctx.blMoThamSo();
  const pt = m.phanTu['blThamSo'].innerHTML;
  assert(/id="blTsBt" value="11\.000\.000"/.test(pt) && /id="blTsNpt" value="4\.400\.000"/.test(pt) && /id="blTsN10" value="2\.000\.000"/.test(pt) && /class="blBacTu" value="10\.000\.000"/.test(pt), 'Tham số tiền hiện 11.000.000');
  console.log('PASS 20: Danh Sách Nhân Viên có cột tick Đóng BHXH, số hiện 5.310.000; bảng lương tự tick theo danh sách + tháng.');

  // ---- 21: cột "Ghi chú" đổi thành tick Chuyển khoản; thực lãnh = chi phí lương của người làm < 14 ngày (công ty chịu thuế 10%) ----
  m = nap();
  m.ctx.blThang = '09'; m.ctx.blNam = 2024; m.ctx.blTS = {};
  m.ctx.blDL = { '09': [dongMau('1', 'A', { ghi_chu: 'CK' }), dongMau('2', 'B', { ghi_chu: '' }), dongMau('3', 'C', { ghi_chu: 'Chuyển khoản' }), dongMau('4', 'D', { ghi_chu: 'TM' })] };
  m.ctx.blVeBang();
  const b21 = m.phanTu['blBangWrap'].innerHTML;
  assert(/>Chuyển khoản \(tick\)</.test(b21) && !/>Ghi chú</.test(b21), 'Cột đổi tên thành Chuyển khoản (tick)');
  const ck = [...b21.matchAll(/<input type="checkbox"([^>]*)onchange="blDoiCk\((\d+),this\.checked\)"/g)];
  assert.strictEqual(ck.length, 4);
  assert.deepStrictEqual(ck.map((x) => /checked/.test(x[1])), [true, false, true, false], 'CK / Chuyển khoản = tick; trống / TM = không tick');
  m.ctx.blDoiCk(1, true); assert.strictEqual(m.ctx.blDL['09'][1].ghi_chu, 'CK'); assert.strictEqual(m.ctx.blBan, true);
  m.ctx.blDoiCk(0, false); assert.strictEqual(m.ctx.blDL['09'][0].ghi_chu, '');
  // cột Kiểm tra: so với thuế THỰC SỰ trừ vào lương (người làm < 14 ngày, công ty chịu thuế: kiểm tra = 0 vẫn đúng, không tô đỏ)
  m.ctx.blDL = { '09': [dongMau('1', 'A', { kiem_tra: 0, thue_tncn: 427885, thue_tru_luong: 0, thoi_vu: true }), dongMau('2', 'B', { kiem_tra: 100, thue_tncn: 100, thue_tru_luong: 100 })] };
  m.ctx.blVeBang();
  assert(!/#fde2e2/.test(m.phanTu['blBangWrap'].innerHTML), 'Kiểm tra khớp thuế thực trừ -> không tô đỏ');
  m.ctx.blDL = { '09': [dongMau('1', 'A', { kiem_tra: 5000, thue_tncn: 100, thue_tru_luong: 100 })] };
  m.ctx.blVeBang(); assert(/#fde2e2/.test(m.phanTu['blBangWrap'].innerHTML), 'Lệch thật thì vẫn tô đỏ');
  // tham số: ô tick "công ty chịu thuế 10% thay" — mặc định KHÔNG tick (thuế trừ vào thực lãnh)
  const tsMau = { ngay_cong_chuan: 26, giam_tru_ban_than: 11000000, giam_tru_npt: 4400000, he_so_tang_ca: 1.33, bh_dn: { bhxh: 17.5, bhyt: 3, bhtn: 1 }, bh_nld: { bhxh: 8, bhyt: 1.5, bhtn: 1 }, bac_thue: [[0, 5]], thue_moi: null };
  m.ctx.blTS = Object.assign({}, tsMau);
  m.ctx.document.getElementById('blThamSo').style.display = 'none'; m.ctx.blMoThamSo();
  assert(/id="blTsCt" >/.test(m.phanTu['blThamSo'].innerHTML) && /Không trừ thuế 10% của người làm/.test(m.phanTu['blThamSo'].innerHTML), 'Mặc định không tick');
  m.ctx.blTS = Object.assign({}, tsMau, { thue_10_cong_ty_chiu: true }); m.ctx.document.getElementById('blThamSo').style.display = 'none'; m.ctx.blMoThamSo();
  assert(/id="blTsCt" checked/.test(m.phanTu['blThamSo'].innerHTML), 'Đã tick thì hiển thị tick');
  // không hiện "-0" khi số âm cực nhỏ (cột Kiểm tra số liệu)
  assert.strictEqual(m.ctx.blDinhDang(-0.1111), '0'); assert.strictEqual(m.ctx.blDinhDang(-0.4), '0'); assert.strictEqual(m.ctx.blDinhDang(-1234), '-1.234'); assert.strictEqual(m.ctx.blDinhDang(0.6), '1');
  console.log('PASS 21: cột Chuyển khoản (tick) thay Ghi chú; kiểm tra số liệu theo thuế thực trừ; tham số công ty chịu thuế 10%.');

  // ---- 22: cột Thuế TNCN cho người dùng tự chỉnh: trống = tự tính (hiện số tính), gõ số = chỉnh tay, xóa số = trở lại tự tính ----
  m = nap({ api: async (url, o) => ({ rows: JSON.parse(o.body).rows, tham_so: {} }) });
  m.ctx.blThang = '09'; m.ctx.blNam = 2024; m.ctx.blTS = {};
  m.ctx.blDL = { '09': [dongMau('1', 'A', { thue_tay: '', thue_tncn: 427885 }), dongMau('2', 'B', { thue_tay: 300000, thue_tncn: 300000, thue_da_chinh: true }), dongMau('3', 'C', { thue_tay: 0, thue_tncn: 0 })] };
  m.ctx.blVeBang();
  const b22 = m.phanTu['blBangWrap'].innerHTML;
  const cellThue = b22.match(/<td [^>]*data-k="thue_tay"[^>]*>[^<]*<\/td>/g);
  assert.strictEqual(cellThue.length, 3); assert(!/data-k="thue_tncn"/.test(b22));
  assert(/contenteditable/.test(cellThue[0]) && />427\.885</.test(cellThue[0]) && /Tự tính/.test(cellThue[0]) && !/✎/.test(cellThue[0]), 'Ô tự tính: hiện số tính, gõ được');
  assert(/300\.000 ✎/.test(cellThue[1]) && /Đã chỉnh tay/.test(cellThue[1]) && /#1d4ed8/.test(cellThue[1]), 'Ô đã chỉnh tay có dấu ✎ + màu khác');
  assert(/>0 ✎</.test(cellThue[2]), 'Chỉnh tay = 0 (miễn thuế) vẫn được coi là đã chỉnh');
  assert(/Thuế TNCN \(sửa được\)/.test(b22));
  assert(/300\.000/.test(b22) && /727\.885/.test(b22), 'Dòng tổng cộng dùng số thuế đang hiển thị (427.885 + 300.000 + 0)');
  // gõ số -> lưu vào thue_tay (chuỗi gõ tay), gọi server tính lại; gõ lại đúng số tự tính -> không coi là chỉnh
  m.ctx.blSuaO({ dataset: { r: '0', k: 'thue_tay' }, textContent: '427.885' }); assert.strictEqual(m.ctx.blBan, false); assert.strictEqual(m.goiApi.length, 0);
  m.ctx.blSuaO({ dataset: { r: '0', k: 'thue_tay' }, textContent: '500.000' });
  assert.strictEqual(m.ctx.blDL['09'][0].thue_tay, '500.000'); assert.strictEqual(m.ctx.blBan, true);
  assert.strictEqual(m.goiApi[m.goiApi.length - 1][1].rows[0].thue_tay, '500.000', 'Gửi số chỉnh tay cho server tính lại');
  // xóa số trong ô đã chỉnh tay (hiện "300.000 ✎") -> trở lại tự tính
  m.ctx.blSuaO({ dataset: { r: '1', k: 'thue_tay' }, textContent: '300.000 ✎' }); assert.strictEqual(m.ctx.blBan, true, 'Không đổi gì: giữ nguyên (đã tính lại ở lần trước)');
  m.ctx.blBan = false;
  m.ctx.blSuaO({ dataset: { r: '1', k: 'thue_tay' }, textContent: '' });
  assert.strictEqual(m.ctx.blDL['09'][1].thue_tay, '', 'Xóa số -> tự tính lại'); assert.strictEqual(m.ctx.blBan, true);
  // lưu gửi thue_tay; sao chép tháng trước bỏ thuế chỉnh tay
  await m.ctx.blLuu(true);
  assert.strictEqual(m.goiApi[m.goiApi.length - 1][1].thang['09'][0].thue_tay, '500.000');
  m.ctx.blDL = { '08': [dongMau('1', 'A', { thue_tay: 123456 })] }; m.ctx.blThang = '09'; await m.ctx.blSaoChepThangTruoc();
  assert.strictEqual(m.ctx.blDL['09'][0].thue_tay, '', 'Sao chép tháng: không mang theo thuế đã chỉnh tay');
  console.log('PASS 22: cột Thuế TNCN tự chỉnh được (trống = tự tính, gõ số = chỉnh tay, xóa = tự tính lại).');

  // ---- 23: IN bảng lương + bảng chấm công (mẫu theo file "BL"), in hàng loạt từ tháng – đến tháng ----
  m = nap();
  const c = m.ctx;
  const leSet = new Set(['2024-05-01']);      // 1/5/2024 (thứ Tư) là ngày lễ
  // chấm công: T5/2024 có 31 ngày, 4 Chủ nhật (5, 12, 19, 26), 1 ngày lễ (1/5) => 26 ngày làm việc
  const full = c.blChamCongThang({ ma: '1', ngay_lam_hd: 26 }, 2024, '05', leSet);
  assert.strictEqual(full.ngay.length, 31); assert.strictEqual(full.soX, 26);
  assert.strictEqual(JSON.stringify(full.ngay.filter((x) => x.cn).map((x) => x.d)), '[5,12,19,26]', 'Chủ nhật của tháng 5/2024');
  assert(full.ngay.filter((x) => x.cn).every((x) => x.dau === ''), 'Chủ nhật không đánh dấu');
  assert.strictEqual(full.ngay[0].dau, 'L', 'Ngày lễ ghi L'); assert.strictEqual(full.ngay[1].dau, 'X');
  const it = c.blChamCongThang({ ma: '2', ngay_lam_hd: 13 }, 2024, '05', leSet);
  assert.strictEqual(it.soX, 13); assert.strictEqual(it.tong, 13);
  assert(it.ngay.filter((x) => x.dau === 'X').every((x) => !x.cn && !x.le), 'Chỉ đánh dấu ngày làm việc (không CN, không lễ)');
  const lai = c.blChamCongThang({ ma: '2', ngay_lam_hd: 13 }, 2024, '05', leSet);
  assert.strictEqual(JSON.stringify(lai.ngay.map((x) => x.dau)), JSON.stringify(it.ngay.map((x) => x.dau)), 'In lại ra đúng bảng chấm công cũ (cố định theo người + tháng)');
  const khac = c.blChamCongThang({ ma: '3', ngay_lam_hd: 13 }, 2024, '05', leSet);
  assert.notStrictEqual(JSON.stringify(khac.ngay.map((x) => x.dau)), JSON.stringify(it.ngay.map((x) => x.dau)), 'Mỗi người nghỉ những ngày khác nhau');
  assert.strictEqual(c.blChamCongThang({ ma: '4', ngay_lam_hd: 0 }, 2024, '05', leSet).soX, 0);
  assert.strictEqual(c.blChamCongThang({ ma: '5', ngay_lam_hd: 30 }, 2024, '05', leSet).soX, 30, 'Công thừa thì dồn sang ngày lễ/CN để số X khớp Tổng NC');
  assert.strictEqual(c.blChamCongThang({ ma: '6', ngay_lam_hd: 12 }, 2024, '02', new Set()).ngay.length, 29, 'Tháng 2/2024 có 29 ngày');
  // cột: ẩn cột toàn 0; nhóm tiêu đề
  const rowsIn = [
    dongMau('2', 'Trần A', { chuc_vu: 'KD', ngay_cong_hd: 26, ngay_lam_hd: 26, luong: 5310000, tt_tien_com: 700000, xang_xe: 500000, tt_pc_chuc_vu: 500000, dien_thoai: 500000, tt_trang_phuc: 400000,
      bhxh_nld: 424800, bhyt_nld: 79650, bhtn_nld: 53100, thue_tru_luong: 0, tt_luong: 7352450, gio_tang_ca: 0, tang_ca: 0, thuong_bh: 0, tt_di_lai: 0, thuong_t13: 0 }),
    dongMau('3', 'Lê B', { chuc_vu: 'KD', ngay_cong_hd: 26, ngay_lam_hd: 13, thoi_vu: true, luong: 2655000, tt_tien_com: 350000, xang_xe: 250000, tt_pc_chuc_vu: 250000, dien_thoai: 250000, tt_trang_phuc: 200000,
      bhxh_nld: 0, bhyt_nld: 0, bhtn_nld: 0, thue_tru_luong: 315500, tt_luong: 3639500, gio_tang_ca: 0, tang_ca: 0, thuong_bh: 1500000, tt_di_lai: 0, thuong_t13: 0 })];
  const ts = { bh_nld: { bhxh: 8, bhyt: 1.5, bhtn: 1 } };
  const cot = c.blCotIn(rowsIn, ts).map((x) => x.k);
  assert(!cot.includes('tt_di_lai') && !cot.includes('thuong_t13') && !cot.includes('tang_ca') && !cot.includes('gio_tang_ca'), 'Cột toàn số 0 bị ẩn');
  assert(cot.includes('tt_tien_com') && cot.includes('thuong_bh') && cot.includes('thue_tru_luong') && cot.includes('bhxh_nld') && cot.includes('ky') && cot.includes('tt_luong'));
  const tuyChon = { tenCty: 'CÔNG TY TNHH A', mst: '0312345678', diaChi: '1/50 Thanh Đa', nguoiLap: 'Đỗ Thái Hưng', giamDoc: 'Nguyễn Văn Kiên', leSet, ts, inLuong: true, inCong: true, kho: 'a4n' };
  const bl = c.blDungBangLuongIn(rowsIn, 2024, '05', tuyChon);
  for (const t of ['CÔNG TY TNHH A', 'ĐC: 1/50 Thanh Đa', 'MST: 0312345678', 'BẢNG TÍNH LƯƠNG VÀ CÁC KHOẢN THU NHẬP KHÁC', 'THÁNG 05 NĂM 2024', 'Họ và Tên', 'Lương căn bản', 'Phụ cấp', 'Các khoản giảm trừ', 'BHXH 8%', 'BHYT 1.5%', 'BHTN 1%', 'Tổng thực nhận', 'Ký nhận',
    'Tổng cộng', 'Ngày 31 tháng 05 năm 2024', 'Người lập biểu', 'Giám đốc', 'Đỗ Thái Hưng', 'Nguyễn Văn Kiên'])
    assert(bl.html.includes(t), 'Bảng lương thiếu: ' + t);
  assert(/7\.352\.450/.test(bl.html) && /3\.639\.500/.test(bl.html) && /10\.991\.950/.test(bl.html), 'Có thực nhận từng người + tổng (7.352.450 + 3.639.500)');
  assert(/<td[^>]*>315\.500<\/td>/.test(bl.html), 'Thuế trừ vào lương hiện ở cột Thuế TNCN');
  assert(!bl.html.includes('Hỗ trợ đi lại'), 'Cột đi lại toàn 0 -> không in');
  const cc = c.blDungChamCongIn(rowsIn, 2024, '05', tuyChon);
  assert(cc.html.includes('BẢNG CHẤM CÔNG THÁNG TỪ 01/05/2024  ĐẾN 31/05/2024') && cc.html.includes('TNC') && cc.html.includes('Ghi chú') && cc.html.includes('Thời vụ (không BHXH)'));
  assert.strictEqual((cc.html.match(/<th class="cn?">|<th class="">|<th class="cn">/g) || []).length >= 62, true, 'Hàng thứ + hàng ngày, 31 cột mỗi hàng');
  assert(cc.html.includes('>T4<') && cc.html.includes('>CN<') && cc.html.includes('X: đi làm'), 'Có thứ trong tuần + chú thích');
  const xTong = (cc.html.match(/>X</g) || []).length; assert.strictEqual(xTong, 26 + 13, 'Số X đúng bằng Tổng NC (26 + 13)');
  // ghép tài liệu in: khổ giấy, tự thu phóng, bỏ tháng trống, chọn bảng
  const ds = [{ t: '05', rows: rowsIn }, { t: '06', rows: [] }, { t: '07', rows: rowsIn }];
  let doc = c.blDungTrangIn(ds, 2024, tuyChon);
  assert.strictEqual(doc.so_bang, 4, '2 tháng x (bảng lương + chấm công)'); assert.strictEqual(JSON.stringify(doc.bo), '["06"]');
  assert(/@page\{size:A4 landscape;margin:8mm\}/.test(doc.html) && (doc.html.match(/<section class="muc">/g) || []).length === 4 && /page-break-after:always/.test(doc.html));
  assert(/thead\{display:table-header-group\}/.test(doc.html), 'Lặp tiêu đề bảng ở mỗi trang');
  const zoom = [...doc.html.matchAll(/zoom:([0-9.]+)/g)].map((x) => +x[1]); assert(zoom.length === 4 && zoom.every((z) => z > 0.3 && z <= 1.2), 'Tự thu phóng để vừa bề ngang: ' + zoom);
  assert(doc.html.indexOf('BẢNG TÍNH LƯƠNG') < doc.html.indexOf('BẢNG CHẤM CÔNG') && doc.html.lastIndexOf('BẢNG TÍNH LƯƠNG') > doc.html.indexOf('BẢNG CHẤM CÔNG'), 'Thứ tự: lương T5, công T5, lương T7, công T7');
  assert(/size:A3 landscape/.test(c.blDungTrangIn(ds, 2024, Object.assign({}, tuyChon, { kho: 'a3n' })).html) && /size:A4 portrait/.test(c.blDungTrangIn(ds, 2024, Object.assign({}, tuyChon, { kho: 'a4d' })).html));
  assert.strictEqual(c.blDungTrangIn(ds, 2024, Object.assign({}, tuyChon, { inCong: false })).so_bang, 2, 'Chỉ in bảng lương');
  assert.strictEqual(c.blDungTrangIn(ds, 2024, Object.assign({}, tuyChon, { inLuong: false })).so_bang, 2, 'Chỉ in bảng chấm công');
  // giao diện: hộp in + kiểm tra khoảng tháng
  const els = {}; const kho = { blInTu: '5', blInDen: '7', blInKho: 'a4n', blInDc: 'ĐC X', blInLap: 'L', blInGd: 'G' }; const cks = { blInLuong: true, blInCong: true };
  c.document.getElementById = (id) => (id in kho ? { value: kho[id] } : id in cks ? { checked: cks[id] } : (els[id] || (els[id] = { style: {}, innerHTML: '', dataset: {} })));
  c.companies = [{ id: 7, ten: 'CÔNG TY A', mst: '031' }]; c.blNam = 2024; c.blThang = '05'; c.blTS = { ngay_le: [{ ngay: '2024-05-01' }], bh_nld: ts.bh_nld };
  c.blMoIn(); assert(/In bảng lương & bảng chấm công — năm 2024/.test(els['blIn'].innerHTML) && /In hàng loạt/.test(els['blIn'].innerHTML) && /A3 ngang/.test(els['blIn'].innerHTML) && /id="blInLuong"/.test(els['blIn'].innerHTML));
  c.blDL = { '05': rowsIn, '06': [], '07': rowsIn };
  const kq = c.blChuanBiIn();
  assert.strictEqual(kq.so_bang, 4); assert(kq.html.includes('CÔNG TY A') && kq.html.includes('MST: 031') && kq.html.includes('ĐC: ĐC X'));
  assert(/2 tháng/.test(els['blInKq'].innerHTML) && /bỏ qua tháng chưa có dữ liệu: 6/.test(els['blInKq'].innerHTML));
  assert(/"diaChi":"ĐC X"/.test(m.luuTru['blIn7']) && /"nguoiLap":"L"/.test(m.luuTru['blIn7']), 'Nhớ địa chỉ/người ký cho lần in sau');
  const nhat = m.toasts.length; kho.blInTu = '8'; kho.blInDen = '3'; assert.strictEqual(c.blChuanBiIn(), null); assert(m.toasts.length > nhat, 'Khoảng tháng sai -> báo lỗi');
  kho.blInTu = '9'; kho.blInDen = '10'; assert.strictEqual(c.blChuanBiIn(), null, 'Không có dữ liệu -> không in');
  kho.blInTu = '5'; kho.blInDen = '5'; cks.blInLuong = false; cks.blInCong = false; assert.strictEqual(c.blChuanBiIn(), null, 'Phải chọn ít nhất 1 loại bảng');
  console.log('PASS 23: in bảng lương + chấm công (theo mẫu file), tự thu phóng theo khổ giấy, in hàng loạt nhiều tháng.');

  // ---- 24: xuất Excel theo mẫu: dữ liệu gửi server = đúng dữ liệu đã dựng cho bản in ----
  m = nap();
  const c24 = m.ctx;
  const rows24 = [dongMau('2', 'Trần A', { chuc_vu: 'KD', ngay_cong_hd: 26, ngay_lam_hd: 26, luong: 5310000, tt_tien_com: 700000, tt_luong: 7352450, bhxh_nld: 424800, thue_tru_luong: 0, xang_xe: 0, tt_pc_chuc_vu: 0, dien_thoai: 0, tt_trang_phuc: 0 }),
    dongMau('3', 'Lê B', { chuc_vu: 'KD', ngay_cong_hd: 26, ngay_lam_hd: 13, thoi_vu: true, luong: 2655000, tt_tien_com: 350000, tt_luong: 3000000, thue_tru_luong: 5000, xang_xe: 0, tt_pc_chuc_vu: 0, dien_thoai: 0, tt_trang_phuc: 0 })];
  const o24 = { tenCty: 'CÔNG TY A', mst: '031', diaChi: 'ĐC', nguoiLap: 'L', giamDoc: 'G', leSet: new Set(['2024-05-01']), ts: { bh_nld: { bhxh: 8, bhyt: 1.5, bhtn: 1 } }, inLuong: true, inCong: true, kho: 'a4n' };
  const goiXm = JSON.parse(JSON.stringify(c24.blDuLieuXuatMau([{ t: '05', rows: rows24 }, { t: '06', rows: [] }], 2024, o24)));
  assert.strictEqual(goiXm.nam, 2024); assert.deepStrictEqual(Object.keys(goiXm.thang), ['05'], 'Tháng trống không gửi');
  const t5 = goiXm.thang['05'];
  assert.strictEqual(t5.rows.length, 2); assert.strictEqual(t5.cham.length, 2); assert.strictEqual(t5.ngay.length, 31);
  assert(t5.cot.some((x) => x.k === 'tt_luong') && t5.cot.some((x) => x.k === 'bhxh_nld' && x.nhom === 'gt') && t5.cot.some((x) => x.k === 'tt_tien_com' && x.nhom === 'pc'));
  assert(!t5.cot.some((x) => x.k === 'thuong_t13'), 'Cột toàn 0 bị ẩn giống bản in');
  assert.strictEqual(t5.rows[0].tt_luong, 7352450); assert.strictEqual(t5.rows[1].thoi_vu, true); assert.strictEqual(t5.cham[0].tong, 26); assert.strictEqual(t5.cham[0].soX, 26); assert.strictEqual(t5.cham[1].soX, 13);
  assert.strictEqual(t5.cham[0].dau.length, 31); assert.strictEqual(t5.cham[0].dau[0], 'L', 'Ngày lễ'); assert.strictEqual(t5.ngay[4].cn, true, '5/5/2024 là Chủ nhật');
  assert.deepStrictEqual(Object.keys(goiXm.tuy_chon).sort(), ['dia_chi', 'giam_doc', 'in_cong', 'in_luong', 'kho', 'mst', 'nguoi_lap', 'ten_cty']);
  // nút + gọi API
  const goiApi24 = []; const luuTep = [];
  c24.fetch = async (url, o) => { goiApi24.push([url, JSON.parse(o.body)]); return { ok: true, headers: { get: () => null }, blob: async () => ({}) }; };
  c24.xuatFile = async (r, ten) => { luuTep.push(ten); };
  c24.blNam = 2024; c24.blThang = '05'; c24.blTS = { ngay_le: [{ ngay: '2024-05-01' }], bh_nld: o24.ts.bh_nld }; c24.companies = [{ id: 7, ten: 'CÔNG TY A', mst: '031' }]; c24.blDL = { '05': rows24 };
  const kho24 = { blInTu: '5', blInDen: '6', blInKho: 'a4n', blInDc: '', blInLap: '', blInGd: '' }; const cks24 = { blInLuong: true, blInCong: true };
  c24.document.getElementById = (id) => (id in kho24 ? { value: kho24[id] } : id in cks24 ? { checked: cks24[id] } : { style: {}, innerHTML: '', dataset: {} });
  await c24.blXuatExcelMau();
  assert.strictEqual(goiApi24.length, 1); assert.strictEqual(goiApi24[0][0], '/api/bang-luong/7/xuat-excel-mau');
  assert.deepStrictEqual(Object.keys(goiApi24[0][1].thang), ['05']); assert.strictEqual(luuTep[0], 'BangLuong_ChamCong_2024_T5-T6.xlsx');
  kho24.blInTu = '9'; kho24.blInDen = '10'; const truoc = goiApi24.length; await c24.blXuatExcelMau(); assert.strictEqual(goiApi24.length, truoc, 'Không có dữ liệu -> không gọi server');
  kho24.blInTu = '8'; kho24.blInDen = '3'; await c24.blXuatExcelMau(); assert.strictEqual(goiApi24.length, truoc, 'Khoảng tháng sai -> không gọi server');
  c24.fetch = async () => ({ ok: false, json: async () => ({ detail: 'Lỗi thử' }) }); kho24.blInTu = '5'; kho24.blInDen = '5';
  const nToast = m.toasts.length; await c24.blXuatExcelMau(); assert(m.toasts.slice(nToast).some((x) => /Lỗi thử/.test(x[0])), 'Báo lỗi server');
  assert(/Xuất Excel theo mẫu/.test(html) && /blXuatExcelMau\(\)/.test(html), 'Có nút Xuất Excel theo mẫu trong hộp in');
  console.log('PASS 24: xuất Excel theo mẫu — dữ liệu gửi server đúng, xử lý lỗi/khoảng tháng/không có dữ liệu.');

  // ---- 25: bảng chấm công có GIỜ TĂNG CA: tổng giờ trong các ô X+n = "Số giờ tăng ca" của bảng lương ----
  m = nap();
  const c25 = m.ctx, le25 = new Set(['2024-09-02']);
  const tongTc = (kq) => Math.round(kq.ngay.reduce((s, x) => s + (x.tc || 0), 0) * 10) / 10;
  for (const [ma, gio, du] of [['2', 11.9864406779661, 12], ['3', 40, 40], ['4', 8.352542372881356, 8.4], ['5', 0.3, 0.3], ['6', 3, 3]]) {
    const kq = c25.blChamCongThang({ ma, ngay_lam_hd: 24, gio_tang_ca: gio }, 2024, '09', le25);
    assert.strictEqual(tongTc(kq), du, `Tổng giờ tăng ca trong bảng chấm công (${ma}) = ${du}`); assert.strictEqual(kq.gio, du);
    const co = kq.ngay.filter((x) => x.tc > 0);
    assert(co.length >= 1 && co.every((x) => x.dau === 'X' && !x.cn && !x.le), 'Tăng ca chỉ ghi vào ngày đi làm (không CN/lễ)');
    assert(co.every((x) => x.tc <= 8), 'Mỗi ngày không quá 8 giờ');
    if (gio >= 4) assert(co.every((x) => x.tc <= 4.5), 'Mỗi ngày tối đa khoảng 4 giờ khi đủ ngày để chia');
    if (gio >= 8) assert(co.length >= 3, 'Số giờ lớn được chia nhiều ngày');
    const le = co.filter((x) => Math.abs(x.tc * 2 - Math.round(x.tc * 2)) > 1e-9);
    assert(le.length <= 1, 'Chỉ 1 ngày có phần lẻ (' + ma + ')');
  }
  const a1 = c25.blChamCongThang({ ma: '2', ngay_lam_hd: 24, gio_tang_ca: 12 }, 2024, '09', le25), a2 = c25.blChamCongThang({ ma: '2', ngay_lam_hd: 24, gio_tang_ca: 12 }, 2024, '09', le25);
  assert.strictEqual(JSON.stringify(a1.ngay.map((x) => x.tc)), JSON.stringify(a2.ngay.map((x) => x.tc)), 'In lại ra đúng số giờ từng ngày');
  assert.strictEqual(tongTc(c25.blChamCongThang({ ma: '7', ngay_lam_hd: 0, gio_tang_ca: 5 }, 2024, '09', le25)), 0, 'Không đi làm thì không có tăng ca');
  assert.strictEqual(tongTc(c25.blChamCongThang({ ma: '8', ngay_lam_hd: 20 }, 2024, '09', le25)), 0, 'Không có giờ tăng ca -> không điền');
  assert.strictEqual(c25.blDauHienThi({ dau: 'X', tc: 2 }), 'X+2'); assert.strictEqual(c25.blDauHienThi({ dau: 'X', tc: 1.5 }), 'X+1,5'); assert.strictEqual(c25.blDauHienThi({ dau: 'X', tc: 0 }), 'X'); assert.strictEqual(c25.blDauHienThi({ dau: 'L', tc: 0 }), 'L');
  // bản in
  const rows25 = [dongMau('2', 'Trần A', { ngay_lam_hd: 24, ngay_cong_hd: 24, gio_tang_ca: 12, luong: 5310000, tt_luong: 5310000 }), dongMau('3', 'Lê B', { ngay_lam_hd: 24, ngay_cong_hd: 24, gio_tang_ca: 0, luong: 5310000, tt_luong: 5310000 })];
  const o25 = { tenCty: 'A', leSet: le25, ts: {}, inLuong: true, inCong: true, kho: 'a4n' };
  const cc25 = c25.blDungChamCongIn(rows25, 2024, '09', o25);
  assert(cc25.html.includes('>Giờ TC<') && /X\+\d/.test(cc25.html) && cc25.html.includes('X+n: đi làm và tăng ca n giờ'), 'Bản in có cột Giờ TC + ô X+n');
  const gioTrongO = [...cc25.html.matchAll(/>X\+([0-9,]+)</g)].reduce((sum, x) => sum + parseFloat(x[1].replace(',', '.')), 0);
  assert.strictEqual(Math.round(gioTrongO * 10) / 10, 12, 'Cộng các ô X+n = 12 giờ = Số giờ tăng ca');
  const khong = c25.blDungChamCongIn(rows25.map((r) => Object.assign({}, r, { gio_tang_ca: 0 })), 2024, '09', o25);
  assert(!khong.html.includes('>Giờ TC<') && !/X\+\d/.test(khong.html), 'Không ai tăng ca -> không thêm cột');
  const gx = JSON.parse(JSON.stringify(c25.blDuLieuXuatMau([{ t: '09', rows: rows25 }], 2024, Object.assign({}, o25, { nguoiLap: '', giamDoc: '', diaChi: '', mst: '' }))));
  assert.strictEqual(gx.thang['09'].cham[0].gio, 12); assert.strictEqual(gx.thang['09'].cham[0].tc.length, 30);
  assert.strictEqual(Math.round(gx.thang['09'].cham[0].tc.reduce((a, b) => a + b, 0) * 10) / 10, 12, 'Payload Excel mang đủ giờ từng ngày');
  console.log('PASS 25: bảng chấm công điền giờ tăng ca (ô X+n, cột Giờ TC), tổng = Số giờ tăng ca; Excel cũng nhận đủ.');

  // ---- 26: Địa chỉ + Giám đốc trong hộp in lấy theo THÔNG TIN CÔNG TY đã nhập ----
  m = nap();
  const c26 = m.ctx, els26 = {};
  ['blInTu', 'blInDen', 'blInLuong', 'blInCong', 'blInKho', 'blInDc', 'blInLap', 'blInGd'].forEach((k) => { els26[k] = { style: {}, innerHTML: '', dataset: {}, value: '', checked: false }; });
  c26.document.getElementById = (id) => (els26[id] || (els26[id] = { style: {}, innerHTML: '', dataset: {}, value: '' }));
  c26.blNam = 2024; c26.blThang = '05'; c26.blTS = {};
  c26.companies = [{ id: 7, ten: 'CÔNG TY A', mst: '031', dia_chi: '1/50 Thanh Đa, P.27, Bình Thạnh', nguoi_ky: 'Nguyễn Văn Kiên' }];
  m.luuTru['blIn7'] = JSON.stringify({ diaChi: '1', nguoiLap: 'Đỗ Thái Hưng', giamDoc: '2', kho: 'a3n' });      // giá trị cũ người dùng đã gõ tay
  c26.blMoIn();
  const hop26 = els26['blIn'].innerHTML;
  assert(/id="blInDc" value="1\/50 Thanh Đa, P\.27, Bình Thạnh"/.test(hop26), 'Địa chỉ lấy theo công ty (không dùng giá trị gõ tay cũ)');
  assert(/id="blInGd" value="Nguyễn Văn Kiên"/.test(hop26), 'Giám đốc lấy theo Tên người ký của công ty');
  assert(/id="blInLap" value="Đỗ Thái Hưng"/.test(hop26), 'Người lập biểu vẫn nhớ lần trước');
  assert(/đã lấy theo thông tin công ty/.test(hop26) && !/công ty chưa có địa chỉ/.test(hop26));
  assert(/<option value="a3n" selected>/.test(hop26), 'Nhớ khổ giấy');
  // dựng bản in dùng đúng thông tin công ty; không nhớ lại địa chỉ/giám đốc của công ty vào bộ nhớ
  els26['blInTu'].value = '5'; els26['blInDen'].value = '5'; els26['blInLuong'].checked = true; els26['blInCong'].checked = true; els26['blInKho'].value = 'a4n';
  els26['blInDc'].value = '1/50 Thanh Đa, P.27, Bình Thạnh'; els26['blInLap'].value = 'Đỗ Thái Hưng'; els26['blInGd'].value = 'Nguyễn Văn Kiên';
  c26.blDL = { '05': [dongMau('2', 'Trần A', { ngay_lam_hd: 26, ngay_cong_hd: 26, luong: 5310000, tt_luong: 5310000 })] };
  const kq26 = c26.blChuanBiIn();
  assert(kq26.html.includes('ĐC: 1/50 Thanh Đa, P.27, Bình Thạnh') && kq26.html.includes('Nguyễn Văn Kiên') && kq26.html.includes('Đỗ Thái Hưng'));
  const saved26 = JSON.parse(m.luuTru['blIn7']); assert.strictEqual(saved26.diaChi, ''); assert.strictEqual(saved26.giamDoc, ''); assert.strictEqual(saved26.nguoiLap, 'Đỗ Thái Hưng');
  // công ty chưa nhập: dùng giá trị gõ ở hộp in và nhớ lại; hiện nhắc nhập
  c26.companies = [{ id: 7, ten: 'CÔNG TY A', mst: '031', dia_chi: '', nguoi_ky: '' }];
  els26['blIn'].style.display = 'none'; m.luuTru['blIn7'] = JSON.stringify({ diaChi: 'ĐC gõ tay', nguoiLap: 'L', giamDoc: 'GĐ gõ tay', kho: 'a4n' });
  c26.blMoIn();
  assert(/id="blInDc" value="ĐC gõ tay"/.test(els26['blIn'].innerHTML) && /id="blInGd" value="GĐ gõ tay"/.test(els26['blIn'].innerHTML));
  assert(/công ty chưa có địa chỉ/.test(els26['blIn'].innerHTML) && /chưa có tên người ký/.test(els26['blIn'].innerHTML));
  els26['blInDc'].value = 'ĐC mới'; els26['blInGd'].value = 'GĐ mới'; c26.blChuanBiIn();
  assert.strictEqual(JSON.parse(m.luuTru['blIn7']).diaChi, 'ĐC mới'); assert.strictEqual(JSON.parse(m.luuTru['blIn7']).giamDoc, 'GĐ mới');
  console.log('PASS 26: địa chỉ + giám đốc trong bản in/Excel lấy theo thông tin công ty đã nhập.');

  console.log('\nALL DONE');
})().catch((e) => { console.error(e); process.exit(1); });
