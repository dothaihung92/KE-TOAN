// Regression test (Node) cho computeBankPayment() trong static/doi_chieu_ngan_hang.html (Kế Toán AI),
// theo báo cáo thật của người dùng kèm ảnh chụp màn hình: gắn 1 GD ngân hàng từ TK USD (362698698,
// "SWF5852787-050126-PHI NN:USD8.-B/O:...GUAVA (AUST.) PTY LTD-UNIEXIM JAP47 REMAINING BALANCE",
// Tiền vào $9,172.54) vào tờ khai XK JAP047 (USD) — kết quả "Trị giá TT (NT)" hiện SAI thành 8 (dò
// nhầm "USD8." — thật ra là phí ngân hàng ghi kèm trong diễn giải, không phải số tiền thanh toán),
// và "Đồng Việt Nam TT" hiện THẲNG số 9,172.54 (dùng nhầm số USD làm số VND, không hề quy đổi qua tỷ
// giá) — khiến "Chênh lệch" tính ra sai lệch hơn 240 triệu đồng (so 1 số VND thật với 1 số bị nhầm là
// USD).
//
// Nguyên nhân: attachTokhai() giả định GD ngân hàng đang gắn LUÔN ở TK VND (bankVND = thẳng số tiền
// GD, còn số ngoại tệ phải dò trong text diễn giải bằng extractForeignAmt) — đúng khi gắn từ 1 TK
// VND thật, nhưng SAI khi gắn từ chính TK NGOẠI TỆ (VD TK USD) cùng loại tiền với tờ khai: lúc đó số
// tiền GD CHÍNH LÀ số ngoại tệ (không cần dò text — dò còn dễ bắt nhầm số phí nhỏ ghi kèm), và số VND
// phải được QUY ĐỔI qua tỷ giá thật (row.tyGia, tỷ giá VCB người dùng đã tự nhập ở màn hình chính).
//
// Fix: thêm computeBankPayment(row, tk) phân biệt 2 trường hợp theo row.tx.currency, dùng row.tyGia
// để quy đổi đúng ra VND khi GD đang ở TK ngoại tệ cùng loại tờ khai.
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'doi_chieu_ngan_hang.html'), 'utf8');

function extractBraceBlock(marker) {
  const start = html.indexOf(marker);
  if (start < 0) throw new Error('Không tìm thấy: ' + marker);
  let i = html.indexOf('{', start);
  let depth = 0, end = -1;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  if (end < 0) throw new Error('Không tìm được dấu } khớp cho: ' + marker);
  return html.slice(start, end);
}

const parseNumSrc = extractBraceBlock('function parseNum(s, usd) {');
const tkTaxVNDSrc = extractBraceBlock('function tkTaxVND(tk) {');
const tkPaymentsSrc = extractBraceBlock('function tkPayments(tk) {');
const tkTotalPaidVNDSrc = extractBraceBlock('function tkTotalPaidVND(tk) {');
const extractForeignAmtSrc = extractBraceBlock('function extractForeignAmt(desc, currency) {');
const rowAmountVNDSrc = extractBraceBlock('function rowAmountVND(row) {');
const computeBankPaymentSrc = extractBraceBlock('function computeBankPayment(row, tk) {');

const factory = new Function(`
${parseNumSrc}
${tkTaxVNDSrc}
${tkPaymentsSrc}
${tkTotalPaidVNDSrc}
${extractForeignAmtSrc}
${rowAmountVNDSrc}
${computeBankPaymentSrc}
return computeBankPayment;
`);
const computeBankPayment = factory();

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); }
}

