// Regression test (Node) cho static/doi_chieu_ngan_hang.html (Kế Toán AI) — 2 yêu cầu tiếp theo
// sau tính năng "cột Tài khoản NH + nhảy về đúng giao dịch" (xem test_cot_tai_khoan_nh_va_nhay_ve_gd.js):
//
// 1) "kiểm tra lại khi chọn giao dịch phần mềm kéo về chưa đúng giao dịch cần" — nguyên nhân tìm
//    được: jumpToPayment() gọi setFilter("all") trước khi nhảy, mà effect reset showCount về
//    SHOW_STEP (150) mỗi khi đổi filter/tab; nếu dòng đích nằm NGOÀI 150 dòng đầu thì dòng đó chưa
//    kịp render ra DOM, hiệu ứng cuộn (dựa vào querySelectorAll("[data-row]")[focusIdx]) tìm không ra
//    phần tử nên KHÔNG cuộn đi đâu cả — nhìn như phần mềm "kéo về nhầm/không đúng giao dịch". Phải
//    bơm showCount đủ lớn TRƯỚC/CÙNG lúc set focusIdx.
// 2) "làm viền đỏ để biết giao dịch đó đang tìm kiếm" — thêm dấu hiệu RÕ RÀNG (viền đỏ + nhãn) cho
//    đúng dòng vừa nhảy tới, khác hẳn viền xanh của focus bàn phím thông thường, để người dùng tự
//    kiểm tra được đúng/sai.
// 3) (theo yêu cầu trước đó, "có hãy làm đi"): đánh dấu rõ các dòng tờ khai "placeholder" (tạo tay
//    bằng "+ Thêm tay", chưa có Số tờ khai nhưng đã gắn giao dịch ngân hàng — dùng để giữ chỗ cho
//    khoản đặt cọc trả trước khi có tờ khai hải quan chính thức).
const fs = require('fs');
const path = require('path');
const REPO_ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO_ROOT, 'static', 'doi_chieu_ngan_hang.html'), 'utf8');

function assert(cond, msg) {
  if (!cond) throw new Error('THẤT BẠI: ' + msg);
}

function braceBlockOf(marker, fromIdx) {
  const start = html.indexOf(marker, fromIdx || 0);
  assert(start >= 0, 'Không tìm thấy: ' + marker);
  let i = html.indexOf('{', start);
  let depth = 0, end = -1;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  assert(end >= 0, 'Không tìm được dấu } khớp cho: ' + marker);
  return { src: html.slice(start, end), start, end };
}

// ===== Phần 1 (QUAN TRỌNG — đúng ca thật "kéo về chưa đúng giao dịch"): effect xử lý
// pendingJumpRowId phải bơm showCount TRƯỚC/CÙNG setFocusIdx khi tìm thấy dòng đích. =====
const jumpEffect = braceBlockOf('React.useEffect(() => {\n    if (!pendingJumpRowId) return;');
const foundBranch = jumpEffect.src.slice(jumpEffect.src.indexOf('idx === -1'));
const afterNotFoundBlock = foundBranch.slice(foundBranch.indexOf('return () => clearTimeout(t);') + 1);
assert(/setShowCount\(c\s*=>\s*Math\.max\(c,\s*idx\s*\+\s*30\)\)/.test(afterNotFoundBlock),
  'Effect xử lý pendingJumpRowId phải gọi setShowCount(c => Math.max(c, idx + 30)) khi tìm thấy dòng ' +
  'đích — nếu không, dòng nằm ngoài 150 dòng đầu (showCount vừa bị reset do jumpToPayment gọi ' +
  'setFilter("all")) sẽ không có trong DOM, hiệu ứng cuộn không tìm thấy phần tử nên KHÔNG cuộn tới ' +
  'đâu cả, đúng lỗi người dùng báo "kéo về chưa đúng giao dịch".');
