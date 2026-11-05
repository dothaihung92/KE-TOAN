// Tự bấm Xuất báo cáo đơn hàng trên trang người bán (dùng chung cho tiện ích Chrome và nút dấu trang).
// Chỉ bấm các nút trên trang của chính shop: Tất cả -> Xuất -> (hỏi lại khoảng ngày) -> Xuất -> Lịch sử Xuất Báo cáo -> Tải về.
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
const SAN={'banhang.shopee.vn':'https://banhang.shopee.vn/portal/sale/order','seller-vn.tiktok.com':'https://seller-vn.tiktok.com/order','sellercenter.lazada.vn':'https://sellercenter.lazada.vn/apps/order/list'};
const host=location.host,url=SAN[host];
if(!url){__ketoanBao('trang này không phải trang đơn hàng Shopee/TikTok/Lazada','#b00020');alert('Xuất đơn TMĐT: hãy mở trang Quản lý đơn hàng của Shopee / TikTok Shop / Lazada rồi bấm lại.');return}
if(!location.href.startsWith(url)){if(tuDong){__ketoanBao('đang ở '+location.pathname+' — hãy vào Quản lý đơn hàng > Tất cả rồi bấm nút ▶ Xuất đơn','#b00020');return}location.href=url;alert('Đã chuyển tới trang Quản lý đơn hàng — chờ trang tải xong rồi bấm lại.');return}
const RX=/^(Xuất|Xuất file|Xuất dữ liệu|Export|Xuất đơn hàng)$/;
// trang tải chậm: chờ nút Xuất tối đa 40 giây
let doi=0;while(tuDong&&doi<40&&![...document.querySelectorAll('button,a,[role=button]')].some(e=>vis(e)&&RX.test((e.innerText||'').trim()))){await sl(1000);doi++}
if(host==='banhang.shopee.vn'&&bam(/^Tất cả$/))await sl(2000);
const x=bam(RX);
if(!x){__ketoanBao('không thấy nút Xuất trên trang — hãy tự bấm Xuất','#b00020');alert('Không thấy nút Xuất trên trang — hãy tự bấm Xuất.');return}
__ketoanBao('đã bấm Xuất, chờ hộp chọn ngày…');
await sl(2500);const h=hop();
const kt=h?([...h.querySelectorAll('input')].map(i=>i.value).filter(Boolean).join(' – ')||((h.innerText||'').match(/\d{4}\/\d{2}\/\d{2}\s*[–-]\s*\d{4}\/\d{2}\/\d{2}/)||[''])[0]):'';
const m=/(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})/.exec(thamSo||'');       // khoảng ngày người dùng đã chọn trong phần mềm kế toán
if(tuDong&&m){
  __ketoanBao('khoảng ngày '+m[3]+'/'+m[2]+'/'+m[1]+' – '+m[6]+'/'+m[5]+'/'+m[4]);
  const tu=new Date(+m[1],+m[2]-1,+m[3]),homNay=new Date();homNay.setHours(0,0,0,0);
  if((homNay-tu)/86400000>29){alert('Phần mềm kế toán — Xuất đơn hàng\n\nKhoảng ngày bạn chọn ('+m[3]+'/'+m[2]+'/'+m[1]+' – '+m[6]+'/'+m[5]+'/'+m[4]+') cũ hơn 30 ngày gần nhất mà hộp Xuất của sàn đang chọn sẵn.\nHãy tự chọn Khoảng thời gian trong hộp rồi bấm Xuất, sau đó bấm Lịch sử Xuất Báo cáo → Tải về.');return}
}else if(!tuDong&&!confirm('Khoảng thời gian trên sàn: '+(kt||'(mặc định của sàn)')+'\n\nOK = xuất với khoảng này. Cancel = bạn tự chọn lại ngày rồi tự bấm Xuất.'))return;
const x2=bam(/^(Xuất|Export|Xác nhận|Confirm|OK|Tạo báo cáo)$/,true);
if(!x2){__ketoanBao('không thấy nút Xuất trong hộp chọn ngày — hãy tự bấm','#b00020');alert('Không thấy nút Xuất trong hộp chọn ngày — hãy tự bấm.');return}
__ketoanBao('đã bấm Xuất trong hộp, chờ báo cáo được tạo…');
await sl(4000);bam(/^(Lịch sử Xuất Báo cáo|Lịch sử xuất|Export History)$/);
for(let i=0;i<30;i++){await sl(3000);const t=bam(/^(Tải về|Tải xuống|Download)$/,true)||bam(/^(Tải về|Tải xuống|Download)$/);if(t){__ketoanBao('đã bấm Tải về — file đang tải vào Downloads','#2e7d32');alert('Đã bấm Tải về — file đơn hàng đang tải vào thư mục Downloads. Phần mềm kế toán sẽ tự nhận file.');return}}
__ketoanBao('báo cáo chưa sẵn sàng — hãy tự bấm Tải về trong Lịch sử Xuất Báo cáo','#b00020');alert('Báo cáo chưa sẵn sàng sau ~90 giây — chờ thêm rồi tự bấm Tải về trong Lịch sử Xuất Báo cáo.');
}
