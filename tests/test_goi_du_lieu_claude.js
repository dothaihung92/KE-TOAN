// 🤝 Gói dữ liệu cho Claude: xuất (claudeTaoGoi) -> Claude điền sheet KET_QUA -> nhập lại (claudeDocKetQua + claudeApDungKetQua). Hàm thuần, dữ liệu giả.
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'doi_chieu_ngan_hang.html'), 'utf8');
function extractFn(name) {
  const start = html.indexOf('function ' + name + '('); if (start < 0) throw new Error('thiếu hàm ' + name);
  let i = html.indexOf('{', start), d = 0, end = -1;
  for (; i < html.length; i++) { if (html[i] === '{') d++; else if (html[i] === '}') { d--; if (!d) { end = i + 1; break } } }
  return html.slice(start, end);
}
const assert = (c, m) => { if (!c) throw new Error('THẤT BẠI: ' + m) };
eval(extractFn('normVN'));
var CLAUDE_COT_KETQUA = ["ID_GIAO_DICH", "ID_HOA_DON", "SO_HD", "MST", "TEN_CTY", "HACH_TOAN", "GHI_CHU", "GHI_DE"];
assert(html.includes('const CLAUDE_COT_KETQUA = ["ID_GIAO_DICH", "ID_HOA_DON", "SO_HD", "MST", "TEN_CTY", "HACH_TOAN", "GHI_CHU", "GHI_DE"];'), 'danh sách cột đồng bộ với bản test');
eval(extractFn('claudeTrangThai')); eval(extractFn('claudeKhoaHoaDon')); eval(extractFn('claudeTaoGoi')); eval(extractFn('claudeDocKetQua')); eval(extractFn('claudeApDungKetQua'));
const hd = (so, ngay, mst, ten, tong) => ({ id: 'i' + so, so_hd: so, ngay, mst, ten_cty: ten, tong });
const invDR = [hd('71', '15/04/2026', '3702753151', 'CÔNG TY TNHH CHẾ TẠO BƠM TS', 18360000), hd('5', '08/01/2026', '0316835171', 'CÔNG TY TÂN TIẾN', 2592000), hd('112', '09/07/2025', '0316835171', 'CÔNG TY TÂN TIẾN', 2592000)];
const invDV = [hd('88', '02/02/2026', '0300000009', 'CÔNG TY ABC', 5000000)];
const rows = [
  { id: 'g1', tx: { date: '25/04/2026', desc: 'thanh toan hoa don 71', credit: 18360000, debit: 0 }, confirmed: '', invMatches: [invDR[0]] },
  { id: 'g2', tx: { date: '08/01/2026', desc: 'Tan tien thanh toan hd', credit: 2592000, debit: 0 }, confirmed: '' },
  { id: 'g3', tx: { date: '02/02/2026', desc: 'tra tien ABC', credit: 0, debit: 5000000 }, confirmed: '' },
  { id: 'g4', tx: { date: '03/02/2026', desc: 'phi quan ly tai khoan', credit: 0, debit: 22000 }, confirmed: '' },
  { id: 'g5', tx: { date: '04/02/2026', desc: 'da xu ly tay', credit: 100000, debit: 0 }, confirmed: 'yes', manualConfirm: true, confirmedMST: '0301', confirmedName: 'X', confirmedHach: '131', confirmedInvId: 'i5' }];
