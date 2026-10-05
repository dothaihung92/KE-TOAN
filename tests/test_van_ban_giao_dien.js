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
  assert.deepStrictEqual(JSON.parse(ex('JSON.stringify(NV_HEADERS.slice(10,16))')), ['Chức vụ', 'Tháng/Năm thay đổi lương', 'Thử việc từ', 'Thử việc đến', 'Part-time', 'Lương theo giờ'], 'cột mới nằm ngay sau Chức vụ');
  // danh sách cũ chưa có cột -> tự thêm cột trống đúng vị trí
  ex(`nvHeader = NV_HEADERS.filter(h => !['Tháng/Năm thay đổi lương', 'Thử việc từ', 'Thử việc đến', 'Part-time', 'Lương theo giờ'].includes(h)); nvRows = [['1','2','Hùng','','','','','12/2024','x','','KD','5.310.000','700.000','0','0','0']]; nvThemCotDoiLuong(); nvThemCotThuViec(); nvThemCotPartTime();`);
  assert.strictEqual(ex('nvHeader.indexOf("Tháng/Năm thay đổi lương")'), 11); assert.strictEqual(ex('nvHeader.indexOf("Thử việc đến")'), 13);
  assert.strictEqual(ex('nvRows[0].length'), ex('nvHeader.length'));
  assert.strictEqual(ex('nvRows[0][16]'), '5.310.000', 'dữ liệu các cột sau không bị lệch'); assert.strictEqual(ex('nvHeader.indexOf("Part-time")'), 14); assert.strictEqual(ex('nvHeader.indexOf("Lương theo giờ")'), 15);
  ex(`nvThemCotDoiLuong(); nvThemCotThuViec(); nvThemCotPartTime(); nvChucDanh = [];`);
  assert.strictEqual(ex('nvHeader.length'), 21, 'không thêm cột lần 2');
  // ＋ ở dòng 0 -> thêm dòng mã 2-001 ngay dưới, xoá tháng thay đổi + nghỉ việc, giữ lương cũ để sửa
  ex(`nvRows[0][9] = '06/2026'; nvRows.push(['2','3','Nam','','','','','12/2024','x','','KD','','5.310.000','0','0','0','0']); nvThemPhienBan(0)`);
  assert.deepStrictEqual(JSON.parse(ex('JSON.stringify(nvRows.map(r => r[1]))')), ['2', '2-001', '3']);
  assert.strictEqual(ex('nvRows[1][9]'), '', 'dòng mới: chưa có tháng nghỉ việc');
  assert.strictEqual(ex('nvRows[1][11]'), '', 'dòng mới: chờ nhập Tháng/Năm thay đổi lương');
  assert.strictEqual(ex('nvRows[1][16]'), '5.310.000', 'dòng mới sao chép lương cũ để sửa');
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
  assert(phan.includes("(l==='hd'||l==='tv'||l==='pt')?'':`<button class=\"btn sm\" style=\"background:#6b3fa0\" onclick=\"vbMoKhoCk()\""), 'ẩn nút Kho chữ ký ở hợp đồng lao động + thử việc (qc/tl vẫn có)');
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

// 14: sang công ty khác — chữ ký đã lưu (kho chung) của người chưa có trong danh sách được tính vào "Chữ ký chưa gán"
(async () => {
  const { ctx, goi, pt } = moiTruong({ vbKhoCk: '', vbCkDuSel1: '2' });
  const muc = [{ khoa: 'gd:x', ten: 'GĐ', co_anh: true }, { khoa: 'cccd:1', ten: 'A', co_anh: true }, { khoa: 'cccd:2', ten: 'Nguyễn B', ma: '5', co_anh: false }];
  ctx.api = async (u, o) => { goi.push([u, o && o.body ? JSON.parse(o.body) : null, o && o.method]); return u.includes('?nam=') ? { giam_doc: muc[0], nhan_vien: muc.slice(1), tong_kho_chung: 3, du: [{ id: 4, ten: 'chu_ky_1.png', anh: 'data:image/png;base64,Y' }], da_luu: [{ khoa: 'cccd:9', ten: 'Nguyen Van B', anh: 'data:image/png;base64,Z' }] } : { ok: true }; };
  ctx.vbNam = 2026; await ctx.vbCkVe();
  const h = pt.vbKhoCk.innerHTML;
  assert(h.includes('id="vbCkDuSo" style="color:#6b3fa0">2</span>') && h.includes('<b>2 chữ ký chưa gán</b>') && !h.includes('Chữ ký đã lưu dùng chung'), 'gộp vào Chữ ký chưa gán: 1 file dư + 1 chữ ký công ty khác = 2');
  assert(h.includes('(đã gắn ở công ty khác)') && h.split('vbCkXoaDu(').length === 3, 'chữ ký công ty khác có nhãn + nút xoá (chỉ ẩn ở công ty này)');
  ctx.confirm = () => false; await ctx.vbCkGanDu(1); assert(!goi.some((x) => x[0].endsWith('/dung-lai')), 'không xác nhận thì không dùng');
  ctx.confirm = (m) => { assert(m.includes('CÙNG MỘT NGƯỜI')); return true; }; await ctx.vbCkGanDu(1);
  const g = goi.find((x) => x[0].endsWith('/dung-lai'));
  assert(g && g[1].nguon_khoa === 'cccd:9' && g[1].khoa === 'cccd:2' && g[1].xac_nhan === true);
  goi.length = 0; ctx.vbCkDu = [{ loai: 'du', id: 4, ten: 'a.png' }, { loai: 'luu', khoa: 'cccd:9', ten: 'Nguyen Van B' }];
  let hoi = ''; ctx.confirm = (m) => { hoi = m; return true; };
  await ctx.vbCkXoaDu(1);
  assert(goi.some((x) => x[2] === 'DELETE' && x[0] === '/api/chu-ky/7/da-luu?khoa=cccd%3A9') && hoi.includes('CÔNG TY NÀY') && hoi.includes('công ty cũ'), 'xoá chữ ký công ty khác: chỉ ẩn ở công ty này');
  goi.length = 0; await ctx.vbCkXoaDu(0);
  assert(goi.some((x) => x[2] === 'DELETE' && x[0] === '/api/chu-ky/7/du?id=4'), 'file dư: xoá hẳn như cũ');
  console.log('PASS 14: chữ ký đã lưu ở công ty khác tính vào Chữ ký chưa gán; gắn phải xác nhận cùng một người.');
})().catch((e) => { console.error(e); process.exit(1); });

