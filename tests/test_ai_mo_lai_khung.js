// Khung "AI xử lý tự động" phải mở lại được ở lần bấm thứ 2, kể cả khi AI đang chạy nền; Gemini có hạn chờ.
const fs = require('fs');
const s = fs.readFileSync(__dirname + '/../static/doi_chieu_ngan_hang.html', 'utf8');
const i = s.indexOf('const chayAiXuLy = async () => {');
const dong = s.slice(i, i + 300);
const iOpen = dong.indexOf('setAiPanel(true)'), iRet = dong.indexOf('if (aiDangChay) return');
if (iOpen < 0 || iRet < 0 || iOpen > iRet) { console.error('FAIL: phải mở khung TRƯỚC khi return vì đang chạy'); process.exit(1); }
if (!s.includes('new AbortController()') || !s.includes('ac.abort(), 90000')) { console.error('FAIL: thiếu hạn chờ Gemini'); process.exit(1); }
console.log('PASS: khung AI luôn mở lại được + Gemini có hạn chờ 90s');
