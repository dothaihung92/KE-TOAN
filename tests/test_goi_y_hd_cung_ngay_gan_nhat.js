// Gợi ý khớp số tiền (rematchPending): 2 hoá đơn CÙNG công ty CÙNG số tiền (HĐ 112 ngày 09/07/2025 và HĐ 5 ngày 08/01/2026) mà giao dịch tiền vào 08/01/2026
// -> phải gợi ý HĐ 5 (cùng ngày), không được bỏ nó vì lọc trùng giữ HĐ cũ.
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'doi_chieu_ngan_hang.html'), 'utf8');
function extractFn(name) {
  const start = html.indexOf('function ' + name + '('); if (start < 0) throw new Error('thiếu hàm ' + name);
  let i = html.indexOf('{', start), d = 0, end = -1;
  for (; i < html.length; i++) { if (html[i] === '{') d++; else if (html[i] === '}') { d--; if (!d) { end = i + 1; break } } }
  return html.slice(start, end);
}
const assert = (c, m) => { if (!c) throw new Error('THẤT BẠI: ' + m) };
eval(extractFn('normVN')); eval(extractFn('parseNgayGanGiaoDich')); eval(extractFn('scoreKw')); eval(extractFn('rematchPending'));
assert(parseNgayGanGiaoDich('08/01/2026') > parseNgayGanGiaoDich('09/07/2025') && parseNgayGanGiaoDich('31/04/2026') === 0 && parseNgayGanGiaoDich('') === 0);
const hd = (so, ngay, mst, ten, tong) => ({ id: 'i' + so + mst, so_hd: so, ngay, mst, ten_cty: ten, tong });
const TT = 'CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ - GIA CÔNG CƠ KHÍ TÂN TIẾN HI - TECH';
const invDR = [hd('112', '09/07/2025', '0316835171', TT, 2592000), hd('5', '08/01/2026', '0316835171', TT, 2592000),
  hd('77', '17/09/2025', '0305540592', 'CÔNG TY CƠ KHÍ XÂY DỰNG DU LỊCH BÁCH TÙNG', 2592000), hd('9', '25/06/2025', '3603153322', 'CÔNG TY ĐÔNG PHƯƠNG', 2574000)];
const rows = [{ id: 'r1', tx: { date: '08/01/2026', desc: 'D.cong ty Tan tien thanh toan hd hop dung man hinh', credit: 2592000, debit: 0 }, confirmed: null }];
const kq = rematchPending(rows, [], invDR, [], [], 'CTY TNHH THIET BI VA GIAI PHAP SAI GON');
const dsSo = kq[0].invMatches.map(x => x.so_hd);
assert(dsSo[0] === '5', 'HĐ 5 (cùng ngày 08/01/2026) phải đứng đầu gợi ý, được: ' + dsSo.join(','));
assert(kq[0].t2_nameAmt.so_hd === '5', 't2_nameAmt phải là HĐ 5');
assert(!dsSo.includes('112'), 'cùng MST + cùng số tiền chỉ giữ hoá đơn gần ngày nhất (112 bị lọc trùng)');
assert(dsSo.includes('77') && dsSo.includes('9'), 'các công ty khác vẫn có gợi ý');
// giao dịch tháng 7/2025 thì ngược lại: HĐ 112 gần ngày hơn
const kq2 = rematchPending([{ id: 'r2', tx: { date: '10/07/2025', desc: 'chuyen khoan', credit: 2592000, debit: 0 }, confirmed: null }], [], invDR, [], [], 'X');
assert(kq2[0].invMatches[0].so_hd === '112', 'giao dịch 10/07/2025 -> HĐ 112 gần ngày nhất');
console.log('PASS: gợi ý khớp số tiền chọn HĐ cùng ngày/gần ngày giao dịch nhất (HĐ 5 08/01/2026), không để HĐ cũ cùng số tiền che mất');
