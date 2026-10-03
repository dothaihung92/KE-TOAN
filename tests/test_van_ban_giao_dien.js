// Giao diện Hợp đồng lao động / Quy chế lương / Thang bảng lương (Nhập Liệu -> Bảng Lương - BHXH): chạy ĐÚNG code JS trong static/index.html.
const fs = require('fs'), path = require('path'), assert = require('assert'), vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'index.html'), 'utf8');

// 1: 3 ô mới nằm cạnh Danh Sách Nhân Viên / Người Phụ Thuộc / Bảng Lương
const iMo = html.indexOf('function moBangLuong(){');
const thanMo = html.slice(iMo, html.indexOf('function moVanBan', iMo));
for (const [loai, ten] of [['hd', 'Hợp Đồng Lao Động'], ['tv', 'Hợp Đồng Thử Việc'], ['qc', 'Quy Chế Lương'], ['tl', 'Thang Bảng Lương']])
  assert(thanMo.includes(`onclick="moVanBan('${loai}')"`) && thanMo.includes(ten), 'thiếu ô ' + ten);
assert(thanMo.includes('moDanhSachNhanVien()') && thanMo.includes('moNguoiPhuThuoc()') && thanMo.includes('moBangLuongNam()'));
console.log('PASS 1: 3 ô mới có trong Bảng Lương - BHXH.');

const b0 = html.indexOf('/* ----- HỢP ĐỒNG LAO ĐỘNG / QUY CHẾ LƯƠNG / THANG BẢNG LƯƠNG');
const b1 = html.indexOf('function moDanhSachNhanVien', b0);
assert(b0 > 0 && b1 > b0);
const khoi = html.slice(b0, b1).replace(/^let (vb\w+)/gm, 'var $1');
function moiTruong(giaTri = {}) {
  const goi = [], pt = {};
  const el = (id) => !(id in giaTri) && !(('c:' + id) in giaTri) ? null : pt[id] || (pt[id] = { id, value: giaTri[id] === undefined ? '' : giaTri[id], checked: !!giaTri['c:' + id], style: {}, classList: { toggle() {} }, innerHTML: '', textContent: '' });
  const ctx = { current: 7, console, toast() {}, document: { getElementById: el, querySelectorAll: () => [] }, localStorage: { getItem: () => null },
    api: async (u, o) => { goi.push([u, o && o.body ? JSON.parse(o.body) : null]); return {}; }, nlDMMode: null };
  vm.createContext(ctx); vm.runInContext(khoi, ctx);
  return { ctx, goi, pt };
}

// 2: trang in dùng ĐÚNG css/html đang xem; khổ A4 dọc/ngang + lề theo canh chỉnh; biến phông/cỡ/giãn dòng
{
  const { ctx } = moiTruong();
  const t = { font: 'Arial', size: 12, line: 1.3, le: [25, 20, 35, 15], ngang: false, tieu_de: 'Hợp đồng <x>' };
  const d = ctx.vbHtmlIn('.vb-doc p{margin:0}', '<section class="vb-trang"><p>Nội dung ĐÃ SỬA</p></section>', t);
  assert(d.includes('@page{size:A4 portrait;margin:25mm 15mm 20mm 35mm}'), d);
  assert(d.includes("--vb-f:'Arial';--vb-s:12pt;--vb-l:1.3;--vb-mt:25mm;--vb-mb:20mm;--vb-ml:35mm;--vb-mr:15mm"));
  assert(d.includes('Nội dung ĐÃ SỬA') && d.includes('.vb-doc p{margin:0}') && d.includes('<body class="vb-doc"') && d.includes('<title>Hợp đồng &lt;x&gt;</title>'));
  assert(ctx.vbHtmlIn('', '', Object.assign({}, t, { ngang: true })).includes('size:A4 landscape'));
}
console.log('PASS 2: trang in đúng css/html/khổ giấy/lề.');

