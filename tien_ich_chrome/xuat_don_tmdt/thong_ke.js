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
    k.style.maxHeight = '85vh'; k.innerHTML = '<div style="font-weight:600;color:#1a7a4a;margin-bottom:4px">Kế toán — báo cáo thống kê <span style="font-weight:400;color:#888;font-size:11px">(tiện ích v' + (() => { try { return chrome.runtime.getManifest().version } catch (e) { return '?' } })() + ')</span></div><div style="color:' + (mau || '#333') + '">' + txt + '</div>'; k.scrollTop = 0;
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

  // ---------- điền bảng mục 7 (doanh thu theo ngành) và mục 6 (sản phẩm): theo cấu trúc trên ảnh trang (nút Thêm -> dòng mới -> chọn mã ngành / nút "Mã SP" -> hộp "TRA CỨU MÃ SẢN PHẨM CÔNG NGHIỆP") ----------
  const so = v => String(Math.round(Number(v) * 1000) / 1000).replace('.', ',');
  const chu = e => bo(e.innerText || e.value || e.title || '');
  const chonLai = async (f, ms, lan) => { for (let i = 0; i < (lan || 20); i++) { const r = f(); if (r) return r; await ngu(ms || 250) } return null };
  const bangTheo = re => {      // bảng nhận diện theo chữ ở tiêu đề cột (không phụ thuộc thẻ tiêu đề mục)
    const ds = [...document.querySelectorAll('table')].filter(t => re.test(bo(t.innerText || '')) && [...t.querySelectorAll('button,input[type=button],input[type=submit],a')].some(b => chu(b) === 'them'))
      .sort((x, y) => (x.innerText || '').length - (y.innerText || '').length);
    return ds[0] || null;
  };
  const mucTheo = re => {
    const bg = /7\s*[.)]?\s*doanh thu/.test(String(re)) ? bangTheo(/ten nganh[\s\S]*ma nganh cap 2/) : bangTheo(/ten san pham[\s\S]*ton kho dau thang/);
    if (bg) return bg;
    return mucTheoTieuDe(re);
  };
  const mucTheoTieuDe = re => {      // bảng của mục (vd "7. Doanh thu thuần…"): nút "Thêm" đầu tiên NẰM SAU tiêu đề mục và bảng chứa nó
    const tieu = [...document.querySelectorAll('body *')].filter(e => !/^(script|style|option|select|textarea|input|button|svg|path)$/i.test(e.tagName) && hien(e) && e.children.length <= 3 && re.test(bo(e.innerText || '')) && bo(e.innerText || '').length < 200)
      .sort((a, b) => (a.innerText || '').length - (b.innerText || '').length)[0];
    if (!tieu) return null;
    const nut = [...document.querySelectorAll('button,input[type=button],input[type=submit],a')].filter(b => hien(b) && chu(b) === 'them' && (tieu.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) && !tieu.contains(b))[0];
    if (!nut) return null;
    return nut.closest('table') || nut.parentElement;
  };
  const dongDuLieu = muc => [...muc.querySelectorAll('tr')].filter(r => hien(r) && !r.querySelector('th') && !/^a b c( 1 2)?/.test(bo(r.innerText || '')) && !(r.innerText || '').trim().startsWith('Thêm') &&
    (r.querySelector('select,input:not([type=hidden]):not([type=button])') || [...r.querySelectorAll('*')].some(e => chu(e) === 'ma sp' || (e.tagName === 'IMG' && /xoa|delete|remove|del/i.test((e.src || '') + (e.alt || '') + (e.title || ''))))));
  const themDong = async muc => {
    const n0 = dongDuLieu(muc).length;
    const b = [...muc.querySelectorAll('button,input[type=button],a')].find(x => hien(x) && chu(x) === 'them'); if (!b) return null;
    b.click();
    const ds = await chonLai(() => { const r = dongDuLieu(muc); return r.length > n0 ? r : null }, 250, 16);
    return ds ? ds[ds.length - 1] : null;
  };
  const oSo = row => [...row.querySelectorAll('input:not([type=hidden]):not([type=button]):not([type=checkbox])')].filter(e => hien(e) && !e.disabled && !e.readOnly);
  const dienMuc7 = async (d, log) => {
    const muc = mucTheo(/^7\s*[.)]?\s*doanh thu thuan/); if (!muc) { log.push('Không thấy mục 7 (Doanh thu thuần).'); return }
    const sl = d.so_lieu || {}; if (!(sl.doanh_thu_trieu > 0)) { log.push('Mục 7: không có doanh thu để điền.'); return }
    let ma = String((d.phieu || {}).ma_nganh_cap2 || '').replace(/\D/g, '');
    if (!ma) {      // ô số (4-6 chữ số) nằm ngay sau nhãn "Mã ngành hoạt động chính"
      const cs = [...document.querySelectorAll('input')].filter(e => hien(e) && /^\d{4,6}$/.test(String(e.value || '').trim()));
      const o = cs.find(e => { let p = e.previousSibling, t = ''; for (let i = 0; i < 4 && p; i++, p = p.previousSibling) t += (p.textContent || ''); const tr = e.closest('tr,td,div'); return /ma nganh hoat dong chinh/.test(bo(t)) || (tr && /ma nganh hoat dong chinh/.test(bo((tr.innerText || '').slice(0, 300)))) });
      const v = o ? String(o.value).replace(/\D/g, '') : ''; ma = v ? v.slice(0, 2) : '' }      // mặc định = 2 số đầu của mã ngành hoạt động chính
    const row = await themDong(muc); if (!row) { log.push('Mục 7: không thêm được dòng (nút Thêm).'); return }
    const sel = row.querySelector('select');
    const op = sel && [...sel.options].find(o => new RegExp('^\\s*0*' + ma.replace(/^0+/, '') + '(\\D|$)').test(o.text) || String(o.value).replace(/^0+/, '') === ma.replace(/^0+/, ''));
    let op2 = op;
    if (!op2 && sel) { op2 = [...sel.options].find(o => String(o.value).trim() !== '' && /\d/.test(o.text)); log.push('Mục 7: ' + (ma ? 'không thấy mã ngành ' + ma : 'chưa biết mã ngành cấp 2') + ' → chọn đại ngành đầu danh sách "' + (op2 ? op2.text.trim() : '') + '" (bạn sửa lại cho đúng).') }
    if (!op2) { log.push('Mục 7: không có danh sách chọn mã ngành trên dòng mới — bạn tự chọn rồi nhập số.'); return }
    sel.value = op2.value; sel.dispatchEvent(new Event('change', { bubbles: true })); await ngu(500);
    const o = oSo(row)[0]; if (!o) { log.push('Mục 7: không thấy ô "Thực hiện tháng trước".'); return }
    gan(o, so(sl.doanh_thu_trieu)); vang(o);
    log.push('Mục 7: ngành ' + ma + ' = ' + so(sl.doanh_thu_trieu) + ' triệu đồng.');
  };
  const hopTraCuu = () => [...document.querySelectorAll('div,table,form')].filter(hien).find(e => /tra cuu ma san pham/.test(bo((e.innerText || '').slice(0, 200))) && e.querySelector('input'));
  const dienMuc6 = async (d, log) => {
    const muc = mucTheo(/^6\s*[.)]?\s*san xuat,? tieu thu/); if (!muc) { log.push('Không thấy mục 6 (Sản xuất, tiêu thụ sản phẩm).'); return }
    const sp = ((d.so_lieu || {}).sp || []).filter(x => x.sl > 0 || x.gia_tri_trieu > 0); const map = d.sp_map || {};
    if (!sp.length) { log.push('Mục 6: chưa có sản phẩm từ hoá đơn.'); return }
    for (const x of sp.slice(0, 30)) {
      const ma = String(map[x.ten] || '').trim();
      const row = await themDong(muc); if (!row) { log.push('Mục 6: không thêm được dòng cho "' + x.ten + '".'); return }
      const nut = [...row.querySelectorAll('button,input[type=button],input[type=submit],a,span,div,td')].filter(b => hien(b) && (/^ma sp$/.test(chu(b)) || (/tra cuu/.test(chu(b)) && chu(b).length < 25))).filter((u, _i, all) => !all.some(w => w !== u && u.contains(w)))[0];      // phần tử SÂU nhất (nút thật, không phải ô chứa nó)
      if (!nut) { log.push('Mục 6: không thấy nút "Mã SP" ở dòng mới.'); return }
      nut.click();
      const hop = await chonLai(hopTraCuu, 300, 20); if (!hop) { log.push('Mục 6: không mở được hộp tra cứu mã sản phẩm.'); return }
      const mo = ma && !/^\d+$/.test(ma) ? ma : '';       // mã số thì để trống Mô tả (liệt kê theo ngành); chữ thì dùng làm từ khoá tìm
      const oMota = [...hop.querySelectorAll('input[type=text],input:not([type])')].find(e => hien(e) && /mo ta/.test(bo(e.closest('td,div,label,tr') ? e.closest('td,div,label,tr').innerText || '' : '')) ) || hop.querySelector('input[type=text]');
      if (oMota && mo) gan(oMota, mo);
      const bm = [...hop.querySelectorAll('button,input[type=button],a')].find(b => hien(b) && /mo danh sach/.test(chu(b)));
      if (bm) bm.click();
      const dsRow = await chonLai(() => { const r = [...hop.querySelectorAll('tr')].filter(t => t.querySelectorAll('td').length >= 3 && /\d{4,}/.test(t.innerText || '') && t.querySelector('a,img,input[type=image],input[type=button],button')); return r.length ? r : null }, 400, 20);
      if (!dsRow) { log.push('Mục 6: "' + x.ten + '" — hộp tra cứu không có kết quả.'); const dong = [...document.querySelectorAll('a,button,span')].find(e => hien(e) && /^(x|dong|close)$/.test(chu(e))); if (dong) dong.click(); continue }
      const tok = bo(x.ten).split(' ').filter(t => t.length > 2);
      const diem = r => { const t = bo(r.innerText); if (ma && /^\d+$/.test(ma)) return t.includes(ma) ? 100 : 0; return tok.filter(w => t.includes(w)).length };
      const tot = x.chon_dau ? [1, dsRow[0]] : dsRow.map(r => [diem(r), r]).sort((a, b) => b[0] - a[0])[0];
      if (!tot || tot[0] <= 0) { log.push('Mục 6: "' + x.ten + '" — không khớp sản phẩm nào trong danh sách (hãy nhập mã SP ở phần mềm). Bỏ qua.'); const dong = [...document.querySelectorAll('a,button,span')].find(e => hien(e) && /^(x|dong|close)$/.test(chu(e))); if (dong) dong.click(); continue }
      const chon = tot[1].querySelector('a,img,input[type=image],input[type=button],button'); chon.click(); await ngu(600);
      const os = oSo(row);
      if (os.length < 3) { log.push('Mục 6: dòng "' + x.ten + '" có ' + os.length + ' ô nhập (cần ≥ 4) — bạn tự nhập số lượng/giá trị.'); continue }
      const tds = [...row.children].filter(c => /^t[dh]$/i.test(c.tagName)); const oTd = i => tds[i] ? oSo({ querySelectorAll: q => tds[i].querySelectorAll(q) })[0] : null;
      const oSx = oTd(6), oSl = oTd(7), oGt = oTd(8);      // bảng thật: SX tháng trước | Tiêu thụ SL | Tiêu thụ giá trị
      if (tds.length >= 9 && oSl && oGt) { if (oSx) { gan(oSx, so(x.sl)); vang(oSx) } gan(oSl, so(x.sl)); vang(oSl); gan(oGt, so(x.gia_tri_trieu)); vang(oGt) }
      else { gan(os[2], so(x.sl)); vang(os[2]); gan(os[3], so(x.gia_tri_trieu)); vang(os[3]) }
      log.push('Mục 6: ' + x.ten + ' — SL ' + so(x.sl) + ', giá trị ' + so(x.gia_tri_trieu) + ' triệu.');
    }
  };
  const dienBang = async d => {
    const log = []; const n = document.getElementById('__ketoanTkLog');
    const ghi = () => { if (n) n.innerHTML = log.map(x => '• ' + esc(x)).join('<br>') };
    if ((d.so_lieu || {}).gia_lap) { log.push('⚠ Không có hoá đơn tháng trước → điền SỐ ƯỚC TÍNH (doanh thu/sản lượng giả lập hợp lý). Hãy sửa lại số thật trước khi hoàn tất.'); ghi() }
    await dienMuc7(d, log); ghi(); await dienMuc6(d, log); ghi();
    log.push('Xong — kiểm tra từng dòng rồi tự bấm Lưu tạm / Hoàn tất phiếu.'); ghi();
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
      '<br><button id="__ketoanTkBang" style="margin:6px 0;padding:4px 10px;border:0;border-radius:6px;background:#1a7a4a;color:#fff;cursor:pointer">▶ Tự điền bảng mục 6 &amp; 7</button><div id="__ketoanTkLog" style="font-size:12px"></div>' +
      '<br>Hãy kiểm tra rồi tự bấm <b>Lưu tạm</b> hoặc <b>Hoàn tất phiếu</b> (phần mềm không bấm thay).' + bangSoLieu(d));
    const nb = document.getElementById('__ketoanTkBang'); let dangDien = false;
    const chay = () => { if (dangDien) return Promise.resolve(); dangDien = true; if (nb) nb.disabled = true; return dienBang(d).then(() => { dangDien = false; if (nb) nb.disabled = false }) };
    if (nb) nb.onclick = chay;
    await ngu(800); await chay();      // tự điền luôn bảng mục 6 & 7 (nút chỉ để chạy lại)
  })();
})();
