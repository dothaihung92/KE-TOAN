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
let __moLaiLich=null;      // hàm mở lại bảng lịch khi nó tự đóng giữa 2 lần chọn ngày (Lazada đóng bảng sau khi chọn ngày bắt đầu)
let __that=false;      // true: bấm bằng CHUỘT THẬT (Chrome debugger) vì trang bỏ qua sự kiện giả lập (Lazada)
const kichThat=e=>new Promise(r=>{try{const b=e.getBoundingClientRect();chrome.runtime.sendMessage({loai:'click-that',x:b.left+b.width/2,y:b.top+b.height/2},x=>{void chrome.runtime.lastError;r(x||{})})}catch(_){r({})}});
const kichX=async e=>{if(__that)await kichThat(e);else kich(e)};
const soLeaf=p=>[...p.querySelectorAll('*')].filter(e=>e.children.length===0&&/^\d{1,2}$/.test((e.innerText||'').trim())&&vis(e));
const timLich=()=>{      // các bảng ngày đang HIỆN trên trang (mỗi bảng >= 28 ô số), không phụ thuộc phần tử mới thêm hay có sẵn
  const nhom=new Set();
  const laLich=p=>{const v=soLeaf(p).map(e=>+(e.innerText||'').trim());return v.length>=28&&v.length<=100&&new Set(v).size>=25};      // lưới ngày thật: >= 28 ô và >= 25 số khác nhau (loại bộ đếm huy hiệu 0-9 lặp lại)
  for(const c of soLeaf(document.body)){let p=c.parentElement;for(let k=0;k<7&&p;k++,p=p.parentElement){if(laLich(p)){nhom.add(p);break}}}
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
  for(let k=0;k<3&&g.parentElement;k++){const c=nut(g);if(c){await kichX(c);await sl(700);return true}g=g.parentElement}
  return false;
  function nut(r){const tu=lui?/^[‹<]$/:/^[›>]$/,lop=lui?/prev|pre-|left/i:/next|right/i,bo=/super|year|double|fast|dbl/i;
    const c=[...r.querySelectorAll('*')].filter(e=>vis(e)&&!soLeaf(e).length);
    return c.find(e=>tu.test((e.innerText||'').trim())&&e.children.length===0)
      ||c.find(e=>{const k=(e.getAttribute('class')||'')+' '+(e.getAttribute('aria-label')||'');return lop.test(k)&&!bo.test(k)&&e.getBoundingClientRect().width<60})}};
