// Ô ngày gõ tay (thay input type=date): phân tích / hiển thị / tự chèn "/" — chạy ĐÚNG code JS trong static/index.html
const fs = require('fs'), path = require('path'), assert = require('assert'), vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'index.html'), 'utf8');
const m = html.match(/<script id="ngayGoTay">([\s\S]*?)<\/script>/);
assert(m, 'thiếu script ngayGoTay');
const ctx = { console }; vm.createContext(ctx); vm.runInContext(m[1], ctx);
const p = (t) => JSON.parse(JSON.stringify(ctx.ngayGoTayParse(t)));
assert.deepStrictEqual(p(''), { iso: '' });
for (const [t, iso] of [['05102026', '2026-10-05'], ['5/10/2026', '2026-10-05'], ['05/10/2026', '2026-10-05'], ['5-1-26', '2026-01-05'], ['05.10.2026', '2026-10-05'],
  ['2026-10-05', '2026-10-05'], ['051026', '2026-10-05'], [' 5 / 10 / 2026 ', '2026-10-05'], ['29/02/2024', '2024-02-29'], ['31/12/1999', '1999-12-31']])
  assert.deepStrictEqual(p(t), { iso }, t);
for (const t of ['31/02/2026', '29/02/2025', '32/01/2026', '01/13/2026', '1/1/1800', '0/5/2026', 'abc', '1234', '05/10', '05102'])
  assert(p(t).loi && !('iso' in p(t)), 'phải báo lỗi: ' + t);
assert.strictEqual(ctx.ngayGoTayHien('2026-10-05'), '05/10/2026');
assert.strictEqual(ctx.ngayGoTayHien(''), '');
// tự chèn "/" khi gõ từng số
let t = ''; for (const c of '05102026') { t = ctx.ngayGoTayTuDinhDang(t + c); }
assert.strictEqual(t, '05/10/2026');
assert.strictEqual(ctx.ngayGoTayTuDinhDang('0'), '0'); assert.strictEqual(ctx.ngayGoTayTuDinhDang('051'), '05/1'); assert.strictEqual(ctx.ngayGoTayTuDinhDang('05/10/20269'), '05/10/2026');
// người dùng tự gõ dấu phân cách / số không đệm 0: để nguyên
assert.strictEqual(ctx.ngayGoTayTuDinhDang('5/'), '5/'); assert.strictEqual(ctx.ngayGoTayTuDinhDang('5/1/26'), '5/1/26'); assert.strictEqual(ctx.ngayGoTayTuDinhDang('5-1-26'), '5-1-26');
// mọi input type=date trong trang đều được bọc bởi script (quét tự động, kể cả ô tạo sau)
assert(html.includes('input[type="date"]:not([data-dt-da])') && html.includes('new MutationObserver') && html.includes("placeholder='dd/mm/yyyy'"));
console.log('PASS: ô ngày gõ tay.');
