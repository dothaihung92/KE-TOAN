// Khung "AI xử lý": đã gỡ Gemini; hiện full màn hình, có tìm kiếm, cột MST/tên/loại thu-chi, sửa hạch toán + đổi HĐ, nền xanh/vàng.
const fs = require('fs'), path = require('path');
const s = fs.readFileSync(path.join(__dirname, '..', 'static', 'doi_chieu_ngan_hang.html'), 'utf8');
const sv = fs.readFileSync(path.join(__dirname, '..', 'server.py'), 'utf8');
const assert = (c, m) => { if (!c) { console.error('FAIL: ' + m); process.exit(1); } };
assert(!/gemini/i.test(s), 'giao diện không còn Gemini');
assert(!/api\/ai\/(gemini|khoa)/.test(sv) && !/_ai_gemini/.test(sv), 'máy chủ không còn Gemini');
assert(/const chayAiXuLy = \(\) => \{\s*setAiPanel\(true\)/.test(s), 'bấm nút luôn mở khung');
const i = s.indexOf('function AiXuLyPanel('), j = s.indexOf('function ConfirmRow(');
const p = s.slice(i, j);
for (const [k, m] of [['position: "fixed", inset: 0, background: "#fff"', 'full màn hình'], ['🔍 Tìm theo ngày, nội dung', 'ô tìm kiếm'], ['MST công ty gắn', 'cột MST'], ['Tên công ty gắn', 'cột tên công ty'], ['Đầu ra (bán)', 'loại đầu ra'], ['Đầu vào (mua)', 'loại đầu vào'], ['#dcfce7', 'nền xanh tiền vào'], ['#fef9c3', 'nền vàng tiền ra'], ['onHach', 'sửa hạch toán'], ['onPick', 'đổi HĐ/công ty'], ['onMst', 'sửa MST']]) assert(p.includes(k), 'thiếu ' + m);
assert(/zIndex: 1100/.test(s), 'hộp chọn HĐ nằm trên khung AI');
console.log('PASS: khung AI xử lý full màn hình, tìm kiếm, MST/tên/loại, nền xanh-vàng, sửa hạch toán + đổi HĐ; đã gỡ Gemini');