const chonNgayLich=async(y,mo,d)=>{      // chọn 1 ngày trong lịch đang mở (tự lùi/tới tháng nếu cần)
  for(let v=0;v<14;v++){let ds=layTnChung();if(!ds.length&&__moLaiLich){await __moLaiLich();ds=layTnChung()}if(!ds.length)return false;const b=ds.find(x=>x.tn&&x.tn[0]===y&&x.tn[1]===mo);
    if(b){const c=oNgay(b.p,d);if(!c.length)return false;await kichX(c[0]);await sl(900);return true}
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
if(host==='sellercenter.lazada.vn'){await __ketoanLazada();return}
async function __ketoanLazada(){      // Lazada: Đơn đặt hàng -> Tất cả -> Tuỳ chỉnh (ngày bắt đầu - kết thúc) -> OK -> Xuất khẩu -> Export All -> OK -> Export History -> Tải file MỚI
  const mm=/(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})/.exec(thamSo||'');
  if(!mm){loi('Chưa có khoảng ngày từ phần mềm kế toán — hãy chọn ngày trong phần mềm rồi bấm Mở trang.');return}
  const tuI=mm[1]+'-'+mm[2]+'-'+mm[3],denI=mm[4]+'-'+mm[5]+'-'+mm[6];
  const chu=e=>(e.innerText||e.value||'').trim().replace(/^[^\p{L}\p{N}]+/u,'').trim();
  const BTN='button,[role=button],[role=tab],[role=menuitem],a,label,li';
  const timNut=(re,goc)=>{const ds=[...(goc||document).querySelectorAll('button,[role=button],[role=tab],[role=menuitem],a,span,div,label,li')].filter(e=>vis(e)&&e.children.length<=4&&re.test(chu(e)));
    const diem=e=>(e.closest(BTN)?0:e.querySelector(BTN)?1:2);
    const e=ds.sort((a,b)=>diem(a)-diem(b)||(a.innerText||'').length-(b.innerText||'').length)[0];return e&&(e.closest(BTN)||e.querySelector(BTN)||e)};
  // đóng các hộp giới thiệu (FFR+, Yêu cầu giao hàng nhanh...) che trang: bấm 'Nhận được Bắt Đầu'/'Got it'/dấu ×
  const dongGt=async()=>{let n=0;for(let k=0;k<8;k++){const b=timNut(/^(Nhận được Bắt Đầu|Nhận được|Bắt Đầu|Got it|Đã hiểu|Bỏ qua|Skip)$/i)||[...document.querySelectorAll('[class*=guide] [class*=close],[class*=tour] [class*=close],[class*=popover] [class*=close],[class*=modal] [class*=close],[aria-label=Close],[aria-label=close]')].filter(vis)[0];
      if(!b)break;kich(b);try{b.click()}catch(e){}n++;await sl(500)}return n};
  let doi=0;while(doi<15&&!timNut(/^Tất cả$/)){await sl(1000);doi++}
  await dongGt();
  const tab=timNut(/^Tất cả$/);if(tab){kich(tab);await sl(2000);await dongGt()}      // nút Tùy chỉnh (Ngày đặt hàng) chỉ có ở tab Tất cả -> bấm Tất cả TRƯỚC, rồi mới chờ Tùy chỉnh
  doi=0;while(doi<15&&!timNut(/^(Tùy chỉnh|Tuỳ chỉnh)$/)){await sl(1000);doi++;if(doi%4===0)await dongGt()}
  const RT=/^(Tùy chỉnh|Tuỳ chỉnh|Custom)$/i;
  const tc=timNut(RT);if(!tc){loi('Không thấy nút "Tùy chỉnh" (Ngày đặt hàng) trên trang Đơn đặt hàng Lazada.');return}
  __ketoanBao('chọn Ngày đặt hàng: Tùy chỉnh '+tuI+' – '+denI+'…');
  // ô Ngày bắt đầu/kết thúc bị KHÓA (xám) cho tới khi chọn Tùy chỉnh. Nút Tùy chỉnh dạng bật/tắt: chỉ bấm khi CHƯA bật (bấm 2 lần sẽ tắt lại)
  const oRg=()=>[...document.querySelectorAll('input')].filter(vis).find(i=>/Ngày bắt đầu|Start/i.test(i.placeholder||''));
  const khoa=i=>!i||i.disabled||[i,i.parentElement,i.parentElement&&i.parentElement.parentElement,i.closest('[class*=picker],[class*=range]')].some(e=>e&&/disabled/i.test((e.getAttribute&&e.getAttribute('class'))||''));
  const xanh=e=>{const m=/rgba?\((\d+),\s*(\d+),\s*(\d+)/.exec(getComputedStyle(e).backgroundColor||'');return !!m&&+m[3]>180&&+m[1]<120&&+m[2]<170};
  const batTc=()=>{const e=timNut(RT);if(!e)return false;return [e,e.parentElement,e.parentElement&&e.parentElement.parentElement].some(x=>x&&(xanh(x)||/(^|[\s_-])(active|selected|checked|current|primary)([\s_-]|$)/i.test((x.getAttribute&&x.getAttribute('class'))||'')||x.getAttribute&&(x.getAttribute('aria-checked')==='true'||x.getAttribute('aria-pressed')==='true')))};
  const daBat=()=>batTc()||!khoa(oRg());
  const choBat=async()=>{for(let w=0;w<5&&!daBat();w++)await sl(300);return daBat()};
  if(!daBat()){
    kich(timNut(RT));await choBat();                                    // lần 1: sự kiện chuột giả lập
    if(!daBat()){const e=timNut(RT);if(e){try{e.click()}catch(_){}await choBat()}}
    if(!daBat()){const e=timNut(RT);if(e){__ketoanBao('trang không nhận bấm giả lập — dùng chuột thật (Chrome sẽ hiện thanh "đang gỡ lỗi", bình thường)…','#1565c0');await kichThat(e);await choBat()}}
  }
  if(!daBat()){const co=sao('Trang Lazada (Tùy chỉnh):\n'+dump([document.body]).slice(0,6000));loi('Đã bấm "Tùy chỉnh" nhưng ô Ngày bắt đầu vẫn bị khóa.'+(co?'\nĐã COPY cấu trúc trang — dán (Ctrl+V) cho người hỗ trợ.':''));return}
  await sl(500);
  const oNgay=()=>[...document.querySelectorAll('input')].filter(vis);
  const oBd=oNgay().find(i=>/Ngày bắt đầu|Start/i.test(i.placeholder||''))||oNgay().find(i=>/^\d{4}-\d{2}-\d{2}/.test(i.value||''));
  if(!oBd){loi('Không thấy ô "Ngày bắt đầu" sau khi bấm Tùy chỉnh.');return}
  const oYmd=()=>oNgay().filter(i=>/YYYY/i.test(i.placeholder||'')||(/^\d{4}-\d{2}-\d{2}$/.test(i.value||'')&&i!==oBd));
  const bangMo=()=>oYmd().length>=2||timLich().length>0;
  // mở bảng chọn ngày: bấm ô Ngày bắt đầu, rồi các phần tử bao quanh / biểu tượng lịch cho tới khi bảng hiện (chờ tối đa ~3 giây mỗi lần thử)
  const ungMo=[oBd,oBd.parentElement,oBd.parentElement&&oBd.parentElement.parentElement,...[...document.querySelectorAll('[class*=calendar],[class*=date-picker],[class*=range-picker],svg')].filter(e=>vis(e)&&e.getBoundingClientRect().top<400)].filter(Boolean);
  let mo=bangMo();
  for(const e of ungMo.slice(0,6)){if(mo)break;kich(e);try{e.click()}catch(_){}for(let w=0;w<4&&!(mo=bangMo());w++)await sl(400)}
  for(const e of ungMo.slice(0,3)){if(mo)break;await kichThat(e);for(let w=0;w<5&&!(mo=bangMo());w++)await sl(400)}      // chưa mở -> chuột thật
  if(!mo){const co=sao('Trang Lazada (chọn ngày):\n'+dump([document.body]));loi('Không mở được bảng chọn ngày của Lazada sau khi bấm Tùy chỉnh.'+(co?'\nĐã COPY cấu trúc trang — dán (Ctrl+V) cho người hỗ trợ.':''));return}
  const go=async(i,v)=>{      // gõ như bàn phím: chọn hết, chèn chữ (sinh sự kiện input thật), Enter; không được thì gán trực tiếp
    kich(i);i.focus();try{i.select()}catch(_){}document.execCommand('insertText',false,v);await sl(150);
    if(i.value!==v){const st=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;st.call(i,v);i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}))}
    for(const t of ['keydown','keyup'])i.dispatchEvent(new KeyboardEvent(t,{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true}));await sl(300)};
  const daDung=()=>{const v=oNgay().map(i=>i.value).join(' ');return v.includes(tuI)&&v.includes(denI)};
  let ys=oYmd();
  if(ys.length>=2){await go(ys[0],tuI);ys=oYmd();await go(ys[1]||ys[0],denI)}
  const oGio=oNgay().filter(i=>/HH:mm/i.test(i.placeholder||'')||/^\d{2}:\d{2}:\d{2}$/.test(i.value||''));
  if(oGio.length>=2){if(!oGio[0].value)await go(oGio[0],'00:00:00');if(!oGio[1].value)await go(oGio[1],'23:59:59')}
  if(!daDung()){      // bấm ngày trên lịch bằng CHUỘT THẬT (Lazada bỏ qua sự kiện giả lập); bảng phải còn mở
    __that=true;
    __moLaiLich=async()=>{const ket=oNgay().find(i=>/Ngày kết thúc|End/i.test(i.placeholder||''))||oNgay().filter(i=>/^\d{4}-\d{2}-\d{2}/.test(i.value||''))[1];      // chọn xong ngày bắt đầu bảng đóng lại -> bấm ô Ngày kết thúc để mở lại
      for(const e of [ket,ket&&ket.parentElement,oBd].filter(Boolean)){await kichThat(e);for(let w=0;w<6&&!timLich().length;w++)await sl(400);if(timLich().length)return true}return false};
    if(!timLich().length){await kichThat(oBd);await sl(1200)}
    const ok1=await chonNgayLich(+mm[1],+mm[2],+mm[3]),ok2=ok1&&await chonNgayLich(+mm[4],+mm[5],+mm[6]);
    if(!ok1||!ok2){const co=sao('Lịch Lazada ('+(ok1?denI:tuI)+'):\n'+dump([document.body]).slice(0,5000)+'\n--- lịch ---\n'+dump(timLich()));loi('Chưa tự chọn được ngày '+(ok1?denI:tuI)+' trong lịch Lazada.'+(co?'\nĐã COPY cấu trúc lịch — dán (Ctrl+V) cho người hỗ trợ.':''));return}}
  const ok=timNut(/^OK$/);if(ok){kich(ok);await sl(2500)}
  const v=oNgay().map(i=>i.value).join(' ');
  if(!(v.includes(tuI)&&v.includes(denI))){loi('Ô Ngày đặt hàng của Lazada chưa đúng '+tuI+' – '+denI+' (đang: '+(oBd.value||'trống')+'). Hãy tự chọn ngày, bấm OK rồi bấm nút ▶ Xuất đơn (Kế toán).');return}
  // 2) chụp danh sách Export History hiện có (để nhận ra file MỚI), rồi Xuất khẩu -> Export All -> OK
  const moMenu=async()=>{const x=timNut(/^Xuất khẩu$|^Export$/);if(!x)return false;kich(x);for(const t of ['mouseover','mouseenter'])x.dispatchEvent(new MouseEvent(t,{bubbles:true}));await sl(900);return true};
  const lopNoi=()=>[...document.querySelectorAll('[role=dialog],.next-dialog,.next-overlay-inner,.ant-modal,.next-drawer,[class*=dialog],[class*=drawer],[class*=modal]')].filter(e=>vis(e)&&e.getBoundingClientRect().width>300);
  const hang=()=>{const o=lopNoi();const g=o[o.length-1]||document;return [...g.querySelectorAll('button,a,[role=button],span')].filter(e=>vis(e)&&/^(Download|Tải xuống|Tải về|下载)$/i.test(chu(e))).map(n=>{let p=n;for(let k=0;k<6&&p.parentElement;k++){p=p.parentElement;if((p.innerText||'').length>20)break}return {n,t:(p.innerText||'').replace(/\s+/g,' ').trim()}})};
  const dong=async()=>{const x=[...document.querySelectorAll('[aria-label=Close],[class*=close]')].filter(vis).pop();if(x){kich(x);x.click&&x.click()}document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',keyCode:27,bubbles:true}));await sl(800)};
  const moLs=async()=>{if(!await moMenu())return false;const h=timNut(/^(Export History|Lịch sử xuất)/i);if(!h)return false;kich(h);await sl(2500);return true};
  let cu=new Set();if(await moLs()){cu=new Set(hang().map(x=>x.t));await dong()}
  if(!await moMenu()){loi('Không thấy nút "Xuất khẩu" trên trang Lazada.');return}
  const ea=timNut(/^(Export All|Xuất tất cả)$/i);if(!ea){loi('Không thấy mục "Export All" trong menu Xuất khẩu.');return}
  kich(ea);await sl(1500);
  const xn=lopNoi().map(o=>[...o.querySelectorAll('button')].find(b=>vis(b)&&/^(OK|Xác nhận|Confirm)$/i.test(chu(b)))).filter(Boolean).pop()||timNut(/^OK$/);
  if(xn){kich(xn);await sl(2000)}
  __ketoanBao('đã bấm Export All ('+tuI+' – '+denI+'), chờ Lazada tạo file…');
  // 3) chờ file mới trong Export History rồi bấm tải
  for(let i=0;i<60;i++){await sl(5000);if(i%3===2)__ketoanBao('đang chờ Lazada tạo file ('+Math.round((i+1)*5/60*10)/10+' phút)… xong sẽ tự tải');
    if(!lopNoi().length&&!await moLs())continue;
    const moi=(cu.size||i>=3)?hang().find(x=>!cu.has(x.t)):null;      // không chụp được danh sách cũ: chờ ~20 giây rồi lấy dòng MỚI NHẤT (trên cùng)
    if(moi){moi.n.click();__ketoanBao('đã bấm tải file Lazada — file đang tải vào Downloads','#2e7d32');alert('Đã bấm tải file đơn hàng Lazada — file đang tải vào thư mục Downloads. Phần mềm kế toán sẽ tự nhận file.');return}
    if(i%2===1)await dong()}
  loi('File Lazada chưa sẵn sàng sau ~5 phút (hoặc không nhận ra danh sách Export History) — hãy vào Xuất khẩu → Export History và tự tải file mới nhất.');
}