// 15: nút "Tải về" chữ ký — tải PNG đúng nội dung, đặt tên file theo tên người
(async () => {
  const { ctx, pt } = moiTruong({ vbKhoCk: '' });
  const png = 'data:image/png;base64,' + Buffer.from('PNGDATA').toString('base64');
  const muc = [{ khoa: 'gd:cty7', ten: 'Dương Thị Hiền', co_anh: true, anh: png }, { khoa: 'cccd:2', ten: 'Nguyễn B', co_anh: false, anh: '' }];
  ctx.api = async () => ({ giam_doc: muc[0], nhan_vien: [muc[1]], tong_kho_chung: 1, du: [{ id: 4, ten: 'chu_ky_12.png', anh: png }], da_luu: [{ khoa: 'cccd:9', ten: 'Nguyễn Hữu Hiệp', anh: png }] });
  ctx.vbNam = 2026; await ctx.vbCkVe();
  const h = pt.vbKhoCk.innerHTML;
  assert.strictEqual(h.split("vbCkTaiVe('muc'").length, 2, 'chỉ dòng đã có chữ ký mới có nút Tải về');
  assert(h.includes("vbCkTaiVe('du',0)") && h.includes("vbCkTaiVe('du',1)"), 'mục chưa gán có nút Tải về');
  const tai = []; let nd = null;
  ctx.URL = { createObjectURL: (b) => { nd = b; return 'blob:x'; }, revokeObjectURL() {} };
  ctx.Blob = class { constructor(p, o) { this.p = p; this.type = o.type; } };
  ctx.Uint8Array = Uint8Array; ctx.atob = (s) => Buffer.from(s, 'base64').toString('binary');
  ctx.setTimeout = (f) => 0;
  ctx.document.createElement = () => ({ click() { tai.push(this.download); }, remove() {} }); ctx.document.body = { appendChild() {} };
  ctx.vbCkTaiVe('muc', 0); ctx.vbCkTaiVe('du', 0); ctx.vbCkTaiVe('du', 1);
  assert.deepStrictEqual(tai, ['chu_ky_duong_thi_hien.png', 'chu_ky_chu_ky_12.png', 'chu_ky_nguyen_huu_hiep.png']);
  assert(nd.type === 'image/png' && Buffer.from(nd.p[0]).toString() === 'PNGDATA', 'nội dung PNG đúng');
  const toasts = []; ctx.toast = (m, k) => toasts.push(k); ctx.vbCkTaiVe('muc', 1); assert.deepStrictEqual(toasts, ['err'], 'chưa có ảnh thì báo lỗi');
  console.log('PASS 15: nút Tải về chữ ký.');
})().catch((e) => { console.error(e); process.exit(1); });

// 16: Esc trong các mục của "Bảng Lương - BHXH" -> quay về màn Bảng Lương - BHXH (không văng ra trang chọn loại)
(() => {
  const i0 = html.indexOf('function nlThoatManHinh'), i1 = html.indexOf('async function capNhatBadge', i0);
  assert(i0 > 0 && i1 > i0);
  const lanh = html.slice(i0, i1);
  assert(html.includes("if(content&&content.style.display!=='none'){nlThoatManHinh();}") && html.includes("e.stopPropagation();nlThoatManHinh();return;"), 'phím Esc toàn cục + trong ô lưới đều dùng nlThoatManHinh');
  const chay = (body, dom = {}) => {
    const log = [];
    const el = (id) => dom[id] || null;
    const ctx = { document: { getElementById: (id) => id === 'nhapLieuBody' ? { querySelector: (sel) => { assert(sel.includes('blQuayLai()') && sel.includes('moBangLuong()')); return body ? { click: () => log.push('click-' + body) } : null; } } : el(id) }, nlDMMode: null, dmDaSua: false, confirm: () => true, capNhatBadge() {} };
    vm.createContext(ctx); vm.runInContext(lanh.replace(/\bfunction quayLaiChonBangKe[\s\S]*$/, '') + '\nfunction quayLaiChonBangKe(){globalThis.__log.push("chon-loai")}', ctx);
    ctx.__log = log; vm.runInContext('globalThis.__log=__log', ctx); ctx.nlThoatManHinh(); return log;
  };
  assert.deepStrictEqual(chay('moBangLuong'), ['click-moBangLuong'], 'Danh sách NV / NPT / hợp đồng / quy chế / thang lương -> về Bảng Lương - BHXH');
  assert.deepStrictEqual(chay('blQuayLai'), ['click-blQuayLai'], 'Bảng lương -> về Bảng Lương - BHXH (có hỏi nếu chưa lưu)');
  assert.deepStrictEqual(chay(null), ['chon-loai'], 'đang ở màn Bảng Lương - BHXH (không có nút quay lại) -> về trang chọn loại như cũ');
  const rm = []; assert.deepStrictEqual(chay('moBangLuong', { vbCkPadWrap: { remove: () => rm.push(1) } }), [], 'hộp thoại ký đang mở: Esc chỉ đóng hộp thoại'); assert.strictEqual(rm.length, 1);
  assert.deepStrictEqual(chay('moBangLuong', { misaModal: { style: { display: 'flex' } } }), [], 'modal khác đang mở: để modal tự xử lý');
  console.log('PASS 16: Esc quay về Bảng Lương - BHXH.');
})();

