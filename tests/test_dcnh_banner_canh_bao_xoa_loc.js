// Regression test (Node) cho xemBannerCanhBao() trong static/doi_chieu_ngan_hang.html (Kế
// Toán AI, màn "Xác nhận kết quả") — người dùng báo (kèm ảnh chụp màn hình): banner đỏ "1 giao
// dịch hạch toán có thể ngược chiều dòng tiền" báo có 1 giao dịch, nhấn vào để lọc thì ra
// "Không có giao dịch nào" — "kiểm tra lại nhấn vào không có giao dịch nào ... nhưng phần mềm
// vẫn báo".
//
// Nguyên nhân: 3 banner cảnh báo (mismatchCount/missingMstCount/wrongHachCount) đều tính trên
// TOÀN BỘ rows, KHÔNG áp ô tìm kiếm (search)/lọc theo mã hạch toán (hachFilter)/khoảng ngày
// (dateFrom/dateTo)/lọc từ modal (locTuModal) đang chọn. Trước fix, bấm vào banner CHỈ đổi
// filter (setFilter("wronghach"/...)) mà KHÔNG xoá các bộ lọc khác — nếu người dùng đang còn ô
// tìm kiếm/lọc từ việc khác (VD gõ tên 1 công ty khác để tra cứu rồi quên xoá — đúng ca thật
// trong ảnh chụp: ô tìm kiếm còn "THUONG MAI HOA HONG PHAT"), giao dịch banner báo có bị chính
// các bộ lọc đó che mất -> "Không có giao dịch nào" dù banner vẫn đúng là có 1 giao dịch.
//
// Cùng nguyên nhân/cách xử lý đã áp dụng cho jumpToPayment() trong CHÍNH file này (comment gốc:
// "Bỏ mọi bộ lọc đang áp — nếu không, giao dịch cần tới có thể đang bị lọc ẩn đi").
//
// Fix: bấm vào 1 trong 3 banner (mismatch/missingmst/wronghach) để BẬT lọc thì xoá sạch
// search/hachFilter/locTuModal/dateFrom/dateTo trước — đảm bảo giao dịch banner báo có LUÔN
// hiện ra được, không bị bộ lọc nào khác che khuất.

const fs = require('fs');
const path = require('path');
const assert = require('assert');
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

// ===== Test 1..2 (QUAN TRỌNG — đúng bug thật): bật lọc (filter khác target) PHẢI xoá sạch
// search/hachFilter/locTuModal/dateFrom/dateTo, không được để bộ lọc nào khác còn sót lại che
// mất giao dịch banner báo có. =====
{
  const xemBannerCanhBaoSrc = extractBraceBlock('const xemBannerCanhBao = target => {');
  const factory = new Function(
    'filter', 'setFilter', 'setSearch', 'setHachFilter', 'setLocTuModal', 'setDateFrom', 'setDateTo',
    'setFocusIdx', 'clearBulkSelection',
    `${xemBannerCanhBaoSrc}
return xemBannerCanhBao;`
  );

  function goi(filterHienTai, target) {
    const calls = { setFilter: [], setSearch: [], setHachFilter: [], setLocTuModal: [], setDateFrom: [], setDateTo: [], setFocusIdx: [], clearBulkSelection: 0 };
    const xemBannerCanhBao = factory(
      filterHienTai,
      v => calls.setFilter.push(v),
      v => calls.setSearch.push(v),
      v => calls.setHachFilter.push(v),
      v => calls.setLocTuModal.push(v),
      v => calls.setDateFrom.push(v),
      v => calls.setDateTo.push(v),
      v => calls.setFocusIdx.push(v),
      () => { calls.clearBulkSelection++; }
    );
    xemBannerCanhBao(target);
    return calls;
  }

  // Ca thật đã gặp: đang ở filter "all", còn sót search="THUONG MAI HOA HONG PHAT" (VD tra cứu việc
  // khác trước đó, quên xoá) — bấm banner "wronghach" (filter khác target) phải BẬT lọc + xoá sạch
  // mọi bộ lọc khác có thể che giao dịch.
  const c1 = goi("all", "wronghach");
  assert.deepStrictEqual(c1.setFilter, ["wronghach"], 'Phải bật đúng filter="wronghach".');
  assert.deepStrictEqual(c1.setSearch, [""], 'Phải xoá sạch ô tìm kiếm (search) — nếu không, giao dịch banner báo có thể bị search cũ che mất (đúng ca thật đã gặp).');
  assert.deepStrictEqual(c1.setHachFilter, [""], 'Phải xoá bộ lọc theo mã hạch toán (hachFilter) — có thể đang lọc riêng 1 mã khác che mất giao dịch cần xem.');
  assert.deepStrictEqual(c1.setLocTuModal, [null], 'Phải xoá bộ lọc từ modal khác (locTuModal).');
  assert.deepStrictEqual(c1.setDateFrom, [""], 'Phải xoá khoảng ngày Từ — banner tính trên toàn bộ rows, không giới hạn ngày.');
  assert.deepStrictEqual(c1.setDateTo, [""], 'Phải xoá khoảng ngày Đến — banner tính trên toàn bộ rows, không giới hạn ngày.');
  assert.strictEqual(c1.clearBulkSelection, 1, 'Phải xoá lựa chọn hàng loạt đang chọn dở (giữ hành vi cũ).');

  // Tương tự cho 2 banner còn lại (mismatch/missingmst) — cùng 1 hàm dùng chung, đảm bảo áp dụng
  // đồng nhất cho cả 3, không chỉ riêng "wronghach".
  const c2 = goi("all", "mismatch");
  assert.deepStrictEqual(c2.setFilter, ["mismatch"]);
  assert.deepStrictEqual(c2.setSearch, [""]);
  const c3 = goi("wronghach", "missingmst");
  assert.deepStrictEqual(c3.setFilter, ["missingmst"]);
  assert.deepStrictEqual(c3.setSearch, [""]);
}
console.log('PASS 1: bật lọc banner cảnh báo (mismatch/missingmst/wronghach) xoá sạch search/hachFilter/locTuModal/dateFrom/dateTo, đảm bảo giao dịch banner báo có luôn hiện ra được.');

