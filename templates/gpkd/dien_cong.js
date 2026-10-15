/* Nút bookmark "Điền dữ liệu GPKD": mở cửa sổ phụ, tự vào đúng khối dữ liệu của cổng (bấm menu, bấm "Tạo mới" nếu cần) rồi ĐIỀN các ô theo dữ liệu đã soạn trong phần mềm.
   CHỈ điều hướng và điền ô — không đăng nhập, không bấm Lưu/Ký/Nộp/Xóa, không đụng ô "Tôi không phải người máy" (reCAPTCHA) và nút "Đối chiếu CSDLQG": các bước đó người dùng tự làm. Có nút Hoàn tác. */
(async function () {
  var BAN = '__BAN_NUT__';
  var sach = function (s) { return (s || '').replace(/\s+/g, ' ').trim(); };
  var chuan = function (s) { return sach(s).normalize('NFC').toLowerCase().replace(/[:*]+$/, '').trim(); };
  var nghi = function (ms) { return new Promise(function (ok) { setTimeout(ok, ms); }); };
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
  var chayNhom = async function (g) {
    var D = document;
    var w = null;
    if (g.vao_khoi && (!coTruong(document, g) || g.truong.some(function (t) { return t.chuoi; }))) {
      w = window.open('', '_dkkd_dien', 'width=1250,height=900,scrollbars=yes,resizable=yes');
      try { if (w && (w.location.href === 'about:blank' || !w.document.querySelector('a'))) { w.location.href = location.href; } } catch (e0) { }
      if (!w) { alert('Chrome đang chặn cửa sổ bật lên. Bấm biểu tượng chặn ở thanh địa chỉ → "Luôn cho phép" rồi bấm lại nút này.'); return; }
      var menuOk = await cho(w, function (d) { return !!timBam(d, g.vao_khoi, 'a'); }, 40);
      if (!menuOk) { alert('Không thấy mục "' + g.vao_khoi + '" trong menu KHỐI DỮ LIỆU của cổng (có thể chưa đăng nhập hoặc đang ở trang khác). Hãy mở hồ sơ rồi bấm lại.'); return; }
      var mk = timBam(w.document, g.vao_khoi, 'a');
      var vaoMenu = await bamVaCho(w, mk, function (d) { return true; });
      if (!vaoMenu) { alert('Chưa mở được khối "' + g.vao_khoi + '". Bạn tự bấm mục đó trong menu rồi bấm lại nút này.'); return; }
      if (g.tao_moi && !coTruong(w.document, g)) {
        var nut = timBam(w.document, 'Tạo mới');
        if (!nut) { alert('Không thấy nút "Tạo mới" trong khối "' + g.vao_khoi + '". Bạn tự bấm "Tạo mới" rồi bấm lại nút này.'); try { w.focus(); } catch (e) { } return; }
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
    var goc = function (x) { return chuan(x).replace(/^(thành phố|tp\.?|tỉnh|thị xã|thị trấn|quận|huyện|phường|xã|đặc khu)\s+/, '').trim(); };
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
      var op = timOption(o, v);
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
    var xuLy = function (t, dsO) {
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
      while (chay < 14) {
        var re2; try { re2 = new RegExp(tc.nhan, 'i'); } catch (e) { re2 = null; }
        var mC = re2 && dsC.filter(function (x) { return re2.test(x.nhan) && x.os.some(function (o) { return o.tagName === 'SELECT'; }); })[0];
        if (mC && mC.os.some(function (o) { return o.tagName === 'SELECT' && o.options.length > 1; })) break;
        await nghi(700);
        dsC = quet(D);
        chay++;
      }
      selMoi = xuLy(tc, dsC);
      if (selMoi && !winDich.closed) {
        var tai = await settle(winDich, selMoi);
        try { D = winDich.document; } catch (e) { }
        cu.forEach(function (x) { if (x.r) vang(tra(x.r)); });
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
    if (khong.length) h += '<div style="margin-top:6px;color:#b45309"><b>Chưa điền được (nhập tay):</b><br>' + khong.map(function (x) { return '• ' + x.replace(/</g, '&lt;'); }).join('<br>') + '</div>';
    h += '<div style="margin-top:8px"><button id="__dkkdHoan" style="padding:4px 10px;margin-right:6px">Hoàn tác</button><button id="__dkkdDong" style="padding:4px 10px">Đóng</button> <span style="color:#888;font-size:11px">bản ' + BAN + '</span></div>';
    if (w) cuaSoPhu = w;
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
  var daBamLuu = false;
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
  var theoDoiLuu = async function (g, mygen) {
    var het = Date.now() + 60 * 60000;
    daBamLuu = false;
    while (Date.now() < het && mygen === gen) {
      await nghi(600);
      var w = cuaSoPhu;
      if (!w || w.closed) return false;
      try {
        var D = w.document;
        if (D.readyState !== 'complete') continue;
        [].slice.call(D.querySelectorAll('input[type=button],input[type=submit],button,a')).forEach(function (e) {
          if (!e.__dkkdL && chuan(tenNut(e)) === 'lưu') { e.__dkkdL = 1; e.addEventListener('click', function () { daBamLuu = true; }, true); }
        });
        if (daBamLuu && daLuuXong(D, g) && D.querySelectorAll('a').length) { await nghi(500); return true; }
      } catch (e) { }
    }
    return false;
  };
  var chayKhoi = async function (i) {
    var mygen = ++gen;
    tt[i].style.color = '#2e7d32';
    tt[i].textContent = 'đang chạy…';
    try { await chayNhom(nhom[i]); } catch (e) { tt[i].style.color = '#b00'; tt[i].textContent = 'lỗi: ' + e; return; }
    if (mygen !== gen) return;
    if (i + 1 >= nhom.length) { tt[i].textContent = 'đã điền — kiểm tra rồi tự Lưu (khối cuối)'; return; }
    tt[i].textContent = 'đã điền — kiểm tra, xác nhận rồi bấm Lưu: phần mềm sẽ tự sang khối kế tiếp';
    var luu = await theoDoiLuu(nhom[i], mygen);
    if (mygen !== gen) return;
    if (luu) { tt[i].textContent = 'đã Lưu ✓'; await chayKhoi(i + 1); }
    else { tt[i].textContent = 'chưa thấy bạn Lưu xong — khi xong bấm khối kế tiếp trong bảng'; }
  };
  var bang = document.createElement('div');
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
