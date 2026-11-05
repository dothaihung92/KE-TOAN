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
const thangNam=(e)=>{      // (năm, tháng) của 1 bảng ngày: đọc tiêu đề gần nhất (Shopee "Tháng 102026", TikTok "11 / 2026", "2026-11", "Th 11 2026"...); chỉ nhận tháng 1-12, năm 2000-2100
  const hl=(y,m)=>y>=2000&&y<=2100&&m>=1&&m<=12;
  for(let p=e,k=0;p&&k<6;p=p.parentElement,k++){const t=(p.innerText||'').slice(0,400);let r;
    const dn=/Th(?:áng)?\s*(\d{5,6})(?!\d)/.exec(t);if(dn&&hl(+dn[1].slice(-4),+dn[1].slice(0,-4)))return[+dn[1].slice(-4),+dn[1].slice(0,-4)];
    const ms=[[/(\d{1,2})\s*[\/\-]\s*(\d{4})/g,2,1],[/(?<!\d)(\d{4})\s*[年\-\/\.]\s*(\d{1,2})(?!\d)/g,1,2],[/Th(?:áng)?\.?\s*(\d{1,2})[^\d]{1,6}(\d{4})/gi,2,1]];
    let tot=null;
    for(const [re,iy,im] of ms){re.lastIndex=0;while((r=re.exec(t))){if(hl(+r[iy],+r[im])&&(!tot||r.index<tot[2])){tot=[+r[iy],+r[im],r.index]}}}
    if(tot)return[tot[0],tot[1]]}
  return null};
const kich=e=>{const r=e.getBoundingClientRect(),o={bubbles:true,cancelable:true,view:window,clientX:r.left+r.width/2,clientY:r.top+r.height/2,button:0};      // chuỗi sự kiện chuột đầy đủ: nhiều bộ chọn ngày chỉ mở khi có mousedown/pointerdown
  for(const t of ['pointerdown','mousedown','pointerup','mouseup','click']){try{e.dispatchEvent(new (t.startsWith('pointer')&&window.PointerEvent?PointerEvent:MouseEvent)(t,o))}catch(_){}}try{e.focus&&e.focus()}catch(_){}};
const soLeaf=p=>[...p.querySelectorAll('*')].filter(e=>e.children.length===0&&/^\d{1,2}$/.test((e.innerText||'').trim())&&vis(e));
const timLich=()=>{      // các bảng ngày đang HIỆN trên trang (mỗi bảng >= 28 ô số), không phụ thuộc phần tử mới thêm hay có sẵn
  const nhom=new Set();
  for(const c of soLeaf(document.body)){let p=c.parentElement;for(let k=0;k<7&&p;k++,p=p.parentElement){if(soLeaf(p).length>=28){nhom.add(p);break}}}
  return [...nhom].filter(p=>![...nhom].some(q=>q!==p&&p.contains(q)))};
const layTnChung=()=>{      // bảng ngày + (năm, tháng); 2 bảng cùng đọc ra 1 tháng (tiêu đề nằm ngoài lưới ngày) thì bảng sau = tháng kế tiếp
  const ds=timLich().map(p=>({p,tn:thangNam(p)}));
  for(let i=1;i<ds.length;i++){const x=ds[i-1].tn,y=ds[i].tn;if(x&&y&&x[0]===y[0]&&x[1]===y[1])ds[i].tn=x[1]===12?[x[0]+1,1]:[x[0],x[1]+1]}
  return ds};
const oNgay=(p,d)=>{      // ô ngày d ĐÚNG tháng của bảng: nằm giữa ô "1" đầu tiên và ô "1" kế tiếp (bỏ ngày mờ của tháng trước/sau, kể cả ghi "01")
  const cs=soLeaf(p),n=e=>+(e.innerText||'').trim();const i1=cs.findIndex(e=>n(e)===1);if(i1<0)return [];
  let i2=cs.findIndex((e,j)=>j>i1&&n(e)===1);if(i2<0)i2=cs.length;return cs.slice(i1,i2).filter(e=>n(e)===d)};
