// Lịch Shopee TIẾNG ANH: tiêu đề "October2026" / "November2026" (không có chữ "Tháng") -> tiện ích phải đọc được (năm, tháng)
// để tự chọn ngày. Trước đây báo "không tìm thấy ngày 2026/11/9 trong lịch (?, ?)".
const fs = require('fs');
const src = fs.readFileSync(__dirname + '/../tien_ich_chrome/xuat_don_tmdt/chay.js', 'utf8');
const i = src.indexOf('const thangNam=');
const j = src.indexOf('const kich=', i);
const thangNam = eval('(()=>{' + src.slice(i, j) + ';return thangNam})()');
const el = t => ({innerText: t, parentElement: null, closest: () => null});
const kt = (t, mong) => { const r = thangNam(el(t)); if (JSON.stringify(r) !== JSON.stringify(mong)) { console.error('SAI', t, r, mong); process.exit(1) } };
kt('October2026', [2026, 10]);
kt('November2026', [2026, 11]);
kt('Nov 2026', [2026, 11]);
kt('Sep. 2025', [2025, 9]);
kt('Tháng 102026', [2026, 10]);
kt('11 / 2026', [2026, 11]);
kt('Marketing Centre', null);
console.log('PASS: đọc được tiêu đề lịch tiếng Anh (October2026, Nov 2026) và tiếng Việt như cũ.');
console.log('\nALL DONE');
