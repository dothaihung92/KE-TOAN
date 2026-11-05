// Tự bấm Xuất báo cáo đơn hàng trên trang người bán (dùng chung cho tiện ích Chrome và nút dấu trang).
// Chỉ bấm các nút trên trang của chính shop: Tất cả -> Xuất -> (hỏi lại khoảng ngày) -> Xuất -> Lịch sử Xuất Báo cáo -> Tải về.
async function __ketoanXuat(tuDong){
const sl=ms=>new Promise(r=>setTimeout(r,ms));
const vis=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'};
const hop=()=>{const d=[...document.querySelectorAll('[role=dialog],.eds-modal,.shopee-modal,.ant-modal,.arco-modal,.next-dialog,.modal')].filter(vis);return d.length?d[d.length-1]:null};
const bam=(re,dlg)=>{let g=document;if(dlg){const h=hop();if(h)g=h}let ds=[...g.querySelectorAll('button,a,[role=button]')].filter(vis);if(dlg&&g===document)ds.reverse();
 for(const e of ds){const t=(e.innerText||'').trim();if(t&&t.length<40&&re.test(t)&&!e.disabled){e.click();return t}}return ''};
const SAN={'banhang.shopee.vn':'https://banhang.shopee.vn/portal/sale/order','seller-vn.tiktok.com':'https://seller-vn.tiktok.com/order','sellercenter.lazada.vn':'https://sellercenter.lazada.vn/apps/order/list'};
const host=location.host,url=SAN[host];
if(!url){alert('Xuất đơn TMĐT: hãy mở trang Quản lý đơn hàng của Shopee / TikTok Shop / Lazada rồi bấm lại.');return}
if(!location.href.startsWith(url)){if(tuDong)return;location.href=url;alert('Đã chuyển tới trang Quản lý đơn hàng — chờ trang tải xong rồi bấm lại.');return}
const RX=/^(Xuất|Xuất file|Xuất dữ liệu|Export|Xuất đơn hàng)$/;
// trang tải chậm: chờ nút Xuất tối đa 40 giây
let doi=0;while(tuDong&&doi<40&&![...document.querySelectorAll('button,a,[role=button]')].some(e=>vis(e)&&RX.test((e.innerText||'').trim()))){await sl(1000);doi++}
if(host==='banhang.shopee.vn'&&bam(/^Tất cả$/))await sl(2000);
const x=bam(RX);
if(!x){alert('Không thấy nút Xuất trên trang — hãy tự bấm Xuất.');return}
await sl(2500);const h=hop();
const kt=h?([...h.querySelectorAll('input')].map(i=>i.value).filter(Boolean).join(' – ')||((h.innerText||'').match(/\d{4}\/\d{2}\/\d{2}\s*[–-]\s*\d{4}\/\d{2}\/\d{2}/)||[''])[0]):'';
if(!confirm('Phần mềm kế toán — Xuất đơn hàng\n\nKhoảng thời gian trên sàn: '+(kt||'(mặc định của sàn)')+'\n\nOK = xuất với khoảng này (phần mềm kế toán sẽ lọc đúng ngày bạn chọn).\nCancel = bạn tự chọn lại ngày trong hộp rồi tự bấm Xuất.'))return;
const x2=bam(/^(Xuất|Export|Xác nhận|Confirm|OK|Tạo báo cáo)$/,true);
if(!x2){alert('Không thấy nút Xuất trong hộp chọn ngày — hãy tự bấm.');return}
await sl(4000);bam(/^(Lịch sử Xuất Báo cáo|Lịch sử xuất|Export History)$/);
for(let i=0;i<30;i++){await sl(3000);const t=bam(/^(Tải về|Tải xuống|Download)$/,true)||bam(/^(Tải về|Tải xuống|Download)$/);if(t){alert('Đã bấm Tải về — file đơn hàng đang tải vào thư mục Downloads. Phần mềm kế toán sẽ tự nhận file.');return}}
alert('Báo cáo chưa sẵn sàng sau ~90 giây — chờ thêm rồi tự bấm Tải về trong Lịch sử Xuất Báo cáo.');
}
