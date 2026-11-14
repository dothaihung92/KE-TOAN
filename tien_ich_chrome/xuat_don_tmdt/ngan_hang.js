// Kế toán — LẤY SAO KÊ NGÂN HÀNG (Vietcombank, ACB, VietinBank, Techcombank). Chạy trong trang internet banking người dùng ĐÃ TỰ ĐĂNG NHẬP.
// Phần mềm kế toán mở trang ngân hàng kèm dấu #ketoan-saoke=<nh>_<từ>_<đến>&j=<mã việc>&p=<cổng>. Tiện ích:
//  1) đang ở trang đăng nhập -> chỉ nhắc người dùng tự đăng nhập + OTP (KHÔNG đọc/nhập mật khẩu, OTP);
//  2) đã đăng nhập -> tìm & mở trang Sao kê / Lịch sử giao dịch;
//  3) ở trang sao kê -> điền Từ ngày/Đến ngày, bấm Tra cứu, rồi bấm Xuất Excel (1 lần; muốn chạy lại bấm nút trên khung);
//  4) hỏi phần mềm kế toán đã thấy file sao kê mới tải về chưa -> báo số giao dịch đã lấy.
// Giao diện mỗi ngân hàng khác nhau và hay đổi: không tìm được nút thì khung nhắc người dùng tự bấm — phần mềm vẫn tự nhận file tải về.
(() => {
  if (window.__ketoanSaoKe) return; window.__ketoanSaoKe = 1;
  const TEN = { vcb: 'Vietcombank', acb: 'ACB', vtb: 'VietinBank', tcb: 'Techcombank' };
  const LA_DINH = window.top === window;
  const kho = (() => { try { return chrome.storage.local } catch (e) { return null } })();
  const doc = k => new Promise(r => { try { kho.get(k, x => { void chrome.runtime.lastError; r((x || {})[k]) }) } catch (e) { r(undefined) } });
  const ghi = (k, v) => new Promise(r => { try { kho.set({ [k]: v }, () => { void chrome.runtime.lastError; r() }) } catch (e) { r() } });
  const hoiNen = m => new Promise(r => { const h = setTimeout(() => r({ loi: 'phần nền không trả lời' }), 12000); try { chrome.runtime.sendMessage(m, x => { void chrome.runtime.lastError; clearTimeout(h); r(x || {}) }) } catch (e) { clearTimeout(h); r({ loi: String(e && e.message || e) }) } });
  const ngu = ms => new Promise(r => setTimeout(r, ms));
  const bo = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').replace(/\s+/g, ' ').trim().toLowerCase();
  const hien = e => { if (!e || !e.isConnected) return false; const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' };
  const chu = e => bo((e.innerText || e.value || e.getAttribute('title') || e.getAttribute('aria-label') || '').slice(0, 80));

  // ---------- việc đang làm ----------
  const docDau = () => { const m = /ketoan-saoke=([a-z]+)_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})(?:&j=(\w+))?(?:&p=(\d+))?(?:&kt=([\w-]+))?/.exec(location.hash || ''); return m ? { nh: m[1], tu: m[2], den: m[3], j: m[4] || '', p: +m[5] || 8686, kt: m[6] || '', han: Date.now() + 2 * 3600e3, buoc: {} } : null };

  // ---------- tự điền ô đăng nhập (tên đăng nhập + mật khẩu đã lưu trong thông tin công ty); mã xác thực/captcha + OTP do NGƯỜI DÙNG nhập ----------
  const oCaptcha = () => [...document.querySelectorAll('input')].find(e => hien(e) && !e.disabled && e.type !== 'password' && /captcha|ma xac thuc|xac thuc|verification|security ?code/.test(nhanCua(e).join(' ')));
  const anhCaptcha = () => {
    // Tìm ảnh captcha gần ô nhập captcha nhất
    const o = oCaptcha(); if (!o) return null;
    const imgs = [...document.querySelectorAll('img')].filter(e => hien(e) && e.naturalWidth > 30 && e.naturalHeight > 20);
    // Ưu tiên ảnh gần ô captcha
    let best = null, bestDist = Infinity;
    const or = o.getBoundingClientRect();
    imgs.forEach(img => {
      const ir = img.getBoundingClientRect();
      const dist = Math.abs(ir.top - or.top) + Math.abs(ir.left - or.left);
      if (dist < bestDist) { bestDist = dist; best = img; }
    });
    return best && bestDist < 400 ? best : imgs.find(e => /captcha|security|verify|ma|xac thuc/i.test(e.src + ' ' + (e.alt || ''))) || imgs[0];
  };
  const giaiCaptcha = async (p) => {
    // Gửi ảnh captcha về server OCR
    const img = anhCaptcha(); if (!img) return null;
    try {
      const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
      c.getContext('2d').drawImage(img, 0, 0);
      const b64 = c.toDataURL('image/png');
      const r = await fetch('http://127.0.0.1:' + (p || 8686) + '/api/ocr-captcha', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ b64 }) });
      const j = await r.json();
      return j.ok && j.ma ? j.ma : null;
    } catch (e) { return null; }
  };
  const dienDangNhap = async v => {
    const mk = [...document.querySelectorAll('input[type=password]')].find(hien); if (!mk) return false;
    if (v.buoc.dn && Date.now() - v.buoc.dn < 120e3) return true;      // đã điền trong 2 phút qua: không điền lại (tránh ghi đè khi người dùng đang gõ)
    const t = await hoiNen({ loai: 'nh-tk-cho' }); if (!t || !t.user) return false;
    const o = [...document.querySelectorAll('input')].filter(e => hien(e) && !e.disabled && e !== mk && /^(text|email|tel|number|)$/i.test(e.getAttribute('type') || '') && (e.compareDocumentPosition(mk) & Node.DOCUMENT_POSITION_FOLLOWING));
    const u = o.find(e => /ten truy cap|ten dang nhap|username|user|tai khoan|account|login/.test(nhanCua(e).join(' ')) && e !== oCaptcha()) || o.filter(e => e !== oCaptcha()).pop();
    if (!u) return false;
    gan(u, t.user); await ngu(200); gan(mk, t.pass);
        v.buoc.dn = Date.now(); await ghi('nh_viec', v);
        // Tự giải captcha nếu có
        const c = oCaptcha();
        if (c) {
          await dat('Đã điền tên truy cập + mật khẩu. Đang đọc mã xác thực…');
          const ma = await giaiCaptcha(v.p);
          if (ma) { gan(c, ma); await ngu(300); await dat('Đã điền mã xác thực: ' + ma + '. Đang bấm Đăng nhập…'); const n = nut(RE_LOGIN); if (n) bam(n); }
          else { try { c.focus() } catch (e) { } await dat('Đã điền tên truy cập + mật khẩu. KHÔNG đọc được mã xác thực — hãy tự gõ rồi bấm Enter / Đăng nhập.', 'nhac'); }
        }
    return true;
  };
  const layViec = async () => { const v = await doc('nh_viec'); return v && v.han > Date.now() ? v : null };
  const dat = async (txt, loai) => { await ghi('nh_tt', { txt, loai: loai || '', luc: Date.now() }) };

  // ---------- tìm phần tử ----------
  const nhanCua = e => {      // các mẩu chữ mô tả 1 ô nhập, GẦN NHẤT trước: placeholder, name/id, label for, chữ ngay trước ô, ô bảng bên trái, khối cha
    const a = [e.placeholder, e.getAttribute('aria-label'), e.getAttribute('formcontrolname'), e.name, e.id, e.title];
    if (e.id) { const l = document.querySelector('label[for="' + CSS.escape(e.id) + '"]'); if (l) a.push(l.innerText) }
    let s = e.previousElementSibling; for (let i = 0; i < 2 && s; i++, s = s.previousElementSibling) a.push(s.innerText);
    const td = e.closest('td'); if (td && td.previousElementSibling) a.push(td.previousElementSibling.innerText);
    let p = e.parentElement;
    for (let i = 0; i < 4 && p; i++, p = p.parentElement) { const t = (p.innerText || '').trim(); if (t && t.length < 60) a.push(t) }
    return a.filter(Boolean).map(bo);
  };
  const RE_TU = /tu ngay|from ?date|fromdate|from_date|start ?date|startdate|ngay bat dau|^tu\b|\bfrom\b/;
  const RE_DEN = /den ngay|to ?date|todate|to_date|end ?date|enddate|ngay ket thuc|^den\b|\bto\b/;
  const loaiNgay = e => { for (const t of nhanCua(e)) { const a = RE_TU.test(t), b = RE_DEN.test(t); if (a && !b) return 'tu'; if (b && !a) return 'den' } return '' };
  const timNgay = () => {
    const os = [...document.querySelectorAll('input')].filter(e => hien(e) && !e.disabled && /^(text|date|search|tel|)$/i.test(e.type || 'text'));
    let tu = null, den = null;
    for (const e of os) { const l = loaiNgay(e); if (l === 'tu' && !tu) tu = e; else if (l === 'den' && !den) den = e }
    if (!(tu && den)) {      // không có nhãn: 2 ô liên tiếp có giá trị/placeholder dạng ngày
      const ng = os.filter(e => /\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{4}|\d{4}-\d{2}-\d{2}|dd.mm.yyyy|dd\/mm/i.test((e.value || '') + ' ' + (e.placeholder || '')) || e.type === 'date');
      if (ng.length >= 2) { tu = ng[0]; den = ng[1] }
    }
    return tu && den ? { tu, den } : null;
  };
  const nut = re => [...document.querySelectorAll('button,a,input[type=button],input[type=submit],[role=button],[role=menuitem],li,span,div')]
    .filter(e => hien(e) && !e.disabled && re.test(chu(e)) && chu(e).length < 40 && !e.closest('#__ketoanNh'))
    .sort((a, b) => chu(a).length - chu(b).length)[0];
  const RE_LOGIN = /dang nhap|login|sign in/;
  const RE_MENU = /^(sao ke|sao ke tai khoan|lich su giao dich|tra cuu giao dich|chi tiet giao dich|account statement|statement|transaction history|tra cuu sao ke|bao cao giao dich)$/;
  const RE_TIM = /^(tim kiem|tra cuu|xem|truy van|tim|loc|ap dung|search|view|query|apply|filter|xem sao ke)$/;
  const RE_XUAT = /^(xuat excel|tai excel|xuat file excel|excel|xlsx|export|export excel|export to excel|xuat file|tai ve|tai xuong|download|xuat bao cao|xuat sao ke|tai sao ke)$/;
  const RE_EXCEL = /excel|xlsx|\bxls\b/;

  // ---------- gán giá trị (React/Angular nhận được) ----------
  const gan = (e, v) => {
    const set = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(e), 'value');
    e.focus(); (set && set.set ? set.set.call(e, v) : (e.value = v));
    for (const t of ['input', 'change', 'blur']) e.dispatchEvent(new Event(t, { bubbles: true }));
    e.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'Enter' }));
  };
  const dinhDang = (e, iso) => {
    if (e.type === 'date') return iso;
    const [y, m, d] = iso.split('-'); const mau = bo((e.placeholder || '') + ' ' + (e.getAttribute('data-format') || ''));
    if (/yyyy-mm-dd/.test(mau) || /^\d{4}-\d{2}-\d{2}/.test(e.value)) return iso;
    if (/mm\/dd\/yyyy/.test(mau)) return m + '/' + d + '/' + y;
    if (/dd-mm-yyyy/.test(mau) || /^\d{2}-\d{2}-\d{4}/.test(e.value)) return d + '-' + m + '-' + y;
    if (/dd\.mm\.yyyy/.test(mau)) return d + '.' + m + '.' + y;
    return d + '/' + m + '/' + y;
  };
  const bam = e => { try { e.scrollIntoView({ block: 'center' }) } catch (_) { } e.click() };

  // ---------- các bước ----------
  let dangChay = false;
  const xuat = async (v, epBuoc) => {
    const f = timNgay();
    if (!f) return false;
    if (v.buoc.xuat && !epBuoc) return true;
    v.buoc.xuat = Date.now(); await ghi('nh_viec', v);
    gan(f.tu, dinhDang(f.tu, v.tu)); await ngu(300); gan(f.den, dinhDang(f.den, v.den)); await ngu(500);
    const n1 = nut(RE_TIM);
    if (n1) { bam(n1); await dat('Đã điền ' + v.tu.split('-').reverse().join('/') + ' → ' + v.den.split('-').reverse().join('/') + ', đã bấm “' + (n1.innerText || n1.value || '').trim() + '”. Đang chờ kết quả…'); await ngu(4000) }
    let n2 = nut(RE_XUAT);
    if (!n2) { await ngu(3000); n2 = nut(RE_XUAT) }
    if (!n2) { await dat('Đã điền khoảng ngày. Không thấy nút Xuất Excel — hãy chọn đúng tài khoản rồi tự bấm Tra cứu → Xuất Excel; phần mềm sẽ tự nhận file.', 'nhac'); return true }
    bam(n2); await ngu(1200);
    const n3 = nut(RE_EXCEL); if (n3 && n3 !== n2) { bam(n3); await ngu(800) }
    await dat('Đã bấm Xuất Excel. Đang chờ file sao kê tải về…');
    return true;
  };
  const buocMot = async () => {
    if (dangChay) return; dangChay = true;
    try {
      const v = await layViec(); if (!v) return;
      const mk = [...document.querySelectorAll('input[type=password]')].some(hien);
      if (mk && await dienDangNhap(v)) return;
      if (mk) { if (LA_DINH) await dat('Hãy tự đăng nhập ' + (TEN[v.nh] || 'ngân hàng') + ' (mật khẩu + OTP) — phần mềm không nhập thay. Đăng nhập xong tiện ích tự mở trang sao kê.', 'nhac'); return }
      if (await xuat(v, false)) return;
      if (!LA_DINH) return;
      const lan = v.buoc.menu || 0;
      if (lan < 4) {
        const m = nut(RE_MENU);
        if (m) { v.buoc.menu = lan + 1; await ghi('nh_viec', v); await dat('Đang mở trang “' + (m.innerText || '').trim() + '”…'); bam(m); return }
      }
      await dat('Hãy mở trang Sao kê / Lịch sử giao dịch của tài khoản cần lấy — tiện ích sẽ tự điền ngày và xuất Excel.', 'nhac');
    } finally { dangChay = false }
  };

  // ---------- khung trên trang (chỉ khung chính) ----------
  const ve = async () => {
    const v = await layViec(); let k = document.getElementById('__ketoanNh');
    if (!v) { if (k) k.remove(); return }
    if (!k) {
      k = document.createElement('div'); k.id = '__ketoanNh';
      k.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:2147483647;width:330px;background:#fff;border:2px solid #1a7a4a;border-radius:10px;box-shadow:0 4px 18px rgba(0,0,0,.25);font:13px/1.45 Segoe UI,Arial,sans-serif;color:#1a1a1a;padding:10px 12px';
      k.innerHTML = '<div style="font-weight:600;color:#1a7a4a;margin-bottom:4px">Kế toán — lấy sao kê <span id="__ketoanNhTen"></span></div><div id="__ketoanNhTt" style="margin-bottom:8px"></div>' +
        '<div style="display:flex;gap:6px;flex-wrap:wrap"><button id="__ketoanNhChay" style="padding:4px 10px;border:0;border-radius:6px;background:#1a7a4a;color:#fff;cursor:pointer">Tự điền ngày &amp; xuất Excel</button>' +
        '<button id="__ketoanNhDung" style="padding:4px 10px;border:1px solid #ccc;border-radius:6px;background:#fff;cursor:pointer">Dừng</button></div>';
      document.documentElement.appendChild(k);
      k.querySelector('#__ketoanNhChay').onclick = async () => { const x = await layViec(); if (!x) return; x.buoc = {}; await ghi('nh_viec', x); await ghi('nh_ep', Date.now()) };
      k.querySelector('#__ketoanNhDung').onclick = async () => { await ghi('nh_viec', null); await dat(''); k.remove() };
    }
    k.querySelector('#__ketoanNhTen').textContent = (TEN[v.nh] || '') + ' ' + v.tu.split('-').reverse().join('/') + ' → ' + v.den.split('-').reverse().join('/');
    const tt = await doc('nh_tt'); const e = k.querySelector('#__ketoanNhTt');
    e.textContent = (tt && tt.txt) || 'Đang chuẩn bị…'; e.style.color = tt && tt.loai === 'xong' ? '#1a7a4a' : tt && tt.loai === 'nhac' ? '#8a5c0a' : '#333';
  };
  const hoiFile = async () => {
    const v = await layViec(); if (!v || !v.j || !LA_DINH) return;
    const f = await hoiNen({ loai: 'nh-file-moi', j: v.j, p: v.p });
    if (f && f.co) {
      await dat('✓ Đã lấy ' + f.so_gd + ' giao dịch' + (f.so_tk ? ' (TK ' + f.so_tk + ')' : '') + ' từ file ' + f.ten + '. Quay lại phần mềm — Đối Chiếu Ngân Hàng đã tự điền ô sao kê.' + ((f.canh_bao || []).length ? ' Lưu ý: ' + f.canh_bao.join(' ') : ''), 'xong');
      v.han = Date.now() + 120e3; v.j = ''; await ghi('nh_viec', v);      // giữ khung thêm 2 phút để người dùng đọc, rồi tự tắt
    } else if (f && f.loi && f.loi.length) await dat('File mới tải về không đọc được: ' + [].concat(f.loi).join('; ') + '. Hãy xuất lại đúng định dạng Excel.', 'nhac');
  };

  (async () => {
    const d = LA_DINH ? docDau() : null;
    if (d) { await ghi('nh_viec', d); await dat('Đang mở ' + (TEN[d.nh] || 'ngân hàng') + '…'); if (d.kt) { await hoiNen({ loai: 'nh-lay-tk', kt: d.kt, p: d.p }); try { history.replaceState(null, '', location.href.replace(/&kt=[\w-]+/, '')) } catch (e) { } } }
    let ep0 = await doc('nh_ep');
    const vong = async () => {
      const ep = await doc('nh_ep');
      if (ep && ep !== ep0) { ep0 = ep; const v = await layViec(); if (v && !(await xuat(v, true))) await dat('Trang này không có ô Từ ngày/Đến ngày — hãy mở trang Sao kê của tài khoản rồi bấm lại.', 'nhac') }
      else await buocMot();
      if (LA_DINH) { await ve(); await hoiFile() }
    };
    await vong();
    setInterval(vong, 2500);
  })();
})();