// 17: Thang bảng lương — sửa tay Hệ số / Mức lương thì các bậc sau tự nhân theo (giữ tỉ lệ), hệ số = mức ÷ lương tối thiểu vùng
(() => {
  const dung = (hs, ml, co_hs = true) => {
    const tb = { dataset: { ltt: '5310000' } };
    const tao = (k, vals) => { const tr = { dataset: { k }, children: [], parentElement: tb, previousElementSibling: null, nextElementSibling: null };
      tr.children = [{ textContent: 'nhan', tagName: 'TD', parentElement: tr, closest: () => tb }].concat(vals.map((v) => ({ textContent: v, tagName: 'TD', parentElement: tr, closest: () => tb }))); tr.children.forEach((c) => { c.closest = (sel) => { assert.strictEqual(sel, 'table.tl-thang'); return tb; }; }); return tr; };
    const trMl = tao('ml', ml), trHs = co_hs ? tao('hs', hs) : null;
    if (trHs) { trHs.nextElementSibling = trMl; trMl.previousElementSibling = trHs; }
    return { trMl, trHs };
  };
  const { ctx } = moiTruong(); const tb = []; ctx.toast = (m, k) => tb.push([m, k]);
  const doc = (tr) => tr.children.slice(1).map((c) => c.textContent);
  // 1) sửa Mức lương bậc II: 5.575.500 -> 6.000.000 => bậc III..VII nhân tỉ lệ 6.000.000/5.575.500, hệ số = mức ÷ 5.310.000
  let { trMl, trHs } = dung(['1,00', '1,05', '1,10', '1,16'], ['5.310.000', '5.575.500', '5.854.275', '6.146.989']);
  let td = trMl.children[2]; ctx.vbTlVao(td); td.textContent = '6.000.000';
  assert.strictEqual(ctx.vbTlTinhLai(td), true);
  const ti = 6000000 / 5575500;
  assert.deepStrictEqual(doc(trMl), ['5.310.000', '6.000.000', Math.round(5854275 * ti).toLocaleString('vi-VN'), Math.round(6146989 * ti).toLocaleString('vi-VN')], 'bậc trước giữ nguyên, bậc sau nhân theo');
  assert.deepStrictEqual(doc(trHs), ['1,00', (6000000 / 5310000).toFixed(2).replace('.', ','), (Math.round(5854275 * ti) / 5310000).toFixed(2).replace('.', ','), (Math.round(6146989 * ti) / 5310000).toFixed(2).replace('.', ',')], 'hệ số = mức ÷ lương tối thiểu');
  // 2) sửa Mức lương bậc I -> mọi bậc sau tự nhân
  ({ trMl, trHs } = dung(['1,00', '1,05'], ['5.310.000', '5.575.500']));
  td = trMl.children[1]; ctx.vbTlVao(td); td.textContent = '6.000.000'; assert(ctx.vbTlTinhLai(td));
  assert.deepStrictEqual(doc(trMl), ['6.000.000', Math.round(5575500 * 6000000 / 5310000).toLocaleString('vi-VN')]);
  // 3) sửa Hệ số bậc I = 1,2 -> mức = 1,2 × 5.310.000 = 6.372.000, bậc sau nhân 1,2
  ({ trMl, trHs } = dung(['1,00', '1,05'], ['5.310.000', '5.575.500']));
  td = trHs.children[1]; ctx.vbTlVao(td); td.textContent = '1,2'; assert(ctx.vbTlTinhLai(td));
  assert.deepStrictEqual(doc(trMl), ['6.372.000', '6.690.600'], 'sửa hệ số: mức lương các bậc sau tự nhân'); assert.deepStrictEqual(doc(trHs), ['1,20', '1,26']);
  // 4) không đổi gì -> không tính lại (hệ số hiển thị đã làm tròn)
  ({ trMl, trHs } = dung(['1,00', '1,16'], ['5.310.000', '6.146.989']));
  td = trHs.children[2]; ctx.vbTlVao(td); assert.strictEqual(ctx.vbTlTinhLai(td), false); assert.deepStrictEqual(doc(trMl), ['5.310.000', '6.146.989']);
  // 5) nhập sai (chữ / số âm) -> trả lại giá trị cũ
  td = trMl.children[2]; ctx.vbTlVao(td); td.textContent = 'abc'; assert.strictEqual(ctx.vbTlTinhLai(td), false); assert.strictEqual(td.textContent, '6.146.989');
  // 6) ẩn dòng hệ số vẫn tính được; ô trống (nhóm ít bậc hơn) bỏ qua; bậc I thấp hơn lương tối thiểu thì cảnh báo
  ({ trMl } = dung([], ['5.310.000', '5.575.500', ''], false));
  td = trMl.children[1]; ctx.vbTlVao(td); td.textContent = '5.000.000'; assert(ctx.vbTlTinhLai(td));
  assert.deepStrictEqual(doc(trMl), ['5.000.000', Math.round(5575500 * 5000000 / 5310000).toLocaleString('vi-VN'), '']);
  assert(tb.some((x) => x[1] === 'err' && x[0].includes('thấp hơn lương tối thiểu')), 'cảnh báo mức bậc I < lương tối thiểu vùng');
  assert(html.includes("xem.addEventListener('beforeinput',()=>vbTlBatDau(vbTlODangChon()))") && html.includes("xem.addEventListener('focusout',()=>vbTlXacNhan())") && !html.includes("addEventListener('selectionchange'"), 'xác nhận khi Enter/sang ô khác/rời khối soạn thảo — không tính lại giữa chừng khi đang gõ');
  assert(/function vbIn\(\)\{\s*vbTlXacNhan\(\);/.test(html) && /async function vbXuatWord\(\)\{\s*vbTlXacNhan\(\);/.test(html), 'xác nhận ô đang sửa trước khi in / xuất Word');
  // xác nhận khi sang ô khác: gõ dở ("6" -> "60" -> "6000000") chưa tính; chỉ tính 1 lần khi xác nhận
  ({ trMl, trHs } = dung(['1,00', '1,05', '1,10'], ['5.310.000', '5.575.500', '5.854.275']));
  const o2 = trMl.children[2], o3 = trMl.children[3];
  ctx.vbTlBatDau(o2); o2.textContent = '6'; ctx.vbTlBatDau(o2); o2.textContent = '6000000';
  assert.strictEqual(o3.textContent, '5.854.275', 'chưa xác nhận thì các bậc sau chưa đổi');
  assert.strictEqual(ctx.vbTlXacNhan(), true); assert.strictEqual(o3.textContent, Math.round(5854275 * 6000000 / 5575500).toLocaleString('vi-VN'));
  assert.strictEqual(ctx.vbTlXacNhan(), false, 'không còn ô đang sửa');
  // sửa nhầm rồi sửa lại: không mất độ chính xác (hệ số lưu chính xác trong ô)
  ctx.vbTlBatDau(o2); o2.textContent = '10'; ctx.vbTlXacNhan(); ctx.vbTlBatDau(o2); o2.textContent = '5.575.500'; ctx.vbTlXacNhan();
  assert.deepStrictEqual(doc(trMl), ['5.310.000', '5.575.500', '5.854.275'], 'đổi nhầm rồi trả lại thì về đúng số cũ');
  console.log('PASS 17: sửa Hệ số / Mức lương thì các bậc sau tự nhân theo.');
})();

// 18: lao động PART-TIME — thẻ Hợp đồng Part-time, form, cột Part-time / Lương theo giờ, cột Bảng Lương chỉ hiện khi có người part-time
(() => {
  const iMo = html.indexOf('function moBangLuong(){'), thanMo = html.slice(iMo, html.indexOf('function moVanBan', iMo));
  assert(thanMo.includes(`onclick="moVanBan('pt')"`) && thanMo.includes('Hợp Đồng Part-time'), 'thẻ Hợp Đồng Part-time ở Bảng Lương - BHXH');
  assert(html.includes("pt:'Hợp Đồng Part-time'") && html.includes("pt:'HopDongPartTime'"));
  const iV = html.indexOf('function vbVeMan'), iE = html.indexOf('function vbTuyChon', iV), phan = html.slice(iV, iE);
  for (const id of ['vb_pt_gio_ngay', 'vb_pt_ngay_tuan', 'vb_pt_lich', 'vb_pt_gio_tuan', 'vb_pt_gio_thang', 'vb_pt_luong_gio', 'vb_pt_mau_so'])
    assert(phan.includes(id), 'form part-time thiếu ' + id);
  const iT = html.indexOf('function vbTuyChon'), tuyChon = html.slice(iT, html.indexOf('\n}', iT));
  for (const k of ['pt_gio_ngay', 'pt_lich', 'pt_gio_thang', 'pt_luong_gio']) assert(tuyChon.includes("'" + k + "'"), 'tuỳ chọn đọc ' + k);
  assert(html.includes("vbLoai==='hd'||vbLoai==='tv'||vbLoai==='pt'"), 'in hàng loạt từ–đến cho part-time');
  // danh sách nhân viên: cột Part-time là ô tick, Lương theo giờ hiện dạng tiền
  const { ctx } = moiTruong();
  const n0 = html.indexOf('const NV_HEADERS='), n1 = html.indexOf('function moBangLuong(){');
  const m0 = html.indexOf('function nvLaCotTick'), m1 = html.indexOf('async function nvLayLuongTheoNam');
  assert(html.slice(n0, n1).includes("'Part-time','Lương theo giờ','Lương Cơ bản'"));
  assert(html.includes("nvLaCotPt(h))html+=`<td") && html.includes("h==='lương theo giờ'"));
  // Bảng Lương: 3 cột part-time chỉ hiện khi tháng có người part-time; giữ nguyên ô nhập gốc sau khi server tính
  const b0 = html.indexOf('const BL_COT=['), b1 = html.indexOf('const BL_TRUONG_NHAP');
  const vm2 = vm.createContext({ console }); vm.runInContext(html.slice(b0, b1).replace(/^const BL_COT/m, 'var BL_COT').replace(/^let blHienMuc/m, 'var blHienMuc').replace(/\bfunction blDoiHienMuc[\s\S]*?\n}\n/, ''), vm2);
  const hien = (rows) => JSON.parse(vm.runInContext('JSON.stringify(blCotHienThi(' + JSON.stringify(rows) + ').map(c=>c.k))', vm2));
  assert(!hien([{ part_time: 0 }]).includes('gio_lam') && !hien([]).includes('part_time'), 'không có người part-time: ẩn các cột part-time');
  const kq = hien([{ part_time: 0 }, { part_time: 1 }]);
  assert(['part_time', 'luong_gio', 'gio_lam'].every((k) => kq.includes(k)), 'có người part-time: hiện cột Part-time / Lương theo giờ / Giờ làm');
  assert.strictEqual(vm.runInContext("BL_COT.filter(c=>c.nhap).map(c=>c.k).includes('gio_lam')", vm2), true, 'giờ làm thực tế là ô nhập (lưu cùng bảng lương)');
  const i1 = html.indexOf('async function blTinhLai'), i2 = html.indexOf('function blSuaO', i1);
  const ctxBl = { blDL: { '03': [{ part_time: 1, luong_cb: 0, tien_com: 700000, gio_lam: 40 }, { part_time: 0, luong_cb: 6e6, tien_com: 0 }] }, blSeq: 0, blTS: {}, blNam: 2026, blThang: '09', toast() {}, blVeBang() {}, blSapXepPartTime: (r) => r,
    api: async () => ({ rows: [{ part_time: 1, luong_cb: 1040000, tien_com: 0, gio_lam: 40, luong: 1040000 }, { part_time: 0, luong_cb: 6e6, tien_com: 0 }], tham_so: {} }) };
  vm.createContext(ctxBl); vm.runInContext(html.slice(i1, i2), ctxBl);
  return ctxBl.blTinhLai('03').then(() => {
    const r = ctxBl.blDL['03'];
    assert(r[0].luong_cb === 0 && r[0].tien_com === 700000 && r[0].luong === 1040000, 'dòng part-time: giữ ô nhập gốc (không bị ghi đè bằng số quy đổi theo giờ), vẫn hiện lương tính được');
    assert(r[1].luong_cb === 6e6);
    console.log('PASS 18: lao động part-time (hợp đồng, danh sách NV, bảng lương).');
  });
})().catch((e) => { console.error(e); process.exit(1); });

// 19: nạp lao động part-time cả năm theo khoảng làm việc + điền giờ theo hợp đồng (chỉ ô trống, không ghi đè)
(async () => {
  assert(html.includes('onclick="blNapPartTime()"') && !html.includes('blDienGioPartTime'), 'đã gỡ nút điền giờ theo hợp đồng');
  const i1 = html.indexOf('async function blNapPartTime'), i2 = html.indexOf('async function blNapNhanVien');
  const goi = [], toasts = [];
  const ctx = { current: 7, blNam: 2026, blDL: { '03': [{ ma: '9', ten: 'PT', part_time: 1, gio_lam: 50 }] }, BL_THANG: Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0')), blBan: false,
    blVeTabs() {}, blVeBang() {}, blVeInfo() {}, toast: (m, k) => toasts.push([m, k]), localStorage: { getItem: () => null, setItem() {} }, prompt: () => '43,3',
    api: async (u) => { goi.push(u); const t = +u.match(/thang=(\d+)/)[1]; return { rows: [{ ma: '1', ten: 'FT', part_time: 0 }].concat(t >= 3 && t <= 5 ? [{ ma: '9', ten: 'PT', part_time: 1, luong_gio: 26000, gio_lam: '' }] : []) }; },
    async blTinhLai(t) { ctx.blDL[t].forEach((r) => { if (r.part_time) { r.pt_phai_dong_bh = (Number(r.gio_lam) || 0) * 26000 >= 2530000; } }); } };
  vm.createContext(ctx); vm.runInContext(html.slice(i1, i2), ctx);
  await ctx.blNapPartTime();
  assert.strictEqual(goi.length, 12, 'duyệt đủ 12 tháng');
  assert.deepStrictEqual(Object.keys(ctx.blDL).sort(), ['03', '04', '05'], 'chỉ các tháng trong khoảng làm việc; người toàn thời gian không bị thêm');
  assert.strictEqual(ctx.blDL['03'].length, 1, 'tháng đã có dòng: không thêm trùng'); assert.strictEqual(ctx.blDL['03'][0].gio_lam, 50, 'giữ nguyên giờ đã nhập');
  assert(['04', '05'].every((t) => ctx.blDL[t][0].gio_lam === ''), 'nạp part-time KHÔNG tự đặt giờ làm (chờ import/nhập giờ thực tế)');
  console.log('PASS 19: nạp part-time cả năm (không tự đặt giờ).');
})().catch((e) => { console.error(e); process.exit(1); });

// 20: giờ làm part-time — bảng chấm công ghi giờ từng ngày (tối đa 8 giờ/ngày, dư sang ngày kế), import file giờ làm
(async () => {
  assert(html.includes('onclick="blTaiMauGioLam()"') && html.includes('onchange="blImportGioLam(this)"'));
  const c0 = html.indexOf('const BL_THU='), c1 = html.indexOf('function blDauHienThi');
  const cc = vm.createContext({ Math, Number, String, Object, Set, Date, parseInt, parseFloat, xkEsc: (x) => x, blDinhDang: (v) => String(v) });
  vm.runInContext(html.slice(c0, c1).replace(/^const /gm, 'var '), cc);
  const cham = (r) => JSON.parse(JSON.stringify(vm.runInContext('(r)=>blChamCongThang(r,2026,"03",null)', cc)(r)));
  const dau = (c) => c.ngay.filter((x) => x.dau).map((x) => x.d + ':' + x.dau).join(' ');
  // chỉ có TỔNG giờ tháng: phân bổ vào các ngày làm việc như người lao động khác (ngẫu nhiên CỐ ĐỊNH theo người + tháng), mỗi ngày 1–8 giờ, tổng ĐÚNG
  const CN = [1, 8, 15, 22, 29];          // Chủ nhật tháng 3/2026
  for (const [ma, g] of [['P', 20], ['2', 50], ['Q', 18.5], ['R', 7.3], ['S', 150], ['T', 0.5]]) {
    const c = cham({ part_time: 1, gio_lam: g, ma });
    const co = c.ngay.filter((x) => x.gio > 0);
    assert.strictEqual(Math.round(co.reduce((a, x) => a + x.gio, 0) * 10) / 10, g, 'tổng đúng số giờ ' + g);
    assert(co.every((x) => x.gio <= 8 && !CN.includes(x.d)), 'không quá 8 giờ/ngày, không Chủ nhật');
    assert(co.length >= Math.ceil(g / 8) && c.tong === g && c.suy === true && c.pt === true);
    assert.strictEqual(dau(cham({ part_time: 1, gio_lam: g, ma })), dau(c), 'in lại ra đúng bảng cũ (cố định theo người + tháng)');
  }
  const c50 = cham({ part_time: 1, gio_lam: 50, ma: '2' }).ngay.filter((x) => x.gio > 0);
  assert(!c50.every((x, i) => x.d === [2, 3, 4, 5, 6, 7, 9][i]) && new Set(c50.map((x) => x.gio)).size > 1, 'không còn dồn 8 giờ từ đầu tháng: rải các ngày, số giờ khác nhau');
  assert.notStrictEqual(dau(cham({ part_time: 1, gio_lam: 50, ma: '2' })), dau(cham({ part_time: 1, gio_lam: 50, ma: '3' })), 'mỗi người một cách rải');
  let c = cham({ part_time: 1, gio_lam: 100.5, ma: 'P' });
  assert(c.ngay.every((x) => x.gio <= 8) && c.tong === 100.5, 'không ngày nào quá 8 giờ');
  assert.strictEqual(c.ngay[7].dau, '', 'Chủ nhật không điền');
  // có giờ theo NGÀY (import): hiện đúng như file, không phân bổ
  c = cham({ part_time: 1, gio_lam: 6.5, gio_ngay: '5:2;6:2;9:2.5', ma: 'P' });
  assert.strictEqual(dau(c), '5:2 6:2 9:2,5'); assert.strictEqual(c.tong, 6.5); assert.strictEqual(c.suy, false);
  // chưa có giờ: trống; người toàn thời gian: như cũ
  assert.strictEqual(dau(cham({ part_time: 1, gio_lam: '' })), ''); assert.strictEqual(cham({ part_time: 0, ngay_lam: 3, ma: 'F' }).pt, undefined);
  assert(html.includes('Người có ghi chú * : giờ từng ngày phân bổ theo TỔNG giờ tháng (chưa có chấm công từng ngày)'), 'bản in ghi rõ phần phân bổ theo tổng giờ');
  // IMPORT
  const i1 = html.indexOf('async function blTaiMauGioLam'), i2 = html.indexOf('async function blNapNhanVien');
  const alerts = [], toasts = [];
  const ctx = { current: 7, blNam: 2026, BL_THANG: Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0')), blBan: false, blVeTabs() {}, blVeBang() {}, blVeInfo() {}, toast: (m, k) => toasts.push([m, k]), alert: (m) => alerts.push(m),
    blDL: { '03': [{ ma: 'P1', ten: 'Lê', part_time: 1, gio_lam: '' }], '04': [{ ma: 'P1', ten: 'Lê', part_time: 1, gio_lam: 5, gio_ngay: '2:5' }], '05': [{ ma: '1', ten: 'FT', part_time: 0 }] },
    FormData: class { append() {} }, async blNapPartTime() {}, async blTinhLai() {},
    fetch: async () => ({ ok: true, json: async () => ({ so_nguoi: 1, gio: [{ ma: 'P1', ten: 'Lê', thang: { '03': 14.5, '04': 30, '06': 10 }, ngay: { '03': { 2: 2, 3: 2, 4: 2.5, 5: 8 } } }], loi: ['Giờ theo ngày, dòng 9 (ngày 7): 9 giờ vượt tối đa 8 giờ/ngày'], canh_bao: [] }) }) };
  vm.createContext(ctx); vm.runInContext(html.slice(i1, i2), ctx);
  await ctx.blImportGioLam({ files: [{}], value: 'x' });
  const r3 = ctx.blDL['03'][0], r4 = ctx.blDL['04'][0];
  assert.strictEqual(r3.gio_lam, 14.5); assert.strictEqual(r3.gio_ngay, '2:2;3:2;4:2.5;5:8', 'giữ giờ từng ngày');
  assert.strictEqual(r4.gio_lam, 30); assert.strictEqual(r4.gio_ngay, '', 'tháng chỉ có giờ theo tháng: bỏ chi tiết ngày cũ');
  assert(alerts[0].includes('vượt tối đa 8 giờ/ngày') && alerts[0].includes('tháng 6: chưa có dòng part-time'), 'báo các dòng bị bỏ qua');
  assert(toasts.at(-1)[1] === 'err' && toasts.at(-1)[0].includes('Đã nhập giờ làm cho 2 dòng'));
  // sửa tay tổng giờ thì bỏ chi tiết giờ theo ngày
  assert(html.includes("if(k==='gio_lam')rows[ri].gio_ngay='';"));
  console.log('PASS 20: chấm công part-time theo giờ + import giờ làm.');
})().catch((e) => { console.error(e); process.exit(1); });

// 21: người part-time trong Bảng Lương — chỉ có Lương theo giờ + Giờ làm (ô Lương CB / Ngày công / Tổng NC để trống), xếp dưới cùng
(() => {
  const b0 = html.indexOf('const BL_PT_TRONG'), b1 = html.indexOf('function blCoPartTime');
  const cx = vm.createContext({}); vm.runInContext(html.slice(b0, b1).replace(/^const /gm, 'var '), cx);
  assert.deepStrictEqual(JSON.parse(vm.runInContext("JSON.stringify(BL_PT_TRONG)", cx)), ['luong_cb', 'ngay_cong', 'ngay_lam', 'gio_tang_ca', 'ngay_cong_hd', 'ngay_lam_hd', 'thuong_bh', 'thuong_t13', 'tang_ca']);
  const rows = [{ ten: 'PT1', part_time: 1 }, { ten: 'A', part_time: 0 }, { ten: 'TV', thu_viec: 1 }, { ten: 'PT2', part_time: 1 }, { ten: 'B' }];
  const kq = JSON.parse(vm.runInContext('JSON.stringify(blSapXepPartTime(' + JSON.stringify(rows) + ').map(r=>r.ten))', cx));
  assert.deepStrictEqual(kq, ['A', 'TV', 'B', 'PT1', 'PT2'], 'chính thức + thử việc giữ thứ tự, part-time xuống cuối (giữ thứ tự giữa họ)');
  assert(html.includes("if(Number(r.part_time)&&BL_PT_TRONG.includes(c.k))h+=`<td"), 'bảng lương: ô trống cho người part-time');
  assert(html.includes("if(Number(r.part_time)&&BL_PT_TRONG.includes(c.k))return '<td></td>';"), 'bản in: ô trống cho người part-time');
  assert(html.includes("{k:'luong_gio',t:'Lương theo giờ',w:70,n:1,opt:1},{k:'gio_lam',t:'Số giờ làm',w:48,c:1,dp:1,opt:1}"), 'bản in có cột Lương theo giờ + Số giờ làm khi có người part-time');
  assert(html.includes('blDL[t]=blSapXepPartTime(kq.rows)') && html.includes('blDL[t]=blSapXepPartTime(blDL[t])'), 'sắp xếp khi tải và sau mỗi lần tính');
  assert((html.match(/Number\(r\.part_time\)&&BL_PT_TRONG\.includes\(c\.k\)\)\?0:/g) || []).length >= 3, 'dòng TỔNG CỘNG (tháng, cả năm, bản in) không cộng ô bị ẩn của người part-time');
  assert(html.includes("'tang_ca','thuong_bh','thuong_t13','dong_bh','thu_viec'].forEach(k=>{if(k in o)r[k]=o[k]})"));
  console.log('PASS 21: part-time chỉ hiện lương theo giờ + giờ làm, xếp dưới cùng.');
})();

