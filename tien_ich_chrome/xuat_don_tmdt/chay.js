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
const hop=()=>{      // hộp thoại: theo role/class quen thuộc; không có thì tìm theo tiêu đề "Xuất ... Đơn hàng" rồi đi lên tới khối có nút Xuất
  const d=[...document.querySelectorAll('[role=dialog],.eds-modal,.shopee-modal,.ant-modal,.arco-modal,.next-dialog,.modal')].filter(vis);if(d.length)return d[d.length-1];
  const tieu=[...document.querySelectorAll('div,span,h1,h2,h3,p')].filter(e=>vis(e)&&e.children.length===0&&/^(Xuất|Export)\b.*(Đơn hàng|đơn hàng|Orders?)\s*$/.test((e.innerText||'').trim())&&(e.innerText||'').trim().length<60);
  for(const t of tieu.reverse()){let p=t;for(let k=0;k<8&&p&&p.parentElement;k++){p=p.parentElement;
      const nut=[...p.querySelectorAll('button')].filter(e=>vis(e)&&/^(Xuất|Export|Xác nhận|OK)$/.test((e.innerText||'').trim()));
      if(nut.length&&p.getBoundingClientRect().width>250&&p!==document.body)return p}}
  return null};
const bam=(re,dlg)=>{let g=document;if(dlg){const h=hop();if(h)g=h}let ds=[...g.querySelectorAll('button,a,[role=button]')].filter(vis);if(dlg&&g===document)ds.reverse();
 for(const e of ds){const t=(e.innerText||'').trim();if(t&&t.length<40&&re.test(t)&&!e.disabled){e.click();return t}}return ''};
const loi=(chu)=>{__ketoanBao(chu,'#b00020');alert('Phần mềm kế toán — Xuất đơn hàng\n\n'+chu)};
// ---- chọn khoảng ngày trong bộ chọn lịch của hộp Xuất (thử theo cấu trúc lịch phổ biến; không được thì chụp cấu trúc lịch để chỉnh)
const sao=chu=>{try{const t=document.createElement('textarea');t.value=chu;t.style.cssText='position:fixed;left:-9999px';document.body.appendChild(t);t.select();document.execCommand('copy');t.remove();return true}catch(e){return false}};
const dump=(goc)=>{const gon=(e,d)=>{if(d>9)return'…';const t=e.tagName.toLowerCase(),c=(e.getAttribute('class')||'').split(/\s+/).filter(x=>x).slice(0,4).join('.');
    const k=[...e.children].filter(x=>vis(x)||x.children.length);const tx=(e.children.length===0?(e.innerText||'').trim().slice(0,14):'');
    return t+(c?'.'+c:'')+(tx?'['+tx+']':'')+(k.length?'{'+k.slice(0,40).map(x=>gon(x,d+1)).join(',')+'}':'')};
  return goc.map(e=>gon(e,0)).join('\n').slice(0,6000)};
const KHONG_PHAI=/disabled|out|other|prev|next|gray|grey|not-?current|outside|adjacent|last-?month|next-?month/i;
const thangNam=(e)=>{for(let p=e,k=0;p&&k<6;p=p.parentElement,k++){const t=(p.innerText||'').slice(0,400);
    let dn=t.match(/Th(?:áng)?\s*(\d{5,6})(?!\d)/);      // Shopee ghi liền "Tháng 102026" (tháng 10, năm 2026): 4 chữ số cuối là năm
    if(dn){return[+dn[1].slice(-4),+dn[1].slice(0,-4)]}
    let m=t.match(/(\d{4})\s*[年\-\/\.]\s*(\d{1,2})/)||t.match(/Th(?:áng)?\.?\s*(\d{1,2})[^\d]{1,6}(\d{4})/i);
    if(m){return m[1].length===4?[+m[1],+m[2]]:[+m[2],+m[1]]}
    m=t.match(/(\d{1,2})\s*[\/\-]\s*(\d{4})/);if(m)return[+m[2],+m[1]]}return null};
const kich=e=>{const r=e.getBoundingClientRect(),o={bubbles:true,cancelable:true,view:window,clientX:r.left+r.width/2,clientY:r.top+r.height/2,button:0};      // chuỗi sự kiện chuột đầy đủ: nhiều bộ chọn ngày chỉ mở khi có mousedown/pointerdown
  for(const t of ['pointerdown','mousedown','pointerup','mouseup','click']){try{e.dispatchEvent(new (t.startsWith('pointer')&&window.PointerEvent?PointerEvent:MouseEvent)(t,o))}catch(_){}}try{e.focus&&e.focus()}catch(_){}};
