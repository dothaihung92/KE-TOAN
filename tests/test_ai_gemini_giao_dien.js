// 🤖 AI + Gemini (giao diện): chọn ứng viên, dựng prompt, đọc JSON, ÁP DỤNG có chốt chặn (tin cậy >= 85, số tiền khớp <= 2%, không gắn trùng hoá đơn), gọi qua /api/ai/gemini (giả lập fetch).
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'doi_chieu_ngan_hang.html'), 'utf8');
function extractFn(name, async_) {
  const start = html.indexOf((async_ ? 'async function ' : 'function ') + name + '('); if (start < 0) throw new Error('thiếu hàm ' + name);
  let i = html.indexOf('{', start), d = 0, end = -1;
  for (; i < html.length; i++) { if (html[i] === '{') d++; else if (html[i] === '}') { d--; if (!d) { end = i + 1; break } } }
  return html.slice(start, end);
}
const assert = (c, m) => { if (!c) throw new Error('THẤT BẠI: ' + m) };
eval(extractFn('normVN')); eval(extractFn('parseNgayGanGiaoDich'));
eval(html.match(/const AI_SKIP = new Set\(\[[^\]]*\]\);/)[0].replace('const', 'var'));
var AI_NGUONG_GEMINI = 85; var AI_HE_THONG_GEMINI = 'x';
eval(extractFn('aiUngVienChoGemini')); eval(extractFn('aiXayPromptGemini')); eval(extractFn('aiDocKetQuaGemini')); eval(extractFn('aiApDungKetQuaGemini')); eval(extractFn('aiXuLyGemini', true));
const hd = (so, ngay, mst, ten, tong) => ({ id: 'i' + so, so_hd: so, ngay, mst, ten_cty: ten, tong });
const invDR = [hd('10', '05/03/2026', '0300000001', 'CÔNG TY A', 1000000), hd('11', '06/03/2026', '0300000002', 'CÔNG TY B', 1000000), hd('12', '07/03/2026', '0300000003', 'CÔNG TY C', 5000000)];
const rows = [{ id: 'r1', tx: { date: '06/03/2026', desc: 'CK tien hang dot 1', credit: 1000000, debit: 0 }, confirmed: '' },
  { id: 'r2', tx: { date: '06/03/2026', desc: 'khong lien quan', credit: 77777, debit: 0 }, confirmed: '' },   // không có ứng viên -> không gửi Gemini
  { id: 'r3', tx: { date: '06/03/2026', desc: 'thanh toan', credit: 5000000, debit: 0 }, confirmed: '' }];
const uv = aiUngVienChoGemini(rows[0].tx, invDR.map(i => ({ ...i, loai: 'DAURA' })), new Set());
assert(uv.length === 2 && uv[0].so_hd === '11' && uv[0].stt === 1, 'ứng viên: 2 HĐ đúng 1.000.000, HĐ ngày gần (11) đứng đầu: ' + JSON.stringify(uv.map(u => u.so_hd)));
const p = aiXayPromptGemini([{ id: 'r1', tx: rows[0].tx, uv }]);
assert(p.includes('"noi_dung":"CK tien hang dot 1"') && p.includes('"ung_vien"') && !p.includes('_inv'), 'prompt có nội dung + ứng viên, không lộ trường nội bộ');
assert(aiDocKetQuaGemini('```json\n{"ket_qua":[{"id":"r1","chon":1}]}\n```').length === 1 && aiDocKetQuaGemini('[{"id":"a"}]').length === 1 && aiDocKetQuaGemini('rác').length === 0, 'đọc JSON (có/không rào ```)');
// áp dụng có chốt chặn
const muc = [{ id: 'r1', tx: rows[0].tx, uv }];
let kq = aiApDungKetQuaGemini(muc, [{ id: 'r1', chon: 1, tin: 92, hach: '131', ly: 'đúng công ty B' }], new Set(), 'now');
assert(kq.capNhat.r1 && kq.capNhat.r1.confirmedMST === '0300000002' && kq.capNhat.r1.confirmedLoai === 'DAURA' && kq.capNhat.r1.ai.nguon === 'gemini' && kq.capNhat.r1.manualConfirm === false, 'gắn HĐ 11');
kq = aiApDungKetQuaGemini(muc, [{ id: 'r1', chon: 1, tin: 70, hach: '131' }], new Set(), 'now'); assert(!kq.capNhat.r1, 'tin cậy < 85 -> không gắn');
kq = aiApDungKetQuaGemini(muc, [{ id: 'r1', chon: 9, tin: 99 }], new Set(), 'now'); assert(!kq.capNhat.r1, 'stt không tồn tại -> không gắn');
kq = aiApDungKetQuaGemini(muc, [{ id: 'r1', chon: null, tin: 99 }], new Set(), 'now'); assert(!kq.capNhat.r1, 'Gemini nói null -> không gắn');
const muc2 = [{ id: 'r1', tx: rows[0].tx, uv: [{ stt: 1, _inv: invDR[2], so_hd: '12' }] }];     // Gemini "đoán" HĐ 5.000.000 cho giao dịch 1.000.000
kq = aiApDungKetQuaGemini(muc2, [{ id: 'r1', chon: 1, tin: 99 }], new Set(), 'now'); assert(!kq.capNhat.r1, 'số tiền không khớp -> chặn dù Gemini tự tin');
kq = aiApDungKetQuaGemini(muc, [{ id: 'r1', chon: 1, tin: 95 }], new Set(['i11']), 'now'); assert(!kq.capNhat.r1, 'HĐ đã gắn giao dịch khác + nội dung không nêu số HĐ -> không gắn trùng');
kq = aiApDungKetQuaGemini(muc, [{ id: 'r1', chon: 1, tin: 95, hach: 'rác' }], new Set(), 'now'); assert(kq.capNhat.r1.confirmedHach === '131', 'hạch toán lạ -> mặc định 131');
// gọi qua máy chủ (fetch giả)
let goi = 0; global.fetch = async (url, o) => { goi++; assert(url === '/api/ai/gemini', 'đúng đường dẫn'); const b = JSON.parse(o.body); assert(b.prompt.includes('r1') && !b.prompt.includes('r2'), 'chỉ gửi giao dịch có ứng viên');
  return { ok: true, json: async () => ({ text: JSON.stringify({ ket_qua: [{ id: 'r1', chon: 1, tin: 93, hach: '131', ly: 'ok' }, { id: 'r3', chon: 1, tin: 60 }] }) }) }; };
(async () => {
  const g = await aiXuLyGemini(rows, [], invDR, new Set(), () => {});
  assert(goi === 1 && g.soGuiGemini === 2 && g.soXuLy === 1 && g.capNhat.r1 && !g.capNhat.r3 && !g.loi, 'luồng đầy đủ: ' + JSON.stringify({ goi, g: g.soGuiGemini, x: g.soXuLy, l: g.loi }));
  global.fetch = async () => ({ ok: false, status: 502, json: async () => ({ detail: 'Gemini báo lỗi 429' }) });
  const g2 = await aiXuLyGemini(rows, [], invDR, new Set(), () => {}); assert(g2.soXuLy === 0 && g2.loi.includes('429'), 'lỗi Gemini được báo, không gắn gì');
  console.log('PASS: 🤖 Gemini — ứng viên, prompt, đọc JSON, áp dụng có chốt chặn (tin cậy/số tiền/trùng HĐ), gọi qua máy chủ, báo lỗi');
})().catch(e => { console.error(e.message); process.exit(1); });