// 22: import giờ làm part-time — bảng lương THEO FILE: tháng không có giờ = không làm = gỡ dòng của người đó khỏi bảng lương tháng đó
(async () => {
  const i1 = html.indexOf('async function blTaiMauGioLam'), i2 = html.indexOf('async function blNapNhanVien');
  const tao = (confirmKq, kqFile) => {
    const toasts = [], hoi = [];
    const ctx = { current: 7, blNam: 2026, BL_THANG: Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0')), blBan: false, blVeTabs() {}, blVeBang() {}, blVeInfo() {}, toast: (m, k) => toasts.push([m, k]), alert() {}, confirm: (m) => { hoi.push(m); return confirmKq; },
      blDL: { '03': [{ ma: 'P1', ten: 'Lê', part_time: 1, gio_lam: 20 }, { ma: '1', ten: 'FT' }], '04': [{ ma: 'P1', ten: 'Lê', part_time: 1, gio_lam: 15 }], '05': [{ ma: 'P1', ten: 'Lê', part_time: 1, gio_lam: '' }, { ma: 'P2', ten: 'Hai', part_time: 1, gio_lam: '' }], '06': [{ ma: 'P1', ten: 'Lê', part_time: 1, gio_lam: 7 }], '07': [{ ma: 'P1', ten: 'Lê', part_time: 1, gio_lam: '' }] },
      FormData: class { append() {} }, async blNapPartTime() {}, async blTinhLai() {}, fetch: async () => ({ ok: true, json: async () => kqFile }) };
    vm.createContext(ctx); vm.runInContext(html.slice(i1, i2), ctx); return { ctx, toasts, hoi };
  };
  // file: P1 chỉ có giờ tháng 3 (14,5) và tháng 7 dòng LỖI; P2 có trong file nhưng không có giờ
  const file = { so_nguoi: 1, gio: [{ ma: 'P1', ten: 'Lê', thang: { '03': 14.5 }, ngay: {} }], nguoi_trong_file: [{ ma: 'P1', ten: 'Lê' }, { ma: 'P2', ten: 'Hai' }], thang_loi: { P1: ['07'] }, loi: ['Giờ theo tháng, dòng 2 (T7): lỗi'], canh_bao: [] };
  let t = tao(false, file); await t.ctx.blImportGioLam({ files: [{}], value: 'x' });
  assert(t.hoi.length === 1 && t.hoi[0].includes('SẼ GỠ') && t.hoi[0].includes('2 dòng'), 'hỏi trước khi gỡ tháng đang có giờ đã nhập (T4: 15, T6: 7)');
  assert.strictEqual(t.ctx.blDL['04'].length, 1, 'không đồng ý: giữ nguyên bảng lương');
  t = tao(true, file); await t.ctx.blImportGioLam({ files: [{}], value: 'x' });
  const L = t.ctx.blDL;
  assert.strictEqual(L['03'][0].gio_lam, 14.5); assert.strictEqual(L['03'].length, 2, 'người toàn thời gian không bị đụng');
  assert.strictEqual(L['04'], undefined, 'T4: file không có giờ -> không làm -> không có dòng (tháng trống thì bỏ tháng)'); assert.strictEqual(L['06'], undefined);
  assert.strictEqual(L['05'], undefined, 'T5: cả P1 và P2 (có trong file, không giờ) bị gỡ');
  assert.strictEqual(L['07'].length, 1, 'T7: dữ liệu lỗi trong file -> giữ nguyên, không coi là không làm');
  assert(t.toasts.at(-1)[0].includes('gỡ 4 dòng tháng không làm'), t.toasts.at(-1)[0]);
  console.log('PASS 22: import giờ làm — tháng không làm thì gỡ khỏi bảng lương tháng đó.');
})().catch((e) => { console.error(e); process.exit(1); });