// ----- Test 1 (đúng ca thật đã báo): GD ngân hàng ở TK USD (currency="USD"), có tỷ giá VCB đã nhập
// (row.tyGia), gắn vào tờ khai XK cũng USD — PHẢI lấy thẳng số tiền GD làm bankAmt (KHÔNG dò "USD8."
// trong diễn giải), và PHẢI quy đổi bankVND qua đúng row.tyGia (KHÔNG dùng thẳng số USD làm VND). -----
{
  const row = {
    tx: {
      debit: 0, credit: 9172.54, currency: 'USD', date: '05/01/2026',
      desc: 'SWF5852787-050126-PHI NN:USD8.-B/O:2121120005763433 GUAVA (AUST.) PTY LTD-UNIEXIM JAP47 REMAINING BALANCE',
    },
    tyGia: 26391, // tỷ giá VCB người dùng đã tự nhập trên dòng NH ở màn hình chính
  };
  const tk = { currency: 'USD', triGiaHoaDon: 9180.54, tyGiaTinhThue: 26169, payments: [] };

  const { bankAmt, bankRate, bankVND, missingRate } = computeBankPayment(row, tk);

  assert(bankAmt === 9172.54, `bankAmt PHẢI lấy thẳng số tiền GD $9,172.54 (KHÔNG dò nhầm "USD8." trong diễn giải) — got ${bankAmt}`);
  assert(bankRate === 26391, `bankRate PHẢI đúng bằng tỷ giá VCB đã nhập trên dòng NH (row.tyGia) — got ${bankRate}`);
  assert(bankVND === Math.round(9172.54 * 26391), `bankVND PHẢI quy đổi ĐÚNG qua tỷ giá 26391 (KHÔNG dùng thẳng 9172.54 làm số VND như lỗi cũ) — got ${bankVND}, expected ${Math.round(9172.54 * 26391)}`);
  assert(!missingRate, 'missingRate phải là false vì row.tyGia đã có sẵn');

  // Chênh lệch đúng phải nhỏ (vài trăm nghìn do lệch tỷ giá thuế/tỷ giá thanh toán), KHÔNG được ra
  // hàng trăm triệu như lỗi cũ (240.236.378đ).
  const taxVND = Math.round(tk.triGiaHoaDon * tk.tyGiaTinhThue);
  const chenhLech = bankVND - taxVND;
  assert(Math.abs(chenhLech) < 10000000, `Chênh lệch sau khi sửa PHẢI ở mức hợp lý (vài trăm nghìn, KHÔNG hàng trăm triệu như lỗi cũ) — got ${chenhLech}`);
  console.log('PASS 1: gắn GD từ TK USD vào tờ khai USD — bankAmt lấy đúng số tiền GD, bankVND quy đổi đúng qua tỷ giá VCB đã nhập, chênh lệch về mức hợp lý (không còn sai lệch hàng trăm triệu).');
}

// ----- Test 2: GD ngân hàng ở TK USD nhưng CHƯA có tỷ giá (row.tyGia rỗng/0) — báo missingRate=true
// để phần mềm cảnh báo người dùng, thay vì âm thầm tính sai như trước. -----
{
  const row = { tx: { debit: 0, credit: 9172.54, currency: 'USD', date: '05/01/2026', desc: 'BAN 9172.54 USD' }, tyGia: 0 };
  const tk = { currency: 'USD', triGiaHoaDon: 9180.54, tyGiaTinhThue: 26169, payments: [] };
  const { bankAmt, missingRate } = computeBankPayment(row, tk);
  assert(bankAmt === 9172.54, `bankAmt vẫn phải lấy đúng số tiền GD dù chưa có tỷ giá — got ${bankAmt}`);
  assert(missingRate === true, 'missingRate PHẢI là true khi row.tyGia chưa được nhập, để phần mềm cảnh báo người dùng');
  console.log('PASS 2: GD USD chưa có tỷ giá VCB → missingRate=true (để cảnh báo), không âm thầm tính sai.');
}

// ----- Test 3 (không hồi quy): GD ngân hàng ở TK VND như trước giờ (hành vi CŨ, đúng thiết kế ban
// đầu) — vẫn phải dò số ngoại tệ trong diễn giải như cũ, không bị ảnh hưởng bởi fix. -----
{
  const row = { tx: { debit: 0, credit: 195000000, currency: 'VND', date: '10/03/2026', desc: 'TT HD JAP030 SO TIEN USD 7477.50 CHO GUAVA' } };
  const tk = { currency: 'USD', triGiaHoaDon: 7477.50, tyGiaTinhThue: 26100, payments: [] };
  const { bankAmt, bankVND, bankRate, missingRate } = computeBankPayment(row, tk);
  assert(bankVND === 195000000, `GD TK VND: bankVND vẫn phải lấy thẳng số tiền GD như cũ — got ${bankVND}`);
  assert(bankAmt === 7477.5, `GD TK VND: bankAmt vẫn phải dò đúng số ngoại tệ trong diễn giải như cũ — got ${bankAmt}`);
  assert(bankRate === Math.round(195000000 / 7477.5), `GD TK VND: bankRate vẫn tính như cũ (bankVND/bankAmt) — got ${bankRate}`);
  assert(!missingRate, 'GD TK VND không cần row.tyGia nên missingRate luôn false');
  console.log('PASS 3: GD từ TK VND (hành vi cũ) không bị ảnh hưởng bởi fix — vẫn dò số ngoại tệ trong diễn giải như trước.');
}

console.log(process.exitCode ? 'CÓ TEST FAIL' : 'TẤT CẢ TEST PASS');
