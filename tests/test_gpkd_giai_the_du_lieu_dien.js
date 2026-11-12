// Mục Giải thể (Bước 1) tạo nhóm điền cổng "Thông tin quyết định giải thể" với 3 ô (Số quyết định, Ngày quyết định dd/mm/yyyy, Lý do giải thể).
const fs = require('fs');
const src = fs.readFileSync(__dirname + '/../static/index.html', 'utf8');
const lay = (ten) => { const i = src.indexOf('function ' + ten + '('); let d = 0, j = src.indexOf('{', i); for (let k = j; k < src.length; k++) { if (src[k] === '{') d++; else if (src[k] === '}') { d--; if (d === 0) return src.slice(i, k + 1) } } };
const code = ['ssNgayVn', 'ssKhoiDienCoSan', 'ssTaoDuLieuDien'].map(lay).join('\n');
const f = new Function('du', `const window={};const SS_KHOI_DIEN={};const ssNganh={them:[],bo:[],sua:[]};const ssThuThap=()=>du;
  const ssNhomThanhVien=()=>{},ssNhomCshhl=()=>{},ssNhomCapNhat=()=>{};${code};return ssTaoDuLieuDien()`);
const r = f({ loai: ['giai_the'], giai_the: { so_qd: '01/QĐ', ngay_qd: '2026-08-24', ly_do: 'Không hoạt động nữa' } });
const ok = (c, m) => { if (!c) { console.error('SAI', m, JSON.stringify(r)); process.exit(1) } };
ok(r.nhom.length === 1 && r.nhom[0].vao_khoi === 'Thông tin quyết định giải thể' && !r.nhom[0].tao_moi, 'nhóm');
const t = Object.fromEntries(r.nhom[0].truong.map(x => [x.ten, x.gia_tri]));
ok(t['Số quyết định'] === '01/QĐ' && t['Ngày quyết định'] === '24/08/2026' && t['Lý do giải thể'] === 'Không hoạt động nữa', 'giá trị');
const r2 = f({ loai: ['giai_the'], giai_the: {} }); ok(r2.nhom.length === 0, 'rỗng thì không có nhóm');
console.log('PASS: Giải thể tạo nhóm điền cổng với 3 ô; rỗng thì không có nhóm.');
console.log('\nALL DONE');
