// "Phần vốn góp hiện có" của thành viên/chủ sở hữu hiện tại tự lấy từ hồ sơ GPKD đã gom (tab "Lấy thông tin GPKD"):
// công ty có 1 chủ sở hữu -> vốn = vốn điều lệ ('700.000.000,000'); danh sách đã lưu thiếu vốn thì được bù từ hồ sơ.
const fs = require('fs');
const src = fs.readFileSync(__dirname + '/../static/index.html', 'utf8');
const lay = (ten) => { const i = src.indexOf('function ' + ten + '('); let d = 0, j = src.indexOf('{', i); for (let k = j; k < src.length; k++) { if (src[k] === '{') d++; else if (src[k] === '}') { d--; if (d === 0) return src.slice(i, k + 1) } } };
const code = ['ssSoVnd', 'ssTienDep', 'ssNguoiTuGom', 'ssLoaiTaiSanGom', 'ssBuVonHienCo', 'ssHienTrangTuGom'].map(lay).join('\n');
const khoi = [
  { khoi: 'Thông tin về chủ sở hữu', cap: [['Họ và tên', 'LÊ THẠCH'], ['Ngày sinh', '02/11/1986'], ['Số giấy tờ pháp lý', '075086004486'], ['Giới tính', 'Nam']] },
  { khoi: 'Thông tin về vốn', cap: [['Vốn điều lệ', '700.000.000,000'], ['Tổng số', '100,000 700.000.000,000']] }];
const f = new Function('khoi', `let gpkdCid=1,current=1,gpkdKhoi=khoi,ssTv={ht:[],moi:[]},ssHienTrang=null;const vbEsc=x=>x;${code};
  const h=ssHienTrangTuGom();ssHienTrang=h;
  ssTv={ht:[{ho_ten:'LÊ THẠCH',cccd:'075086004486'}],moi:[]};ssBuVonHienCo();
  return {tv:h.thanh_vien,von:h.von,ssTv:ssTv.ht}`);
const r = f(khoi);
const ok = (c, m) => { if (!c) { console.error('SAI', m, JSON.stringify(r)); process.exit(1) } };
ok(r.tv.length === 1 && r.tv[0].von === '700.000.000', 'vốn thành viên = vốn điều lệ');
ok(r.tv[0].loai_tai_san === 'Đồng Việt Nam', 'loại tài sản');
ok(r.ssTv[0].von === '700.000.000' && r.ssTv[0].ngay_sinh === '02/11/1986', 'danh sách đã lưu thiếu vốn được bù từ hồ sơ');
console.log('PASS: phần vốn góp hiện có tự lấy từ hồ sơ GPKD (1 chủ sở hữu = vốn điều lệ); danh sách đã lưu được bù.');
console.log('\nALL DONE');