// 23: dòng phiên bản (mã gốc-001) chưa ghi "thay đổi lương" nhưng có "vào làm": hiệu lực từ tháng vào làm; Nạp từ Danh Sách NV thay dòng cũ (không để 2 dòng của 1 người)
(async () => {
  const i1 = html.indexOf('async function blNapNhanVien'), i2 = html.indexOf('\n}\n', i1) + 3;
  const mk = (blDL, dsRows, daNghi = []) => { const toasts = [];
    const ctx = { current: 7, blNam: 2024, blThang: '12', blDL, blBan: false, blVeTabs() {}, blVeBang() {}, blVeInfo() {}, toast: (m, k) => toasts.push([m, k]), async blTinhLai() {}, parseInt, String, Number, Set, Map,
      nvMaGoc: (ma) => { const m = String(ma == null ? '' : ma).trim().match(/^(.+)-(\d{3})$/); return m ? m[1] : String(ma == null ? '' : ma).trim(); },
      api: async () => ({ rows: dsRows, da_nghi: daNghi }) };
    vm.createContext(ctx); vm.runInContext(html.slice(i1, i2), ctx); return { ctx, toasts }; };
  // T12/2024: Danh sách NV trả dòng 2-001 (đang hiệu lực); bảng lương T12 đang có dòng part-time cũ "2" -> thay bằng 2-001
  let { ctx } = mk({ '12': [{ ma: '2', ten: 'Hùng', part_time: 1, gio_lam: '' }, { ma: '3', ten: 'Nam', luong_cb: 5310000 }] },
    [{ ma: '2-001', ten: 'Hùng', part_time: 0, dong_bh: 1, luong_cb: 5310000 }, { ma: '3', ten: 'Nam', luong_cb: 5310000 }]);
  await ctx.blNapNhanVien();
  assert.deepStrictEqual(ctx.blDL['12'].map((r) => r.ma), ['2-001', '3'], 'dòng cũ được thay, không trùng người'); assert.strictEqual(ctx.blDL['12'][0].dong_bh, 1); assert.strictEqual(ctx.blDL['12'][0].part_time, 0);
  // ngược lại (T11): bảng lương đang có 2-001, danh sách trả dòng gốc "2"
  ({ ctx } = mk({ '11': [{ ma: '2-001', ten: 'Hùng' }] }, [{ ma: '2', ten: 'Hùng', part_time: 1 }])); ctx.blThang = '11';
  await ctx.blNapNhanVien(); assert.deepStrictEqual(ctx.blDL['11'].map((r) => r.ma), ['2']);
  // người khác mã gốc (2 và 22) không bị gộp nhầm
  ({ ctx } = mk({ '12': [{ ma: '22', ten: 'Khác' }] }, [{ ma: '2-001', ten: 'Hùng' }])); await ctx.blNapNhanVien(); assert.deepStrictEqual(ctx.blDL['12'].map((r) => r.ma), ['22', '2-001']);
  console.log('PASS 23: đổi phiên bản mã -001 khi nạp từ Danh Sách NV.');
})().catch((e) => { console.error(e); process.exit(1); });

