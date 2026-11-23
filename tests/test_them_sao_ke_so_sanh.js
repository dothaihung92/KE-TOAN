// Thêm sao kê chồng lấn: khoảng ngày dữ liệu + so sánh (trùng bỏ qua, đổi số liệu báo, dòng đã xử lý không bị sửa).
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'doi_chieu_ngan_hang.html'), 'utf8');
function extractFn(name) {
  const start = html.indexOf('function ' + name + '('); if (start < 0) throw new Error('thiếu hàm ' + name);
  let i = html.indexOf('{', start), d = 0, end = -1;
  for (; i < html.length; i++) { if (html[i] === '{') d++; else if (html[i] === '}') { d--; if (!d) { end = i + 1; break } } }
  return html.slice(start, end);
}
const assert = (c, m) => { if (!c) { console.error('FAIL: ' + m); process.exit(1); } };
eval(extractFn('normVN')); eval(extractFn('parseNgayGanGiaoDich')); eval(extractFn('khoangNgaySaoKe')); eval(extractFn('soSanhSaoKeThem'));
const gd = (date, desc, n, cr, extra) => Object.assign({ id: date + desc + n + (cr ? 'c' : 'd') + Math.random(), tx: { date, desc, debit: cr ? 0 : n, credit: cr ? n : 0 }, confirmed: '' }, extra || {});
// khoảng ngày
let k = khoangNgaySaoKe([gd('15/03/2026', 'a', 1), gd('01/01/2026', 'b', 1), gd('30/09/2026', 'c', 1)]);
assert(k.tu === '01/01/2026' && k.den === '30/09/2026' && k.soNgay === 273, 'khoảng ngày: ' + JSON.stringify(k));
assert(khoangNgaySaoKe([]).tu === '' && khoangNgaySaoKe([{ tx: { date: '' } }]).tu === '', 'rỗng');
// dữ liệu cũ 01/01–30/09; sao kê mới 01/09–31/12
const cu = [gd('05/01/2026', 'tt hd 1', 1000, 1), gd('02/09/2026', 'PHI IB', 15400), gd('02/09/2026', 'PHI IB', 15400), gd('10/09/2026', 'CK Tan Tien tt hd 77', 5000000, 1, { confirmed: 'yes', confirmedHach: '131' }),
  gd('15/09/2026', 'NGUYEN VAN A chuyen tien', 2000000, 1), gd('20/09/2026', 'Cty B tra tien', 800000, 1, { confirmed: 'yes' }), gd('25/09/2026', 'Dong cu khong con', 123000)];
const moi = [gd('02/09/2026', 'PHI IB', 15400), gd('02/09/2026', 'PHI IB', 15400), gd('02/09/2026', 'PHI IB', 15400),      // 3 phí (cũ có 2) -> thêm 1
  gd('10/09/2026', 'CK Tan Tien tt hd 77', 5000000, 1),                                                                  // giống hệt, đã hạch toán -> bỏ qua
  gd('15/09/2026', 'NGUYEN VAN A chuyen tien', 2500000, 1),                                                              // đổi số tiền
  gd('20/09/2026', 'Cty B tra tien them noi dung', 800000, 1),                                                           // đổi nội dung (đã xử lý)
  gd('05/10/2026', 'Moi thang 10', 999000, 1), gd('31/12/2026', 'Moi thang 12', 111000)];                                // mới hoàn toàn
const r = soSanhSaoKeThem(cu, moi);
assert(r.giongHet === 3, 'giống hệt = 3 (2 phí + HĐ 77): ' + r.giongHet);
assert(r.moi.length === 3 && r.moi.some(x => x.tx.desc === 'PHI IB') && r.moi.some(x => x.tx.desc === 'Moi thang 10') && r.moi.some(x => x.tx.desc === 'Moi thang 12'), 'dòng mới: ' + JSON.stringify(r.moi.map(x => x.tx.desc)));
assert(r.thayDoi.length === 2, 'thay đổi 2: ' + r.thayDoi.length);
const t1 = r.thayDoi.find(x => x.loai === 'so_tien'), t2 = r.thayDoi.find(x => x.loai === 'noi_dung');
assert(t1 && t1.cu.tx.credit === 2000000 && t1.moi.tx.credit === 2500000 && !t1.daXuLy, 'đổi số tiền chỉ đúng dòng');
assert(t2 && t2.daXuLy === true && t2.cu.tx.desc === 'Cty B tra tien', 'đổi nội dung của dòng ĐÃ xử lý được báo là đã xử lý');
assert(r.cuKhongCon.length === 1 && r.cuKhongCon[0].cu.tx.desc === 'Dong cu khong con', 'dòng cũ không còn trong sao kê mới (trong khoảng ngày)');
assert(!r.cuKhongCon.some(x => x.cu.tx.date === '05/01/2026'), 'dòng cũ NGOÀI khoảng ngày sao kê mới không bị báo');
assert(r.khoangMoi.tu === '02/09/2026' && r.khoangMoi.den === '31/12/2026', 'khoảng sao kê mới');
// không sửa dữ liệu cũ
assert(cu[3].confirmed === 'yes' && cu[3].confirmedHach === '131' && cu[3].tx.credit === 5000000, 'dòng đã hạch toán không bị đổi');
// dán lại y hệt -> không có gì thay đổi
const r2 = soSanhSaoKeThem(cu, cu.map(x => gd(x.tx.date, x.tx.desc, Math.max(x.tx.debit, x.tx.credit), x.tx.credit > 0)));
assert(r2.moi.length === 0 && r2.thayDoi.length === 0 && r2.cuKhongCon.length === 0 && r2.giongHet === cu.length, 'dán lại y hệt: không có gì');
// nối tiếp không trùng
const r3 = soSanhSaoKeThem(cu, [gd('01/11/2026', 'x', 1), gd('02/11/2026', 'y', 2)]);
assert(r3.moi.length === 2 && r3.thayDoi.length === 0 && r3.cuKhongCon.length === 0, 'nối tiếp');
// giao diện
assert(html.includes('📅 Sao kê đã nhập: ') && html.includes('Dữ liệu vừa dán: ') && html.includes('AddCanhBaoModal') && html.includes('soSanhSaoKeThem(rows, newResults)'), 'giao diện nối dây');
console.log('PASS: thêm sao kê — hiện khoảng ngày, so sánh chồng lấn (bỏ qua trùng, báo đổi số liệu, không sửa dòng đã xử lý)');
// Lỗi thật đã gặp: dùng useMemo trần (file chỉ lấy sẵn useState/useEffect/useRef) làm sập cả màn hình.
{
  const m = html.match(/const \{([^}]*)\}\s*=\s*React;/);
  const co = new Set((m ? m[1] : '').split(',').map(s => s.trim()).filter(Boolean));
  const dung = new Set((html.match(/[^.\w]use(?:Effect|Ref|Callback|Memo|State|LayoutEffect|Reducer)\(/g) || []).map(s => s.slice(1, -1)));
  const thieu = [...dung].filter(h => !co.has(h));
  assert(thieu.length === 0, 'hook dùng trần nhưng chưa khai báo: ' + thieu.join(', '));
  console.log('PASS: không dùng hook React trần chưa khai báo');
}
