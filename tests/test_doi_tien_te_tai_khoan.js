// Regression test (Node) cho hàm THUẦN doiTienTeTaiKhoan() trong
// static/doi_chieu_ngan_hang.html (Kế Toán AI), theo báo cáo thật của người
// dùng kèm ảnh chụp màn hình: "tài khoản ngoại tệ Mã hạch toán MISA bị sai
// hãy xem lại" — TK USD 24449247 (nhãn "USD") vẫn hiện "Mã hạch toán MISA"
// = "1121" (mã TK con VND) dù đã đổi tiền tệ tab sang USD.
//
// Nguyên nhân: nút toggle "Đổi VND<->USD" trên tab (updateCurrency) trước
// đây CHỈ đổi field "currency" của tài khoản, KHÔNG hề đụng tới "misaAcct"
// — nếu misaAcct đã được gán CỤ THỂ từ trước (vd "1121", do tự gõ tay/đồng
// bộ từ MISA khi TK còn đang ở VND), giá trị đó GIỮ NGUYÊN VĨNH VIỄN dù
// currency đổi sang USD, khiến "Mã hạch toán MISA" hiện SAI tiền tệ.
//
// Fix: doiTienTeTaiKhoan(accounts, accId, cur) — đổi currency THÌ ĐỔI LUÔN
// misaAcct sang đúng tiền tệ MỚI, NẾU misaAcct hiện tại đang khớp tiền tệ
// CŨ (prefix "1121"/"1122", tự sinh hoặc gõ tay theo tiền tệ cũ) hoặc còn
// để trống. Mã đã gõ tay khác hẳn 2 tiền tệ (không khớp tiền tệ cũ) thì
// GIỮ NGUYÊN — coi là người dùng chủ động tuỳ chỉnh, không tự đổi.
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'doi_chieu_ngan_hang.html'), 'utf8');

function extractFn(name) {
  const marker = 'function ' + name + '(';
  const start = html.indexOf(marker);
  if (start < 0) throw new Error('Không tìm thấy hàm ' + name);
  let i = html.indexOf('{', start);
  let depth = 0, end = -1;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  if (end < 0) throw new Error('Không tìm được dấu } khớp cho hàm ' + name);
  return html.slice(start, end);
}

const srcAll = ['suggestMisaAcct', 'doiTienTeTaiKhoan'].map(extractFn).join('\n');
eval(srcAll);

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

// ----- Test 1 (đúng ca thật đã báo): TK "USD 24449247" đang có misaAcct
// "1121" (mã VND, sót lại từ trước) -> đổi currency VND -> nào? Thật ra
// trong ca thật thì currency HIỆN TẠI đã là USD (đổi rồi) nhưng misaAcct
// bị kẹt "1121" — mô phỏng ĐÚNG: TK đang currency="VND"/misaAcct="1121",
// bấm đổi sang "USD" -> misaAcct PHẢI đổi theo, không được giữ "1121". -----
{
  const accounts = [
    { id: 'acc1', label: 'USD', currency: 'VND', misaAcct: '1121', accountNo: '24449247' },
  ];
  const updated = doiTienTeTaiKhoan(accounts, 'acc1', 'USD');
  const acc = updated.find(a => a.id === 'acc1');
  assert(acc.currency === 'USD', `currency phải đổi thành 'USD' — got '${acc.currency}'`);
  assert(acc.misaAcct === '1122', (
    `misaAcct PHẢI đổi theo sang mã USD '1122' (KHÔNG được giữ nguyên '1121' của VND) — đúng lỗi thật `
    + `đã báo 'tài khoản ngoại tệ Mã hạch toán MISA bị sai' — got '${acc.misaAcct}'`));
  console.log("PASS 1: đổi currency VND->USD trên TK đang có misaAcct '1121' (mã VND) -> misaAcct tự đổi đúng sang '1122' (mã USD), không còn kẹt sai tiền tệ.");
}

