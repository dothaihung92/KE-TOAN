// Phần nền của tiện ích: (1) đổi mã dùng 1 lần lấy tài khoản sàn của công ty từ phần mềm kế toán trên máy (127.0.0.1);
// (2) xoá cookie đăng nhập của sàn để đăng xuất tài khoản đang mở; (3) giữ tài khoản tạm + việc đang chờ (bộ nhớ phiên, theo TỪNG SÀN — trang đăng nhập có thể mở ở thẻ mới).
const MIEN={'banhang.shopee.vn':'shopee.vn','accounts.shopee.vn':'shopee.vn','seller-vn.tiktok.com':'tiktok.com','sellercenter.lazada.vn':'lazada.vn'};
const GAN=new Map();      // thẻ đang gắn debugger -> hẹn giờ gỡ
chrome.debugger.onDetach.addListener((src)=>{if(src.tabId)GAN.delete(src.tabId)});
chrome.runtime.onMessage.addListener((m,s,tl)=>{(async()=>{
  let h='';try{h=new URL(s.url||(s.tab&&s.tab.url)||'').host}catch(e){}
  const site=MIEN[h]||h,k='tk_'+site,kc='cho_'+site;
  try{
    if(m.loai==='lay-tk'){
      const r=await fetch('http://127.0.0.1:'+(+m.p||8686)+'/api/san-tmdt/tk-mot-lan?t='+encodeURIComponent(m.kt));
      if(!r.ok){tl({loi:'Không lấy được tài khoản từ phần mềm kế toán ('+r.status+') — mã đã dùng/hết hạn, hãy bấm Mở trang lại.'});return}
      const t=await r.json();await chrome.storage.session.set({[k]:{user:t.user,pass:t.pass,han:Date.now()+600000,lan:0}});
      tl({user:t.user,ten_shop:t.ten_shop||''});return}
    if(m.loai==='dang-xuat'){
      const d=MIEN[m.host];if(!d){tl({n:0});return}
      const cs=await chrome.cookies.getAll({domain:d});let n=0;
      for(const c of cs){try{await chrome.cookies.remove({url:'https://'+c.domain.replace(/^\./,'')+c.path,name:c.name,storeId:c.storeId});n++}catch(e){}}
      tl({n});return}
    if(m.loai==='tk-cho-tab'){
      const o=(await chrome.storage.session.get(k))[k];
      if(!o||o.han<Date.now()||o.lan>=2){tl({});return}
      o.lan++;await chrome.storage.session.set({[k]:o});tl({user:o.user,pass:o.pass});return}
    if(m.loai==='co-tk'){const o=(await chrome.storage.session.get(k))[k];tl({co:!!(o&&o.han>Date.now()&&o.lan<2),chua_dung:!!(o&&o.han>Date.now()&&o.lan===0)});return}
    if(m.loai==='xoa-tk'){await chrome.storage.session.remove(k);tl({});return}
    if(m.loai==='click-that'){      // chuột THẬT (isTrusted) qua chrome.debugger; giữ kết nối ~20 giây để các lần bấm liên tiếp không chớp thanh 'đang gỡ lỗi'
      const t={tabId:s.tab.id};
      if(!GAN.has(t.tabId)){await chrome.debugger.attach(t,'1.3');GAN.set(t.tabId,0)}
      clearTimeout(GAN.get(t.tabId));GAN.set(t.tabId,setTimeout(async()=>{GAN.delete(t.tabId);try{await chrome.debugger.detach(t)}catch(e){}},20000));
      for(const ty of ['mouseMoved','mousePressed','mouseReleased'])await chrome.debugger.sendCommand(t,'Input.dispatchMouseEvent',{type:ty,x:m.x,y:m.y,button:'left',buttons:ty==='mousePressed'?1:0,clickCount:ty==='mouseMoved'?0:1});
      await new Promise(r=>setTimeout(r,200));tl({ok:1});return}
    if(m.loai==='luu-cong'){await chrome.storage.local.set({cong:+m.p||8686});tl({});return}
    if(m.loai==='file-moi'){      // hỏi phần mềm kế toán: đã có file MỚI tải xong trong Downloads chưa (luu=1: chép ra Desktop)
      const cong=(await chrome.storage.local.get('cong')).cong||8686;
      const r=await fetch('http://127.0.0.1:'+cong+'/api/san-tmdt/file-moi?san='+encodeURIComponent(m.san)+'&tu='+(+m.tu||0)+'&luu='+(m.luu?1:0)+'&khoang='+encodeURIComponent(m.khoang||''));
      tl(r.ok?await r.json():{loi:'Phần mềm kế toán trả lỗi '+r.status});return}
    if(m.loai==='luu-cho'){await chrome.storage.session.set({[kc]:m.cho});tl({});return}
    if(m.loai==='lay-cho'){const o=(await chrome.storage.session.get(kc))[kc];tl({cho:o&&o.han>Date.now()?o:null});return}
    if(m.loai==='xoa-cho'){await chrome.storage.session.remove(kc);tl({});return}
    tl({})
  }catch(e){tl({loi:String(e&&e.message||e)})}})();return true});
