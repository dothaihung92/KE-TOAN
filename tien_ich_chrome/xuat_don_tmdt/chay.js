// Tự bấm Xuất báo cáo đơn hàng trên trang người bán (dùng chung cho tiện ích Chrome và nút dấu trang).
// Chỉ bấm các nút trên trang của chính shop: Tất cả -> Xuất -> (đặt khoảng ngày) -> Xuất -> Lịch sử Xuất Báo cáo -> Tải về ĐÚNG báo cáo vừa tạo.
function __ketoanBao(chu,mau){      // thanh trạng thái nhỏ trên trang: cho người dùng thấy tiện ích đang ở bước nào / vì sao dừng
  let b=document.getElementById('ketoan-bao');
  if(!b){b=document.createElement('div');b.id='ketoan-bao';b.style.cssText='position:fixed;left:12px;bottom:12px;z-index:2147483647;max-width:420px;padding:8px 12px;border-radius:8px;font:13px/1.4 Arial,sans-serif;color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.35)';(document.body||document.documentElement).appendChild(b)}
  b.style.background=mau||'#2e5c8a';b.textContent='Kế toán: '+chu;
}
async function __ketoanXuat(tuDong,thamSo){
__ketoanBao('đã nhận lệnh xuất đơn, đang tìm nút Xuất…');
const sl=ms=>new Promise(r=>setTimeout(r,ms));
const vis=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'};
const hop=()=>{const d=[...document.querySelectorAll('[role=dialog],.eds-modal,.shopee-modal,.ant-modal,.arco-modal,.next-dialog,.modal')].filter(vis);return d.length?d[d.length-1]:null};
const bam=(re,dlg)=>{let g=document;if(dlg){const h=hop();if(h)g=h}let ds=[...g.querySelectorAll('button,a,[role=button]')].filter(vis);if(dlg&&g===document)ds.reverse();
 for(const e of ds){const t=(e.innerText||'').trim();if(t&&t.length<40&&re.test(t)&&!e.disabled){e.click();return t}}return ''};
const loi=(chu)=>{__ketoanBao(chu,'#b00020');alert('Phần mềm kế toán — Xuất đơn hàng\n\n'+chu)};
const SAN={'banhang.shopee.vn':'https://banhang.shopee.vn/portal/sale/order','seller-vn.tiktok.com':'https://seller-vn.tiktok.com/order','sellercenter.lazada.vn':'https://sellercenter.lazada.vn/apps/order/list'};
const host=location.host,url=SAN[host];
if(!url){loi('Hãy mở trang Quản lý đơn hàng của Shopee / TikTok Shop / Lazada rồi bấm lại.');return}
if(!location.href.startsWith(url)){if(tuDong){__ketoanBao('đang ở '+location.pathname+' — hãy vào Quản lý đơn hàng > Tất cả rồi bấm nút ▶ Xuất đơn','#b00020');return}location.href=url;alert('Đã chuyển tới trang Quản lý đơn hàng — chờ trang tải xong rồi bấm lại.');return}
const RX=/^(Xuất|Xuất file|Xuất dữ liệu|Export|Xuất đơn hàng)$/;
// trang tải chậm: chờ nút Xuất tối đa 40 giây
let doi=0;while(tuDong&&doi<40&&![...document.querySelectorAll('button,a,[role=button]')].some(e=>vis(e)&&RX.test((e.innerText||'').trim()))){await sl(1000);doi++}
if(host==='banhang.shopee.vn'&&bam(/^Tất cả$/))await sl(2000);
if(!bam(RX)){loi('Không thấy nút Xuất trên trang — hãy tự bấm Xuất.');return}
__ketoanBao('đã bấm Xuất, chờ hộp chọn ngày…');
await sl(2500);
// ---- khoảng ngày: đọc 2 ô ngày trong hộp (định dạng yyyy/mm/dd), nếu khác ngày người dùng chọn trong phần mềm thì gõ lại
const lay=()=>{const h=hop();if(!h)return null;const v=[...h.querySelectorAll('input')].map(i=>i.value).filter(x=>/\d{4}\D\d{2}\D\d{2}/.test(x));
  if(v.length>=2)return [v[0],v[1]];const t=(h.innerText||'').match(/(\d{4})\D(\d{2})\D(\d{2})\s*[–-]\s*(\d{4})\D(\d{2})\D(\d{2})/);return t?[t[1]+'/'+t[2]+'/'+t[3],t[4]+'/'+t[5]+'/'+t[6]]:null};
const chuan=s=>(s||'').replace(/\D/g,'').slice(0,8);          // yyyymmdd
const m=/(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})/.exec(thamSo||'');       // khoảng ngày người dùng đã chọn trong phần mềm kế toán
let can=null;
if(m){can=[m[1]+m[2]+m[3],m[4]+m[5]+m[6]];
  const dat=(i,gt)=>{const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;i.focus();setter.call(i,gt);
    i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}));
    i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',keyCode:13,bubbles:true}));i.dispatchEvent(new Event('blur',{bubbles:true}))};
  let cur=lay();
  if(cur&&(chuan(cur[0])!==can[0]||chuan(cur[1])!==can[1])){
    const h=hop(),ins=[...h.querySelectorAll('input')].filter(x=>/\d{4}\D\d{2}\D\d{2}/.test(x.value));
    if(ins.length>=2){__ketoanBao('đang đặt khoảng ngày '+m[3]+'/'+m[2]+'/'+m[1]+' – '+m[6]+'/'+m[5]+'/'+m[4]+'…');
      dat(ins[0],m[1]+'/'+m[2]+'/'+m[3]);await sl(600);dat(ins[1],m[4]+'/'+m[5]+'/'+m[6]);await sl(900);cur=lay()}
  }
  if(!cur||chuan(cur[0])!==can[0]||chuan(cur[1])!==can[1]){      // không đặt được -> chỉ tiếp tục khi khoảng sàn đang chọn BAO TRÙM khoảng cần lấy
    const bao=cur&&chuan(cur[0])<=can[0]&&chuan(cur[1])>=can[1];
    if(!bao){loi('Hộp Xuất đang chọn '+(cur?cur[0]+' – '+cur[1]:'(không đọc được)')+', khác khoảng bạn chọn ('+m[3]+'/'+m[2]+'/'+m[1]+' – '+m[6]+'/'+m[5]+'/'+m[4]+').\nHãy tự chọn Khoảng thời gian trong hộp, bấm Xuất, rồi vào Lịch sử Xuất Báo cáo → Tải về.');return}
    __ketoanBao('khoảng sàn đang chọn '+cur[0]+' – '+cur[1]+' bao trùm khoảng cần lấy — phần mềm sẽ lọc đúng ngày');
  }
}else if(!tuDong){const c=lay();if(!confirm('Khoảng thời gian trên sàn: '+(c?c[0]+' – '+c[1]:'(mặc định của sàn)')+'\n\nOK = xuất với khoảng này. Cancel = bạn tự chọn lại ngày rồi tự bấm Xuất.'))return}
const dang=lay();                                                              // khoảng thật sự sẽ xuất -> tên báo cáo mong đợi: Order.all.yyyymmdd_yyyymmdd
const ten=dang?'Order.all.'+chuan(dang[0])+'_'+chuan(dang[1]):'';
if(!bam(/^(Xuất|Export|Xác nhận|Confirm|OK|Tạo báo cáo)$/,true)){loi('Không thấy nút Xuất trong hộp chọn ngày — hãy tự bấm.');return}
__ketoanBao('đã bấm Xuất trong hộp'+(ten?' ('+ten+')':'')+', chờ báo cáo được tạo…');
await sl(4000);bam(/^(Lịch sử Xuất Báo cáo|Lịch sử xuất|Export History)$/);
// ---- tải ĐÚNG báo cáo: hàng có tên khớp và đã có nút Tải về (hàng "Đang được xử lý" thì chờ)
const tim=()=>{const nut=[...document.querySelectorAll('button,a,[role=button]')].filter(e=>vis(e)&&/^(Tải về|Tải xuống|Download)$/.test((e.innerText||'').trim()));
  for(const n of nut){let p=n;for(let k=0;k<6&&p;k++){p=p.parentElement;if(!p)break;const t=(p.innerText||'');
      if(/Order\.\S*?\d{8}_\d{8}/.test(t)){if(t.includes(ten)&&(t.match(/Order\.\S*?\d{8}_\d{8}/g)||[]).length===1)return n;break}}}return null};
for(let i=0;i<30;i++){await sl(3000);
  if(!ten){const t=bam(/^(Tải về|Tải xuống|Download)$/,true)||bam(/^(Tải về|Tải xuống|Download)$/);if(t){__ketoanBao('đã bấm Tải về — file đang tải vào Downloads','#2e7d32');alert('Đã bấm Tải về — file đơn hàng đang tải vào thư mục Downloads. Phần mềm kế toán sẽ tự nhận file.');return}continue}
  const n=tim();if(n){n.click();__ketoanBao('đã bấm Tải về báo cáo '+ten+' — file đang tải vào Downloads','#2e7d32');alert('Đã bấm Tải về báo cáo '+ten+' — file đang tải vào thư mục Downloads. Phần mềm kế toán sẽ tự nhận file.');return}}
loi('Báo cáo '+ten+' chưa sẵn sàng sau ~90 giây — chờ thêm rồi tự bấm Tải về ĐÚNG báo cáo '+ten+' trong Lịch sử Xuất Báo cáo.');
}
