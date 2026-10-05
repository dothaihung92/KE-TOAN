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
  const ctxBl = { blDL: { '03': [{ part_time: 1, luong_cb: 0, tien_com: 700000, gio_lam: 40 }, { part_time: 0, luong_cb: 6e6, tien_com: 0 }] }, blSeq: 0, blTS: {}, blNam: 2026, blThang: '09', toast() {}, blVeBang() {},
    api: async () => ({ rows: [{ part_time: 1, luong_cb: 1040000, tien_com: 0, gio_lam: 40, luong: 1040000 }, { part_time: 0, luong_cb: 6e6, tien_com: 0 }], tham_so: {} }) };
  vm.createContext(ctxBl); vm.runInContext(html.slice(i1, i2), ctxBl);
  return ctxBl.blTinhLai('03').then(() => {
    const r = ctxBl.blDL['03'];
    assert(r[0].luong_cb === 0 && r[0].tien_com === 700000 && r[0].luong === 1040000, 'dòng part-time: giữ ô nhập gốc (không bị ghi đè bằng số quy đổi theo giờ), vẫn hiện lương tính được');
    assert(r[1].luong_cb === 6e6);
    console.log('PASS 18: lao động part-time (hợp đồng, danh sách NV, bảng lương).');
  });
})().catch((e) => { console.error(e); process.exit(1); });
