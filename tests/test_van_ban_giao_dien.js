// Giao diện Hợp đồng lao động / Quy chế lương / Thang bảng lương (Nhập Liệu -> Bảng Lương - BHXH): chạy ĐÚNG code JS trong static/index.html.
const fs = require('fs'), path = require('path'), assert = require('assert'), vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'index.html'), 'utf8');

// 1: 3 ô mới nằm cạnh Danh Sách Nhân Viên / Người Phụ Thuộc / Bảng Lương
const iMo = html.indexOf('function moBangLuong(){');
const thanMo = html.slice(iMo, html.indexOf('function moVanBan', iMo));
for (const [loai, ten] of [['hd', 'Hợp Đồng Lao Động'], ['qc', 'Quy Chế Lương'], ['tl', 'Thang Bảng Lương']])
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
