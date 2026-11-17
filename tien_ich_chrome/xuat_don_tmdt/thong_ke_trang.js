// Chạy trong CHÍNH trang gtsphcm.cosis.vn (world MAIN): khi phần mềm đang tự điền (thuộc tính data-ketoan-tk=1) thì
// confirm() tự trả lời "OK" và alert() không chặn trang — nội dung được ghi lại để hiện trong nhật ký; ngoài lúc tự điền, hộp thoại hoạt động bình thường.
(function () {
  if (window.__ketoanTkTrang) return; window.__ketoanTkTrang = true;
  const A = window.alert, C = window.confirm, R = document.documentElement;
  const dang = () => R.getAttribute('data-ketoan-tk') === '1';
  const ghi = (k, m) => { try { const c = R.getAttribute('data-ketoan-tk-hop') || ''; R.setAttribute('data-ketoan-tk-hop', (c ? c + '\n' : '') + k + ': ' + String(m || '').replace(/\s+/g, ' ').slice(0, 300)) } catch (_) { } };
  window.alert = function (m) { if (dang()) { ghi('Lỗi/báo', m); return } return A.apply(this, arguments) };
  window.confirm = function (m) { if (dang()) { ghi('Xác nhận (đã chọn OK)', m); return true } return C.apply(this, arguments) };
})();
