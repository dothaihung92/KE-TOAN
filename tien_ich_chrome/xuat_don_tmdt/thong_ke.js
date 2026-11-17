// Kế toán — BÁO CÁO THỐNG KÊ (Phiếu 01/DN-ĐP, gtsphcm.cosis.vn). Phần mềm kế toán mở trang kèm #ketoan-thongke&kt=<mã dùng 1 lần>&p=<cổng>.
// Tiện ích đổi mã lấy tài khoản CỦA CÔNG TY + số liệu phiếu, rồi: (1) trang đăng nhập -> điền tài khoản/mật khẩu (có ô mã xác nhận thì để người dùng gõ);
// (2) trang phiếu -> điền các ô nhập đơn giản (số lao động, số ngày hoạt động, tình hình, người ghi phiếu, chức vụ, điện thoại) — ô vừa điền tô vàng;
// bảng sản phẩm (mục 6) và doanh thu theo ngành (mục 7) chỉ HIỂN THỊ số liệu trong khung để bạn nhập (cần chọn mã sản phẩm/ngành trên trang).
// KHÔNG bấm Lưu tạm / Hoàn tất phiếu — bạn tự kiểm tra rồi bấm.
(() => {
  if (window.__ketoanThongKe) return; window.__ketoanThongKe = 1;
  const hoiNen = m => new Promise(r => { const h = setTimeout(() => r({ loi: 'phần nền không trả lời' }), 12000); try { chrome.runtime.sendMessage(m, x => { void chrome.runtime.lastError; clearTimeout(h); r(x || {}) }) } catch (e) { clearTimeout(h); r({ loi: String(e && e.message || e) }) } });
  const ngu = ms => new Promise(r => setTimeout(r, ms));
  const bo = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').replace(/\s+/g, ' ').trim().toLowerCase();
  const hien = e => { if (!e || !e.isConnected) return false; const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' };
  const gan = (e, v) => {
    const set = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(e), 'value');
    e.focus(); (set && set.set ? set.set.call(e, v) : (e.value = v));
    for (const t of ['input', 'change', 'blur']) e.dispatchEvent(new Event(t, { bubbles: true }));
  };
  const vang = e => { try { e.style.background = '#fff3b0'; e.title = 'Phần mềm kế toán vừa điền — hãy kiểm tra' } catch (_) { } };
  const kho = (() => { try { return chrome.storage.local } catch (e) { return null } })();

  const layDuLieu = async () => {      // payload: từ mã trong địa chỉ (lần đầu) hoặc bộ nhớ phiên (sau khi đăng nhập trang đổi địa chỉ)
    const m = /ketoan-thongke&kt=([\w-]+)(?:&p=(\d+))?/.exec(location.hash || '');
    if (m) {
      const r = await hoiNen({ loai: 'tk-lay', kt: m[1], p: m[2] });
      try { history.replaceState(null, '', location.href.replace(/#.*$/, '')) } catch (e) { }
      return r && r.user ? r : { loi: (r && r.loi) || 'không lấy được dữ liệu' };
    }
    const r = await hoiNen({ loai: 'tk-cho' });
    return r && r.user ? r : null;
  };

  const khung = (txt, mau) => {
    let k = document.getElementById('__ketoanTk');
    if (!k) {
      k = document.createElement('div'); k.id = '__ketoanTk';
      k.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:2147483647;width:340px;max-height:60vh;overflow:auto;background:#fff;border:2px solid #1a7a4a;border-radius:10px;box-shadow:0 4px 18px rgba(0,0,0,.25);font:13px/1.45 Segoe UI,Arial,sans-serif;color:#1a1a1a;padding:10px 12px';
      document.documentElement.appendChild(k);
    }
    k.innerHTML = '<div style="font-weight:600;color:#1a7a4a;margin-bottom:4px">Kế toán — báo cáo thống kê</div><div style="color:' + (mau || '#333') + '">' + txt + '</div>';
  };
  const esc = s => String(s == null ? '' : s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const bangSoLieu = d => {
    const sl = d.so_lieu || {}; const f = x => Number(x).toLocaleString('vi-VN', { maximumFractionDigits: 3 });
    let h = '<div style="margin-top:6px"><b>Số liệu từ hoá đơn bán ra tháng ' + esc(sl.thang_so_lieu) + '/' + esc(sl.nam_so_lieu) + '</b> (' + esc(sl.so_hd) + ' hoá đơn):<br>Doanh thu thuần: <b>' + f(sl.doanh_thu_trieu || 0) + ' triệu đồng</b> (mục 7 — chọn mã ngành cấp 2 rồi nhập)';
    if ((sl.sp || []).length) h += '<table style="border-collapse:collapse;font-size:12px;margin-top:4px;width:100%"><tr style="background:#f3f3f3"><td>Sản phẩm (mục 6)</td><td>ĐVT</td><td>SL</td><td>Giá trị (triệu)</td></tr>' +
      sl.sp.slice(0, 40).map(x => '<tr><td style="border-top:1px solid #eee">' + esc(x.ten) + '</td><td>' + esc(x.dvt) + '</td><td align=right>' + f(x.sl) + '</td><td align=right>' + f(x.gia_tri_trieu) + '</td></tr>').join('') + '</table>';
    if (sl.thieu_chi_tiet) h += '<div style="color:#8a5c0a;margin-top:4px">⚠ ' + esc(sl.thieu_chi_tiet) + ' hoá đơn chưa có chi tiết dòng hàng — bảng sản phẩm có thể thiếu.</div>';
    return h + '</div>';
  };

  // ---------- đăng nhập ----------
  const oMk = () => [...document.querySelectorAll('input[type=password]')].find(hien);
  const dangNhap = async d => {
    const mk = oMk(); if (!mk) return false;
    const o = [...document.querySelectorAll('input')].filter(e => hien(e) && !e.disabled && e !== mk && /^(text|email|tel|number|)$/i.test(e.getAttribute('type') || '') && (e.compareDocumentPosition(mk) & Node.DOCUMENT_POSITION_FOLLOWING));
    const nhan = e => bo([e.placeholder, e.name, e.id, e.getAttribute('aria-label')].join(' '));
    const u = o.find(e => /user|ten dang nhap|tai khoan|account|login|mst|ma so thue/.test(nhan(e))) || o[0];
    if (!u) { khung('Không thấy ô tên đăng nhập — hãy tự đăng nhập (tài khoản: ' + esc(d.user) + ').', '#b00020'); return true }
    gan(u, d.user); await ngu(200); gan(mk, d.pass);
    const cap = [...document.querySelectorAll('input')].find(e => hien(e) && !e.disabled && e !== u && e !== mk && e.type !== 'hidden' && /captcha|ma xac|xac nhan|verify/.test(nhan(e)));
    if (cap) { try { cap.focus() } catch (e) { } khung('Đã điền tài khoản <b>' + esc(d.user) + '</b> + mật khẩu. Hãy gõ MÃ XÁC NHẬN rồi bấm Đăng nhập — phiếu sẽ được điền sau khi đăng nhập.', '#8a5c0a'); return true }
    const b = [...document.querySelectorAll('button,input[type=submit],input[type=button],a')].filter(hien).find(e => /^(dang nhap|login|dang nhap he thong)$/.test(bo(e.innerText || e.value || '')));
    khung('Đã điền tài khoản <b>' + esc(d.user) + '</b>' + (b ? ' và bấm Đăng nhập…' : '. Hãy bấm Đăng nhập.'));
    if (b) b.click(); else if (mk.form) { try { mk.form.requestSubmit ? mk.form.requestSubmit() : mk.form.submit() } catch (e) { } }
    return true;
  };

  // ---------- điền phiếu ----------
  const hang = e => e.closest('tr') || e.closest('.row') || e.parentElement;
  const timO = (re, loai) => {      // ô nhập đầu tiên nằm cùng hàng/khối với nhãn khớp re
    const cac = [...document.querySelectorAll('td,th,div,span,label,b,p')].filter(e => hien(e) && e.children.length <= 3 && re.test(bo(e.innerText || '')) && bo(e.innerText || '').length < 160);
    for (const n of cac.sort((a, b) => (a.innerText || '').length - (b.innerText || '').length)) {
      let p = n;
      for (let i = 0; i < 4 && p; i++, p = p.parentElement) {
        const os = [...p.querySelectorAll(loai || 'input:not([type=hidden]):not([type=button]):not([type=submit]):not([type=checkbox]):not([type=radio])')].filter(e => hien(e) && !e.disabled && !e.readOnly);
        const sau = os.filter(e => n.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_FOLLOWING);
        if (sau.length) return sau[0];
      }
    }
    return null;
  };
  const dienPhieu = async d => {
    const p = d.phieu || {}; const da = [], khong = [];
    const them = (ten, re, v, loai) => {
      v = String(v == null ? '' : v).trim(); if (!v) return;
      const o = timO(re, loai); if (!o) { khong.push(ten); return }
      gan(o, v); vang(o); da.push(ten);
    };
    them('Số lao động cuối tháng trước', /thoi diem cuoi thang truoc/, p.lao_dong_cuoi_thang_truoc);
    them('Số lao động dự kiến cuối tháng báo cáo', /du kien thoi diem cuoi thang bao cao/, p.lao_dong_du_kien);
    them('Số ngày hoạt động', /so ngay hoat dong trong thang/, p.so_ngay_hoat_dong);
    them('Tình hình sản xuất', /tinh hinh san xuat trong thang/, p.tinh_hinh, 'textarea');
    them('Người ghi phiếu', /^nguoi ghi phieu/, p.nguoi_ghi);
    them('Chức vụ', /^chuc vu/, p.chuc_vu);
    them('Điện thoại ghi phiếu', /^dien thoai ghi phieu/, p.dien_thoai);
    return { da, khong };
  };

  (async () => {
    const d = await layDuLieu();
    if (!d) return;
    if (d.loi) { khung(esc(d.loi), '#b00020'); return }
    for (let i = 0; i < 20 && !oMk() && !document.querySelector('textarea'); i++) await ngu(500);
    if (oMk()) { await hoiNen({ loai: 'tk-giu', d }); await dangNhap(d); return }
    await ngu(1200);
    const r = await dienPhieu(d);
    await hoiNen({ loai: 'tk-xoa' });
    khung('Đã điền <b>' + r.da.length + '</b> ô' + (r.da.length ? ': ' + esc(r.da.join(', ')) : '') + '.' + (r.khong.length ? '<br><span style="color:#8a5c0a">Không thấy ô: ' + esc(r.khong.join(', ')) + ' — bạn tự nhập.</span>' : '') +
      '<br>Hãy kiểm tra, nhập bảng sản phẩm/doanh thu theo ngành rồi tự bấm <b>Lưu tạm</b> hoặc <b>Hoàn tất phiếu</b> (phần mềm không bấm thay).' + bangSoLieu(d));
  })();
})();
