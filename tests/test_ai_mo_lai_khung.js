// Khung "AI xử lý": đã gỡ Gemini; hiện full màn hình, có tìm kiếm, cột MST/tên/loại thu-chi, sửa hạch toán + đổi HĐ, nền xanh/vàng.
const fs = require('fs'), path = require('path');
const s = fs.readFileSync(path.join(__dirname, '..', 'static', 'doi_chieu_ngan_hang.html'), 'utf8');
const sv = fs.readFileSync(path.join(__dirname, '..', 'server.py'), 'utf8');
const assert = (c, m) => { if (!c) { console.error('FAIL: ' + m); process.exit(1); } };
assert(!/gemini/i.test(s), 'giao diện không còn Gemini');
assert(!/api\/ai\/(gemini|khoa)/.test(sv) && !/_ai_gemini/.test(sv), 'máy chủ không còn Gemini');
assert(/const chayAiXuLy = \(\) => setAiPanel\(true\)/.test(s), 'bấm nút chỉ mở khung');
assert(!/aiXuLyHangLoat|aiPhanTichGiaoDich/.test(s), 'đã gỡ AI nội bộ trên máy');
assert(s.includes('r.ai.nguon === "claude" && r.confirmed === "yes"'), 'khung chỉ hiện kết quả Claude');
const i = s.indexOf('function AiXuLyPanel('), j = s.indexOf('function ConfirmRow(');
const p = s.slice(i, j);
for (const [k, m] of [['position: "fixed", inset: 0, background: "#fff"', 'full màn hình'], ['🔍 Tìm theo ngày, nội dung', 'ô tìm kiếm'], ['MST công ty', 'cột MST'], ['Tên công ty', 'cột tên công ty'], ['#dcfce7', 'nền xanh tiền vào'], ['#fef9c3', 'nền vàng tiền ra'], ['onHach', 'sửa hạch toán'], ['onPick', 'đổi HĐ/công ty']]) assert(p.includes(k), 'thiếu ' + m);
for (const k of ['Loại"', 'Tiền vào"', 'onUndo', 'Hoàn tác', 'onMst', 'Tin cậy']) assert(!p.includes(k), 'đã bỏ ' + k);
assert(!/\(vao \? "\+" : "−"\)/.test(p), 'số tiền không dấu +/−');
assert(p.includes('fontSize: 15') && p.includes('Ctrl+Z'), 'chữ to + hướng dẫn Ctrl+Z');
assert(p.includes('dsXep') && p.includes('TIỀN VÀO —') && p.includes('TIỀN RA —') && p.includes('(y.tx.credit > 0) - (x.tx.credit > 0)'), 'tiền vào xếp trước, tiền ra sau, có tiêu đề nhóm');
assert(/zIndex: 1100/.test(s), 'hộp chọn HĐ nằm trên khung AI');
console.log('PASS: khung AI xử lý full màn hình, tìm kiếm, MST/tên/loại, nền xanh-vàng, sửa hạch toán + đổi HĐ; đã gỡ Gemini');