const goi = claudeTaoGoi(rows, invDV, invDR, [{ keyword: 'tan tien', mst: '0316835171', ten_cty: 'CÔNG TY TÂN TIẾN', hach_toan: '131' }], 'CTY TEST');
assert(Object.keys(goi).join(',') === 'HUONG_DAN,GIAO_DICH,HD_DAU_RA,HD_DAU_VAO,TU_DIEN,KET_QUA', 'đủ 6 sheet: ' + Object.keys(goi));
assert(goi.GIAO_DICH.length === 6 && goi.GIAO_DICH[0][0] === 'ID_GIAO_DICH' && goi.GIAO_DICH[1][0] === 'g1' && goi.GIAO_DICH[1][5] === 'Chờ' && goi.GIAO_DICH[5][5] === 'Thủ công', 'sheet GIAO_DICH + trạng thái');
assert(goi.HD_DAU_RA.length === 4 && goi.HD_DAU_RA[2][0] === 'i5' && goi.HD_DAU_RA[2][6] === 'g5', 'HD_DAU_RA có ID hoá đơn và hoá đơn đã gắn cho giao dịch nào');
assert(goi.TU_DIEN[1][0] === 'tan tien' && goi.KET_QUA.length === 1 && goi.KET_QUA[0].join(',') === CLAUDE_COT_KETQUA.join(','), 'từ điển + KET_QUA chỉ có dòng tiêu đề');
assert(goi.HUONG_DAN.flat().join('\n').includes('CÂU LỆNH MẪU') && goi.HUONG_DAN.flat().join('\n').includes('ID_GIAO_DICH'), 'có hướng dẫn + câu lệnh mẫu');
// Claude trả file: tiêu đề có thể lệch hoa/thường/dấu, có dòng rác phía trên
const aoa = [['KẾT QUẢ'], ['id giao dich', 'ID_HOA_DON', 'so_hd', 'mst', 'ten cty', 'Hach toan', 'ghi chu', 'ghi de'],
  ['g1', 'i71', '', '', '', '131', 'số HĐ 71 + đúng tiền', ''],
  ['g2', '', '5', '316835171', '', '131.0', 'cùng ngày + tên Tân Tiến', ''],     // chỉ có SO_HD + MST thiếu số 0 đầu
  ['g3', '', '', '300000009', 'CÔNG TY ABC', '3311', 'trả NCC', ''],               // không có HĐ, chỉ MST
  ['g4', '', '', '', '', '6427', 'phí ngân hàng', ''],                              // chỉ hạch toán
  ['g5', 'i71', '', '', '', '131', 'đã xử lý tay', ''],                              // giao dịch đã xử lý -> bỏ qua
  ['zz', 'i71', '', '', '', '131', 'id lạ', ''],
  ['g1', '', '999', '', '', '', 'HĐ không tồn tại', 'x']];
const dk = claudeDocKetQua(aoa);
assert(dk.thieuCot.length === 0 && dk.ds.length === 7 && dk.ds[0]._dong === 3 && dk.ds[1].HACH_TOAN === '131.0', 'đọc file Claude trả về');
assert(claudeDocKetQua([['a', 'b']]).thieuCot[0] === 'ID_GIAO_DICH', 'thiếu cột ID -> báo');
const kq = claudeApDungKetQua(rows, invDV, invDR, dk.ds);
const c = kq.capNhat;
assert(c.g1.confirmedInvId === 'i71' && c.g1.confirmedMST === '3702753151' && c.g1.confirmedHach === '131' && c.g1.confirmedLoai === 'DAURA' && c.g1.ai.nguon === 'claude' && c.g1.manualConfirm === false, 'g1 gắn HĐ 71');
assert(c.g2.confirmedInvId === 'i5' && c.g2.confirmedMST === '0316835171' && c.g2.confirmedHach === '131', 'g2: chọn HĐ 5 theo SO_HD + MST (thiếu số 0) + số tiền gần nhất, hạch toán "131.0" -> 131');
assert(c.g3.confirmedInvId === '' && c.g3.confirmedMST === '0300000009' && c.g3.confirmedHach === '3311' && c.g3.confirmedLoai === 'DAUVAO', 'g3: chỉ MST + hạch toán');
assert(c.g4.confirmedMST === '' && c.g4.confirmedHach === '6427' && c.g4.confirmedLoai === 'DAUVAO', 'g4: chỉ hạch toán');
assert(!c.g5 && kq.boQua === 1, 'g5 đã xử lý tay -> bỏ qua');
assert(kq.loi.length >= 2 && kq.loi.some(x => x.includes('zz')) && kq.loi.some(x => x.includes('999')), 'báo lỗi id lạ / HĐ không tồn tại: ' + kq.loi.join(' | '));
assert(kq.soXuLy === 4, 'tổng 4 giao dịch: ' + kq.soXuLy);
// GHI_DE=x cho phép ghi đè giao dịch đã xử lý
const kq2 = claudeApDungKetQua(rows, invDV, invDR, claudeDocKetQua([CLAUDE_COT_KETQUA, ['g5', 'i5', '', '', '', '131', 'sửa', 'x']]).ds);
assert(kq2.capNhat.g5 && kq2.capNhat.g5.confirmedInvId === 'i5', 'GHI_DE = x thì ghi đè');
console.log('PASS: gói dữ liệu cho Claude — xuất 6 sheet có ID + hướng dẫn/câu lệnh mẫu; nhập KET_QUA (tiêu đề lệch, HĐ theo ID/số HĐ+MST, chỉ MST, chỉ hạch toán), bỏ qua dòng đã xử lý, báo lỗi');
