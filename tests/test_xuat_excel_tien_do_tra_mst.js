// Regression test: nút "Xuất Excel" khi ĐÃ tick "Tra cứu tình trạng MST" phải hiện TIẾN ĐỘ dò MST ngay
// dưới nút (tổng số MST, đã dò tới đâu, tra được bao nhiêu, đang dò MST nào, còn khoảng bao lâu) —
// người dùng yêu cầu: "làm ra hiện thông tin đang dò bao nhiêu mst và đang dò tới đâu rồi trên phần mềm
// để người dùng biết" (đã bỏ giới hạn 180s, 100 MST có thể mất ~10 phút). Chạy ĐÚNG hàm exportExcel()
// trong static/index.html với các hàm phụ giả lập.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'index.html'), 'utf8');

function layHam(ten) {
  const i = html.indexOf(`async function ${ten}(`);
  assert(i >= 0, `không thấy hàm ${ten}`);
  let j = html.indexOf('{', i), sau = 0;
  for (let k = j; k < html.length; k++) {
    if (html[k] === '{') sau++;
    else if (html[k] === '}') { sau--; if (sau === 0) return html.slice(i, k + 1); }
  }
  throw new Error('không tách được hàm ' + ten);
}

async function chay({ traMst }) {
  const toasts = [], goiApi = [];
  let hop = null, daChen = false;
  const btn = {
    innerHTML: 'Xuất Excel', disabled: false,
    parentNode: { insertBefore(el) { hop = el; daChen = true; } }, nextSibling: null,
  };
  const oNhap = {
    cLuuKetXuat: { checked: false }, cTraMst: { checked: traMst },
    tuNgay: { value: '' }, denNgay: { value: '' },
  };
  const document = {
    getElementById: (id) => oNhap[id] || null,
    createElement: () => ({ style: {}, textContent: '', innerHTML: '', className: '', daXoa: false,
                            remove() { this.daXoa = true; } }),
  };
  const tienDo = [
    { dang_chay: false, tong: 0, da_xong: 0, tra_duoc: 0, dang_tra: '', con_lai_giay: 0 },
    { dang_chay: true, tong: 10, da_xong: 3, tra_duoc: 2, dang_tra: '0312345678', con_lai_giay: 46 },
    { dang_chay: true, tong: 10, da_xong: 9, tra_duoc: 8, dang_tra: '0319999999', con_lai_giay: 130 },
  ];
  const cuoi = { dang_chay: false, tong: 10, da_xong: 10, tra_duoc: 9, dang_tra: '', con_lai_giay: 0 };
  let daXong = false;
  const noiDungHop = [];
  const api = async (p) => {
    goiApi.push(p);
    if (daXong) return cuoi;
    const td = tienDo.shift() || tienDo[tienDo.length - 1] || cuoi;
    return td;
  };
  const fetch = () => new Promise((res) => setTimeout(() => {
    daXong = true;
    res({ ok: true, headers: { get: () => null } });
  }, 3300));
  const theoDoi = setInterval(() => { if (hop && hop.innerHTML) noiDungHop.push(hop.innerHTML); }, 200);
  const fn = new Function('document', 'api', 'fetch', 'toast', 'fmtDate', 'xuatFile', 'current',
    'loadCompanies', 'companies', 'renderFetchErrorBanner',
    layHam('exportExcel') + '\nreturn exportExcel;')(
    document, api, fetch, (m, k) => toasts.push([m, k]), (x) => x, async () => {}, 1,
    async () => {}, [], () => {});
  await fn(btn);
  clearInterval(theoDoi);
  const soGoiKhiXong = goiApi.length;
  await new Promise((r) => setTimeout(r, 1500));
  return { toasts, goiApi, hop, daChen, noiDungHop, btn, soGoiKhiXong };
}

(async () => {
  // ===== 1: đã tick tra MST -> hộp tiến độ hiện dưới nút, cập nhật đúng số liệu, xong thì tự xoá và
  // ngừng hỏi tiến độ; báo tổng kết tra được bao nhiêu MST. =====
  const kq = await chay({ traMst: true });
  assert(kq.daChen, 'Phải chèn hộp tiến độ ngay dưới nút Xuất Excel');
  const coSo = kq.noiDungHop.find((h) => h.includes('3/10'));
  assert(coSo && coSo.includes('0312345678') && coSo.includes('tra được 2') && coSo.includes('~46 giây'),
    'Hộp tiến độ phải hiện đã dò/tổng, MST đang dò, số tra được, thời gian còn lại — got ' + kq.noiDungHop.join(' || '));
  assert(kq.noiDungHop.some((h) => h.includes('9/10') && h.includes('~3 phút')),
    'Còn >= 60 giây phải hiện theo phút — got ' + kq.noiDungHop.join(' || '));
  assert(kq.hop.daXoa, 'Xuất Excel xong phải xoá hộp tiến độ');
  assert.strictEqual(kq.goiApi.length, kq.soGoiKhiXong, 'Xuất xong phải ngừng hỏi tiến độ (clearInterval)');
  assert.strictEqual(kq.btn.disabled, false);
  assert(kq.toasts.some(([m]) => m.includes('tra được 9/10')), 'Phải báo tổng kết số MST tra được');
  console.log('PASS 1: tick tra MST -> hiện tiến độ (đã dò/tổng, MST đang dò, tra được, còn bao lâu), xong tự '
    + 'xoá hộp, ngừng hỏi, báo tổng kết.');

  // ===== 2: KHÔNG tick tra MST -> không hiện hộp tiến độ, không hỏi tiến độ. =====
  const kq2 = await chay({ traMst: false });
  assert(!kq2.daChen && kq2.goiApi.length === 0, 'Không tick tra MST thì không hiện/không hỏi tiến độ');
  console.log('PASS 2: không tick tra MST -> không hiện tiến độ.');
  console.log('\nALL DONE');
})().catch((e) => { console.error(e); process.exit(1); });