const doiThang=async(lui)=>{      // bấm mũi tên ‹ (lùi) / › (tới) 1 tháng của lịch đang mở
  const ds=timLich();if(!ds.length)return false;let g=ds[0];
  for(let k=0;k<6&&g.parentElement;k++){g=g.parentElement;if(ds.every(p=>g.contains(p))&&/\d{4}/.test((g.innerText||'').slice(0,300)))break}
  for(let k=0;k<3&&g.parentElement;k++){const c=nut(g);if(c){kich(c);await sl(700);return true}g=g.parentElement}
  return false;
  function nut(r){const tu=lui?/^[‹<]$/:/^[›>]$/,lop=lui?/prev|pre-|left/i:/next|right/i,bo=/super|year|double|fast|dbl/i;
    const c=[...r.querySelectorAll('*')].filter(e=>vis(e)&&!soLeaf(e).length);
    return c.find(e=>tu.test((e.innerText||'').trim())&&e.children.length===0)
      ||c.find(e=>{const k=(e.getAttribute('class')||'')+' '+(e.getAttribute('aria-label')||'');return lop.test(k)&&!bo.test(k)&&e.getBoundingClientRect().width<60})}};
const chonNgayLich=async(y,mo,d)=>{      // chọn 1 ngày trong lịch đang mở (tự lùi/tới tháng nếu cần)
  for(let v=0;v<14;v++){const ds=layTnChung();if(!ds.length)return false;const b=ds.find(x=>x.tn&&x.tn[0]===y&&x.tn[1]===mo);
    if(b){const c=oNgay(b.p,d);if(!c.length)return false;kich(c[0]);await sl(900);return true}
    const dau=ds.find(x=>x.tn);if(!dau)return false;if(!await doiThang(y*12+mo<dau.tn[0]*12+dau.tn[1]))return false}
  return false};
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
  const layTn=layTnChung;      // đọc lại bảng ngày MỖI LẦN bấm: lịch dựng lại sau mỗi lần chọn nên phần tử cũ không còn dùng được
  const moLai=async()=>{for(const e of ung.slice(0,10)){if(timLich().length)return true;kich(e);await sl(900)}return timLich().length>0};   // lịch tự đóng sau khi chọn ngày đầu -> mở lại
  const chon=async(y,mo,d)=>{if(!layTn().length)await moLai();const b=layTn().find(x=>x.tn&&x.tn[0]===y&&x.tn[1]===mo);if(!b)return false;
    const tat=/disabled|other-?month|out-?of|outside|not-?current|prev-?month|next-?month|gray|grey/i;
    const tatE=e=>[e,e.parentElement,e.parentElement&&e.parentElement.parentElement].some(q=>q&&q.getAttribute&&(tat.test(q.getAttribute('class')||'')||q.getAttribute('aria-disabled')==='true'));
    let tc=oNgay(b.p,d);if(!tc.length)tc=[...b.p.querySelectorAll('*')].filter(e=>e.children.length===0&&(e.innerText||'').trim()===String(d));
    let cs=tc.filter(e=>vis(e)&&!tatE(e));
    if(!cs.length)cs=tc.filter(e=>vis(e));            // dự phòng: bỏ lọc lớp, lấy ô hiển thị đúng số ngày
    if(!cs.length)cs=tc;
    if(!cs.length)return false;
    const c=cs[0];kich(c);await sl(900);
    return true};
  const ok1=await chon(...dich[0]),ok2=ok1&&await chon(...dich[1]);
  if(!ok1||!ok2)return {ok:false,dump:'Bảng ngày tìm thấy:\n'+dump(timLich())+'\n--- ô có số '+dich[ok1?1:0][2]+' ---\n'+[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&(e.innerText||'').trim()===String(dich[ok1?1:0][2])).slice(0,8).map(e=>e.tagName+'.'+(e.className||'')+' < '+(e.parentElement&&e.parentElement.className)+' vis='+vis(e)).join('\n'),ly:'không tìm thấy ngày '+dich[ok1?1:0].join('/')+' trong lịch ('+layTn().map(x=>x.tn?x.tn.join('/'):'?').join(', ')+')'};
  bam(/^(OK|Xác nhận|Áp dụng|Apply|Confirm)$/);await sl(900);
  return {ok:true};
};
const SAN={'banhang.shopee.vn':'https://banhang.shopee.vn/portal/sale/order','seller-vn.tiktok.com':'https://seller-vn.tiktok.com/order','sellercenter.lazada.vn':'https://sellercenter.lazada.vn/apps/order/list'};
const host=location.host,url=SAN[host];
if(!url){loi('Hãy mở trang Quản lý đơn hàng của Shopee / TikTok Shop / Lazada rồi bấm lại.');return}
if(!location.href.startsWith(url)){if(tuDong){__ketoanBao('đang ở '+location.pathname+' — hãy vào Quản lý đơn hàng > Tất cả rồi bấm nút ▶ Xuất đơn','#b00020');return}location.href=url;alert('Đã chuyển tới trang Quản lý đơn hàng — chờ trang tải xong rồi bấm lại.');return}
if(host==='seller-vn.tiktok.com'){await __ketoanTiktok();return}
async function __ketoanTiktok(){      // TikTok Shop: Tất cả -> Bộ lọc -> Thời gian đã tạo (từ - đến) -> Áp dụng -> Xuất -> Excel -> Xuất -> Tải xuống báo cáo MỚI
  const mm=/(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})/.exec(thamSo||'');
  if(!mm){loi('Chưa có khoảng ngày từ phần mềm kế toán — hãy chọn ngày trong phần mềm rồi bấm Mở trang.');return}
  const tuT=mm[3]+'/'+mm[2]+'/'+mm[1],denT=mm[6]+'/'+mm[5]+'/'+mm[4];
  const chu=e=>(e.innerText||'').trim().replace(/^[^\p{L}\p{N}]+/u,'').trim();      // bỏ biểu tượng đứng trước chữ (vd ↗ Xuất)
  const timNut=(re,goc)=>[...(goc||document).querySelectorAll('button,[role=button],a,span,div,label')].filter(e=>vis(e)&&e.children.length<=4&&re.test(chu(e))).sort((a,b)=>(a.innerText||'').length-(b.innerText||'').length)[0];
  const khung=(tieu,nutRe)=>{for(const x of [...document.querySelectorAll('div,span,h1,h2,h3,h4')].filter(e=>vis(e)&&e.children.length===0&&tieu.test((e.innerText||'').trim()))){
      let p=x;for(let k=0;k<9&&p.parentElement;k++){p=p.parentElement;if([...p.querySelectorAll('button')].some(b=>vis(b)&&nutRe.test((b.innerText||'').trim())))return p}}return null};
  let doi=0;while(doi<40&&!timNut(/^Bộ lọc(\s*\(\d+\))?$/)){await sl(1000);doi++}
  const tc=timNut(/^Tất cả$/);if(tc){kich(tc);await sl(1500)}
  // 1) Bộ lọc -> chọn khoảng ngày
  const bl=timNut(/^Bộ lọc(\s*\(\d+\))?$/);if(!bl){loi('Không thấy nút Bộ lọc trên trang Quản lý đơn hàng TikTok.');return}
  __ketoanBao('mở Bộ lọc, chọn Thời gian đã tạo '+tuT+' – '+denT+'…');kich(bl);await sl(1500);
  const dr=khung(/^Bộ lọc$/,/^Áp dụng$/);if(!dr){loi('Không mở được khung Bộ lọc của TikTok.');return}
  const oNhap=[...dr.querySelectorAll('input')].filter(vis);
  const oTu=oNhap.find(i=>/^từ$/i.test((i.placeholder||'').trim()))||oNhap.find(i=>/từ|start|bắt đầu/i.test(i.placeholder||''));
  if(!oTu){loi('Không thấy ô "Từ" (Thời gian đã tạo) trong Bộ lọc.');return}
  kich(oTu);await sl(1200);
  if(!timLich().length){kich(oTu.parentElement||oTu);await sl(1200)}
  const ok1=await chonNgayLich(+mm[1],+mm[2],+mm[3]),ok2=ok1&&await chonNgayLich(+mm[4],+mm[5],+mm[6]);
  if(!ok1||!ok2){const co=sao('Lịch TikTok:\n'+dump(timLich()));loi('Chưa tự chọn được ngày '+(ok1?denT:tuT)+' trong lịch Bộ lọc TikTok.'+(co?'\nĐã COPY cấu trúc lịch — dán (Ctrl+V) cho người hỗ trợ.':'')+'\nBạn có thể tự chọn ngày, bấm Áp dụng rồi bấm Xuất.');return}
  await sl(800);
  const gt=[...dr.querySelectorAll('input')].map(i=>i.value).join(' ');
  if(!(gt.includes(tuT)&&gt.includes(denT)))__ketoanBao('ô ngày hiện: '+gt.trim()+' (cần '+tuT+' – '+denT+')','#b26a00');
  const ad=[...dr.querySelectorAll('button')].find(b=>vis(b)&&/^Áp dụng$/.test((b.innerText||'').trim()));if(!ad){loi('Không thấy nút Áp dụng.');return}
  kich(ad);await sl(2500);
  const chip=(document.body.innerText||'').replace(/\s/g,'');
  if(!chip.includes(tuT+'-'+denT)){loi('Bộ lọc TikTok chưa đúng khoảng '+tuT+' – '+denT+' sau khi Áp dụng. Hãy tự chọn lại ngày trong Bộ lọc, bấm Áp dụng rồi bấm nút ▶ Xuất đơn (Kế toán).');return}
  // 2) Xuất -> Đơn hàng đã lọc + Excel -> Xuất
  const moXuat=async()=>{let k=khung(/^Xuất đơn hàng$/,/^Xuất$/);if(k)return k;const x=timNut(/^Xuất$/);if(!x)return null;kich(x);await sl(1800);return khung(/^Xuất đơn hàng$/,/^Xuất$/)};
  const kx=await moXuat();if(!kx){loi('Không mở được khung Xuất đơn hàng của TikTok.');return}
  const chonR=re=>{const l=timNut(re,kx);if(l){kich(l);return true}return false};
  chonR(/^Đơn hàng đã lọc/);await sl(300);chonR(/^Excel$/);await sl(300);
  const tenFile=k=>((k&&k.innerText)||'').match(/[^\n]+?\.(xlsx|csv)/g)||[];
  const cu=new Set(tenFile(kx).map(x=>x.trim()));
  const nx=[...kx.querySelectorAll('button')].find(b=>vis(b)&&/^Xuất$/.test((b.innerText||'').trim()));if(!nx){loi('Không thấy nút Xuất trong khung Xuất đơn hàng.');return}
  kich(nx);__ketoanBao('đã bấm Xuất (Excel, đơn hàng đã lọc '+tuT+' – '+denT+'), chờ TikTok tạo file…');
  // 3) chờ báo cáo MỚI (không có trong danh sách trước khi bấm) có nút Tải xuống
  for(let i=0;i<100;i++){await sl(3000);const k=await moXuat();if(!k)continue;
    if(i%5===4)__ketoanBao('đang chờ TikTok tạo file ('+Math.round((i+1)*3/60*10)/10+' phút)… xong sẽ tự bấm Tải xuống');
    for(const n of [...k.querySelectorAll('button,a,[role=button]')].filter(e=>vis(e)&&/^(Tải xuống|Tải về|Download)$/.test((e.innerText||'').trim()))){
      let p=n;for(let j=0;j<6&&p;j++){p=p.parentElement;const t=tenFile(p);if(t.length){const ten=t[0].trim();
          if(t.length===1&&!cu.has(ten)){n.click();__ketoanBao('đã bấm Tải xuống '+ten+' — file đang tải vào Downloads','#2e7d32');alert('Đã bấm Tải xuống báo cáo TikTok '+ten+' — file đang tải vào thư mục Downloads. Phần mềm kế toán sẽ tự nhận file.');return}break}}}}
  loi('File TikTok chưa sẵn sàng sau ~5 phút — chờ thêm rồi tự bấm Tải xuống báo cáo MỚI NHẤT trong khung Xuất đơn hàng.');
}
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
await sl(4000);
const LS=/^(Lịch sử Xuất Báo cáo|Lịch sử xuất|Export History)$/;
const lsHien=()=>[...document.querySelectorAll('div,section,aside')].some(e=>vis(e)&&e.children.length<12&&/Báo cáo gần nhất|Recent reports/i.test((e.innerText||'').slice(0,60)));
const moLs=async()=>{if(lsHien())return;      // bảng Lịch sử tự đóng sau vài giây -> mở lại mỗi vòng chờ
  const b=[...document.querySelectorAll('button,a,[role=button],span,div')].filter(e=>vis(e)&&e.children.length<4&&LS.test((e.innerText||'').trim())).sort((a,b)=>a.innerText.length-b.innerText.length)[0];
  if(b){for(const t of ['mouseover','mouseenter']){try{b.dispatchEvent(new MouseEvent(t,{bubbles:true,view:window}))}catch(_){}}kich(b);await sl(1200)}};
