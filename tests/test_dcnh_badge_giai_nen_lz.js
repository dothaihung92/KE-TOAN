// Regression test (Node) cho badge "còn dữ liệu chưa hoàn thành"/"▶ Tiếp tục" của thẻ
// "Đối Chiếu Ngân Hàng" ở màn Nhập Liệu (static/index.html: _dcnhKvGet/dcnhTrangThaiCty).
//
// Bug thật đã gặp: người dùng up bảng sao kê MỚI, hạch toán 1 giao dịch, bấm lưu (đã lưu tự
// động ngay, xem saveNow/setRowsH trong doi_chieu_ngan_hang.html) — nhưng quay lại màn Nhập
// Liệu, thẻ "Đối Chiếu Ngân Hàng" VẪN không hiện badge/"▶ Tiếp tục" dù dữ liệu đã lưu thật.
//
// Nguyên nhân: commit "nén dữ liệu lưu trữ" (b104c95) đổi LS.set trong doi_chieu_ngan_hang.html
// NÉN mọi giá trị bằng LZString trước khi ghi IndexedDB (tiền tố "~LZ~" + base64, xem LS_LZ_PREFIX)
// — nhưng cầu nối đọc trạng thái ở static/index.html (_dcnhKvGet/dcnhTrangThaiCty, thêm TRƯỚC đó ở
// commit 40c77c4) vẫn JSON.parse THẲNG giá trị đọc được, không hề giải nén. Với dữ liệu đã nén,
// JSON.parse ném lỗi (không phải JSON hợp lệ) -> bị nuốt bởi try/catch -> coi như "không có dữ liệu"
// -> badge KHÔNG BAO GIỜ hiện nữa cho MỌI công ty có dữ liệu lưu SAU khi tính năng nén ra đời (kể cả
// danh sách "companies" cũng bị nén nên dcnhTrangThaiCty còn không tìm ra công ty).
//
// Fix: thêm _dcnhGiaiNen() giải nén ĐÚNG Y HỆT cách LS.get bên doi_chieu_ngan_hang.html làm (kiểm
// tra tiền tố "~LZ~", gọi LZString.decompressFromBase64 rồi mới JSON.parse; dữ liệu CŨ không có
// tiền tố thì coi là JSON thuần, không giải nén) — dùng trong cả _dcnhKvGet lẫn vòng quét cursor
// trong dcnhTrangThaiCty.

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'index.html'), 'utf8');

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

function sliceBetween(startMarker, endMarkerAfterStart) {
  const s = html.indexOf(startMarker);
  if (s < 0) throw new Error('Không tìm thấy: ' + startMarker);
  const e = html.indexOf(endMarkerAfterStart, s);
  if (e < 0) throw new Error('Không tìm thấy điểm kết thúc: ' + endMarkerAfterStart);
  return html.slice(s, e);
}

// _DCNH_LZ_PREFIX + _dcnhGiaiNen() + _dcnhKvGet() khai báo liền nhau, gộp chung 1 khối.
const helpersSrc = sliceBetween('const _DCNH_LZ_PREFIX=', '// Xoá mọi key có tiền tố');
const dcnhTrangThaiCtySrc = extractBraceBlock('async function dcnhTrangThaiCty(mst){');

// _dcnhGiaiNen() dùng "window.LZString ? LZString.decompressFromBase64(...) : null" — đúng cách
// LS.get() bên doi_chieu_ngan_hang.html đã dùng (tương thích: trình duyệt thật gán LZString là
// biến toàn cục lẫn thuộc tính window, 2 cách viết trỏ về CÙNG 1 đối tượng) — factory phải nhận
// CẢ HAI (window.LZString và biến LZString trần) để mô phỏng đúng môi trường trình duyệt thật.
const factory = new Function(
  'window', 'LZString', 'IDBKeyRange', '_dcnhOpenDb',
  `${helpersSrc}
${dcnhTrangThaiCtySrc}
return { _dcnhGiaiNen, _dcnhKvGet, dcnhTrangThaiCty };`
);

// Stub LZString tối giản (chỉ cần round-trip đúng qua decompressFromBase64 — logic đọc ở
// index.html chỉ GỌI decompressFromBase64, không tự nén) — không cần cài thật thư viện LZString
// trong môi trường test, chỉ cần khớp đúng "hợp đồng" (tiền tố "~LZ~" + chuỗi base64 giải nén ra
// đúng JSON gốc), đúng cách doi_chieu_ngan_hang.html thật sự dùng thư viện đó.
const fakeLZString = {
  compressToBase64: s => Buffer.from(s, 'utf8').toString('base64'),
  decompressFromBase64: s => Buffer.from(s, 'base64').toString('utf8'),
};
function nen(obj) { return '~LZ~' + fakeLZString.compressToBase64(JSON.stringify(obj)); }

// Fake IndexedDB db — mô phỏng đúng chuỗi gọi thật: db.transaction(...).objectStore(...).get(key)
// / .openCursor(range), IDBKeyRange.bound(lo,hi) lọc theo khoảng khoá (đúng cách dcnhTrangThaiCty
// dùng để quét mọi key "session_<coId>*").
function makeFakeDb(store) {
  return {
    transaction() {
      return {
        objectStore() {
          return {
            get(key) {
              const req = {};
              setTimeout(() => { req.result = store[key]; if (req.onsuccess) req.onsuccess(); }, 0);
              return req;
            },
            openCursor(range) {
              const keys = Object.keys(store).filter(k => k >= range.lo && k < range.hi).sort();
              let idx = 0;
              const req = {};
              const fireNext = () => {
                setTimeout(() => {
                  if (idx < keys.length) {
                    const k = keys[idx++];
                    req.result = { value: store[k], continue: fireNext };
                  } else {
                    req.result = null;
                  }
                  if (req.onsuccess) req.onsuccess({ target: req });
                }, 0);
              };
              fireNext();
              return req;
            },
          };
        },
      };
    },
  };
}