async function __ketoanTiktok(){      // TikTok Shop: Tất cả -> Bộ lọc -> Thời gian đã tạo (từ - đến) -> Áp dụng -> Xuất -> Excel -> Xuất -> Tải xuống báo cáo MỚI
  const mm=/(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})/.exec(thamSo||'');
  if(!mm){loi('Chưa có khoảng ngày từ phần mềm kế toán — hãy chọn ngày trong phần mềm rồi bấm Mở trang.');return}
  const tuT=mm[3]+'/'+mm[2]+'/'+mm[1],denT=mm[6]+'/'+mm[5]+'/'+mm[4];
  const chu=e=>(e.innerText||'').trim().replace(/^[^\p{L}\p{N}]+/u,'').trim();      // bỏ biểu tượng đứng trước chữ (vd ↗ Xuất)
  const BTN='button,[role=button],[role=tab],a,label';
  const timNut=(re,goc)=>{const ds=[...(goc||document).querySelectorAll('button,[role=button],[role=tab],a,span,div,label')].filter(e=>vis(e)&&e.children.length<=4&&re.test(chu(e)));
    const diem=e=>(e.closest(BTN)?0:e.querySelector(BTN)?1:2);      // ưu tiên phần tử nằm TRONG nút (bấm lên trên mới tới nút), khối bọc ngoài nút xếp sau
    const e=ds.sort((a,b)=>diem(a)-diem(b)||(a.innerText||'').length-(b.innerText||'').length)[0];
    return e&&(e.closest(BTN)||e.querySelector(BTN)||e)};
  const khung=(tieu,nutRe)=>{for(const x of [...document.querySelectorAll('div,span,h1,h2,h3,h4')].filter(e=>vis(e)&&e.children.length===0&&tieu.test((e.innerText||'').trim()))){
      let p=x;for(let k=0;k<9&&p.parentElement;k++){p=p.parentElement;if([...p.querySelectorAll('button,[role=button]')].some(b=>vis(b)&&nutRe.test((b.innerText||'').trim())))return p}}return null};
  let doi=0;while(doi<40&&!timNut(/^Bộ lọc(\s*\(\d+\))?$/)){await sl(1000);doi++}
  // vào đúng tab "Tất cả" (sau khi đăng nhập TikTok có thể mở tab "Cần gửi"); đổi tab thì trang vẽ lại nên phải chờ rồi mới tìm nút Bộ lọc
  const tabTatCa=()=>timNut(/^Tất cả$/);
  const dangTatCa=()=>/[?&]tab=all\b/.test(location.search)||(()=>{const t=tabTatCa();return !!t&&(t.getAttribute('aria-selected')==='true'||/active|selected|checked/i.test((t.getAttribute('class')||'')+' '+((t.parentElement&&t.parentElement.getAttribute('class'))||'')))})();
  for(let l=0;l<3&&!dangTatCa();l++){const t=tabTatCa();if(!t)break;kich(t);await sl(2500)}
  await sl(1500);
  // 1) Bộ lọc -> chọn khoảng ngày
  const nutBl=()=>timNut(/^Bộ lọc(\s*\(\d+\))?$/);      // tìm lại MỖI lần bấm (nút cũ có thể đã bị vẽ lại)
  if(!nutBl()){loi('Không thấy nút Bộ lọc trên trang Quản lý đơn hàng TikTok.');return}
  const timDr=()=>{const k=khung(/^Bộ lọc$/,/^Áp dụng$/);if(k)return k;      // dự phòng: đi lên từ ô "Từ" tới khối có nút Áp dụng
    const o=[...document.querySelectorAll('input')].find(i=>vis(i)&&/^từ$/i.test((i.placeholder||'').trim()));if(!o)return null;
    let p=o;for(let k2=0;k2<12&&p.parentElement;k2++){p=p.parentElement;if([...p.querySelectorAll('button,[role=button]')].some(b=>vis(b)&&/^Áp dụng$/.test((b.innerText||'').trim())))return p}return null};
  __ketoanBao('mở Bộ lọc, chọn Thời gian đã tạo '+tuT+' – '+denT+'…');
  let dr=null;for(let l=0;l<4&&!dr;l++){const b=nutBl();if(b)kich(b);for(let w=0;w<8&&!(dr=timDr());w++)await sl(500)}      // trang vừa đăng nhập còn tải: bấm lại tối đa 3 lần
  if(!dr){const co=sao('Trang TikTok (Bộ lọc):\n'+dump([document.body]));loi('Không mở được khung Bộ lọc của TikTok.'+(co?'\nĐã COPY cấu trúc trang — dán (Ctrl+V) cho người hỗ trợ.':''));return}
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
  const ad=[...dr.querySelectorAll('button,[role=button]')].find(b=>vis(b)&&/^Áp dụng$/.test((b.innerText||'').trim()));if(!ad){loi('Không thấy nút Áp dụng.');return}
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
