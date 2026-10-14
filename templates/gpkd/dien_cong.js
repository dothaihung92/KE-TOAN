/* Nút bookmark "Điền dữ liệu GPKD": điền các ô trên trang đang mở của cổng đăng ký doanh nghiệp theo dữ liệu đã soạn trong phần mềm.
   CHỈ điền ô — không bấm Lưu/Ký/Nộp, không đăng nhập, không gửi gì lên cổng. Ô nào không chắc thì để trống và báo lại. Có nút Hoàn tác. */
(async function () {
  var BAN = '__BAN_NUT__';
  var sach = function (s) { return (s || '').replace(/\s+/g, ' ').trim(); };
  var chuan = function (s) { return sach(s).normalize('NFC').toLowerCase().replace(/[:*]+$/, '').trim(); };
  var txt = null;
  try { txt = await navigator.clipboard.readText(); } catch (e) { txt = null; }
  var dl = null;
  try { dl = JSON.parse(txt); } catch (e) { dl = null; }
  if (!dl || !dl.dkkd_dien || !dl.truong) {
    var tay = prompt('Không đọc được dữ liệu từ clipboard. Hãy bấm "Copy dữ liệu điền" trong phần mềm rồi dán (Ctrl+V) vào đây:', '');
    try { dl = JSON.parse(tay); } catch (e) { dl = null; }
  }
  if (!dl || !dl.dkkd_dien || !dl.truong) { alert('Chưa có dữ liệu điền. Vào phần mềm → Soạn hồ sơ → bấm "Copy dữ liệu điền", rồi bấm lại nút này.'); return; }

  var dsO = [];
  var laO = function (e) { var t = (e.type || '').toLowerCase(); return /^(INPUT|SELECT|TEXTAREA)$/.test(e.tagName) && !/^(hidden|button|submit|image|password|reset|checkbox|radio|file)$/.test(t); };
  var layO = function (node) { return /^(INPUT|SELECT|TEXTAREA)$/.test(node.tagName) ? (laO(node) ? [node] : []) : [].slice.call(node.querySelectorAll('input,select,textarea')).filter(laO); };
  document.querySelectorAll('tr').forEach(function (r) {
    var c = [].slice.call(r.children).filter(function (x) { return x.tagName === 'TD' || x.tagName === 'TH'; });
    var cap = function (a, b) { if (!c[a] || !c[b]) return; if (layO(c[a]).length) return; var nhan = chuan(c[a].innerText); var os = layO(c[b]); if (nhan && nhan.length < 160 && os.length) dsO.push({ nhan: nhan, os: os }); };
    if (c.length === 4) { cap(0, 1); cap(2, 3); } else if (c.length >= 2) { cap(0, c.length - 1); }
  });
  document.querySelectorAll('label[for]').forEach(function (l) {
    var e = document.getElementById(l.getAttribute('for'));
    if (e && laO(e)) dsO.push({ nhan: chuan(l.innerText), os: [e] });
  });

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
    var op = [].slice.call(o.options).filter(function (x) { return chuan(x.text) === vv; })[0] || [].slice.call(o.options).filter(function (x) { return chuan(x.text).indexOf(vv) === 0 && vv; })[0];
    if (!op) return false;
    cu.push({ o: o, v: o.value, s: o.style.cssText });
    o.value = op.value;
    o.style.background = '#fff3a0';
    o.style.outline = '2px solid #e6a700';
    return true;
  };
  dl.truong.forEach(function (t) {
    var re;
    try { re = new RegExp(t.nhan, 'i'); } catch (e) { return; }
    var tim = dsO.filter(function (x) { return re.test(x.nhan) && daDung.indexOf(x) < 0; });
    var m = tim.filter(function (x) { return x.os.some(function (o) { return !o.disabled && !o.readOnly; }); })[0];
    if (!m) { khong.push(t.ten + (tim.length ? ' (ô bị khóa, không sửa được)' : ' (không thấy ô)')); return; }
    daDung.push(m);
    var os = m.os.filter(function (o) { return !o.disabled && !o.readOnly; });
    var sel = os.filter(function (o) { return o.tagName === 'SELECT'; });
    var inp = os.filter(function (o) { return o.tagName !== 'SELECT'; });
    var v = String(t.gia_tri);
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
    if (sel.length && !inp.length) { if (chonSelect(sel[0], v)) daDien.push(t.ten); else khong.push(t.ten + ' (không có lựa chọn "' + v + '")'); return; }
    if (inp.length) { gan(inp[0], v); daDien.push(t.ten); return; }
    khong.push(t.ten + ' (ô không điền được)');
  });

  var hop = document.createElement('div');
  hop.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:2147483647;max-width:420px;background:#fff;border:2px solid #e6a700;border-radius:10px;padding:10px 12px;font:13px/1.4 Arial,sans-serif;color:#222;box-shadow:0 4px 18px rgba(0,0,0,.3)';
  var h = '<b>Đã điền ' + daDien.length + ' ô</b> (tô vàng) — <b>hãy kiểm tra từng ô</b> rồi tự bấm Lưu. Phần mềm không tự lưu, không ký, không nộp.';
  if (khong.length) h += '<div style="margin-top:6px;color:#b45309"><b>Chưa điền được (nhập tay):</b><br>' + khong.map(function (x) { return '• ' + x.replace(/</g, '&lt;'); }).join('<br>') + '</div>';
  h += '<div style="margin-top:8px"><button id="__dkkdHoan" style="padding:4px 10px;margin-right:6px">Hoàn tác</button><button id="__dkkdDong" style="padding:4px 10px">Đóng</button> <span style="color:#888;font-size:11px">bản ' + BAN + '</span></div>';
  hop.innerHTML = h;
  document.body.appendChild(hop);
  document.getElementById('__dkkdDong').onclick = function () { hop.remove(); };
  document.getElementById('__dkkdHoan').onclick = function () {
    cu.forEach(function (x) { x.o.value = x.v; x.o.style.cssText = x.s; });
    hop.remove();
  };
})().catch(function (e) { alert('Lỗi điền dữ liệu GPKD: ' + e); });
