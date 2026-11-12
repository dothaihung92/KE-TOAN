// Văn bản TAB do sao_ke_nh.py tạo phải được parseSaoke() của Đối Chiếu Ngân Hàng đọc đúng (ngày, nội dung, tiền ra/vào).
const fs = require('fs'), cp = require('child_process');
const src = fs.readFileSync(__dirname + '/../static/doi_chieu_ngan_hang.html', 'utf8');
const lay = (ten) => { const i = src.indexOf('function ' + ten + '('); if (i < 0) throw new Error('thiếu ' + ten); let d = 0, j = src.indexOf('{', src.indexOf(')', i)); for (let k = j; k < src.length; k++) { if (src[k] === '{') d++; else if (src[k] === '}') { d--; if (d === 0) return src.slice(i, k + 1) } } };
const can = ['normVN', 'parseTable', 'parseNum', 'parseSaoke'];
let code = can.map(lay).join('\n');
const tsv = cp.execFileSync('python3', ['-c', `
import sys; sys.path.insert(0,'.')
import sao_ke_nh as s
print(s.tsv([{"ngay":"02/09/2026","noi_dung":"THANH TOAN CTY ANH DUNG HD SO 1749","tien_ra":15053400,"tien_vao":0},
             {"ngay":"03/09/2026","noi_dung":"NICESTAR THANH TOAN TIEN HANG","tien_ra":0,"tien_vao":30240000}]))`], { cwd: __dirname + '/..' }).toString();
let r;
for (let lan = 0; lan < 6; lan++) {
  try { r = new Function('t', code + ';return parseSaoke(t,"VND")')(tsv); break }
  catch (e) { const m = /(\w+) is not defined/.exec(e.message); if (!m) throw e; code = lay(m[1]) + '\n' + code }
}
const ok = (c, m) => { if (!c) { console.error('SAI', m, JSON.stringify(r)); process.exit(1) } };
ok(r.length === 2, 'số dòng');
const a = r[0], b = r[1];
ok(JSON.stringify(a).includes('1749') && a.debit === 15053400 && !a.credit, 'dòng 1');
ok(b.credit === 30240000 && !b.debit, 'dòng 2');
console.log('PASS: Đối Chiếu Ngân Hàng đọc đúng văn bản sao kê do phần mềm chuẩn hoá.');
console.log('\nALL DONE');
