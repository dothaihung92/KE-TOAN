/* Nút bookmark "Điền dữ liệu GPKD": mở cửa sổ phụ, tự vào đúng khối dữ liệu của cổng (bấm menu, bấm "Tạo mới" nếu cần) rồi ĐIỀN các ô theo dữ liệu đã soạn trong phần mềm.
   CHỈ điều hướng và điền ô — không đăng nhập, không bấm Lưu/Ký/Nộp/Xóa, không đụng ô "Tôi không phải người máy" (reCAPTCHA) và nút "Đối chiếu CSDLQG": các bước đó người dùng tự làm. Có nút Hoàn tác. */
(async function () {
  var BAN = '__BAN_NUT__';
  var MA_NUT = '__MA_NUT__';
  var sach = function (s) { return (s || '').replace(/\s+/g, ' ').trim(); };
  var chuan = function (s) { return sach(s).normalize('NFC').toLowerCase().replace(/[:*]+$/, '').trim(); };
  var cho_doi = [];
  var dongHo = null;
  try {
    dongHo = new Worker(URL.createObjectURL(new Blob(['setInterval(function(){postMessage(1)},250)'], { type: 'text/javascript' })));
    dongHo.onmessage = function () { var bay = Date.now(); cho_doi = cho_doi.filter(function (x) { if (x.t <= bay) { x.ok(); return false; } return true; }); };
  } catch (eW) { dongHo = null; }
  var nghi = function (ms) { return new Promise(function (ok) { if (dongHo) cho_doi.push({ t: Date.now() + ms, ok: ok }); else setTimeout(ok, ms); }); };
  var txt = null;
  try { txt = await navigator.clipboard.readText(); } catch (e) { txt = null; }
  var dl = null;
  try { dl = JSON.parse(txt); } catch (e) { dl = null; }
  if (!dl || !dl.dkkd_dien || !dl.truong) {
    var tay = prompt('Không đọc được dữ liệu từ clipboard. Hãy bấm "Copy dữ liệu điền" trong phần mềm rồi dán (Ctrl+V) vào đây:', '');
    try { dl = JSON.parse(tay); } catch (e) { dl = null; }
  }
  if (!dl || !dl.dkkd_dien || !dl.truong) { alert('Chưa có dữ liệu điền. Vào phần mềm → Soạn hồ sơ → chọn khối, bấm "Copy dữ liệu điền", rồi bấm lại nút này.'); return; }

  var laO = function (e) { var t = (e.type || '').toLowerCase(); return /^(INPUT|SELECT|TEXTAREA)$/.test(e.tagName) && !/^(hidden|button|submit|image|password|reset|checkbox|radio|file)$/.test(t); };
  var layO = function (node) { return /^(INPUT|SELECT|TEXTAREA)$/.test(node.tagName) ? (laO(node) ? [node] : []) : [].slice.call(node.querySelectorAll('input,select,textarea')).filter(laO); };
  var layR = function (node, D) {
    return [].slice.call(node.querySelectorAll('input[type=radio]')).map(function (r) {
      var lb = r.id && D.querySelector('label[for="' + r.id + '"]');
      var nhan = lb ? lb.innerText : (r.nextSibling && r.nextSibling.nodeType === 3 ? r.nextSibling.nodeValue : (r.nextElementSibling ? r.nextElementSibling.innerText : ''));
      return { el: r, nhan: chuan(nhan) };
    });
  };
  var quet = function (D) {
    var ds = [];
    D.querySelectorAll('tr').forEach(function (r) {
      var c = [].slice.call(r.children).filter(function (x) { return x.tagName === 'TD' || x.tagName === 'TH'; });
      var cap = function (a, b) {
        if (!c[a] || !c[b]) return;
        if (layO(c[a]).length || c[a].querySelector('input[type=radio]')) return;
        var nhan = chuan(c[a].innerText);
        var os = layO(c[b]);
        var rs = layR(c[b], D);
        if (nhan && nhan.length < 160 && (os.length || rs.length)) ds.push({ nhan: nhan, os: os, rs: rs });
      };
      if (c.length === 4) { cap(0, 1); cap(2, 3); } else if (c.length >= 2) { cap(0, c.length - 1); }
    });
    D.querySelectorAll('label[for]').forEach(function (l) {
      var e = D.getElementById(l.getAttribute('for'));
      if (e && laO(e)) ds.push({ nhan: chuan(l.innerText), os: [e], rs: [] });
    });
    return ds;
  };
  var coTruong = function (D, g) {
    var ds = quet(D);
    return g.truong.some(function (t) { var re; try { re = new RegExp(t.nhan, 'i'); } catch (e) { return false; } return ds.some(function (x) { return re.test(x.nhan); }); });
  };
  var cho = async function (w, dieuKien, giay) {
    var het = Date.now() + giay * 1000;
    while (Date.now() < het) {
      try { if (!w.closed && w.document && w.document.readyState === 'complete' && dieuKien(w.document)) return true; } catch (e) { }
      await nghi(300);
    }
    return false;
  };
  var timBam = function (D, ten, loaiTag) {
    var vv = chuan(ten);
    return [].slice.call(D.querySelectorAll(loaiTag || 'a,input[type=button],input[type=submit],button')).filter(function (e) {
      var n = chuan(e.tagName === 'INPUT' ? e.value : e.innerText);
      return n === vv;
    })[0] || null;
  };
  var timTaoMoiTrongMuc = function (D, muc) {
    var ns = function (x) { return chuan(x).replace(/\s+/g, ''); };
    var tieuDe = [].slice.call(D.querySelectorAll('div,td,th,span,legend,b,h1,h2,h3,h4,p')).filter(function (e) { return e.children.length <= 1 && ns(e.innerText) === ns(muc); })[0];
    if (!tieuDe) return null;
    var cur = tieuDe;
    for (var k = 0; k < 7; k++) {
      cur = cur.parentElement;
      if (!cur) break;
      var bs = [].slice.call(cur.querySelectorAll('a,input[type=button],input[type=submit],button')).filter(function (e) { return chuan(e.tagName === 'INPUT' ? e.value : e.innerText) === 'tạo mới' && (tieuDe.compareDocumentPosition(e) & 4); });
      if (bs.length) return bs[0];
    }
    return null;
  };
  var timSuaDong = function (D, sd) {
    // dòng của ĐÚNG người cần sửa (khớp số giấy tờ, không có thì khớp họ tên) trong bảng danh sách của khối -> nút "Sửa đổi" của dòng đó (không bao giờ bấm Xóa)
    var so = String(sd.cccd || '').replace(/\D/g, ''), ten = chuan(sd.ten);
    var dong = [].slice.call(D.querySelectorAll('tr')).filter(function (r) {
      var t = r.innerText || '';
      return (so.length >= 9 && t.replace(/\D/g, '').indexOf(so) >= 0) || (ten && chuan(t).indexOf(ten) >= 0);
    }).sort(function (a, b) { return (a.innerText || '').length - (b.innerText || '').length; });
    for (var i = 0; i < dong.length; i++) {
      var n = [].slice.call(dong[i].querySelectorAll('a,input[type=button],input[type=submit],button')).filter(function (e) {
        var t = chuan(e.tagName === 'INPUT' ? e.value : (e.innerText || e.title || ''));
        return /^(sửa đổi|sửa|chỉnh sửa|cập nhật)$/.test(t);
      })[0];
      if (n) return n;
    }
    return null;
  };
  var bamVaCho = async function (w, e, dieuKien) {
    w.__dkkdMark = 1;
    e.click();
    var het = Date.now() + 30000;
    while (Date.now() < het) {
      await nghi(300);
      try { if (!w.closed && !w.__dkkdMark && w.document.readyState === 'complete' && dieuKien(w.document)) return true; } catch (e2) { }
    }
    return false;
  };

  var cuaSoPhu = null;
  var khungLoi = '';
  var moKhung = async function () {
    if (cuaSoPhu && !cuaSoPhu.closed) return cuaSoPhu;
    var ov = null;
    try {
      ov = document.createElement('div');
      ov.id = '__dkkdKhung';
      ov.style.cssText = 'position:fixed;left:0;top:0;right:0;bottom:0;z-index:2147483000;background:#fff;display:flex;flex-direction:column';
      var bar = document.createElement('div');
      bar.style.cssText = 'background:#2e7d32;color:#fff;padding:6px 10px;font:13px Arial,sans-serif;display:flex;justify-content:space-between;align-items:center';
      bar.innerHTML = '<span>Cổng đăng ký doanh nghiệp — khung điền tự động (ngay trong tab này)</span>';
      var dong = document.createElement('button');
      dong.textContent = 'Đóng khung, về trang gốc';
      dong.style.cssText = 'padding:3px 10px';
      dong.onclick = function () { ov.remove(); cuaSoPhu = null; gen++; };
      bar.appendChild(dong);
      var ifr = document.createElement('iframe');
      ifr.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-forms allow-popups allow-modals');
      ifr.style.cssText = 'flex:1;border:0;width:100%';
      ov.appendChild(bar);
      ov.appendChild(ifr);
      await new Promise(function (xong) {
        var tm = setTimeout(xong, 30000);
        ifr.addEventListener('load', function () { clearTimeout(tm); xong(); });
        ifr.src = location.href;
        document.body.appendChild(ov);
      });
      var dk = null;
      try { dk = ifr.contentDocument; } catch (e0) { dk = null; }
      if (!dk || !dk.body) throw new Error('cổng không cho hiện trong khung');
      var ok = await cho(ifr.contentWindow, function (d) { return d.body && sach(d.body.innerText).length > 80; }, 15);
      if (!ok) throw new Error('khung không tải được');
      var bb = document.getElementById('__dkkdBang');
      if (bb) { bb.style.left = 'auto'; bb.style.right = '12px'; bb.style.top = '46px'; bb.style.bottom = 'auto'; }
      cuaSoPhu = ifr.contentWindow;
      return cuaSoPhu;
    } catch (eK) {
      khungLoi = String(eK);
      try { if (ov) ov.remove(); } catch (e1) { }
    }
    var tab = window.open('', '_dkkd_dien');
    if (tab) {
      try { if (tab.location.href === 'about:blank' || !tab.document.querySelector('a')) tab.location.href = location.href; } catch (e2) { }
    }
    return tab;
  };
  var daBamLuu = false;
  var luuLuc = 0;
  var thayGuiLai = false;
  var epSang = false;
  var ganNgheLuu = function (D) {
    [].slice.call(D.querySelectorAll('input[type=button],input[type=submit],button,a')).forEach(function (e) {
      var ten = e.tagName === 'INPUT' ? e.value : e.innerText;
      if (!e.__dkkdL && chuan(ten) === 'lưu') {
        e.__dkkdL = 1;
        e.addEventListener('click', function () {
          daBamLuu = true; luuLuc = Date.now(); thayGuiLai = false;
          try { e.ownerDocument.defaultView.__dkkdLuuMk = 1; } catch (e1) { }   /* trang tải lại sau Lưu -> dấu này mất */
        }, true);
      }
    });
  };
  var nhom_tong = (dl.nhom && dl.nhom.length) || 1;
  var chayNhom = async function (g, taiCho) {
    var D = document;
    var w = null;
    if (taiCho && cuaSoPhu && !cuaSoPhu.closed) {
      w = cuaSoPhu;
      D = w.document;
    } else if (g.vao_khoi && (!coTruong(document, g) || g.sua_dong || g.tao_moi || g.truong.some(function (t) { return t.chuoi; }))) {
      w = await moKhung();
      if (!w) { alert('Chrome đang chặn tab/cửa sổ mới. Bấm biểu tượng chặn ở thanh địa chỉ → "Luôn cho phép" rồi bấm lại nút này.'); return; }
      var menuOk = await cho(w, function (d) { return !!timBam(d, g.vao_khoi, 'a'); }, 40);
      if (!menuOk) { alert('Không thấy mục "' + g.vao_khoi + '" trong menu KHỐI DỮ LIỆU của cổng (có thể chưa đăng nhập hoặc đang ở trang khác). Hãy mở hồ sơ rồi bấm lại.'); return; }
      var mk = timBam(w.document, g.vao_khoi, 'a');
      var vaoMenu = await bamVaCho(w, mk, function (d) { return true; });
      if (!vaoMenu) { alert('Chưa mở được khối "' + g.vao_khoi + '". Bạn tự bấm mục đó trong menu rồi bấm lại nút này.'); return; }
      if (g.sua_dong) {
        var nutS = timSuaDong(w.document, g.sua_dong);
        if (!nutS) { alert('Không thấy dòng của "' + g.sua_dong.ten + '" (nút "Sửa đổi") trong khối "' + g.vao_khoi + '". Bạn tự bấm "Sửa đổi" ở dòng người này rồi bấm lại nút này.'); try { w.focus(); } catch (e) { } return; }
        var vaoS = await bamVaCho(w, nutS, function (d) { return true; });
        if (!vaoS) { alert('Chưa mở được trang sửa của "' + g.sua_dong.ten + '". Bạn tự bấm "Sửa đổi" rồi bấm lại nút này.'); try { w.focus(); } catch (e) { } return; }
      } else if (g.tao_moi && !coTruong(w.document, g)) {
        var nut = g.muc_tao_moi ? timTaoMoiTrongMuc(w.document, g.muc_tao_moi) : timBam(w.document, 'Tạo mới');
        if (!nut) { alert('Không thấy nút "Tạo mới"' + (g.muc_tao_moi ? ' của mục "' + g.muc_tao_moi + '"' : '') + ' trong khối "' + g.vao_khoi + '". Bạn tự bấm "Tạo mới" rồi bấm lại nút này.'); try { w.focus(); } catch (e) { } return; }
        var vaoForm = await bamVaCho(w, nut, function (d) { return true; });
        if (!vaoForm) { alert('Chưa mở được trang nhập. Bạn tự bấm "Tạo mới" rồi bấm lại nút này.'); try { w.focus(); } catch (e) { } return; }
      }
      D = w.document;
      await nghi(600);
      try { w.focus(); } catch (e) { }
    }

    var daDung = [];
    var cu = [];
    var daDien = [];
    var khong = [];
    var goc = function (x) { return chuan(x).replace(/^(thành phố\s+|tp\.\s*|tp\s+|tỉnh\s+|thị xã\s+|thị trấn\s+|quận\s+|huyện\s+|phường\s+|xã\s+|đặc khu\s+)/, '').trim(); };   /* "TP.Hồ Chí Minh" (không cách) cũng khớp "Hồ Chí Minh" */
    var ref = function (o) { return { id: o.id || '', name: o.name || '' }; };
    var tra = function (r) { return (r.id && D.getElementById(r.id)) || (r.name && D.getElementsByName(r.name)[0]) || null; };
    var vang = function (o) { if (o) { o.style.background = '#fff3a0'; o.style.outline = '2px solid #e6a700'; } };
    var luu = function (o) { cu.push({ r: ref(o), v: o.value, s: o.style.cssText }); };
    var gan = function (o, v) {
      luu(o);
      o.value = v;
      o.dispatchEvent(new Event('input', { bubbles: true }));
      vang(o);
    };
    var timOption = function (o, v) {
      var vv = chuan(v), gv = goc(v);
      var ops = [].slice.call(o.options);
      return ops.filter(function (x) { return chuan(x.text) === vv; })[0]
        || ops.filter(function (x) { return gv && goc(x.text) === gv; })[0]
        || ops.filter(function (x) { return vv && chuan(x.text).indexOf(vv) === 0; })[0]
        || ops.filter(function (x) { return gv && goc(x.text).indexOf(gv) >= 0 && x.value !== ''; })[0];
    };
    var chonSelect = function (o, v) {
      var op = null;
      String(v).split(' || ').some(function (x) { op = timOption(o, x); return !!op; });   /* nhiều lựa chọn thay thế: lấy lựa chọn đầu tiên cổng có */
      if (!op) return false;
      luu(o);
      o.value = op.value;
      vang(o);
      return true;
    };
    var chonRadio = function (rs, v) {
      var vv = chuan(v);
      var r = rs.filter(function (x) { return x.nhan === vv; })[0];
      if (!r || r.el.disabled) return false;
      var truoc = rs.filter(function (x) { return x.el.checked; })[0];
      cu.push({ radio: ref(r.el), truoc: truoc ? ref(truoc.el) : null });
      r.el.checked = true;
      r.el.parentNode.style.background = '#fff3a0';
      return true;
    };
    var chonRadioNhan = function (t) {
      var vv = chuan(t.radio);
      var rs = layR(D.body, D).filter(function (x) { return x.nhan === vv && !x.el.disabled; });
      if (!rs.length) { khong.push(t.ten + ' (không thấy lựa chọn "' + t.radio + '")'); return; }
      var truoc = layR(D.body, D).filter(function (x) { return x.el.checked && x.el.name === rs[0].el.name; })[0];
      cu.push({ radio: ref(rs[0].el), truoc: truoc ? ref(truoc.el) : null });
      var doi = !rs[0].el.checked;
      if (doi) rs[0].el.click();
      rs[0].el.checked = true;
      rs[0].el.parentNode.style.background = '#fff3a0';
      daDien.push(t.ten);
      return doi ? rs[0].el : null;
    };
    var dienOBang = function (t) {
      /* bảng nhiều cột (vd. "Loại tài sản | Tỷ lệ (%) | Giá trị (VNĐ)" của thành viên): tìm dòng có nhãn ở ô đầu, điền ô nhập thứ t.o_thu của dòng */
      var re; try { re = new RegExp(t.bang, 'i'); } catch (e) { return null; }
      var dong = [].slice.call(D.querySelectorAll('tr')).filter(function (r) {
        var c = [].slice.call(r.children).filter(function (x) { return x.tagName === 'TD' || x.tagName === 'TH'; });
        return c.length >= 3 && !layO(c[0]).length && re.test(chuan(c[0].innerText));
      })[0];
      if (!dong) { khong.push(t.ten + ' (không thấy dòng)'); return null; }
      var os = [];
      [].slice.call(dong.children).slice(1).forEach(function (c) { os = os.concat(layO(c)); });
      var o = os[t.o_thu || 0];
      if (!o || o.disabled || o.readOnly) { khong.push(t.ten + ' (ô bị khóa/không có)'); return null; }
      gan(o, String(t.gia_tri));
      try { ['keydown', 'keyup', 'change', 'blur'].forEach(function (ev) { o.dispatchEvent(new Event(ev, { bubbles: true })); }); } catch (e) { }   /* để cổng tự tính dòng 'Tổng số' (ô khóa, không điền tay được) */
      daDien.push(t.ten);
      return null;
    };
    var xuLy = function (t, dsO) {
      if (t.radio) return chonRadioNhan(t);
      if (t.bang) return dienOBang(t);
      var re;
      try { re = new RegExp(t.nhan, 'i'); } catch (e) { return null; }
      var tim = dsO.filter(function (x) { return re.test(x.nhan) && daDung.indexOf(x.nhan) < 0; });
      var m = tim.filter(function (x) { return x.rs.length || x.os.some(function (o) { return !o.disabled && !o.readOnly; }); })[0];
      if (!m) { khong.push(t.ten + (tim.length ? ' (ô bị khóa, không sửa được)' : ' (không thấy ô)')); return null; }
      daDung.push(m.nhan);
      var v = String(t.gia_tri);
      if (m.rs.length && !m.os.length) { if (chonRadio(m.rs, v)) daDien.push(t.ten); else khong.push(t.ten + ' (không có lựa chọn "' + v + '")'); return null; }
      var os = m.os.filter(function (o) { return !o.disabled && !o.readOnly; });
      var sel = os.filter(function (o) { return o.tagName === 'SELECT'; });
      var inp = os.filter(function (o) { return o.tagName !== 'SELECT'; });
      if (sel.length && inp.length && t.tien_to) {
        var best = null;
        sel.forEach(function (s) { [].slice.call(s.options).forEach(function (op) { var p = chuan(op.text); if (p && chuan(v).indexOf(p + ' ') === 0 && (!best || p.length > best.p.length)) best = { s: s, op: op, p: p }; }); });
        if (best) {
          luu(best.s);
          best.s.value = best.op.value;
          vang(best.s);
          gan(inp[0], sach(v).slice(best.p.length).trim());
          daDien.push(t.ten);
          return null;
        }
      }
      if (sel.length && !inp.length) {
        var truoc = sel[0].value;
        if (chonSelect(sel[0], v)) { daDien.push(t.ten); return sel[0].value !== truoc ? sel[0] : null; }
        khong.push(t.ten + ' (không có lựa chọn "' + v + '" — chọn tay)');
        return null;
      }
      if (inp.length) { gan(inp[0], v); daDien.push(t.ten); return null; }
      khong.push(t.ten + ' (ô không điền được)');
      return null;
    };
    var settle = async function (win, o) {
      win.__dkkdMk = 1;
      o.dispatchEvent(new Event('change', { bubbles: true }));
      var het = Date.now() + 25000;
      var bd = Date.now();
      await nghi(900);
      while (Date.now() < het) {
        if (win.closed) return false;
        try {
          if (!win.__dkkdMk) { if (win.document.readyState === 'complete') { await nghi(600); return true; } }
          else {
            var ban = false;
            try { ban = !!(win.Sys && win.Sys.WebForms && win.Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostBack()); } catch (e1) { ban = false; }
            if (!ban && Date.now() - bd > 2500) return true;
          }
        } catch (e2) { }
        await nghi(300);
      }
      return false;
    };
    var daGuiLai = false;
    var thuong = g.truong.filter(function (t) { return !t.chuoi; });
    var chuoi = g.truong.filter(function (t) { return t.chuoi; });
    var dsO = quet(D);
    thuong.forEach(function (t) { xuLy(t, dsO); });
    var winDich = w || window;
    for (var ci = 0; ci < chuoi.length; ci++) {
      var tc = chuoi[ci];
      var dsC = quet(D);
      var selMoi = null;
      var chay = 0;
      while (!tc.radio && chay < 14) {
        var re2; try { re2 = new RegExp(tc.nhan, 'i'); } catch (e) { re2 = null; }
        var mC = re2 && dsC.filter(function (x) { return re2.test(x.nhan) && x.os.some(function (o) { return o.tagName === 'SELECT'; }); })[0];
        if (mC && mC.os.some(function (o) { return o.tagName === 'SELECT' && o.options.length > 1; })) break;
        await nghi(700);
        dsC = quet(D);
        chay++;
      }
      selMoi = xuLy(tc, dsC);
      if (selMoi && !winDich.closed) {
        daGuiLai = true;
        var tai = await settle(winDich, selMoi);
        try { D = winDich.document; } catch (e) { }
        cu.forEach(function (x) { if (x.r) vang(tra(x.r)); });
      }
    }

    if (daGuiLai) {
      /* ô chỉ hiện SAU khi chọn danh sách (vd. chọn "Loại chủ sở hữu hưởng lợi" thì cổng mới hiện các ô thông tin) -> điền lại các ô lúc đầu chưa thấy */
      var thieu = thuong.filter(function (t) { return khong.indexOf(t.ten + ' (không thấy ô)') >= 0; });
      if (thieu.length) {
        khong = khong.filter(function (k) { return !thieu.some(function (t) { return k === t.ten + ' (không thấy ô)'; }); });
        var dsL = quet(D);
        thieu.forEach(function (t) { xuLy(t, dsL); });
      }
    }
    var huong = '';
    if (!daDien.length) {
      var khoiCan = [];
      g.truong.forEach(function (t) { if (t.khoi && khoiCan.indexOf(t.khoi) < 0) khoiCan.push(t.khoi); });
      var tim2 = [];
      D.querySelectorAll('a').forEach(function (a) {
        var nh = chuan(a.innerText);
        khoiCan.forEach(function (k) { if (nh && nh === chuan(k)) { a.style.outline = '3px solid #d62020'; a.style.background = '#ffe4e4'; tim2.push(k); } });
      });
      huong = '<div style="margin:6px 0;padding:6px;background:#ffe9e9;border-radius:6px"><b>Trang này chưa phải trang nhập của khối cần sửa</b> (nên chưa điền được ô nào). Hãy bấm mục ' + (khoiCan.length ? '<b>"' + khoiCan.join('" / "').replace(/</g, '&lt;') + '"</b>' : 'cần sửa') + ' trong menu "KHỐI DỮ LIỆU" bên trái' + (tim2.length ? ' (đã viền đỏ)' : '') + ', vào trang <b>nhập/sửa đổi</b> (có các ô nhập), rồi bấm lại nút này.</div>';
    }
    var hop = D.createElement('div');
    hop.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:2147483647;max-width:420px;background:#fff;border:2px solid #e6a700;border-radius:10px;padding:10px 12px;font:13px/1.4 Arial,sans-serif;color:#222;box-shadow:0 4px 18px rgba(0,0,0,.3)';
    var h = '<b>Đã điền ' + daDien.length + ' ô</b> (tô vàng) — <b>hãy kiểm tra từng ô</b>.';
    if (daDien.length) h += '<div style="margin-top:4px">Bạn tự làm tiếp: tick "Tôi không phải là người máy" (nếu có), bấm "Đối chiếu với CSDLQG về dân cư" (nếu cần), chọn các ô danh sách còn trống, rồi <b>tự bấm Lưu</b>. Phần mềm không tự lưu, không ký, không nộp, không xóa.</div>';
    h += huong;
    if (dl.ma_nut && dl.ma_nut !== MA_NUT) h = '<div style="margin-bottom:6px;padding:6px;background:#ffe9e9;border-radius:6px;color:#a00"><b>Nút bookmark này đã CŨ</b> so với phần mềm. Vào phần mềm bấm <b>"Copy mã nút điền"</b> rồi sửa dấu trang "Điền dữ liệu GPKD", dán mã mới vào ô URL.</div>' + h;
    if (daDien.length && nhom_tong === 1) h += '<div style="margin-top:6px;color:#555">Chỉ có <b>1 khối</b> cần điền nên sau khi Lưu phần mềm không còn khối nào để tự sang.</div>';
    if (dl.bo_qua && dl.bo_qua.length) {
      var ten_bq = { nganh: 'Ngành nghề kinh doanh', chu_so_huu: 'Chủ sở hữu/thành viên', cshhl: 'Chủ sở hữu hưởng lợi', thue: 'Thông tin về thuế' };
      h += '<div style="margin-top:6px;color:#555">Mục chưa hỗ trợ điền tự động — <b>bạn nhập tay</b>: ' + dl.bo_qua.map(function (k) { return ten_bq[k] || k; }).join(', ') + '.</div>';
    }
    if (dl.nhac && dl.nhac.length) h += '<div style="margin-top:6px;color:#a00"><b>Bạn tự làm trên cổng:</b><br>' + dl.nhac.map(function (x) { return '• ' + String(x).replace(/</g, '&lt;'); }).join('<br>') + '</div>';
    if (khong.length) h += '<div style="margin-top:6px;color:#b45309"><b>Chưa điền được (nhập tay):</b><br>' + khong.map(function (x) { return '• ' + x.replace(/</g, '&lt;'); }).join('<br>') + '</div>';
    h += '<div style="margin-top:8px"><button id="__dkkdHoan" style="padding:4px 10px;margin-right:6px">Hoàn tác</button><button id="__dkkdDong" style="padding:4px 10px">Đóng</button> <span style="color:#888;font-size:11px">bản ' + BAN + '</span></div>';
    if (w) cuaSoPhu = w;
    ganNgheLuu(D);
    hop.innerHTML = h;
    D.body.appendChild(hop);
    D.getElementById('__dkkdDong').onclick = function () { hop.remove(); };
    D.getElementById('__dkkdHoan').onclick = function () {
      cu.forEach(function (x) {
        if (x.radio) { var r1 = tra(x.radio); if (r1) { r1.checked = false; r1.parentNode.style.background = ''; } var r2 = x.truoc && tra(x.truoc); if (r2) r2.checked = true; }
        else { var o = tra(x.r); if (o) { o.value = x.v; o.style.cssText = x.s; } }
      });
      hop.remove();
    };

  };
  var nhom = dl.nhom && dl.nhom.length ? dl.nhom : [{ ten: dl.vao_khoi || '', vao_khoi: dl.vao_khoi, tao_moi: dl.tao_moi, truong: dl.truong, luu_y: dl.luu_y }];
  if (nhom.length === 1) { await chayNhom(nhom[0]); return; }
  var tenNut = function (e) { return e.tagName === 'INPUT' ? e.value : e.innerText; };
  var gen = 0;
  var tt = [];
  var daLuuXong = function (D, g) {
    var ds = quet(D);
    var tong = 0;
    var sua = 0;
    g.truong.forEach(function (t) {
      var re;
      try { re = new RegExp(t.nhan, 'i'); } catch (e) { return; }
      var m = ds.filter(function (x) { return re.test(x.nhan); })[0];
      if (!m) return;
      tong++;
      if (m.rs.some(function (r) { return !r.el.disabled; }) || m.os.some(function (o) { return !o.disabled && !o.readOnly; })) sua++;
    });
    return tong === 0 || sua <= tong / 2;
  };
  var daLuuTaiCho = function (w, D) {
    // Cổng thật (vd. khối Địa chỉ): sau Lưu vẫn ở lại CÙNG trang, các ô vẫn mở -> nhận ra đã Lưu qua: trang đã gửi lại xong (tải lại toàn trang
    // hoặc gửi lại một phần đã kết thúc), nút Lưu bị khóa, hoặc cổng báo "lưu/cập nhật thành công". Có lỗi của cổng thì không tính.
    var ban = false;
    try { ban = !!(w.Sys && w.Sys.WebForms && w.Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostBack()); } catch (e) { ban = false; }
    if (ban) { thayGuiLai = true; return false; }
    if (Date.now() - luuLuc < 1500) return false;
    if (!w.__dkkdLuuMk) return true;   /* trang đã tải lại sau khi bấm Lưu */
    if (thayGuiLai) return true;   /* gửi lại một phần (UpdatePanel) đã xong */
    var khoa = [].slice.call(D.querySelectorAll('input[type=button],input[type=submit],button,a')).some(function (e) {
      return chuan(e.tagName === 'INPUT' ? e.value : e.innerText) === 'lưu' && (e.disabled || /aspnetdisabled/i.test(e.className || ''));
    });
    if (khoa) return true;
    return /(lưu|cập nhật)( dữ liệu| hồ sơ| thông tin)? thành công/i.test(sach(D.body.innerText));
  };
  var loiCong = function (D) {
    var kq = [];
    [].slice.call(D.querySelectorAll('div,span,p,li,td,font,label')).forEach(function (e) {
      if (e.children.length > 2 || e.closest('#__dkkdTT') || e.closest('a')) return;
      var t = sach(e.innerText);
      if (t && /nếu (bạn muốn|để trống)|^thông tin liên hệ/i.test(t)) return;   /* lời hướng dẫn luôn hiện của cổng (vd. ô email), không phải lỗi */
      if (t && t.length < 220 && /(captcha|mã xác thực|người máy).*(sai|không đúng|chưa)|không hợp lệ|vui lòng (nhập|chọn)|bắt buộc|^lỗi|sai mã/i.test(t) && e.offsetParent !== null && kq.indexOf(t) < 0) kq.push(t);
    });
    return kq.slice(0, 3);
  };
  var veTrangThai = function (D, ten, ke, loi, dienLai) {
    var ex = D.getElementById('__dkkdTT');
    if (ex) ex.remove();
    var b = D.createElement('div');
    b.id = '__dkkdTT';
    b.style.cssText = 'position:fixed;left:12px;bottom:12px;z-index:2147483647;max-width:400px;background:#fff;border:2px solid #2e7d32;border-radius:10px;padding:10px 12px;font:13px/1.4 Arial,sans-serif;color:#222;box-shadow:0 4px 18px rgba(0,0,0,.3)';
    var h = '<b>Khối "' + ten.replace(/</g, '&lt;') + '"</b> — đang chờ bạn <b>Lưu</b>' + (ke ? ' để tự sang khối <b>"' + ke.replace(/</g, '&lt;') + '"</b>' : '') + '.';
    if (loi.length) h += '<div style="margin-top:6px;padding:6px;background:#ffe9e9;border-radius:6px;color:#a00"><b>Cổng báo:</b> ' + loi.map(function (x) { return x.replace(/</g, '&lt;'); }).join(' | ') + '<br>Hãy xử lý (ví dụ tick "Tôi không phải là người máy") rồi bấm <b>Lưu</b> lại.</div>';
    h += '<div style="margin-top:8px"><button id="__dkkdLai" style="padding:4px 10px;margin-right:6px">Điền lại khối này</button>' + (ke ? '<button id="__dkkdSang" style="padding:4px 10px;margin-right:6px">Đã Lưu xong → sang khối kế tiếp</button>' : '') + '<button id="__dkkdDongTT" style="padding:4px 10px">Ẩn</button></div>';
    b.innerHTML = h;
    D.body.appendChild(b);
    if (ke) D.getElementById('__dkkdSang').onclick = function () { epSang = true; };
    D.getElementById('__dkkdDongTT').onclick = function () { b.remove(); };
    D.getElementById('__dkkdLai').onclick = function () { dienLai(); };
  };
  var theoDoiLuu = async function (g, mygen, ten, ke, dienLai) {
    var het = Date.now() + 60 * 60000;
    while (Date.now() < het && mygen === gen) {
      await nghi(600);
      var w = cuaSoPhu;
      if (!w || w.closed) return false;
      try {
        var D = w.document;
        if (D.readyState !== 'complete') continue;
        ganNgheLuu(D);
        var loi = loiCong(D);
        if (epSang || (daBamLuu && D.querySelectorAll('a').length && (daLuuXong(D, g) || (!loi.length && daLuuTaiCho(w, D))))) {
          if (!epSang) { await nghi(1200); try { D = w.document; if (loiCong(D).length) continue; } catch (e3) { continue; } }
          epSang = false;
          var cu0 = D.getElementById('__dkkdTT'); if (cu0) cu0.remove();
          return true;
        }
        var sig = loi.join('|');
        if (D.__dkkdSig === undefined || sig !== D.__dkkdSig) { D.__dkkdSig = sig; veTrangThai(D, ten, ke, loi, dienLai); }
      } catch (e) { }
    }
    return false;
  };
  var chayKhoi = async function (i) {
    var mygen = ++gen;
    daBamLuu = false;
    tt[i].style.color = '#2e7d32';
    tt[i].textContent = 'đang chạy…';
    try { await chayNhom(nhom[i]); } catch (e) { tt[i].style.color = '#b00'; tt[i].textContent = 'lỗi: ' + e; return; }
    if (mygen !== gen) return;
    if (i + 1 >= nhom.length) { tt[i].textContent = 'đã điền — kiểm tra rồi tự Lưu (khối cuối)'; return; }
    tt[i].textContent = 'đã điền — kiểm tra, xác nhận rồi bấm Lưu: phần mềm sẽ tự sang khối kế tiếp';
    var luu = await theoDoiLuu(nhom[i], mygen, nhom[i].ten || nhom[i].vao_khoi, nhom[i + 1].ten || nhom[i + 1].vao_khoi, function () { chayNhom(nhom[i], true); });
    if (mygen !== gen) return;
    if (luu) { tt[i].textContent = 'đã Lưu ✓'; await chayKhoi(i + 1); }
    else { tt[i].textContent = 'chưa thấy bạn Lưu xong — khi xong bấm khối kế tiếp trong bảng'; }
  };
  var bang = document.createElement('div');
  bang.id = '__dkkdBang';
  bang.style.cssText = 'position:fixed;left:12px;bottom:12px;z-index:2147483647;max-width:430px;background:#fff;border:2px solid #2e7d32;border-radius:10px;padding:10px 12px;font:13px/1.4 Arial,sans-serif;color:#222;box-shadow:0 4px 18px rgba(0,0,0,.3)';
  bang.innerHTML = '<b>Điền ' + nhom.length + ' khối — lần lượt</b><div style="margin:4px 0;color:#555">Mỗi khối mở ở cửa sổ phụ: bạn kiểm tra các ô tô vàng, xác nhận và <b>tự bấm Lưu</b> — phần mềm thấy bạn đã Lưu thì <b>tự sang khối kế tiếp</b>. Phần mềm không tự lưu/ký/nộp/xóa. Nếu không tự sang được, bấm nút của khối kế tiếp trong bảng.</div>';
  nhom.forEach(function (g, i) {
    var dong = document.createElement('div');
    dong.style.cssText = 'margin:4px 0';
    var nut = document.createElement('button');
    nut.style.cssText = 'padding:4px 10px;margin-right:6px';
    nut.textContent = (i + 1) + '. ' + (g.ten || g.vao_khoi) + ' ▶ Điền';
    var t = document.createElement('div');
    t.style.cssText = 'color:#555;font-size:12px;margin:2px 0 0 4px';
    tt.push(t);
    nut.onclick = function () { chayKhoi(i); };
    dong.appendChild(nut); dong.appendChild(t); bang.appendChild(dong);
  });
  var dong2 = document.createElement('div');
  dong2.innerHTML = '<button id="__dkkdDongBang" style="padding:3px 8px;margin-top:6px">Đóng bảng</button>';
  bang.appendChild(dong2);
  document.body.appendChild(bang);
  document.getElementById('__dkkdDongBang').onclick = function () { gen++; bang.remove(); };
  chayKhoi(0);
})().catch(function (e) { alert('Lỗi điền dữ liệu GPKD: ' + e); });
