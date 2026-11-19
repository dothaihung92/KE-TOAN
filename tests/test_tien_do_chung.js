// Thanh tiến độ CHUNG của Tra cứu: 0 -> 100%, không lùi, 100% chỉ khi xong. Dữ liệu giả theo các dòng log thật.
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const src = fs.readFileSync(__dirname + '/../static/index.html', 'utf8');
const lay = (a, b) => { const i = src.indexOf(a); const j = src.indexOf(b, i); assert(i >= 0 && j > i, 'thiếu ' + a); return src.slice(i, j) };
const code = lay('const RE_TAG_THANG=', '\n') + '\n' + lay('function tdMoi()', 'async function watchFetchProgress');
const dom = {};
const ctx = { document: { getElementById: id => dom[id] || null }, Date };
vm.createContext(ctx); vm.runInContext(code + '\nthis.tdMoi=tdMoi;this.tdXuLy=tdXuLy;this.tdTinh=tdTinh;this.tdThoiGian=tdThoiGian;', ctx);
const T = (tienTo, loai, sub) => ({ text: `${tienTo}: [${loai} chung] ${sub}` });
const td = ctx.tdMoi(); let truoc = 0; const buoc = (m) => { ctx.tdXuLy(td, m); const p = ctx.tdTinh(td); assert(p >= truoc, 'tiến độ không được lùi: ' + truoc + '→' + p); assert(p >= 0 && p <= 100); truoc = p; return p };
// 4 tổ hợp báo "xong 0/1 tháng"
['mua vào', 'mua vào (máy tính tiền)', 'bán ra', 'bán ra (máy tính tiền)'].forEach(t => buoc(T(t, 'TIẾN ĐỘ', 'xong 0/1 tháng — đã lấy 0 hóa đơn — đã chạy 0 giây')));
assert.strictEqual(ctx.tdTinh(td), 0);
// 2 tổ hợp xong danh sách -> ~22%
buoc(T('mua vào', 'TIẾN ĐỘ', '✓ xong 1/1 tháng — đã lấy 113 hóa đơn')); buoc(T('bán ra', 'TIẾN ĐỘ', '✓ xong 1/1 tháng — đã lấy 0 hóa đơn'));
let p = ctx.tdTinh(td); assert(p >= 20 && p <= 24, 'sau 2/4 danh sách ≈22%: ' + p);
// bán ra MTT đang lấy danh sách 200/1918 -> tăng nhẹ
const p2 = buoc({ text: 'bán ra (máy tính tiền): [ĐOẠN 01/10/2026→31/10/2026] đang tải danh sách… đã lấy 200/1918 hóa đơn (còn 1718)' }); assert(p2 > p, 'đoạn đang chạy làm thanh nhích lên');
buoc(T('mua vào (máy tính tiền)', 'TIẾN ĐỘ', '✓ xong 1/1 tháng — đã lấy 15 hóa đơn')); buoc(T('bán ra (máy tính tiền)', 'TIẾN ĐỘ', '✓ xong 1/1 tháng — đã lấy 1918 hóa đơn'));
p = ctx.tdTinh(td); assert.strictEqual(p, 45, 'xong cả 4 danh sách = 45%: ' + p);
// tải file bán ra 917/1918 -> 45 + 40*(0.478/2)...
buoc({ stage: 'download', text: 'Đang tải file bán ra: 917/1918 (còn 1001)', cur: 917, total: 1918 });
p = ctx.tdTinh(td); assert(p > 45 && p < 85, 'đang tải file: ' + p);
buoc({ stage: 'download', text: 'Đang tải file mua vào: 84/84', cur: 84, total: 84 }); buoc({ stage: 'download', text: 'Đang tải file bán ra: 1918/1918', cur: 1918, total: 1918 });
p = ctx.tdTinh(td); assert.strictEqual(p, 85, 'tải đủ file = 85%: ' + p);
buoc({ stage: 'info', text: 'Đang tự động kết xuất Excel…' }); assert.strictEqual(ctx.tdTinh(td), 85);
assert(td.buoc === 3);
buoc({ stage: 'done', text: 'Hoàn tất' }); assert.strictEqual(ctx.tdTinh(td), 100);
// chưa xong thì tối đa 99%
const t2 = ctx.tdMoi(); ctx.tdXuLy(t2, T('bán ra', 'TIẾN ĐỘ', '✓ xong 1/1 tháng')); ctx.tdXuLy(t2, { stage: 'download', text: 'tải file bán ra: 5/5', cur: 5, total: 5 }); ctx.tdXuLy(t2, { text: 'kết xuất Excel' });
assert(ctx.tdTinh(t2) < 100);
assert.strictEqual(ctx.tdThoiGian(45), '45 giây'); assert.strictEqual(ctx.tdThoiGian(135), '2 phút 15 giây');
console.log('PASS: thanh tiến độ chung 0→100% (danh sách 45% + tải file 40% + đối chiếu/Excel 15%), không lùi, 100% chỉ khi xong');