await moLs();
// ---- tải ĐÚNG báo cáo: hàng có tên khớp và đã có nút Tải về (hàng "Đang được xử lý" thì chờ)
const tim=()=>{const nut=[...document.querySelectorAll('button,a,[role=button]')].filter(e=>vis(e)&&/^(Tải về|Tải xuống|Download)$/.test((e.innerText||'').trim()));
  for(const n of nut){let p=n;for(let k=0;k<6&&p;k++){p=p.parentElement;if(!p)break;const t=(p.innerText||'');
      if(/Order\.\S*?\d{8}_\d{8}/.test(t)){if(t.includes(ten)&&(t.match(/Order\.\S*?\d{8}_\d{8}/g)||[]).length===1)return n;break}}}return null};
for(let i=0;i<100;i++){await sl(3000);await moLs();if(i%5===4)__ketoanBao('đang chờ Shopee tạo báo cáo '+ten+' ('+Math.round((i+1)*3/60*10)/10+' phút)… xong sẽ tự bấm Tải về');
  if(!ten){const t=bam(/^(Tải về|Tải xuống|Download)$/,true)||bam(/^(Tải về|Tải xuống|Download)$/);if(t){__ketoanBao('đã bấm Tải về — file đang tải vào Downloads','#2e7d32');alert('Đã bấm Tải về — file đơn hàng đang tải vào thư mục Downloads. Phần mềm kế toán sẽ tự nhận file.');return}continue}
  const n=tim();if(n){n.click();__ketoanBao('đã bấm Tải về báo cáo '+ten+' — file đang tải vào Downloads','#2e7d32');alert('Đã bấm Tải về báo cáo '+ten+' — file đang tải vào thư mục Downloads. Phần mềm kế toán sẽ tự nhận file.');return}}
loi('Báo cáo '+ten+' chưa sẵn sàng sau ~5 phút — chờ thêm rồi tự bấm Tải về ĐÚNG báo cáo '+ten+' trong Lịch sử Xuất Báo cáo.');
}
