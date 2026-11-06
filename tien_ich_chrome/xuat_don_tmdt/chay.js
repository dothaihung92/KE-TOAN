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
// hỏi phần mềm kế toán (qua phần nền tiện ích) file vừa tải đã XONG chưa; xong thì phần mềm lưu ra DESKTOP. Chạy bằng nút dấu trang (không có tiện ích) -> {loi}
const hoiNen=m=>new Promise(r=>{const h=setTimeout(()=>r({loi:'phần nền không trả lời'}),12000);try{if(!(window.chrome&&chrome.runtime&&chrome.runtime.sendMessage)){clearTimeout(h);r({loi:'không chạy trong tiện ích'});return}
  chrome.runtime.sendMessage(m,x=>{void chrome.runtime.lastError;clearTimeout(h);r(x||{loi:'phần nền không trả lời'})})}catch(e){clearTimeout(h);r({loi:String(e&&e.message||e)})}});
const choTai=(san,ms)=>hoiNen({loai:'cho-tai',san,ms});      // báo phần nền: lượt tải sắp tới là file đơn hàng -> tự lưu ra Desktop, không hiện hộp Save As
const choLuuDesktop=async(san,tu,khoang,ten)=>{      // sau khi bấm Tải về: chờ file tải XONG (kể cả khi Chrome hỏi "Save As") rồi phần mềm lưu ra Desktop
  const SAN={shopee:'Shopee',tiktok:'TikTok',lazada:'Lazada'}[san]||san;let f={};let daBaoLuc=0;
  for(let i=0;i<72;i++){      // tối đa ~6 phút
    f=await hoiNen({loai:'file-moi',san,tu,luu:0,khoang});
    if(f.co&&!f.dang_tai)break;if(f.loi&&(i>=2||/không chạy trong tiện ích/.test(f.loi)))break;
    const kt=await hoiNen({loai:'kq-tai',san});if(kt&&kt.loi&&kt.luc!==daBaoLuc){daBaoLuc=kt.luc;__ketoanBao('không tự lưu được file '+(kt.ten||'')+' ('+kt.loi+(kt.host?' — nguồn '+kt.host:'')+') — hãy bấm Save trong hộp "Save As" của Chrome; xong phần mềm tự nhận','#b26a00');await sl(5000);continue}
    __ketoanBao('đang chờ file '+SAN+(ten?' '+ten:'')+' tải xong ('+(i*5)+' giây)… nếu Chrome hiện hộp "Save As / Lưu thành" hãy bấm Save — xong phần mềm tự lưu ra Desktop','#1565c0');
    await sl(5000)}
  if(f.co&&!f.dang_tai){const r=await hoiNen({loai:'file-moi',san,tu,luu:1,khoang});
    const noi=r.desktop?'Đã lưu ra Desktop: '+r.desktop.split(/[\\/]/).pop():'Không chép được ra Desktop'+(r.loi_desktop?' ('+r.loi_desktop+')':'')+' — file: '+f.ten;
    __ketoanBao('xong: '+noi,'#2e7d32');alert('Đã tải đơn hàng '+SAN+(ten?' ('+ten+')':'')+'.\n'+noi+'\nPhần mềm kế toán sẽ tự nhận file.');return true}
  if(f.loi){__ketoanBao('đã bấm tải file '+SAN+' — không hỏi được phần mềm kế toán ('+f.loi+'), file nằm ở thư mục Downloads','#b26a00');
    alert('Đã bấm tải file '+SAN+(ten?' '+ten:'')+' — file đang tải vào thư mục Downloads.\nKhông kết nối được phần mềm kế toán ('+f.loi+') nên chưa lưu được ra Desktop.');return false}
  loi('Đã chờ ~6 phút nhưng chưa thấy file '+SAN+' tải xong — xem thanh tải xuống của Chrome (có thể Chrome đang chờ bạn bấm Save trong hộp "Save As").');return false};