// ----- Test 2: chiều ngược lại (USD -> VND) cũng phải đổi theo. -----
{
  const accounts = [
    { id: 'acc1', label: 'USD', currency: 'USD', misaAcct: '1122', accountNo: '24449247' },
  ];
  const updated = doiTienTeTaiKhoan(accounts, 'acc1', 'VND');
  const acc = updated.find(a => a.id === 'acc1');
  assert(acc.currency === 'VND' && acc.misaAcct === '1121', (
    `Đổi USD->VND phải ra currency='VND'/misaAcct='1121' — got currency='${acc.currency}', misaAcct='${acc.misaAcct}'`));
  console.log('PASS 2: đổi currency USD->VND cũng tự đổi misaAcct đúng chiều ngược lại (1122 -> 1121).');
}

// ----- Test 3: misaAcct đã được gõ tay THÀNH MÃ TUỲ CHỈNH khác hẳn 2 tiền
// tệ (không khớp cả '1121' lẫn '1122', vd 1 mã hạch toán nội bộ khác) ->
// GIỮ NGUYÊN khi đổi currency, không tự ý đổi (coi là chủ động tuỳ chỉnh). -----
{
  const accounts = [
    { id: 'acc1', label: 'TK đặc biệt', currency: 'VND', misaAcct: '1128-NOIBO', accountNo: '999' },
  ];
  const updated = doiTienTeTaiKhoan(accounts, 'acc1', 'USD');
  const acc = updated.find(a => a.id === 'acc1');
  assert(acc.currency === 'USD' && acc.misaAcct === '1128-NOIBO', (
    `Mã tuỳ chỉnh không khớp tiền tệ nào (KHÔNG bắt đầu bằng '1121'/'1122') PHẢI được GIỮ NGUYÊN khi đổi `
    + `currency — got currency='${acc.currency}', misaAcct='${acc.misaAcct}'`));
  console.log('PASS 3: misaAcct tuỳ chỉnh khác hẳn 2 tiền tệ được giữ nguyên khi đổi currency, không bị ghi đè.');
}

// ----- Test 4: misaAcct CHƯA từng gán (rỗng/undefined) -> đổi currency thì
// tự gán MỚI đúng theo tiền tệ mới (dùng suggestMisaAcct), không lỗi. -----
{
  const accounts = [
    { id: 'acc1', label: '24449247', currency: 'VND', accountNo: '' },
  ];
  const updated = doiTienTeTaiKhoan(accounts, 'acc1', 'USD');
  const acc = updated.find(a => a.id === 'acc1');
  assert(acc.currency === 'USD' && acc.misaAcct === '1122', (
    `misaAcct chưa từng gán -> đổi currency phải tự gán đúng mã USD '1122' — got currency='${acc.currency}', misaAcct='${acc.misaAcct}'`));
  console.log('PASS 4: misaAcct chưa từng gán (rỗng) -> đổi currency tự gán mới đúng theo tiền tệ mới.');
}

// ----- Test 5: các TK KHÁC (không phải TK đang đổi) không bị đụng tới. -----
{
  const accounts = [
    { id: 'acc1', label: 'VND chính', currency: 'VND', misaAcct: '1121', accountNo: '111' },
    { id: 'acc2', label: 'USD', currency: 'VND', misaAcct: '1121', accountNo: '222' },
  ];
  const updated = doiTienTeTaiKhoan(accounts, 'acc2', 'USD');
  const acc1 = updated.find(a => a.id === 'acc1');
  const acc2 = updated.find(a => a.id === 'acc2');
  assert(acc1.currency === 'VND' && acc1.misaAcct === '1121', `TK 'acc1' không được đụng tới — got ${JSON.stringify(acc1)}`);
  assert(acc2.currency === 'USD' && acc2.misaAcct === '1122', `TK 'acc2' phải đổi đúng — got ${JSON.stringify(acc2)}`);
  console.log("PASS 5: chỉ đổi đúng TK được chọn, các TK khác giữ nguyên vẹn.");
}

console.log('\nTẤT CẢ TEST PASS');