// 3: đọc canh chỉnh + tuỳ chọn từ form
{
  const { ctx } = moiTruong({ vb_font: 'Tahoma', vb_size: '12,5', vb_line: '1.5', vb_mt: '10', vb_mb: '11', vb_ml: '12', vb_mr: '13', 'c:vb_ngang': true });
  const t = ctx.vbDocTrang();
  assert.deepStrictEqual(JSON.parse(JSON.stringify(t)), { font: 'Tahoma', size: 12.5, line: 1.5, le: [10, 11, 12, 13], ngang: true });
  const k = moiTruong({ vb_nguoi_ky: ' Hồ Thị Cẩm Vân ', vb_ngay_tra: '10', vb_vung: '2', 'c:vb_kem_phu_luc': true, 'c:vb_pl_hieu_hy': true, vb_pl_hieu_hy_1: '1000000', vb_pl_hieu_hy_2: '500000' });
  k.ctx.vbLoai = 'qc';
  const tc = JSON.parse(JSON.stringify(k.ctx.vbTuyChon()));
  assert.strictEqual(tc.nguoi_ky, 'Hồ Thị Cẩm Vân'); assert.strictEqual(tc.ngay_tra, '10'); assert.strictEqual(tc.vung, '2'); assert.strictEqual(tc.kem_phu_luc, true);
  assert.deepStrictEqual(tc.phuc_loi.hieu_hy, { bat: true, m1: '1000000', m2: '500000' });
  assert(!('tham_nien' in tc.phuc_loi), 'khoản không có trên màn hình thì không gửi');
  assert(!('ngay_ky' in tc), 'ô không có trên màn hình thì không gửi');
}
console.log('PASS 3: đọc canh chỉnh + tuỳ chọn.');

// 4: tạo xem trước gọi đúng API (hợp đồng gửi khoảng từ-đến); xuất Word gửi đúng HTML đã sửa
(async () => {
  const { ctx, goi, pt } = moiTruong({ vb_tu: '2', vb_den: '4', vb_font: 'Times New Roman', vb_size: '13', vb_line: '1.15', vb_mt: '20', vb_mb: '20', vb_ml: '30', vb_mr: '15' });
  ctx.api = async (u, o) => { goi.push([u, JSON.parse(o.body)]); return { html: '<section class="vb-trang"><p>HĐ</p></section>', css: '.x{}', trang: { font: 'Times New Roman', size: 13, line: 1.15, le: [20, 20, 30, 15], ngang: false }, so_van_ban: 3 }; };
  const xem = { id: 'vbXem', innerHTML: '', setAttribute() {}, querySelectorAll: () => [], scrollIntoView() {} };
  const phan = { vbXem: xem, vbThongTin: { textContent: '' }, vbStyle: { textContent: '' }, vbCongCu: { style: {} }, vb_ngang: { checked: false } };
  const got = ctx.document.getElementById;
  ctx.document.getElementById = (id) => phan[id] || got(id);
  ctx.vbLoai = 'hd'; ctx.vbNam = 2026;
  await ctx.vbTaoXemTruoc();
  assert.strictEqual(goi[0][0], '/api/van-ban/7/xem-truoc');
  assert.strictEqual(goi[0][1].loai, 'hd'); assert.strictEqual(goi[0][1].tu, 2); assert.strictEqual(goi[0][1].den, 4); assert.strictEqual(goi[0][1].nam, 2026);
  assert(xem.innerHTML.includes('HĐ') && phan.vbThongTin.textContent.includes('3 hợp đồng') && phan.vbCongCu.style.display === 'block');
  // xuất Word: gửi đúng innerHTML đang hiển thị (đã sửa tay) + canh chỉnh
  xem.innerHTML = '<section class="vb-trang"><p>ĐÃ SỬA TAY</p></section>';
  let gui = null, tai = null;
  ctx.fetch = async (u, o) => { gui = [u, JSON.parse(o.body)]; return { ok: true, headers: { get: () => '1' } }; };
  ctx.xuatFile = async (r, ten) => { tai = ten; };
  await ctx.vbXuatWord();
  assert.strictEqual(gui[0], '/api/van-ban/7/word'); assert(gui[1].html.includes('ĐÃ SỬA TAY')); assert.strictEqual(gui[1].trang.size, 13);
  assert.strictEqual(tai, 'HopDongLaoDong_2026.docx');
  console.log('PASS 4: xem trước / xuất Word gọi đúng API với nội dung đã sửa.');
})().catch((e) => { console.error(e); process.exit(1); });