// ---- chọn khoảng ngày trong bộ chọn lịch của hộp Xuất (thử theo cấu trúc lịch phổ biến; không được thì chụp cấu trúc lịch để chỉnh)
const sao=chu=>{try{const t=document.createElement('textarea');t.value=chu;t.style.cssText='position:fixed;left:-9999px';document.body.appendChild(t);t.select();document.execCommand('copy');t.remove();return true}catch(e){return false}};
const dump=(goc)=>{const gon=(e,d)=>{if(d>9)return'…';const t=e.tagName.toLowerCase(),c=(e.getAttribute('class')||'').split(/\s+/).filter(x=>x).slice(0,4).join('.');
    const k=[...e.children].filter(x=>vis(x)||x.children.length);const tx=(e.children.length===0?(e.innerText||'').trim().slice(0,14):'');
    return t+(c?'.'+c:'')+(tx?'['+tx+']':'')+(k.length?'{'+k.slice(0,40).map(x=>gon(x,d+1)).join(',')+'}':'')};
  return goc.map(e=>gon(e,0)).join('\n').slice(0,6000)};
const KHONG_PHAI=/disabled|out|other|prev|next|gray|grey|not-?current|outside|adjacent|last-?month|next-?month/i;
const thangNam=(e)=>{      // (năm, tháng) của 1 bảng ngày: đọc tiêu đề gần nhất (Shopee "Tháng 102026", TikTok "11 / 2026", "2026-11", "Th 11 2026"...); chỉ nhận tháng 1-12, năm 2000-2100
  const hl=(y,m)=>y>=2000&&y<=2100&&m>=1&&m<=12;
  {const c=e.closest&&e.closest('[class*=calendar-body-left],[class*=calendar-body-right]'),cal=c&&c.closest('[class*=next-calendar],[class*=calendar-range]');      // lịch Fusion (Lazada): tiêu đề trái/phải riêng "tháng 11" + "2026"
    if(c&&cal){const h=cal.querySelector(/right/.test(c.getAttribute('class')||'')?'[class*=panel-header-right]':'[class*=panel-header-left]');
      if(h){const ts=[...h.querySelectorAll('*')].filter(x=>!x.children.length).map(x=>(x.innerText||'').trim()),th=ts.map(x=>/(\d{1,2})/.exec(x)).find(x=>x&&+x[1]<=12),nm=ts.find(x=>/^\d{4}$/.test(x));      // nút "tháng 11" và nút "2026" tách riêng (innerText dính liền "tháng 112026")
        if(th&&nm&&hl(+nm,+th[1]))return[+nm,+th[1]]}}}
  for(let p=e,k=0;p&&k<6;p=p.parentElement,k++){const t=(p.innerText||'').normalize('NFC').slice(0,400);let r;
    const dn=/Th(?:áng)?\s*(\d{5,6})(?!\d)/i.exec(t);if(dn&&hl(+dn[1].slice(-4),+dn[1].slice(0,-4)))return[+dn[1].slice(-4),+dn[1].slice(0,-4)];
    const ms=[[/(\d{1,2})\s*[\/\-]\s*(\d{4})/g,2,1],[/(?<!\d)(\d{4})\s*[年\-\/\.]\s*(\d{1,2})(?!\d)/g,1,2],[/Th(?:áng)?\.?\s*(\d{1,2})[^\d]{1,6}(\d{4})/gi,2,1],[/th[^\s\d]{0,5}\s*(\d{1,2})[^\d]{1,6}(\d{4})/gi,2,1]];
    let tot=null;
    for(const [re,iy,im] of ms){re.lastIndex=0;while((r=re.exec(t))){if(hl(+r[iy],+r[im])&&(!tot||r.index<tot[2])){tot=[+r[iy],+r[im],r.index]}}}
    if(tot)return[tot[0],tot[1]]}
  return null};
const kich=e=>{if(!e||!e.getBoundingClientRect)return;const r=e.getBoundingClientRect(),o={bubbles:true,cancelable:true,view:window,clientX:r.left+r.width/2,clientY:r.top+r.height/2,button:0};      // chuỗi sự kiện chuột đầy đủ: nhiều bộ chọn ngày chỉ mở khi có mousedown/pointerdown
  for(const t of ['pointerdown','mousedown','pointerup','mouseup','click']){try{e.dispatchEvent(new (t.startsWith('pointer')&&window.PointerEvent?PointerEvent:MouseEvent)(t,o))}catch(_){}}try{e.focus&&e.focus()}catch(_){}};
