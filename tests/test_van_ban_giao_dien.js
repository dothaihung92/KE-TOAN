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