const idxShowCount = afterNotFoundBlock.search(/setShowCount\(/);
const idxFocusIdx = afterNotFoundBlock.search(/setFocusIdx\(idx\)/);
assert(idxShowCount >= 0 && idxFocusIdx >= 0 && idxShowCount < idxFocusIdx,
  'setShowCount(...) phải gọi TRƯỚC setFocusIdx(idx) (cùng 1 lượt state update) để dòng đích chắc ' +
  'chắn đã có trong DOM khi hiệu ứng cuộn chạy.');
console.log('PASS 1: effect nhảy về giao dịch có bơm showCount trước khi focus, tránh "cuộn hụt" cho dòng nằm ngoài trang đầu.');

// ===== Phần 2 (đúng ca thật): phải có jumpTargetRowId — đặt lại khi nhảy thành công, và tự tắt sau
// vài giây (không được ở lại vĩnh viễn, cũng không biến mất ngay lập tức). =====
assert(/const \[jumpTargetRowId, setJumpTargetRowId\] = useState\(null\)/.test(html),
  'Phải có state jumpTargetRowId để đánh dấu ĐÚNG DÒNG vừa nhảy tới.');
assert(/setJumpTargetRowId\(pendingJumpRowId\)/.test(afterNotFoundBlock),
  'Khi tìm thấy dòng đích, effect phải setJumpTargetRowId(pendingJumpRowId) để dòng đó được tô viền đỏ.');
const autoClearEffect = braceBlockOf('React.useEffect(() => {\n    if (!jumpTargetRowId) return;');
assert(/setTimeout\(\s*\(\s*\)\s*=>\s*setJumpTargetRowId\(cur\s*=>\s*\(cur\s*===\s*jumpTargetRowId\s*\?\s*null\s*:\s*cur\)\),\s*6000\)/
  .test(autoClearEffect.src),
  'jumpTargetRowId phải tự tắt sau 1 khoảng thời gian cố định (setTimeout ~6s) để không ở lại mãi mãi ' +
  'trên màn hình, nhưng đủ lâu để người dùng kịp nhìn thấy và kiểm tra.');
console.log('PASS 2: jumpTargetRowId được đặt đúng lúc nhảy thành công và tự tắt sau vài giây.');

// ===== Phần 3 (đúng ca thật "làm viền đỏ"): ConfirmRow phải nhận prop isJumpTarget và tô viền ĐỎ,
// khác với viền xanh của isFocused (điều hướng bàn phím thông thường) — không được lẫn 2 ý nghĩa. =====
const confirmRowSig = html.slice(html.indexOf('function ConfirmRow({'), html.indexOf('function ConfirmRow({') + 400);
assert(/\bisJumpTarget\b/.test(confirmRowSig), 'ConfirmRow phải nhận thêm prop isJumpTarget.');
const borderLineIdx = html.indexOf('border: isJumpTarget ? "3px solid #dc2626"');
assert(borderLineIdx >= 0,
  'Dòng vừa nhảy tới phải có viền ĐỎ (#dc2626), dày hơn viền focus bàn phím thông thường, để không bị ' +
  'nhầm là "chỉ đang chọn" như khi bấm chuột bình thường.');
const borderLine = html.slice(borderLineIdx, html.indexOf('\n', borderLineIdx));
assert(borderLine.indexOf('isJumpTarget') < borderLine.indexOf('isFocused'),
  'isJumpTarget phải được xét ƯU TIÊN TRƯỚC isFocused trong biểu thức viền (viền đỏ đè lên viền xanh ' +
  'khi cả 2 cùng đúng — VD vừa nhảy tới, dòng đó cũng đang là focus bàn phím).');
const badgeBlock = html.slice(borderLineIdx, borderLineIdx + 1200);
assert(/isJumpTarget\s*&&/.test(badgeBlock) && /Giao dịch vừa tìm/.test(badgeBlock),
  'Phải có nhãn/badge hiện rõ chữ khi isJumpTarget=true (VD "🔎 Giao dịch vừa tìm") — chỉ viền đỏ suông ' +
  'có thể không đủ rõ, cần cả chữ để chắc chắn người dùng biết đây là dòng phần mềm vừa tìm ra.');
console.log('PASS 3: ConfirmRow tô viền đỏ + nhãn rõ ràng cho đúng dòng vừa nhảy tới, ưu tiên hơn focus bàn phím.');

// ===== Phần 4 (không hồi quy — nơi gọi ConfirmRow phải truyền đúng prop): =====
const callSite = braceBlockOf('React.createElement(ConfirmRow, {');
assert(/isJumpTarget:\s*r\.id === jumpTargetRowId/.test(callSite.src),
  'Chỗ tạo từng ConfirmRow phải truyền isJumpTarget: r.id === jumpTargetRowId — thiếu dòng này thì ' +
  'state jumpTargetRowId có đặt đúng cũng không hiện viền đỏ ra được.');
console.log('PASS 4: nơi render danh sách giao dịch truyền đúng isJumpTarget cho từng dòng.');

// ===== Phần 5 (đúng ca thật, tính năng "đặt cọc chờ tờ khai"): bảng Tờ khai NK/XK phải đánh dấu rõ
// dòng placeholder (chưa có Số tờ khai nhưng đã gắn giao dịch ngân hàng). =====
const tbodyBlock = braceBlockOf('React.createElement("tbody", null, filtered.map(tk => {');
assert(/!tk\.toKhaiSo\s*&&\s*payments\.length\s*>\s*0/.test(tbodyBlock.src),
  'Phải có điều kiện đúng "chưa có Số tờ khai nhưng đã gắn giao dịch ngân hàng" (!tk.toKhaiSo && ' +
  'payments.length > 0) để nhận diện dòng placeholder đặt cọc.');
assert(/Đặt cọc — chờ tờ khai/.test(tbodyBlock.src),
  'Phải hiện nhãn rõ ràng kiểu "Đặt cọc — chờ tờ khai" cho dòng placeholder, để không quên bổ sung ' +
  'Số/Ngày tờ khai thật sau này (nếu không, dòng chưa hoàn tất dễ bị bỏ quên lẫn trong danh sách).');
console.log('PASS 5: dòng tờ khai placeholder (đặt cọc trước khi có tờ khai) được đánh dấu rõ trong bảng.');

// ===== Phần 6 (QUAN TRỌNG — ĐÚNG CA THẬT người dùng báo TIẾP: "vẫn chưa hiện đúng giao dịch trên
// màn hình" dù ô "Dòng X/Y" đã nhảy đúng vị trí): cuộn tới dòng đích phải dò TRỰC TIẾP theo
// data-row-id, KHÔNG được dựa vào querySelectorAll(...)[focusIdx] theo index — cách cũ dễ lệch nhịp
// khi đổi filter/tab ngay trước đó làm danh sách render lại đúng lúc effect chạy (key="list_"+filter
// đổi -> remount), khiến index tính sai thời điểm dù focusIdx/jumpTargetRowId đã đúng ID. =====
assert(/"data-row-id":\s*String\(r\.id\)/.test(html),
  'Mỗi dòng giao dịch phải có data-row-id = r.id để dò/cuộn tới ĐÚNG dòng bằng ID thay vì suy theo ' +
  'vị trí (index) dễ lệch nhịp khi danh sách vừa render lại do đổi filter/tab.');
const scrollByIdEffect = braceBlockOf('React.useEffect(() => {\n    if (!jumpTargetRowId) return;\n    let cancelled = false;');
assert(/data-row-id="\s*'\s*\+\s*String\(jumpTargetRowId\)/.test(scrollByIdEffect.src) ||
       /'\[data-row-id="'\s*\+\s*String\(jumpTargetRowId\)/.test(scrollByIdEffect.src),
  'Phải dò phần tử DOM của dòng đích bằng querySelector([data-row-id="<jumpTargetRowId>"]) — cuộn theo ' +
  'ID chắc chắn đúng dòng, không phụ thuộc thứ tự DOM tại đúng thời điểm effect chạy.');
assert(/scrollIntoView\(/.test(scrollByIdEffect.src),
  'Phải gọi scrollIntoView() lên đúng phần tử tìm được theo data-row-id.');
assert(/setTimeout\(tryScroll,\s*100\)/.test(scrollByIdEffect.src) && /attempts\s*<\s*20/.test(scrollByIdEffect.src),
  'Phải thử lại nhiều lần (vòng lặp hẹn giờ, tối đa ~2s) trước khi bỏ cuộc — dòng đích có thể chưa kịp ' +
  'vẽ ra DOM ngay lượt render đầu tiên (showCount/rows vừa cập nhật xong).');
console.log('PASS 6: cuộn tới dòng đích dò trực tiếp theo data-row-id (có thử lại), không còn lệ thuộc index dễ lệch nhịp.');

console.log('\nALL DONE');