let __truocChon=null;      // hàm chạy TRƯỚC khi chọn từng ngày (ix 0=bắt đầu, 1=kết thúc): Lazada phải bấm vào ô Ngày kết thúc để chuyển sang chọn ngày kết thúc
let __moLaiLich=null;      // hàm mở lại bảng lịch khi nó tự đóng giữa 2 lần chọn ngày (Lazada đóng bảng sau khi chọn ngày bắt đầu)
let __that=false;      // true: bấm bằng CHUỘT THẬT (Chrome debugger) vì trang bỏ qua sự kiện giả lập (Lazada)
const diemBam=e=>{const b=e.getBoundingClientRect();      // điểm bấm KHÔNG bị phần tử khác (hộp thông báo nổi...) che: thử giữa, trái, phải, trên, dưới
  for(const [fx,fy] of [[.5,.5],[.2,.5],[.35,.5],[.8,.5],[.5,.25],[.5,.8]]){const x=b.left+b.width*fx,y=b.top+b.height*fy,t=document.elementFromPoint(x,y);if(t&&(t===e||e.contains(t)||t.contains(e)))return [x,y]}
  return [b.left+b.width/2,b.top+b.height/2]};
const kichThat=e=>new Promise(r=>{try{if(!e){r({});return}try{e.scrollIntoView({block:'center',inline:'nearest'})}catch(_){}const [px,py]=diemBam(e);chrome.runtime.sendMessage({loai:'click-that',x:px,y:py},x=>{void chrome.runtime.lastError;r(x||{})})}catch(_){r({})}});
const kichBen=async e=>{const r=await kichThat(e);if(!r||!r.ok)kich(e)};      // chuột thật; không dùng được (chưa cấp quyền gỡ lỗi...) thì quay về sự kiện giả lập
const kichX=async e=>{if(!e)return;if(__that)await kichBen(e);else kich(e)};
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
  const cs0=soLeaf(p),n=e=>+(e.innerText||'').trim();
  if(cs0.some(e=>e.closest('[class*=cell-prev-month],[class*=cell-next-month]')))return cs0.filter(e=>n(e)===d&&!e.closest('[class*=cell-prev-month],[class*=cell-next-month]'));      // lịch Fusion/Lazada: ô ngoài tháng có lớp riêng
  const cs=cs0;const i1=cs.findIndex(e=>n(e)===1);if(i1<0)return [];
  let i2=cs.findIndex((e,j)=>j>i1&&n(e)===1);if(i2<0)i2=cs.length;return cs.slice(i1,i2).filter(e=>n(e)===d)};
const gocLich=()=>{const ds=timLich();if(!ds.length)return null;let g=ds[0];      // khối chứa TẤT CẢ bảng ngày + tiêu đề tháng (không leo quá xa ra ngoài trang)
  for(let k=0;k<10&&g.parentElement&&g.parentElement!==document.body;k++){g=g.parentElement;if(ds.every(p=>g.contains(p))&&/th[aá]ng|\d{1,2}\s*\/\s*\d{4}|\d{4}/i.test((g.innerText||'').slice(0,200)))break}
  return g};