// 5: Danh Sách Nhân Viên — Chức vụ chỉ chọn theo thang bảng lương; "Lấy lương theo Bảng Lương năm" cập nhật lương cơ bản + phụ cấp
(async () => {
  const n0 = html.indexOf('const NV_HEADERS='), n1 = html.indexOf('function moBangLuong(){');
  const m0 = html.indexOf('function moDanhSachNhanVien'), m1 = html.indexOf('/* ----- NGƯỜI PHỤ THUỘC');
  assert(n0 > 0 && m0 > n1 && m1 > m0);
  const src = (html.slice(n0, n1) + html.slice(m0, m1)).replace(/^let (nv\w+)/gm, 'var $1').replace(/^const NV_HEADERS/m, 'var NV_HEADERS');
  const wrap = { innerHTML: '' }, toasts = [], goi = [];
  const ctx = { current: 7, console, toast: (m, k) => toasts.push([m, k]), document: { getElementById: (id) => id === 'nvTableWrap' ? wrap : null, querySelector: () => null },
    localStorage: { getItem: () => '2026' }, prompt: () => '2026', confirm: () => true, fetch: async () => ({}), nlDMMode: null,
    api: async (u) => { goi.push(u); return { nguoi: [{ ma: '2', ten: 'A', luong_cb: 6500000, tien_com: 730000, xang_xe: 500000, dien_thoai: 300000, trang_phuc: 0 },
                                                  { ma: '', ten: 'Nguyễn Giang Nam', luong_cb: 7000000, tien_com: 700000, xang_xe: 0, dien_thoai: 0, trang_phuc: 400000 },
                                                  { ma: '99', ten: 'Không có trong danh sách', luong_cb: 1 }] }; } };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  vm.runInContext(`nvHeader = NV_HEADERS.slice(); nvChucDanh = ['Giám đốc','Nhân viên kinh doanh'];
    nvRows = [['1','2','Trần Minh Hùng','','','','','','x','','Kinh Doanh','5.310.000','700.000','500.000','500.000','400.000'],
              ['2','3','Nguyễn Giang Nam','','','','','','x','','Giám đốc','5.310.000','700.000','0','0','0']]; veGridNhanVien();`, ctx);
  const h = wrap.innerHTML;
  assert(h.includes('— chọn chức vụ —') && h.includes('<option value="Giám đốc" selected>'), 'Chức vụ phải là ô chọn theo thang bảng lương');
  assert(h.includes('⚠ Kinh Doanh (chưa có trong thang bảng lương)'), 'chức vụ cũ không có trong thang lương phải được cảnh báo, không mất');
  // không có thang lương (chưa tải được) -> vẫn là ô gõ tự do
  vm.runInContext(`nvChucDanh = []; veGridNhanVien();`, ctx);
  assert(!wrap.innerHTML.includes('— chọn chức vụ —') && wrap.innerHTML.includes('Kinh Doanh'));
  vm.runInContext(`nvChucDanh = ['Giám đốc','Nhân viên kinh doanh']; nvDoiChucVu(0, nvHeader.indexOf('Chức vụ'), 'Nhân viên kinh doanh')`, ctx);
  assert.strictEqual(vm.runInContext('nvRows[0][nvHeader.indexOf("Chức vụ")]', ctx), 'Nhân viên kinh doanh');
  await ctx.nvLayLuongTheoNam();
  assert(goi[0] === '/api/van-ban/7/luong-theo-nam?nam=2026', goi[0]);
  const r = JSON.parse(vm.runInContext('JSON.stringify(nvRows)', ctx));
  const c = (t) => vm.runInContext(`nvHeader.indexOf(${JSON.stringify(t)})`, ctx);
  assert.deepStrictEqual([r[0][c('Lương Cơ bản')], r[0][c('PC Tiền cơm')], r[0][c('PC Xăng xe')], r[0][c('PC Điện thoại')], r[0][c('PC Trang phục')]], ['6.500.000', '730.000', '500.000', '300.000', '0'], 'khớp theo Mã NV');
  assert.deepStrictEqual([r[1][c('Lương Cơ bản')], r[1][c('PC Tiền cơm')], r[1][c('PC Trang phục')]], ['7.000.000', '700.000', '400.000'], 'không có mã thì khớp theo Họ và tên');
  assert(toasts.some(([m]) => m.includes('cho 2/2 nhân viên')), JSON.stringify(toasts));
  console.log('PASS 5: Chức vụ chọn theo thang bảng lương + lấy lương theo Bảng Lương từng năm.');
})().catch((e) => { console.error(e); process.exit(1); });