const soLeaf=p=>[...p.querySelectorAll('*')].filter(e=>e.children.length===0&&/^\d{1,2}$/.test((e.innerText||'').trim())&&vis(e));
const timLich=()=>{      // các bảng ngày đang HIỆN trên trang (mỗi bảng >= 28 ô số), không phụ thuộc phần tử mới thêm hay có sẵn
  const nhom=new Set();
  for(const c of soLeaf(document.body)){let p=c.parentElement;for(let k=0;k<7&&p;k++,p=p.parentElement){if(soLeaf(p).length>=28){nhom.add(p);break}}}
  return [...nhom].filter(p=>![...nhom].some(q=>q!==p&&p.contains(q)))};
const datNgay=async(dlg,m)=>{
  const dich=[[+m[1],+m[2],+m[3]],[+m[4],+m[5],+m[6]]];
  const re=/\d{4}\D\d{2}\D\d{2}\s*[–-]\s*\d{4}\D\d{2}\D\d{2}/;
  const gt=[...dlg.querySelectorAll('*')].filter(e=>vis(e)&&re.test(e.innerText||'')).sort((a,b)=>a.innerText.length-b.innerText.length);
  const ung=[];                                       // các phần tử thử bấm: ô chứa chữ ngày, cha của nó, ô input, biểu tượng lịch
  if(gt[0]){ung.push(gt[0]);let p=gt[0];for(let k=0;k<4&&p.parentElement&&p.parentElement!==dlg;k++){p=p.parentElement;ung.push(p)}}
  dlg.querySelectorAll('input,[class*=icon],[class*=calendar],svg').forEach(e=>{if(vis(e)&&!ung.includes(e))ung.push(e)});
  let bang=timLich();
  for(const e of ung.slice(0,10)){if(bang.length)break;kich(e);await sl(1000);bang=timLich()}
  if(!bang.length){const lop=[...document.querySelectorAll('[class*=picker],[class*=calendar],[class*=popper],[class*=popover],[class*=date]')];
    return {ok:false,dump:'Thử bấm '+ung.slice(0,10).length+' phần tử nhưng không thấy bảng ngày. Hộp:\n'+dump([dlg])+'\n--- phần tử lịch/popup trên trang ('+lop.length+') ---\n'+dump(lop.filter(e=>!lop.some(x=>x!==e&&x.contains(e))).slice(0,6)),ly:'không mở được lịch'}}
  const tn=bang.map(p=>({p,tn:thangNam(p)}));
  const chon=async(y,mo,d)=>{const b=tn.find(x=>x.tn&&x.tn[0]===y&&x.tn[1]===mo);if(!b)return false;
    const cs=[...b.p.querySelectorAll('*')].filter(e=>e.children.length===0&&(e.innerText||'').trim()===String(d)&&vis(e)&&![e,...[...Array(4)].map((_,i)=>{let q=e;for(let j=0;j<=i;j++)q=q&&q.parentElement;return q})].some(q=>q&&q.getAttribute&&KHONG_PHAI.test(q.getAttribute('class')||'')));
    if(!cs.length)return false;kich(cs[0]);await sl(500);return true};
  const ok1=await chon(...dich[0]),ok2=ok1&&await chon(...dich[1]);
  if(!ok1||!ok2)return {ok:false,dump:'Bảng ngày tìm thấy:\n'+dump(bang),ly:'không tìm thấy ngày '+dich[ok1?1:0].join('/')+' trong lịch ('+tn.map(x=>x.tn?x.tn.join('/'):'?').join(', ')+')'};
  bam(/^(OK|Xác nhận|Áp dụng|Apply|Confirm)$/);await sl(900);
  return {ok:true};
};
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
    __ketoanBao('đang chọn khoảng ngày '+m[3]+'/'+m[2]+'/'+m[1]+' – '+m[6]+'/'+m[5]+'/'+m[4]+' trong hộp…');
    const dlg=hop();
    if(dlg){const kq=await datNgay(dlg,m);cur=lay();
      if(!kq.ok&&(!cur||chuan(cur[0])!==can[0]||chuan(cur[1])!==can[1])&&!(cur&&chuan(cur[0])<=can[0]&&chuan(cur[1])>=can[1]&&false)){
        const co=sao(kq.dump||'');
        loi('Chưa tự chọn được ngày trong lịch của Shopee ('+(kq.ly||'')+').\n'+(co?'Đã COPY sẵn cấu trúc lịch vào bộ nhớ tạm — bạn dán (Ctrl+V) cho người hỗ trợ để chỉnh tiện ích.\n':'')+'Bạn có thể tự chọn ngày trong hộp rồi bấm Xuất, sau đó vào Lịch sử Xuất Báo cáo → Tải về.');return}}
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