const muiTen=(lui)=>{      // các ứng viên mũi tên lùi/tới 1 THÁNG trong lịch đang mở (không lấy « » năm, không lấy ô ngày)
  const g=gocLich();if(!g)return [];let r=g;for(let k=0;k<3&&r.parentElement&&r.parentElement!==document.body;k++)r=r.parentElement;
  const ngoai=e=>!e.closest('td,[class*=calendar-cell],[class*=sider],[class*=sidebar],aside,nav');
  const ds=[];const them=e=>{if(e&&vis(e)&&ngoai(e)&&!ds.includes(e))ds.push(e)};
  // 1) lớp của lịch Fusion/Ant: ...btn-prev-month / prev-month-btn / ant-picker-header-prev-btn
  r.querySelectorAll(lui?'[class*=prev-month],[class*=month-prev],[class*=header-prev-btn]':'[class*=next-month],[class*=month-next],[class*=header-next-btn]').forEach(e=>{if(!/year|super|double/i.test(e.getAttribute('class')||''))them(e.closest('button,a,[role=button]')||e)});
  // 2) theo VỊ TRÍ: cùng hàng tiêu đề tháng, sát tiêu đề nhất
  const ti=[...g.querySelectorAll('*')].filter(e=>vis(e)&&e.children.length<=2&&/^(th[aá]ng\s*\d{1,2}(\s+\d{4})?|\d{1,2}\s*\/\s*\d{4}|\d{4}\s*[-\/年]\s*\d{1,2}月?)$/i.test((e.innerText||'').trim())).sort((a,b)=>a.getBoundingClientRect().left-b.getBoundingClientRect().left);
  if(ti.length){const A=ti[0].getBoundingClientRect(),Z=ti[ti.length-1].getBoundingClientRect(),cy=(A.top+A.bottom)/2;
    const ung=[...r.querySelectorAll('button,a,i,svg,span,div')].filter(e=>vis(e)&&ngoai(e)&&!/\d/.test(e.innerText||'')&&e.getBoundingClientRect().width<=44&&e.getBoundingClientRect().height<=44).map(e=>({e,b:e.getBoundingClientRect()})).filter(x=>Math.abs((x.b.top+x.b.bottom)/2-cy)<=16);
    (lui?ung.filter(x=>x.b.right<=A.left+2).sort((p,q)=>q.b.left-p.b.left):ung.filter(x=>x.b.left>=Z.right-2).sort((p,q)=>p.b.left-q.b.left)).slice(0,2).forEach(x=>them(x.e.closest('button,a,[role=button]')||x.e))}
  // 3) chữ ‹ ›
  [...r.querySelectorAll('*')].filter(e=>e.children.length===0&&(lui?/^[‹<]$/:/^[›>]$/).test((e.innerText||'').trim())).forEach(them);
  // 4) theo lớp/nhãn chung (TikTok/Arco: biểu tượng svg 'arco-icon-left' trong 'picker-header-icon'): prev/left — bỏ nút năm (super/double/year)
  const lop=lui?/prev|pre-|left/i:/next|right/i,bo=/super|year|double|fast|dbl|panel-header|sider|menu|nav/i;
  [...r.querySelectorAll('*')].filter(e=>{if(!vis(e)||/\d/.test(e.innerText||''))return false;const k=(e.getAttribute('class')||'')+' '+(e.getAttribute('aria-label')||'');const b=e.getBoundingClientRect();
    return lop.test(k)&&!bo.test(k)&&!bo.test((e.parentElement&&e.parentElement.getAttribute('class'))||'')&&b.width<60&&b.height<60}).forEach(e=>them(e.closest('button,a,[role=button],[class*=header-icon],[class*=btn]')||e));
  return ds};
const doiThang=async(lui)=>{      // bấm mũi tên lùi/tới 1 tháng; CHỈ coi là được khi tháng hiển thị thực sự đổi
  const tn=()=>JSON.stringify(layTnChung().map(x=>x.tn));const truoc=tn();
  for(const c of muiTen(lui).slice(0,4)){await kichX(c);for(let w=0;w<6;w++){await sl(250);if(tn()!==truoc)return true}}
  return false};
