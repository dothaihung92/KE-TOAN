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
  var coTruong = function (D) {
    var ds = quet(D);
    return dl.truong.some(function (t) { var re; try { re = new RegExp(t.nhan, 'i'); } catch (e) { return false; } return ds.some(function (x) { return re.test(x.nhan); }); });
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

  var D = document;
  var w = null;
  if (dl.vao_khoi && !coTruong(document)) {
    w = window.open(location.href, '_dkkd_dien', 'width=1250,height=900,scrollbars=yes,resizable=yes');
    if (!w) { alert('Chrome đang chặn cửa sổ bật lên. Bấm biểu tượng chặn ở thanh địa chỉ → "Luôn cho phép" rồi bấm lại nút này.'); return; }
    var menuOk = await cho(w, function (d) { return !!timBam(d, dl.vao_khoi, 'a'); }, 40);
    if (!menuOk) { alert('Không thấy mục "' + dl.vao_khoi + '" trong menu KHỐI DỮ LIỆU của cổng (có thể chưa đăng nhập hoặc đang ở trang khác). Hãy mở hồ sơ rồi bấm lại.'); return; }
    var mk = timBam(w.document, dl.vao_khoi, 'a');
    var vaoMenu = await bamVaCho(w, mk, function (d) { return true; });
    if (!vaoMenu) { alert('Chưa mở được khối "' + dl.vao_khoi + '". Bạn tự bấm mục đó trong menu rồi bấm lại nút này.'); return; }
    if (dl.tao_moi && !coTruong(w.document)) {
      var nut = timBam(w.document, 'Tạo mới');
      if (!nut) { alert('Không thấy nút "Tạo mới" trong khối "' + dl.vao_khoi + '". Bạn tự bấm "Tạo mới" rồi bấm lại nút này.'); try { w.focus(); } catch (e) { } return; }
      var vaoForm = await bamVaCho(w, nut, function (d) { return true; });
      if (!vaoForm) { alert('Chưa mở được trang nhập. Bạn tự bấm "Tạo mới" rồi bấm lại nút này.'); try { w.focus(); } catch (e) { } return; }
    }
    D = w.document;
    await nghi(600);
    try { w.focus(); } catch (e) { }
  }

  var dsO = quet(D);
  var daDung = [];
  var cu = [];
  var daDien = [];
  var khong = [];
  var gan = function (o, v) {
    cu.push({ o: o, v: o.value, s: o.style.cssText });
    o.value = v;
    o.dispatchEvent(new Event('input', { bubbles: true }));
    o.style.background = '#fff3a0';
    o.style.outline = '2px solid #e6a700';
  };
  var chonSelect = function (o, v) {
    var vv = chuan(v);
    var op = [].slice.call(o.options).filter(function (x) { return chuan(x.text) === vv; })[0] || [].slice.call(o.options).filter(function (x) { return vv && chuan(x.text).indexOf(vv) === 0; })[0];
    if (!op) return false;
    cu.push({ o: o, v: o.value, s: o.style.cssText });
    o.value = op.value;
    o.style.background = '#fff3a0';
    o.style.outline = '2px solid #e6a700';
    return true;
  };
  var chonRadio = function (rs, v) {
    var vv = chuan(v);
    var r = rs.filter(function (x) { return x.nhan === vv; })[0];
    if (!r || r.el.disabled) return false;
    var truoc = rs.filter(function (x) { return x.el.checked; })[0];
    cu.push({ radio: r.el, truoc: truoc ? truoc.el : null });
    r.el.checked = true;
    r.el.parentNode.style.background = '#fff3a0';
    return true;
  };
  dl.truong.forEach(function (t) {
    var re;
    try { re = new RegExp(t.nhan, 'i'); } catch (e) { return; }
    var tim = dsO.filter(function (x) { return re.test(x.nhan) && daDung.indexOf(x) < 0; });
    var m = tim.filter(function (x) { return x.rs.length || x.os.some(function (o) { return !o.disabled && !o.readOnly; }); })[0];
    if (!m) { khong.push(t.ten + (tim.length ? ' (ô bị khóa, không sửa được)' : ' (không thấy ô)')); return; }
    daDung.push(m);
    var v = String(t.gia_tri);
    if (m.rs.length && !m.os.length) { if (chonRadio(m.rs, v)) daDien.push(t.ten); else khong.push(t.ten + ' (không có lựa chọn "' + v + '")'); return; }
    var os = m.os.filter(function (o) { return !o.disabled && !o.readOnly; });
    var sel = os.filter(function (o) { return o.tagName === 'SELECT'; });
    var inp = os.filter(function (o) { return o.tagName !== 'SELECT'; });
    if (sel.length && inp.length && t.tien_to) {
      var best = null;
      sel.forEach(function (s) { [].slice.call(s.options).forEach(function (op) { var p = chuan(op.text); if (p && chuan(v).indexOf(p + ' ') === 0 && (!best || p.length > best.p.length)) best = { s: s, op: op, p: p }; }); });
      if (best) {
        cu.push({ o: best.s, v: best.s.value, s: best.s.style.cssText });
        best.s.value = best.op.value;
        best.s.style.background = '#fff3a0';
        gan(inp[0], sach(v).slice(best.p.length).trim());
        daDien.push(t.ten);
        return;
      }
    }
    if (sel.length && !inp.length) { if (chonSelect(sel[0], v)) daDien.push(t.ten); else khong.push(t.ten + ' (không có lựa chọn "' + v + '" — chọn tay)'); return; }
    if (inp.length) { gan(inp[0], v); daDien.push(t.ten); return; }
    khong.push(t.ten + ' (ô không điền được)');
  });

  var huong = '';
  if (!daDien.length) {
    var khoiCan = [];
    dl.truong.forEach(function (t) { if (t.khoi && khoiCan.indexOf(t.khoi) < 0) khoiCan.push(t.khoi); });
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
  hop.innerHTML = h;
  D.body.appendChild(hop);
  D.getElementById('__dkkdDong').onclick = function () { hop.remove(); };
  D.getElementById('__dkkdHoan').onclick = function () {
    cu.forEach(function (x) {
      if (x.radio) { x.radio.checked = false; if (x.truoc) x.truoc.checked = true; x.radio.parentNode.style.background = ''; }
      else { x.o.value = x.v; x.o.style.cssText = x.s; }
    });
    hop.remove();
  };
})().catch(function (e) { alert('Lỗi điền dữ liệu GPKD: ' + e); });