// 24: tham số năm có ô "Part-time: khấu trừ 10% mọi khoản (→ 05-2)" (mặc định bật)
(() => {
  assert(html.includes('id="blTsPt10" ${t.pt_thue_10===false?\'\':\'checked\'}') && html.includes("pt_thue_10:(()=>{const e=document.getElementById('blTsPt10');return e&&e.checked!==undefined?e.checked:true})(),"));
  console.log('PASS 24: tham số part-time khấu trừ 10%.');
})();

// 25: form Hợp Đồng Part-time: danh sách từ–đến CHỈ gồm người part-time (d.nhan_vien_pt), không lấy cả danh sách nhân viên
(() => {
  const iV = html.indexOf('function vbVeMan'), iE = html.indexOf('function vbTuyChon', iV), phan = html.slice(iV, iE);
  assert(phan.includes('const ptNv=d.nhan_vien_pt||[]') && !phan.includes('optPt.length?optPt:optNv') && phan.includes('— chưa có người part-time —'));
  console.log('PASS 25: hợp đồng part-time chỉ liệt kê người part-time.');
})();

// 26: Danh Sách NV — ô lọc giữ focus khi gõ + lọc không dấu; bôi đen ô trong 1 cột + Fill down; import đặt ô theo TÊN cột
(async () => {
  const i1 = html.indexOf('function nvBoDau'), i2 = html.indexOf('function nvRowsLoc');
  const j1 = html.indexOf('/* ----- BÔI ĐEN Ô TRONG 1 CỘT'), j2 = html.indexOf('function nvSuaO');
  assert(i1 > 0 && j1 > 0);
  const toasts = [], tds = {}, daFocus = [];
  const mkTd = (r, c) => { const k = r + ':' + c; return tds[k] || (tds[k] = { dataset: { r: String(r), c: String(c) }, _cls: new Set(), classList: { add(x) { tds[k]._cls.add(x); }, remove(x) { tds[k]._cls.delete(x); } } }); };
  const ctx = { nvHeader: ['STT', 'Họ và tên', 'Chức vụ', 'Đóng BHXH'], nvRows: [[1, 'Nguyễn Văn Khoan', 'A', 'x'], [2, 'Lý Thị Thu Hiền', 'B', ''], [3, 'Lê Đức Tấn', 'C', 'x'], [4, 'Nguyễn Văn Cảnh', 'D', '']], nvFilters: {}, toast: (m, k) => toasts.push([m, k]),
    veGridNhanVien() { ctx.nveRender = (ctx.nveRender || 0) + 1; }, String, Number, Set,
    document: { querySelector: (sel) => { const m = sel.match(/data-fci="(\d+)"/); if (m) return { focus() { daFocus.push('focus'); }, setSelectionRange(a, b) { daFocus.push([a, b]); } }; const t = sel.match(/data-r="(\d+)"\]\[data-c="(\d+)"/); return t ? mkTd(+t[1], +t[2]) : null; },
      querySelectorAll: () => [], getElementById: () => null, addEventListener() {} } };
  vm.createContext(ctx); vm.runInContext(html.slice(i1, i2) + html.slice(i2, html.indexOf('function veGridNhanVien')) + html.slice(j1, j2), ctx);
  // lọc không dấu + giữ focus ở ô lọc
  ctx.nvLoc(1, 'nguyen v');
  assert.deepStrictEqual(JSON.parse(vm.runInContext('JSON.stringify(nvRowsLoc())', ctx)), [0, 3], 'gõ "nguyen v" tìm ra Nguyễn Văn…');
  assert.deepStrictEqual(daFocus, ['focus', [8, 8]], 'vẽ lại bảng rồi trả focus + con trỏ về ô lọc (gõ liên tục được)');
  ctx.nvLoc(1, 'đức'); assert.deepStrictEqual(JSON.parse(vm.runInContext('JSON.stringify(nvRowsLoc())', ctx)), [2]); ctx.nvLoc(1, '');
  // bôi đen: bấm ô đầu rồi Shift+bấm ô cuối cùng cột -> vùng chọn; Fill down điền giá trị ô trên cùng
  vm.runInContext('nvNeo={ri:0,c:2}', ctx); vm.runInContext('nvSelDat(0,2,2)', ctx);
  assert.deepStrictEqual(JSON.parse(vm.runInContext('JSON.stringify(nvSel)', ctx)), { c: 2, ris: [0, 1, 2] });
  assert(tds['0:2']._cls.has('nv-sel') && tds['2:2']._cls.has('nv-sel') && !tds['3:2']);
  ctx.nvFillDown();
  assert.deepStrictEqual(ctx.nvRows.map((r) => r[2]), ['A', 'A', 'A', 'D'], 'điền xuống đúng vùng bôi đen, ô ngoài vùng giữ nguyên');
  assert(toasts.at(-1)[0].includes('xuống 2 ô') && toasts.at(-1)[1] === 'ok');
  // cột tick (Đóng BHXH): điền cả giá trị trống; cột STT bị chặn
  vm.runInContext('nvSelDat(0,3,3)', ctx); ctx.nvRows[0][3] = 'x'; ctx.nvFillDown(); assert.deepStrictEqual(ctx.nvRows.map((r) => r[3]), ['x', 'x', 'x', 'x']);
  vm.runInContext('nvSelDat(0,3,0)', ctx); const truoc = JSON.stringify(ctx.nvRows); ctx.nvFillDown(); assert.strictEqual(JSON.stringify(ctx.nvRows), truoc, 'không điền xuống cột STT'); assert(toasts.at(-1)[1] === 'err');
  // bấm tiêu đề = chọn cả cột (theo các dòng đang hiện)
  ctx.nvLoc(1, 'nguyen'); ctx.nvChonCot(2); assert.deepStrictEqual(JSON.parse(vm.runInContext('JSON.stringify(nvSel)', ctx)), { c: 2, ris: [0, 3] });
  // chưa chọn gì: báo lỗi hướng dẫn
  vm.runInContext('nvSelXoa()', ctx); ctx.nvFillDown(); assert(toasts.at(-1)[1] === 'err' && toasts.at(-1)[0].includes('Bôi đen'));
  assert(html.includes("td.nv-sel{") && html.includes('Ctrl+D'));
  // import: ô đặt theo TÊN cột, giữ nguyên thứ tự dòng của file
  const iI = html.indexOf('async function nvImportExcel'), iE = html.indexOf('/* ----- NGƯỜI PHỤ THUỘC');
  const c2 = { nvHeader: ['STT', 'Họ và tên', 'Mã NV', 'Đóng BHXH'], nvRows: [[0, 'Đã có', 'X0', 'x']], current: 7, toast() {}, nvBoCotPcChucVu() {}, nvThemCotTick() {}, nvThemCotNghiViec() {}, nvDanhLaiStt() {}, veGridNhanVien() {}, nvLaCotTick: (h) => String(h).toLowerCase() === 'đóng bhxh', FormData: class { append() {} },
    fetch: async () => ({ ok: true, json: async () => ({ header: ['STT', 'Mã NV', 'Họ và tên', 'Đóng BHXH'], rows: [[1, 'M3', 'Zeta', 'x'], [2, 'M1', 'Alpha', ''], [3, 'M2', 'Mike', 'x']], loi: [] }) }) };
  vm.createContext(c2); vm.runInContext(html.slice(iI, iE), c2);
  await c2.nvImportExcel({ files: [{}], value: '' });
  assert.deepStrictEqual(c2.nvRows.slice(1).map((r) => r.join('|')), ['1|Zeta|M3|x', '2|Alpha|M1|', '3|Mike|M2|x'], 'đúng cột theo tên dù thứ tự cột khác nhau; thứ tự dòng như file');
  console.log('PASS 26: lọc giữ focus + không dấu, bôi đen + Fill down, import đúng cột/thứ tự.');
})().catch((e) => { console.error(e); process.exit(1); });