const moTaLich=()=>{const g=gocLich();return 'Tháng đọc được: '+JSON.stringify(layTnChung().map(x=>x.tn))+'\nMũi tên lùi: '+muiTen(true).map(e=>e.tagName+'.'+(e.getAttribute('class')||'')).join(' | ')+'\nMũi tên tới: '+muiTen(false).map(e=>e.tagName+'.'+(e.getAttribute('class')||'')).join(' | ')+'\n--- khối lịch ---\n'+(g?dump([g.parentElement&&g.parentElement!==document.body?g.parentElement:g]).slice(0,5000):'(không thấy)')};
const chonNgayLich=async(y,mo,d,ix)=>{      // chọn 1 ngày trong lịch đang mở (tự lùi/tới tháng nếu cần)
  if(__truocChon&&ix!==undefined)await __truocChon(ix);
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
async function __ketoanLazada(){      // Lazada: Đơn đặt hàng -> Tất cả -> Tuỳ chỉnh (ngày bắt đầu - kết thúc) -> OK -> Xuất khẩu -> Export All -> OK -> chờ chuẩn bị xong -> Tải về Tập Tin -> phần mềm chép file ra Desktop
  const mm=/(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})/.exec(thamSo||'');
  if(!mm){loi('Chưa có khoảng ngày từ phần mềm kế toán — hãy chọn ngày trong phần mềm rồi bấm Mở trang.');return}
  const tuI=mm[1]+'-'+mm[2]+'-'+mm[3],denI=mm[4]+'-'+mm[5]+'-'+mm[6];
  const chu=e=>(e.innerText||e.value||'').trim().replace(/^[^\p{L}\p{N}]+/u,'').trim();
  const BTN='button,[role=button],[role=tab],[role=menuitem],a,label,li';
  const timNut=(re,goc)=>{const ds=[...(goc||document).querySelectorAll('button,[role=button],[role=tab],[role=menuitem],a,span,div,label,li')].filter(e=>vis(e)&&e.children.length<=4&&re.test(chu(e)));
    const diem=e=>(e.closest(BTN)?0:e.querySelector(BTN)?1:2);
    const e=ds.sort((a,b)=>diem(a)-diem(b)||(a.innerText||'').length-(b.innerText||'').length)[0];return e&&(e.closest(BTN)||e.querySelector(BTN)||e)};
  // đóng các hộp giới thiệu (FFR+, Yêu cầu giao hàng nhanh...) che trang: bấm 'Nhận được Bắt Đầu'/'Got it'/dấu ×
  const dongGt=async()=>{let n=0;for(let k=0;k<8;k++){const b=timNut(/^(Nhận được Bắt Đầu|Nhận được|Bắt Đầu|Got it|Đã hiểu|Bỏ qua|Skip)$/i)||[...document.querySelectorAll('[class*=guide] [class*=close],[class*=tour] [class*=close],[class*=popover] [class*=close],[class*=modal] [class*=close],[aria-label=Close],[aria-label=close],[class*=notification] [class*=close],[class*=notification-operate-btn],[class*=pin] [class*=close]')].filter(vis)[0];
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
    kich(timNut(RT)||tc);await choBat();                                    // lần 1: sự kiện chuột giả lập
    if(!daBat()){const e=timNut(RT);if(e){try{e.click()}catch(_){}await choBat()}}
    if(!daBat()){const e=timNut(RT);if(e){__ketoanBao('trang không nhận bấm giả lập — dùng chuột thật (Chrome sẽ hiện thanh "đang gỡ lỗi", bình thường)…','#1565c0');await kichBen(e);await choBat()}}
  }
  if(!daBat()){const co=sao('Trang Lazada (Tùy chỉnh):\n'+dump([document.body]).slice(0,6000));loi('Đã bấm "Tùy chỉnh" nhưng ô Ngày bắt đầu vẫn bị khóa.'+(co?'\nĐã COPY cấu trúc trang — dán (Ctrl+V) cho người hỗ trợ.':''));return}
  await sl(500);
  const oNgay=()=>[...document.querySelectorAll('input')].filter(vis);
  const oBd=oNgay().find(i=>/Ngày bắt đầu|Start/i.test(i.placeholder||''))||oNgay().find(i=>/^\d{4}-\d{2}-\d{2}/.test(i.value||''));
  if(!oBd){loi('Không thấy ô "Ngày bắt đầu" sau khi bấm Tùy chỉnh.');return}
  const oYmd=()=>oNgay().filter(i=>/YYYY/i.test(i.placeholder||'')||(/^\d{4}-\d{2}-\d{2}$/.test(i.value||'')&&i!==oBd));
  const bangMo=()=>oYmd().length>=2||timLich().length>0;
  // mở bảng chọn ngày: bấm ô Ngày bắt đầu, rồi các phần tử bao quanh / biểu tượng lịch cho tới khi bảng hiện (chờ tối đa ~3 giây mỗi lần thử)
  const khungO=oBd.closest('[class*=range-picker],[class*=date-picker],[class*=picker]')||(oBd.parentElement&&oBd.parentElement.parentElement)||oBd;      // CHỈ các phần tử của ô chọn ngày (không bấm nhầm mũi tên thu gọn menu bên trái)
  const ungMo=[oBd,oBd.parentElement,oBd.parentElement&&oBd.parentElement.parentElement,...[...khungO.querySelectorAll('[class*=calendar],[class*=icon],svg,i')].filter(vis)].filter(Boolean);
  let mo=bangMo();
  for(const e of ungMo.slice(0,6)){if(mo)break;kich(e);try{e.click()}catch(_){}for(let w=0;w<4&&!(mo=bangMo());w++)await sl(400)}
  for(const e of ungMo.slice(0,3)){if(mo)break;await kichBen(e);for(let w=0;w<5&&!(mo=bangMo());w++)await sl(400)}      // chưa mở -> chuột thật
  if(!mo){const co=sao('Trang Lazada (chọn ngày):\n'+dump([document.body]));loi('Không mở được bảng chọn ngày của Lazada sau khi bấm Tùy chỉnh.'+(co?'\nĐã COPY cấu trúc trang — dán (Ctrl+V) cho người hỗ trợ.':''));return}
  // KHÔNG gõ ngày vào ô (Lazada hiểu sai chữ gõ, vd 2026-10-29 thành 2026-11-02): chỉ bấm ngày trên lịch bằng CHUỘT THẬT và đọc lại giá trị để kiểm tra
  const giaTri=()=>oNgay().map(i=>i.value).join(' ');
  const daDung=()=>{const v=giaTri();return v.includes(tuI)&&v.includes(denI)};
  __that=true;
  const oBang=()=>oNgay().filter(i=>/YYYY/i.test(i.placeholder||'')||/^\d{4}-\d{2}-\d{2}$/.test(i.value||''));
  __moLaiLich=async()=>{const ket=oNgay().find(i=>/Ngày kết thúc|End/i.test(i.placeholder||''));      // bảng lịch tự đóng -> bấm ô Ngày kết thúc / Ngày bắt đầu để mở lại
    for(const e of [ket,ket&&ket.parentElement,oBd].filter(Boolean)){await kichBen(e);for(let w=0;w<6&&!timLich().length;w++)await sl(400);if(timLich().length)return true}return false};
  const focusO=async ix=>{      // bấm vào ô tương ứng để Lazada chuyển sang chọn ngày bắt đầu (0) / kết thúc (1)
    const b=oBang();let o=ix===1?(b.find(i=>!i.value)||b[1]):b[0];
    if(!o&&ix===1)o=oNgay().find(i=>/Ngày kết thúc|End/i.test(i.placeholder||''));
    if(o){await kichBen(o);for(let w=0;w<5&&!timLich().length;w++)await sl(400)}
    if(!timLich().length&&o){let g=o;for(let k=0;k<3&&g.parentElement;k++){g=g.parentElement;const ic=[...g.querySelectorAll('svg,i,[class*=icon],[class*=calendar]')].filter(vis).pop();if(ic){await kichBen(ic);for(let w=0;w<6&&!timLich().length;w++)await sl(400);break}}}
    if(!timLich().length)await __moLaiLich()};
  const chonKT=async(y,mo,d,ix,iso)=>{
    for(let lan=0;lan<4;lan++){
      __ketoanBao('chọn ngày '+(ix?'KẾT THÚC ':'BẮT ĐẦU ')+iso+(lan?' (thử lại lần '+lan+')':'')+'…','#1565c0');
      if(!timLich().length)await __moLaiLich();
      if(ix===1||lan>0)await focusO(ix);
      const ok=await chonNgayLich(y,mo,d);await sl(800);
      if(ok&&giaTri().includes(iso))return true}
    return false};
  if(!timLich().length){await kichBen(oBd);await sl(1200)}
  if(!daDung()){
    const ok1=await chonKT(+mm[1],+mm[2],+mm[3],0,tuI),ok2=ok1&&await chonKT(+mm[4],+mm[5],+mm[6],1,denI);
    if(!ok1||!ok2){const co=sao('Lịch Lazada ('+(ok1?denI:tuI)+') — ô ngày: '+giaTri()+'\n'+moTaLich());loi('Chưa tự chọn được ngày '+(ok1?'kết thúc '+denI:'bắt đầu '+tuI)+' trong lịch Lazada (các ô ngày đang: '+(giaTri().trim()||'trống')+').'+(co?'\nĐã COPY cấu trúc lịch — dán (Ctrl+V) cho người hỗ trợ.':''));return}}
  const ok=timNut(/^OK$/);if(ok){kich(ok);await sl(2500)}
  const v=oNgay().map(i=>i.value).join(' ');
  if(!(v.includes(tuI)&&v.includes(denI))){loi('Ô Ngày đặt hàng của Lazada chưa đúng '+tuI+' – '+denI+' (đang: '+(oBd.value||'trống')+'). Hãy tự chọn ngày, bấm OK rồi bấm nút ▶ Xuất đơn (Kế toán).');return}
  // 2) Xuất khẩu -> Export All -> OK (KHÔNG mở Export History)
  // Lazada BỎ QUA bấm giả lập ở menu Xuất khẩu -> mọi bước dưới đây đều bấm bằng CHUỘT THẬT; nút Xuất khẩu dạng bật/tắt nên chỉ bấm khi menu CHƯA mở, và chờ menu hiện (có hiệu ứng trễ)
  const RXK=/^(Xuất khẩu|Export)$/i,REA=/^(Export All|Xuất tất cả|Xuất toàn bộ)$/i;
  const la=re=>{const t=[...document.querySelectorAll('li,[role=menuitem],[class*=menu-item],[class*=dropdown] *,[class*=overlay] *,[class*=popup] *,span,div,a,button')].filter(e=>vis(e)&&e.children.length<=3&&re.test((e.textContent||'').replace(/\s+/g,' ').trim()));
    t.sort((x,y)=>(x.textContent||'').length-(y.textContent||'').length);const e=t[0];return e&&(e.closest('li,[role=menuitem],[class*=menu-item],button,a')||e)};
  const muc=re=>timNut(re)||la(re);
  const cho=async(f,n)=>{for(let w=0;w<n;w++){const x=f();if(x)return x;await sl(300)}return f()};
  const moMenu=async re=>{      // mở menu Xuất khẩu cho tới khi thấy mục re (Export All)
    let m=await cho(()=>muc(re),2);if(m)return m;
    const x=timNut(RXK);if(!x)return null;
    for(const t of ['mouseover','mouseenter'])x.dispatchEvent(new MouseEvent(t,{bubbles:true}));
    m=await cho(()=>muc(re),4);if(m)return m;
    for(let lan=0;lan<3;lan++){const y=timNut(RXK)||x;await kichBen(y);m=await cho(()=>muc(re),10);if(m)return m}
    return null};
  const lopNoi=()=>[...document.querySelectorAll('[role=dialog],.next-dialog,.next-overlay-inner,.ant-modal,.next-drawer,[class*=dialog],[class*=drawer],[class*=modal]')].filter(e=>vis(e)&&e.getBoundingClientRect().width>300);
  __ketoanBao('bấm Xuất khẩu → Export All…','#1565c0');
  if(!timNut(RXK)&&!muc(REA)){loi('Không thấy nút "Xuất khẩu" trên trang Lazada.');return}
  const ea=await moMenu(REA);
  if(!ea){const co=sao('Trang Lazada (menu Xuất khẩu):\n'+dump([document.body]).slice(0,8000));loi('Không thấy mục "Export All" trong menu Xuất khẩu.'+(co?'\nĐã COPY cấu trúc trang — dán (Ctrl+V) cho người hỗ trợ.':''));return}
  const tXuat=Date.now();await choTai('lazada',900000);await kichBen(ea);
  // hộp Confirm Export -> OK (chuột thật); chưa đóng thì bấm lại
  const nutXn=()=>lopNoi().map(o=>[...o.querySelectorAll('button')].find(b=>vis(b)&&/^(OK|Xác nhận|Confirm|Đồng ý)$/i.test(chu(b)))).filter(Boolean).pop();
  let xn=await cho(nutXn,12);
  for(let lan=0;xn&&lan<3;lan++){await kichBen(xn);await sl(1200);xn=nutXn()}
  if(xn){loi('Đã bấm Export All nhưng không bấm được nút OK của hộp "Confirm Export" — hãy tự bấm OK trên trang Lazada.');return}
  // 3) CHỜ Lazada chuẩn bị dữ liệu xong (hộp "Xuất khẩu Dữ Liệu" báo "Các nhiệm vụ chạy thành công!" + "Tải về Tập Tin"), file tải vào Downloads -> phần mềm chép ra DESKTOP
  const hoi=m=>new Promise(r=>{const h=setTimeout(()=>r({loi:'phần nền không trả lời'}),12000);try{chrome.runtime.sendMessage(m,x=>{void chrome.runtime.lastError;clearTimeout(h);r(x||{loi:'phần nền không trả lời'})})}catch(e){clearTimeout(h);r({loi:String(e&&e.message||e)})}});
  const khoang=tuI+'_'+denI,hoiFile=luu=>hoi({loai:'file-moi',san:'lazada',tu:tXuat,luu:luu?1:0,khoang});
  const hopXk=()=>{const ds=lopNoi();return ds.filter(o=>/Xuất khẩu Dữ Liệu|Export Data|nhiệm vụ|task/i.test(o.innerText||'')).pop()||ds.pop()};
  const RLK=/^(Tải về Tập Tin|Tải về tập tin|Tải về file|Download File|Download Result File|Tải về|Download)$/i;
  const lienKet=()=>{const o=hopXk();return o&&[...o.querySelectorAll('a,button,span,[role=button]')].filter(e=>vis(e)&&RLK.test(chu(e))).map(e=>e.closest('a,button,[role=button]')||e).pop()};
  const xong=()=>{const o=hopXk();return !!lienKet()||!!(o&&/chạy thành công|thành công!|successful|succeeded/i.test(o.innerText||''))};
  const hong=()=>{const o=hopXk();return !!(o&&/thất bại|không thành công|failed/i.test(o.innerText||''))};
  let f={},daBam=false,lanLoi=0;
  for(let i=0;i<120;i++){      // tối đa ~10 phút
    f=await hoiFile(false);if(f.loi)lanLoi++;
    if(f.co&&!f.dang_tai)break;
    if(hong()){loi('Lazada báo xuất dữ liệu KHÔNG thành công — hãy bấm Xuất đơn lại.');return}
    if(xong()&&!f.dang_tai){
      if(!daBam){for(let w=0;w<3&&!(f.co&&!f.dang_tai);w++){await sl(2000);f=await hoiFile(false)}      // Lazada tự tải trong giây lát; chưa có thì bấm "Tải về Tập Tin"
        if(f.co&&!f.dang_tai)break;
        const l=lienKet();if(l){__ketoanBao('Lazada đã chuẩn bị xong — bấm "Tải về Tập Tin"…','#1565c0');await choTai('lazada');await kichBen(l);daBam=true;await sl(3000);continue}}
      if(f.loi&&lanLoi>=3)break}
    __ketoanBao((xong()?'đang tải file Lazada về máy':'Lazada đang chuẩn bị dữ liệu')+' ('+(i*5)+' giây)… phần mềm chờ xong sẽ lưu ra Desktop','#1565c0');
    await sl(5000)}
  if(f.co&&!f.dang_tai){await choLuuDesktop('lazada',tXuat,khoang,'');return}
  if(f.loi){__ketoanBao('đã bấm Export All → OK'+(daBam?' và Tải về Tập Tin':'')+' — không hỏi được phần mềm kế toán ('+f.loi+')','#b00020');
    alert('Đã bấm Xuất khẩu → Export All → OK trên Lazada'+(daBam?' và "Tải về Tập Tin"':'')+'.\nKhông kết nối được phần mềm kế toán ('+f.loi+') nên chưa chép được file ra Desktop — file nằm ở thư mục Downloads. Hãy mở phần mềm kế toán rồi bấm Mở trang lại nếu cần.');return}
  loi('Đã chờ ~10 phút nhưng chưa thấy file Lazada tải về thư mục Downloads — hãy bấm "Tải về Tập Tin" trong hộp Xuất khẩu Dữ Liệu (hoặc Xem Lịch Sử) để tải tay.');
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
  if(!ok1||!ok2){const co=sao('Lịch TikTok ('+(ok1?denT:tuT)+'):\n'+moTaLich());loi('Chưa tự chọn được ngày '+(ok1?denT:tuT)+' trong lịch Bộ lọc TikTok.'+(co?'\nĐã COPY cấu trúc lịch — dán (Ctrl+V) cho người hỗ trợ.':'')+'\nBạn có thể tự chọn ngày, bấm Áp dụng rồi bấm Xuất.');return}
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
          if(t.length===1&&!cu.has(ten)){const t0=Date.now();await choTai('tiktok');n.click();__ketoanBao('đã bấm Tải xuống '+ten+' — chờ file tải xong…','#1565c0');await choLuuDesktop('tiktok',t0,mm[1]+'-'+mm[2]+'-'+mm[3]+'_'+mm[4]+'-'+mm[5]+'-'+mm[6],ten);return}break}}}}
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
  const kh=m?m[1]+'-'+m[2]+'-'+m[3]+'_'+m[4]+'-'+m[5]+'-'+m[6]:(dang?[dang[0],dang[1]].map(x=>chuan(x).replace(/(\d{4})(\d{2})(\d{2})/,'$1-$2-$3')).join('_'):'');
  if(!ten){const t0=Date.now();await choTai('shopee');const t=bam(/^(Tải về|Tải xuống|Download)$/,true)||bam(/^(Tải về|Tải xuống|Download)$/);if(t){__ketoanBao('đã bấm Tải về — chờ file tải xong…','#1565c0');await choLuuDesktop('shopee',t0,kh,'');return}continue}
  const n=tim();if(n){const t0=Date.now();await choTai('shopee');n.click();__ketoanBao('đã bấm Tải về báo cáo '+ten+' — chờ file tải xong…','#1565c0');await choLuuDesktop('shopee',t0,kh,ten);return}}
loi('Báo cáo '+ten+' chưa sẵn sàng sau ~5 phút — chờ thêm rồi tự bấm Tải về ĐÚNG báo cáo '+ten+' trong Lịch sử Xuất Báo cáo.');
}