// ===== Test 2 (không hồi quy — QUAN TRỌNG): bấm LẠI đúng banner đang bật (filter === target,
// tức đang lọc rồi bấm để BỎ lọc) -> chỉ cần setFilter("all") + focus/bulk, KHÔNG được xoá
// search/hachFilter/locTuModal/dateFrom/dateTo — người dùng có thể đang cố tình giữ các bộ lọc
// khác đó, tắt banner đi không nên xoá mất chúng ngoài ý muốn. =====
{
  const xemBannerCanhBaoSrc = extractBraceBlock('const xemBannerCanhBao = target => {');
  const factory = new Function(
    'filter', 'setFilter', 'setSearch', 'setHachFilter', 'setLocTuModal', 'setDateFrom', 'setDateTo',
    'setFocusIdx', 'clearBulkSelection',
    `${xemBannerCanhBaoSrc}
return xemBannerCanhBao;`
  );
  const calls = { setFilter: [], setSearch: [], setHachFilter: [], setLocTuModal: [], setDateFrom: [], setDateTo: [] };
  const xemBannerCanhBao = factory(
    "wronghach",
    v => calls.setFilter.push(v),
    v => calls.setSearch.push(v),
    v => calls.setHachFilter.push(v),
    v => calls.setLocTuModal.push(v),
    v => calls.setDateFrom.push(v),
    v => calls.setDateTo.push(v),
    () => {},
    () => {}
  );
  xemBannerCanhBao("wronghach"); // bấm lại đúng banner đang bật -> tắt đi
  assert.deepStrictEqual(calls.setFilter, ["all"], 'Bấm lại đúng banner đang bật -> phải tắt về filter="all".');
  assert.strictEqual(calls.setSearch.length, 0, 'Tắt banner (đang bật -> bỏ) KHÔNG được đụng tới ô tìm kiếm (search) của người dùng.');
  assert.strictEqual(calls.setHachFilter.length, 0, 'Tắt banner KHÔNG được đụng tới hachFilter của người dùng.');
  assert.strictEqual(calls.setLocTuModal.length, 0, 'Tắt banner KHÔNG được đụng tới locTuModal của người dùng.');
  assert.strictEqual(calls.setDateFrom.length, 0, 'Tắt banner KHÔNG được đụng tới dateFrom của người dùng.');
  assert.strictEqual(calls.setDateTo.length, 0, 'Tắt banner KHÔNG được đụng tới dateTo của người dùng.');
}
console.log('PASS 2: bấm lại banner đang bật để tắt đi -> chỉ tắt filter, không xoá nhầm các bộ lọc khác của người dùng.');

// ===== Test 3 (nguồn — QUAN TRỌNG): cả 3 banner (mismatch/missingmst/wronghach) phải THỰC SỰ
// gọi xemBannerCanhBao(...) trong onClick, không còn dùng lại kiểu setFilter(...) trực tiếp cũ
// (không xoá các bộ lọc khác) — tránh sửa nhầm 1 trong 3 chỗ mà quên chỗ còn lại. =====
{
  assert.ok(html.includes('onClick: () => xemBannerCanhBao("mismatch")'),
    'Banner "mismatch" phải gọi xemBannerCanhBao("mismatch") trong onClick.');
  assert.ok(html.includes('onClick: () => xemBannerCanhBao("missingmst")'),
    'Banner "missingmst" phải gọi xemBannerCanhBao("missingmst") trong onClick.');
  assert.ok(html.includes('onClick: () => xemBannerCanhBao("wronghach")'),
    'Banner "wronghach" phải gọi xemBannerCanhBao("wronghach") trong onClick.');
  assert.ok(!html.includes('setFilter(filter === "wronghach" ? "all" : "wronghach")'),
    'Kiểu gọi setFilter trực tiếp CŨ (không xoá search/hachFilter/...) cho banner "wronghach" phải không còn.');
  assert.ok(!html.includes('setFilter(filter === "mismatch" ? "all" : "mismatch")'),
    'Kiểu gọi setFilter trực tiếp CŨ cho banner "mismatch" phải không còn.');
  assert.ok(!html.includes('setFilter(filter === "missingmst" ? "all" : "missingmst")'),
    'Kiểu gọi setFilter trực tiếp CŨ cho banner "missingmst" phải không còn.');
}
console.log('PASS 3: cả 3 banner cảnh báo đều dùng chung xemBannerCanhBao(), không còn sót kiểu gọi setFilter trực tiếp cũ.');

console.log('\nALL DONE');