// 6: Danh Sách Nhân Viên — nút ＋ thêm dòng thay đổi lương (mã gốc-001, -002…), cột "Tháng/Năm thay đổi lương"
(() => {
  const n0 = html.indexOf('const NV_HEADERS='), n1 = html.indexOf('function moBangLuong(){');
  const m0 = html.indexOf('function moDanhSachNhanVien'), m1 = html.indexOf('/* ----- NGƯỜI PHỤ THUỘC');
  const a0 = html.indexOf('const NV_COT_DOI_LUONG'), a1 = html.indexOf('const NV_COT_NGHI', a0);
  const src = (html.slice(n0, n1) + html.slice(m0, m1)).replace(/^let (nv\w+)/gm, 'var $1').replace(/^const NV_HEADERS/m, 'var NV_HEADERS');
  const wrap = { innerHTML: '' }, toasts = [];
  const ctx = { current: 7, console, toast: (m, k) => toasts.push([m, k]), document: { getElementById: (id) => id === 'nvTableWrap' ? wrap : null, querySelector: () => ({ focus() {} }) }, localStorage: { getItem: () => null }, confirm: () => true, nlDMMode: null };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  const ex = (c) => vm.runInContext(c, ctx);
  assert(a0 > 0 && a1 > a0);
  assert.deepStrictEqual(JSON.parse(ex('JSON.stringify(NV_HEADERS.slice(10,14))')), ['Chức vụ', 'Tháng/Năm thay đổi lương', 'Thử việc từ', 'Thử việc đến'], 'cột mới nằm ngay sau Chức vụ');
  // danh sách cũ chưa có cột -> tự thêm cột trống đúng vị trí
  ex(`nvHeader = NV_HEADERS.filter(h => !['Tháng/Năm thay đổi lương', 'Thử việc từ', 'Thử việc đến'].includes(h)); nvRows = [['1','2','Hùng','','','','','12/2024','x','','KD','5.310.000','700.000','0','0','0']]; nvThemCotDoiLuong(); nvThemCotThuViec();`);
  assert.strictEqual(ex('nvHeader.indexOf("Tháng/Năm thay đổi lương")'), 11); assert.strictEqual(ex('nvHeader.indexOf("Thử việc đến")'), 13);
  assert.strictEqual(ex('nvRows[0].length'), ex('nvHeader.length'));
  assert.strictEqual(ex('nvRows[0][14]'), '5.310.000', 'dữ liệu các cột sau không bị lệch');
  ex(`nvThemCotDoiLuong(); nvThemCotThuViec(); nvChucDanh = [];`);
  assert.strictEqual(ex('nvHeader.length'), 19, 'không thêm cột lần 2');
  // ＋ ở dòng 0 -> thêm dòng mã 2-001 ngay dưới, xoá tháng thay đổi + nghỉ việc, giữ lương cũ để sửa
  ex(`nvRows[0][9] = '06/2026'; nvRows.push(['2','3','Nam','','','','','12/2024','x','','KD','','5.310.000','0','0','0','0']); nvThemPhienBan(0)`);
  assert.deepStrictEqual(JSON.parse(ex('JSON.stringify(nvRows.map(r => r[1]))')), ['2', '2-001', '3']);
  assert.strictEqual(ex('nvRows[1][9]'), '', 'dòng mới: chưa có tháng nghỉ việc');
  assert.strictEqual(ex('nvRows[1][11]'), '', 'dòng mới: chờ nhập Tháng/Năm thay đổi lương');
  assert.strictEqual(ex('nvRows[1][14]'), '5.310.000', 'dòng mới sao chép lương cũ để sửa');
  assert.strictEqual(ex('nvRows[0][0]'), 1); assert.strictEqual(ex('nvRows[2][0]'), 3, 'STT đánh lại');
  // ＋ lần nữa (từ dòng gốc hoặc từ dòng -001) -> -002, xếp sau -001, trước người khác
  ex('nvThemPhienBan(1)');
  assert.deepStrictEqual(JSON.parse(ex('JSON.stringify(nvRows.map(r => r[1]))')), ['2', '2-001', '2-002', '3']);
  ex('nvThemPhienBan(0)');
  assert.deepStrictEqual(JSON.parse(ex('JSON.stringify(nvRows.map(r => r[1]))')), ['2', '2-001', '2-002', '2-003', '3']);
  // người chưa có Mã NV -> báo lỗi, không thêm
  const so = ex('nvRows.length'); ex(`nvRows[4][1] = ''; nvThemPhienBan(4)`);
  assert.strictEqual(ex('nvRows.length'), so); assert(toasts.some(([m, k]) => k === 'err' && m.includes('Mã NV')));
  // lưới: có cột ＋ ở đầu mỗi dòng, dòng thay đổi lương (có tháng) tô nền nhạt
  ex(`nvRows[1][11] = '01/2027'; veGridNhanVien();`);
  assert((wrap.innerHTML.match(/nvThemPhienBan\(/g) || []).length === 5 && wrap.innerHTML.includes('background:#fffaf0'));
  assert.strictEqual(ex('nvMaGoc("2-001")'), '2'); assert.strictEqual(ex('nvMaGoc("NV-12")'), 'NV-12');
  console.log('PASS 6: ＋ thêm dòng thay đổi lương (mã -001…), cột Tháng/Năm thay đổi lương.');
})();

// 7: Kho chữ ký — thao tác theo chỉ số (tên có dấu ' không làm hỏng nút), lưu phải kèm xác nhận đồng ý
(async () => {
  const { ctx, goi, pt } = moiTruong({ vbKhoCk: '' });
  ctx.api = async (u, o) => {
    goi.push([u, o && o.body ? JSON.parse(o.body) : null, o && o.method]);
    if (u.startsWith('/api/chu-ky/7?nam=')) return { giam_doc: { khoa: 'giam_doc', ten: 'Hồ Thị Cẩm Vân', ma: '', chuc_vu: '', co_anh: true, xac_nhan: true, anh: 'data:image/png;base64,AAA' },
      nhan_vien: [{ khoa: 'ma:3', ten: "Nguyễn D'Arc", ma: '3', chuc_vu: 'KD', co_anh: false, xac_nhan: false, anh: '' }] };
    return { ok: true };
  };
  ctx.vbNam = 2026;
  await ctx.vbCkVe();
  const h = pt.vbKhoCk.innerHTML;
  assert(h.includes('onclick="vbCkMoPad(1)"') && h.includes('onclick="vbCkTai(1)"') && h.includes('vbCkXacNhan(0,this.checked)'), 'nút thao tác theo chỉ số');
  assert(!/onclick="[^"]*D'Arc/.test(h) && !/onclick="[^"]*Nguy/.test(h), 'tên không nằm trong onclick');
  assert(h.includes('<img src="data:image/png;base64,AAA"') && h.includes('disabled'), 'có ảnh thì hiện; chưa có ảnh thì không cho tick đồng ý');
  await ctx.vbCkGui('ma:3', 'A', 'data:image/png;base64,BBB', true);
  assert.deepStrictEqual(goi.pop().slice(0, 3), ['/api/chu-ky/7', { khoa: 'ma:3', ten: 'A', anh: 'data:image/png;base64,BBB', xac_nhan: true }, 'POST']);
  await ctx.vbCkXacNhan(0, false);
  const g = goi.find((x) => x[2] === 'POST' && x[1] && x[1].khoa === 'giam_doc');
  assert(g && g[1].xac_nhan === false && !('anh' in g[1]), 'bỏ đồng ý: chỉ gửi xác nhận, không gửi lại ảnh');
  ctx.confirm = () => true; await ctx.vbCkXoa(1);
  assert(goi.some((x) => x[2] === 'DELETE' && x[0] === '/api/chu-ky/7?khoa=ma%3A3'));
  // ký trên màn hình: chưa ký / chưa tick đồng ý -> không lưu
  const toasts = []; ctx.toast = (m, k) => toasts.push([m, k]);
  ctx.vbCkIdx = 1; ctx.vbCkPad = { co: false, cv: { toDataURL: () => 'data:image/png;base64,CCC' } };
  const so = goi.length; await ctx.vbCkPadLuu();
  assert.strictEqual(goi.length, so); assert(toasts.some(([m]) => m.includes('ký vào khung')));
  ctx.vbCkPad.co = true; const gd = ctx.document.getElementById; ctx.document.getElementById = (id) => id === 'vbCkDongY' ? { checked: false } : gd(id);
  await ctx.vbCkPadLuu(); assert.strictEqual(goi.length, so); assert(toasts.some(([m]) => m.includes('xác nhận')));
  console.log('PASS 7: Kho chữ ký — thao tác theo chỉ số, bắt buộc xác nhận đồng ý.');
})().catch((e) => { console.error(e); process.exit(1); });

// 8: Kho chữ ký có ngay trong Danh Sách Nhân Viên (nút + vùng hiển thị dùng chung với màn Hợp đồng)
{
  const m0 = html.indexOf('function moDanhSachNhanVien'), m1 = html.indexOf('/* ----- NGƯỜI PHỤ THUỘC');
  const khoi = html.slice(m0, m1);
  assert(khoi.includes('onclick="nvMoKhoCk()"') && khoi.includes('id="vbKhoCk"') && /function nvMoKhoCk\(\)\{[^}]*vbMoKhoCk\(\)/.test(khoi));
  console.log('PASS 8: Kho chữ ký trong Danh Sách Nhân Viên.');
}

// 9: chọn nhiều chữ ký 1 lần — ghép tên file với nhân viên
(async () => {
  const { ctx, goi } = moiTruong({ vbKhoCk: '' });
  const muc = [{ khoa: 'gd:ho thi cam van', ten: 'Hồ Thị Cẩm Vân', ma: '' }, { khoa: 'cccd:1', ten: 'Trần Minh Hùng', ma: '2' }, { khoa: 'cccd:2', ten: 'Nguyễn Giang Nam', ma: '3' }, { khoa: 'cccd:3', ten: 'Nguyễn Giang', ma: '10' }];
  const k = (f) => ctx.vbCkKhopTen(f, muc);
  assert.strictEqual(k('2.png'), 1, 'tên file = mã NV'); assert.strictEqual(k('NV-2_chu_ky.jpg'), 1, 'mã NV là 1 từ trong tên file');
  assert.strictEqual(k('Tran Minh Hung.png'), 1, 'họ tên không dấu'); assert.strictEqual(k('chuky_trần_minh_hùng.png'), 1, 'họ tên có dấu, gạch dưới');
  assert.strictEqual(k('Nguyen Giang Nam.png'), 2, 'khi 2 tên cùng khớp: lấy tên dài hơn'); assert.strictEqual(k('giam doc.png'), 0); assert.strictEqual(k('GD.png'), 0);
  assert.strictEqual(k('abc.png'), -1); assert.strictEqual(k('12.png'), -1, 'mã 12 không có');
  // lưu: 1 người nhiều file lấy file cuối; bắt buộc xác nhận
  ctx.vbCkMuc = muc; ctx.vbCkNhieuDs = [{ ten: 'a', anh: 'data:image/png;base64,A', idx: 1 }, { ten: 'b', anh: 'data:image/png;base64,B', idx: 1 }, { ten: 'c', anh: 'data:image/png;base64,C', idx: -1 }, { ten: 'd', anh: 'data:image/png;base64,D', idx: 0 }];
  const toasts = []; ctx.toast = (m, kk) => toasts.push([m, kk]);
  const gd = ctx.document.getElementById; let dongy = false; ctx.document.getElementById = (id) => id === 'vbCkNhieuDongY' ? { checked: dongy } : id === 'vbCkNhieuKq' ? { innerHTML: '' } : gd(id);
  ctx.api = async (u, o) => { goi.push([u, o && o.body ? JSON.parse(o.body) : null]); return u.endsWith('/nhieu') ? { da_luu: 2, loi: [] } : { giam_doc: muc[0], nhan_vien: [], tong_kho_chung: 0 }; };
  await ctx.vbCkNhieuLuu(); assert(!goi.length && toasts.some(([m]) => m.includes('xác nhận')));
  dongy = true; await ctx.vbCkNhieuLuu();
  const g = goi.find((x) => x[0].endsWith('/nhieu'));
  assert(g && g[1].du.length === 2 && g[1].du.map((x) => x.ten).join() === 'a,c' && g[1].xac_nhan === true && g[1].muc.length === 2 && g[1].muc.find((x) => x.khoa === 'cccd:1').anh.endsWith('B') && g[1].muc.find((x) => x.khoa === 'gd:ho thi cam van'));
  console.log('PASS 9: chọn nhiều chữ ký — tự ghép tên file, bắt buộc xác nhận, lưu 1 lần.');
})().catch((e) => { console.error(e); process.exit(1); });

// 10: bản in bảng lương — chữ ký trong Kho gắn vào cột Ký nhận + chỗ ký giám đốc (chỉ chữ ký đã xác nhận do server trả về)
(() => {
  const b0 = html.indexOf('let blChuKyIn=null;'), b1 = html.indexOf('function blDocTuyChonIn');
  assert(b0 > 0 && b1 > b0);
  const calls = [];
  const ctx = { current: 7, blNam: 2026, console, api: async (u) => { calls.push(u); return { giam_doc: 'data:image/png;base64,GD', nhan_vien: [{ ma: '2', ten: 'Trần Minh Hùng', anh: 'data:image/png;base64,A' }, { ma: '', ten: 'Nguyễn Giang Nam', anh: 'data:image/png;base64,B' }] }; } };
  vm.createContext(ctx); vm.runInContext(html.slice(b0, b1).replace(/^let (bl\w+)/gm, 'var $1').replace(/^let blInKq=null;/m, 'var blInKq=null;'), ctx);
  assert.strictEqual(ctx.blAnhKy('2', 'x'), '', 'chưa nạp: không có ảnh');
  ctx.blNapChuKyIn();
  return new Promise((ok) => setTimeout(() => {
    assert.deepStrictEqual(calls, ['/api/chu-ky/7/in?nam=2026']);
    assert.strictEqual(ctx.blAnhKy('2', 'khác'), 'data:image/png;base64,A', 'khớp mã');
    assert.strictEqual(ctx.blAnhKy('2-001', 'khác'), 'data:image/png;base64,A', 'mã đổi 2-001 vẫn là người đó');
    assert.strictEqual(ctx.blAnhKy('99', 'nguyen giang nam'), 'data:image/png;base64,B', 'khớp họ tên không dấu');
    assert.strictEqual(ctx.blAnhKy('99', 'Người lạ'), '');
    const iBang = html.indexOf('function blDungBangLuongIn'), iHet = html.indexOf('// Trang "BẢNG CHẤM CÔNG', iBang);
    const hBang = html.slice(iBang, iHet);
    assert(hBang.includes('class="ky-nhan"') && hBang.includes('blAnhKy(r.ma,r.ten)'), 'cột Ký nhận chèn ảnh');
    const iKy = html.indexOf('function blKhungKy'); assert(html.slice(iKy, iKy + 900).includes('blChuKyIn.giam_doc') && html.includes('.o-ky{height:80px'), 'chỗ ký giám đốc rộng hơn + ảnh');
    console.log('PASS 10: chữ ký trong Kho gắn vào bản in bảng lương.');
    ok();
  }, 30));
})();

// 11: bảng ghép nhiều chữ ký — người đã có chữ ký / đã được ghép ở dòng khác không hiện trong danh sách chọn
(() => {
  const { ctx, pt } = moiTruong({ vbCkNhieuKq: '' });
  ctx.vbCkMuc = [{ khoa: 'gd:x', ten: 'Giám Đốc', ma: '', co_anh: true }, { khoa: 'cccd:1', ten: 'Trần Minh Hùng', ma: '2', co_anh: true }, { khoa: 'cccd:2', ten: 'Nguyễn Giang Nam', ma: '3', co_anh: false }, { khoa: 'cccd:3', ten: 'Lê Văn C', ma: '4', co_anh: false }];
  assert.strictEqual(ctx.vbCkKhopTen('Tran Minh Hung.png', ctx.vbCkMuc), 1);
  ctx.vbCkNhieuDs = [{ ten: 'a.png', anh: 'data:image/png;base64,A', idx: 2 }, { ten: 'b.png', anh: 'data:image/png;base64,B', idx: -1 }];
  ctx.vbCkNhieuVe();
  const h = pt.vbCkNhieuKq.innerHTML;
  const sel = h.split('<select');
  assert(!h.includes('Trần Minh Hùng') && !h.includes('Giám đốc: '), 'người đã có chữ ký bị ẩn');
  assert(sel[1].includes('Nguyễn Giang Nam') && sel[1].includes('Lê Văn C'), 'dòng 1 giữ lựa chọn của mình + còn người chưa ghép');
  assert(!sel[2].includes('Nguyễn Giang Nam') && sel[2].includes('Lê Văn C'), 'người đã ghép ở dòng khác không hiện ở dòng này');
  console.log('PASS 11: ẩn người đã có chữ ký / đã ghép khỏi danh sách chọn.');
})();

// 12: hợp đồng lao động / thử việc không còn nút Kho chữ ký; chữ ký chưa gán gắn sau cho người khác
(async () => {
  const iV = html.indexOf('function vbVeMan'), iE = html.indexOf('function vbTuyChon', iV);
  const phan = html.slice(iV, iE);
  assert(phan.includes("(l==='hd'||l==='tv')?'':`<button class=\"btn sm\" style=\"background:#6b3fa0\" onclick=\"vbMoKhoCk()\""), 'ẩn nút Kho chữ ký ở hợp đồng lao động + thử việc (qc/tl vẫn có)');
  const { ctx, goi } = moiTruong({ vbCkDuSel0: '3' });
  ctx.vbCkMuc = [{ khoa: 'gd:x', ten: 'GĐ', co_anh: true }, { khoa: 'cccd:1', ten: 'A', co_anh: true }, { khoa: 'cccd:2', ten: 'B', co_anh: false }, { khoa: 'cccd:3', ten: 'Người mới', ma: '9', co_anh: false }];
  ctx.vbCkDu = [{ id: 5, ten: 'chu_ky_20.png', anh: 'data:image/png;base64,Z' }];
  ctx.api = async (u, o) => { goi.push([u, o && o.body ? JSON.parse(o.body) : null, o && o.method]); return u.includes('?nam=') ? { giam_doc: ctx.vbCkMuc[0], nhan_vien: ctx.vbCkMuc.slice(1), du: [] } : { ok: true }; };
  ctx.confirm = () => false; await ctx.vbCkGanDu(0); assert(!goi.length, 'không xác nhận thì không gắn');
  ctx.confirm = () => true; await ctx.vbCkGanDu(0);
  const g = goi.find((x) => x[0].endsWith('/gan-du'));
  assert(g && g[1].id === 5 && g[1].khoa === 'cccd:3' && g[1].xac_nhan === true);
  console.log('PASS 12: ẩn Kho chữ ký ở hợp đồng; gắn chữ ký chưa gán cho người mới.');
})().catch((e) => { console.error(e); process.exit(1); });

// 13: mục "Chữ ký chưa gán" luôn hiện kèm số lượng (kể cả 0) trong Kho chữ ký
(async () => {
  for (const du of [[], [{ id: 1, ten: 'a.png', anh: 'data:image/png;base64,A' }, { id: 2, ten: 'b.png', anh: 'data:image/png;base64,B' }]]) {
    const { ctx, pt } = moiTruong({ vbKhoCk: '' });
    ctx.api = async () => ({ giam_doc: { khoa: 'giam_doc', ten: 'GĐ', co_anh: true, xac_nhan: true, anh: 'data:image/png;base64,G' }, nhan_vien: [{ khoa: 'ma:3', ten: 'B', ma: '3', co_anh: false, anh: '' }], tong_kho_chung: 3, du });
    ctx.vbNam = 2026; await ctx.vbCkVe();
    const h = pt.vbKhoCk.innerHTML, n = du.length;
    assert(h.includes('Chữ ký chưa gán:') && h.includes(`id="vbCkDuSo" style="color:${n ? '#6b3fa0' : '#666'}">${n}</span> chữ ký`), 'luôn hiện mục + số lượng');
    assert(h.includes(`<b>${n} chữ ký chưa gán</b>`), 'số lượng ở dòng đầu kho');
    assert.strictEqual(h.includes('vbCkGanDu(0)'), n > 0);
    assert.strictEqual(h.includes('Chưa có chữ ký nào chưa gán'), n === 0);
  }
  console.log('PASS 13: mục Chữ ký chưa gán luôn hiện kèm số lượng (kể cả 0).');
})().catch((e) => { console.error(e); process.exit(1); });
