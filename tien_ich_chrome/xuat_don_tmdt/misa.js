// MISA meInvoice (trang "HĐ khởi tạo từ máy tính tiền"): tự bấm nút XUẤT KHẨU danh sách hoá đơn ra Excel; phần mềm kế toán tự đọc file tải về để lưu SỐ HOÁ ĐƠN.
async function __ketoanMisa(tuDong){
const sl=ms=>new Promise(r=>setTimeout(r,ms));
const vis=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'};
const loi=chu=>{__ketoanBao(chu,'#b00020');alert('Phần mềm kế toán — Lấy số hoá đơn\n\n'+chu)};
const dkClick=e=>e.closest('button,a,[role=button],[class*=btn]')||e;
const kich=e=>{const r=e.getBoundingClientRect(),o={bubbles:true,cancelable:true,view:window,clientX:r.left+r.width/2,clientY:r.top+r.height/2,button:0};
  for(const t of ['pointerdown','mousedown','pointerup','mouseup','click']){try{e.dispatchEvent(new (t.startsWith('pointer')&&window.PointerEvent?PointerEvent:MouseEvent)(t,o))}catch(_){}}};
__ketoanBao('đang chờ danh sách hoá đơn MISA tải xong…');
let doi=0;while(doi<60&&![...document.querySelectorAll('td,div,span')].some(e=>e.children.length===0&&/^\d{6,8}$/.test((e.innerText||'').trim())&&vis(e))){await sl(1000);doi++}
if(doi>=60){loi('Không thấy danh sách hoá đơn — hãy mở menu "Hóa đơn từ máy tính tiền > HĐ từ máy tính tiền" rồi bấm nút ▶ Lấy số HĐ.');return}
// 1) nút xuất khẩu theo nhãn/biểu tượng Excel
const bam=[];
document.querySelectorAll('[title],[aria-label],[data-original-title]').forEach(e=>{const t=(e.getAttribute('title')||e.getAttribute('aria-label')||e.getAttribute('data-original-title')||'');if(/xuất khẩu|export|excel/i.test(t)&&vis(e))bam.push(e)});
document.querySelectorAll('img[src*=excel i],img[src*=xls i],[class*=excel i],[class*=xls i],[class*=export i]').forEach(e=>{if(vis(e))bam.push(e)});
// 2) dự phòng theo vị trí: các nút chỉ có biểu tượng (không chữ) bên phải thanh lọc, cùng hàng với nút "Lọc" — Excel là nút thứ 2 sau nút làm mới
if(!bam.length){const loc=[...document.querySelectorAll('button,div,span')].find(e=>vis(e)&&e.children.length<=2&&/^Lọc$/.test((e.innerText||'').trim()));
  if(loc){const y=loc.getBoundingClientRect().top,x0=loc.getBoundingClientRect().right;
    const ic=[...document.querySelectorAll('button,[role=button],a,[class*=btn]')].filter(e=>vis(e)&&!(e.innerText||'').trim()&&Math.abs(e.getBoundingClientRect().top-y)<40&&e.getBoundingClientRect().left>x0+300&&e.querySelector('img,svg,i')).sort((a,b)=>a.getBoundingClientRect().left-b.getBoundingClientRect().left);
    if(ic.length>=3)bam.push(ic[1])}}
if(!bam.length){const toolbar=[...document.querySelectorAll('button,[role=button],a,[class*=btn]')].filter(e=>vis(e)&&e.getBoundingClientRect().top<400).map(e=>e.tagName.toLowerCase()+'.'+(e.className||'').toString().split(' ').slice(0,3).join('.')+'['+(e.innerText||e.title||'').trim().slice(0,20)+']@'+Math.round(e.getBoundingClientRect().left)+','+Math.round(e.getBoundingClientRect().top));
  try{const t=document.createElement('textarea');t.value=toolbar.join('\n');document.body.appendChild(t);t.select();document.execCommand('copy');t.remove()}catch(e){}
  loi('Chưa tìm thấy nút Xuất khẩu (biểu tượng Excel) trên thanh công cụ.\nĐã COPY sẵn danh sách nút — dán (Ctrl+V) cho người hỗ trợ để chỉnh. Bạn có thể tự bấm biểu tượng Excel để xuất danh sách.');return}
const nut=dkClick(bam[0]);kich(nut);__ketoanBao('đã bấm nút xuất khẩu danh sách hoá đơn…');await sl(1500);
// 3) nếu hiện menu/hộp lựa chọn: chọn mục xuất danh sách / Excel
const muc=[...document.querySelectorAll('li,div,span,a,button,[role=menuitem]')].filter(e=>vis(e)&&e.children.length===0&&/^(Xuất khẩu|Xuất Excel|Xuất danh sách|Xuất file|Excel|Tải về|Đồng ý|Xuất)$/i.test((e.innerText||'').trim()));
if(muc.length){kich(dkClick(muc[0]));__ketoanBao('đã chọn "'+(muc[0].innerText||'').trim()+'" — file đang tải vào Downloads','#2e7d32')}
else __ketoanBao('đã bấm xuất khẩu — file đang tải vào Downloads (nếu chưa thấy, tự chọn mục xuất danh sách)','#2e7d32');
}