const fakeIDBKeyRange = { bound: (lo, hi) => ({ lo, hi }) };

async function chay(store, mst) {
  const fakeWindow = { LZString: fakeLZString };
  const db = makeFakeDb(store);
  const { _dcnhGiaiNen, _dcnhKvGet, dcnhTrangThaiCty } =
    factory(fakeWindow, fakeLZString, fakeIDBKeyRange, () => Promise.resolve(db));
  return { _dcnhGiaiNen, _dcnhKvGet, dcnhTrangThaiCty, db };
}

(async () => {
  // ===== Test 1 (QUAN TRỌNG — đúng bug thật): "companies" + "session_..." lưu ở dạng ĐÃ NÉN
  // (~LZ~...), đúng như doi_chieu_ngan_hang.html thật sự ghi sau khi có tính năng nén — badge
  // PHẢI nhận ra hasData:true, không được coi nhầm là "không có dữ liệu". =====
  {
    const coId = 'co_abc123';
    const mst = '0318712827';
    const store = {
      'companies': nen([{ id: coId, mst, name: 'CTY TEST' }]),
      ['session_' + coId + '_acc1']: nen({ results: [{ id: 'r1', confirmed: 'yes' }] }),
    };
    const { dcnhTrangThaiCty } = await chay(store, mst);
    const st = await dcnhTrangThaiCty(mst);
    assert.ok(st, 'dcnhTrangThaiCty phải trả về kết quả (không phải null) khi công ty có dữ liệu đã nén.');
    assert.strictEqual(st.hasData, true,
      'Dữ liệu "companies"/"session_..." lưu dạng ĐÃ NÉN (~LZ~...) -> phải nhận ra hasData:true (giải nén đúng), ' +
      'không được coi nhầm là không có dữ liệu do JSON.parse thẳng chuỗi nén bị lỗi.');
  }
  console.log('PASS 1: dữ liệu đã nén (~LZ~...) -> dcnhTrangThaiCty nhận ra đúng hasData:true.');

  // ===== Test 2 (không hồi quy — QUAN TRỌNG): dữ liệu CŨ lưu từ TRƯỚC khi có tính năng nén
  // (JSON thuần, không có tiền tố "~LZ~") vẫn phải đọc được bình thường — không được để fix giải
  // nén làm hỏng khả năng đọc dữ liệu cũ đã có sẵn trên máy người dùng. =====
  {
    const coId = 'co_old1';
    const mst = '0107239009';
    const store = {
      'companies': JSON.stringify([{ id: coId, mst, name: 'CTY CU (JSON thuan)' }]),
      ['session_' + coId]: JSON.stringify({ results: [{ id: 'r1', confirmed: 'no' }] }),
    };
    const { dcnhTrangThaiCty } = await chay(store, mst);
    const st = await dcnhTrangThaiCty(mst);
    assert.ok(st, 'Dữ liệu JSON thuần (chưa nén, lưu từ bản cũ) vẫn phải đọc được, không được trả về null.');
    assert.strictEqual(st.hasData, true,
      'Dữ liệu JSON thuần (chưa nén) vẫn phải nhận ra đúng hasData:true — không hồi quy khả năng đọc dữ liệu cũ.');
  }
  console.log('PASS 2: dữ liệu JSON thuần cũ (chưa nén) vẫn đọc đúng — không hồi quy.');

  // ===== Test 3 (không hồi quy): công ty có trong "companies" (đã nén) nhưng CHƯA có session
  // nào (chưa từng dán sao kê) -> hasData:false, không hiện badge vô ích. =====
  {
    const coId = 'co_moi1';
    const mst = '0999999999';
    const store = { 'companies': nen([{ id: coId, mst, name: 'CTY CHUA CO DU LIEU' }]) };
    const { dcnhTrangThaiCty } = await chay(store, mst);
    const st = await dcnhTrangThaiCty(mst);
    assert.ok(st, 'Công ty có trong danh sách (dù chưa có session) vẫn phải tìm thấy (st != null).');
    assert.strictEqual(st.hasData, false, 'Chưa có session nào -> hasData phải là false, không hiện badge vô ích.');
  }
  console.log('PASS 3: công ty chưa có session nào -> hasData:false đúng, không hiện badge vô ích.');

  // ===== Test 4 (đơn vị — _dcnhGiaiNen trực tiếp): giá trị rác/hỏng không làm crash, trả về null. =====
  {
    const { _dcnhGiaiNen } = await chay({}, '');
    assert.strictEqual(_dcnhGiaiNen(null), null, 'null -> null.');
    assert.strictEqual(_dcnhGiaiNen(undefined), null, 'undefined -> null.');
    assert.strictEqual(_dcnhGiaiNen('~LZ~___khong_phai_base64_hop_le___'), null,
      'Chuỗi rác sau tiền tố "~LZ~" không được làm crash — phải trả về null (bị try/catch nuốt gọn).');
    assert.deepStrictEqual(_dcnhGiaiNen(JSON.stringify({ a: 1 })), { a: 1 },
      'JSON thuần (không tiền tố) phải parse đúng bình thường.');
  }
  console.log('PASS 4: _dcnhGiaiNen xử lý an toàn null/undefined/chuỗi rác, JSON thuần vẫn đúng.');

  console.log('\nALL DONE');
})().catch(e => { console.error(e); process.exitCode = 1; });
