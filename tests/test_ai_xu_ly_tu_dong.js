// 🤖 AI xử lý tự động (Đối chiếu ngân hàng): tự gắn hoá đơn + hạch toán cho giao dịch Chờ đủ chắc, ghi r.ai để có mục "AI xử lý"; không gắn bừa khi mơ hồ. Dữ liệu giả theo ca thật.
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'doi_chieu_ngan_hang.html'), 'utf8');
function extractFn(name) {
  const start = html.indexOf('function ' + name + '('); if (start < 0) throw new Error('thiếu hàm ' + name);
  let i = html.indexOf('{', start), d = 0, end = -1;
  for (; i < html.length; i++) { if (html[i] === '{') d++; else if (html[i] === '}') { d--; if (!d) { end = i + 1; break } } }
  return html.slice(start, end);
}
const assert = (c, m) => { if (!c) throw new Error('THẤT BẠI: ' + m) };
eval(extractFn('normVN')); eval(extractFn('parseNgayGanGiaoDich'));
const AI_NGUONG_TIN_CAY = 80; eval(html.match(/const AI_BIGRAM_BO = new Set\(\[[^\]]*\]\);/)[0].replace('const', 'var')); eval(html.match(/const AI_SKIP = new Set\(\[[^\]]*\]\);/)[0].replace('const', 'var'));
eval(extractFn('aiTrichSoHd')); eval(extractFn('aiPhanTichGiaoDich')); eval(extractFn('aiXuLyHangLoat'));
const hd = (so, ngay, mst, ten, tong) => ({ id: 'i' + so + mst, so_hd: so, ngay, mst, ten_cty: ten, tong });
const row = (id, date, desc, credit, debit = 0) => ({ id, tx: { date, desc, credit, debit }, confirmed: '' });
// 1) số HĐ trong nội dung + tên công ty + đúng số tiền
assert(aiTrichSoHd('Bomts thanh toan hoa don so71 CKN 160067 I2QAR81I - CTY TNHH CHE TAO BOM TS') === '71', 'trích số HĐ 71');
const invDR = [hd('71', '15/04/2026', '3702753151', 'CÔNG TY TNHH CHẾ TẠO BƠM TS', 18360000), hd('1', '06/01/2025', '1201608865', 'CÔNG TY TNHH DỊCH VỤ KỸ THUẬT HỮU PHÁT', 18598800),
  hd('112', '09/07/2025', '0316835171', 'CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ - GIA CÔNG CƠ KHÍ TÂN TIẾN HI - TECH', 2592000), hd('5', '08/01/2026', '0316835171', 'CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ - GIA CÔNG CƠ KHÍ TÂN TIẾN HI - TECH', 2592000),
  hd('77', '17/09/2025', '0305540592', 'CÔNG TY TNHH CƠ KHÍ XÂY DỰNG DU LỊCH BÁCH TÙNG', 2592000), hd('9', '05/01/2026', '0109646049', 'CÔNG TY TNHH THIẾT BỊ CÔNG NGHIỆP VTP VIỆT NAM', 2592000)];
const rows = [row('a', '25/04/2026', 'Bomts thanh toan hoa don so71 CKN 160067 I2QAR81I - CTY TNHH CHE TAO BOM TS - Ngan hang TMCP Tien Phong', 18360000),
  row('b', '08/01/2026', 'MBVCB.12488372333 D.cong ty Tan tien thanh toan hd hop dung man hinh.CT tu 0011002255201 HOANG THI HANG', 2592000),
  row('c', '20/03/2026', 'chuyen khoan linh tinh', 2592000), // 4 công ty cùng số tiền, không manh mối -> AI KHÔNG gắn
  row('d', '10/05/2026', 'khong ro', 99999999)];
const kq = aiXuLyHangLoat(rows, [], invDR, [], 80);
assert(kq.capNhat.a && kq.capNhat.a.confirmedMST === '3702753151' && kq.capNhat.a.confirmedLoai === 'DAURA' && kq.capNhat.a.confirmedHach === '131' && kq.capNhat.a.confirmed === 'yes' && kq.capNhat.a.manualConfirm === false, 'a: gắn HĐ 71');
assert(kq.capNhat.a.ai.tin >= 95 && kq.capNhat.a.ai.soHd === '71' && kq.capNhat.a.ai.lyDo.join(';').includes('số HĐ 71'), 'a: có lý do + độ tin cậy');
assert(kq.capNhat.b && kq.capNhat.b.confirmedInvId === 'i50316835171' && kq.capNhat.b.ai.soHd === '5', 'b: HĐ 5 (cùng ngày) được AI gắn: ' + JSON.stringify(kq.capNhat.b && kq.capNhat.b.ai));
assert(!kq.capNhat.c && !kq.capNhat.d, 'c, d: không đủ chắc -> không gắn');
assert(kq.soXuLy === 2 && kq.soKhongChac >= 1, 'đếm: ' + kq.soXuLy + '/' + kq.soKhongChac);
// 2) hoá đơn đã gắn giao dịch khác không bị gắn lần 2
const rows2 = [Object.assign(row('x', '25/04/2026', 'thanh toan hoa don so71 CTY TNHH CHE TAO BOM TS', 18360000), { confirmed: 'yes', confirmedInvId: 'i713702753151' }),
  row('y', '26/04/2026', 'thanh toan hoa don so71 CTY TNHH CHE TAO BOM TS', 18360000)];
const kq2 = aiXuLyHangLoat(rows2, [], invDR, [], 80);
assert(!kq2.capNhat.y, 'HĐ đã gắn cho giao dịch khác bị trừ điểm -> không gắn lần 2');
// 3) tiền ra -> hoá đơn đầu vào, hạch toán 331; hạch toán lấy theo từ điển của công ty nếu có
const invDV = [hd('88', '02/02/2026', '0300000009', 'CÔNG TY TNHH ABC', 5000000)];
const kq3 = aiXuLyHangLoat([row('z', '02/02/2026', 'thanh toan hoa don 88 cho CTY ABC', 0, 5000000)], invDV, [], [{ mst: '0300000009', hach_toan: '3311' }], 80);
assert(kq3.capNhat.z && kq3.capNhat.z.confirmedLoai === 'DAUVAO' && kq3.capNhat.z.confirmedHach === '3311', 'tiền ra -> DAUVAO, hạch toán theo từ điển: ' + JSON.stringify(kq3.capNhat.z));
const kq4 = aiXuLyHangLoat([row('z', '02/02/2026', 'thanh toan hoa don 88 cho CTY ABC', 0, 5000000)], invDV, [], [], 80);
assert(kq4.capNhat.z.confirmedHach === '331', 'không có từ điển -> 331');
// 4) dòng đã xác nhận/nội bộ không đụng
const kq5 = aiXuLyHangLoat([Object.assign(row('k', '25/04/2026', 'hoa don so71 CHE TAO BOM TS', 18360000), { confirmed: 'yes' }), Object.assign(row('m', '25/04/2026', 'hoa don so71 CHE TAO BOM TS', 18360000), { isInternal: true })], [], invDR, [], 80);
assert(kq5.soXuLy === 0, 'không đụng dòng đã xác nhận/chuyển tiền nội bộ');
console.log('PASS: 🤖 AI xử lý tự động — tự gắn HĐ #71 và HĐ #5, không gắn khi mơ hồ/đã dùng, hạch toán theo từ điển, ghi lý do + độ tin cậy');
