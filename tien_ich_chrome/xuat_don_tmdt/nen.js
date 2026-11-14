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
    if(m.loai==='cho-tai'){await chrome.storage.session.set({cho_tai:{san:m.san,tabId:s.tab&&s.tab.id,han:Date.now()+(+m.ms||180000)}});await chrome.storage.session.remove('kq_tai_'+m.san);tl({});return}
    if(m.loai==='kq-tai'){tl((await chrome.storage.session.get('kq_tai_'+m.san))['kq_tai_'+m.san]||{});return}
    if(m.loai==='luu-cong'){await chrome.storage.local.set({cong:+m.p||8686});tl({});return}
    if(m.loai==='file-moi'){      // hỏi phần mềm kế toán: đã có file MỚI tải xong trong Downloads chưa (luu=1: chép ra Desktop)
      const cong=(await chrome.storage.local.get('cong')).cong||8686;
      const r=await fetch('http://127.0.0.1:'+cong+'/api/san-tmdt/file-moi?san='+encodeURIComponent(m.san)+'&tu='+(+m.tu||0)+'&luu='+(m.luu?1:0)+'&khoang='+encodeURIComponent(m.khoang||''));
      tl(r.ok?await r.json():{loi:'Phần mềm kế toán trả lỗi '+r.status});return}
    if(m.loai==='nh-lay-tk'){      // đổi mã dùng 1 lần lấy tài khoản internet banking đã lưu trong thông tin công ty; giữ ở bộ nhớ phiên 10 phút, mỗi trang đăng nhập lấy tối đa 3 lần
      const r=await fetch('http://127.0.0.1:'+(+m.p||8686)+'/api/ngan-hang/tk-mot-lan?t='+encodeURIComponent(m.kt));
      if(!r.ok){tl({loi:'mã hết hạn hoặc đã dùng — bấm “Mở ngân hàng” trong phần mềm lại'});return}
      const t=await r.json();await chrome.storage.session.set({nh_tk:{user:t.user,pass:t.pass,han:Date.now()+600000,lan:0}});tl({ok:1});return}
    if(m.loai==='nh-tk-cho'){const o=(await chrome.storage.session.get('nh_tk')).nh_tk;
      if(!o||o.han<Date.now()||o.lan>=3){tl({});return}
      o.lan++;await chrome.storage.session.set({nh_tk:o});tl({user:o.user,pass:o.pass});return}
    if(m.loai==='nh-xoa-tk'){await chrome.storage.session.remove('nh_tk');tl({});return}
    if(m.loai==='nh-ocr-captcha'){      // OCR captcha: clip (chụp màn hình + crop) hoặc url (fetch+cookie) hoặc b64
      let b64=m.b64, clip=m.clip;
      if(!b64&&clip){       // Chụp toàn trang, server sẽ crop theo clip
        try{
          b64=await chrome.tabs.captureVisibleTab(null,{format:'png'});
        }catch(e){}
      }
      if(!b64&&m.url){      // Fetch URL với cookie ngân hàng
        try{
          const u=new URL(m.url);
          const cs=await chrome.cookies.getAll({domain:u.hostname.replace(/^www\./,'')});
          const ck=cs.map(c=>c.name+'='+c.value).join('; ');
          const r=await fetch(m.url,{headers:{Cookie:ck}});
          if(r.ok){const buf=await r.arrayBuffer();const u8=new Uint8Array(buf);let s='';for(let i=0;i<u8.length;i+=0x8000)s+=String.fromCharCode.apply(null,u8.subarray(i,i+0x8000));b64='data:;base64,'+btoa(s)}
        }catch(e){}
      }
      if(!b64){tl({ok:false,ma:''});return}
      const body={b64};if(clip)body.clip=clip;
      const r=await fetch('http://127.0.0.1:'+(+m.p||8686)+'/api/ocr-captcha',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      tl(r.ok?await r.json():{ok:false,ma:''});return}
    if(m.loai==='nh-file-moi'){      // sao kê ngân hàng: hỏi phần mềm kế toán đã đọc được file sao kê mới tải về chưa
      const r=await fetch('http://127.0.0.1:'+(+m.p||8686)+'/api/ngan-hang/file-moi?j='+encodeURIComponent(m.j||''));
      tl(r.ok?await r.json():{loi:['Phần mềm kế toán trả lỗi '+r.status]});return}
    if(m.loai==='luu-cho'){await chrome.storage.session.set({[kc]:m.cho});tl({});return}
    if(m.loai==='lay-cho'){const o=(await chrome.storage.session.get(kc))[kc];tl({cho:o&&o.han>Date.now()?o:null});return}
    if(m.loai==='xoa-cho'){await chrome.storage.session.remove(kc);tl({});return}
    tl({})
  }catch(e){tl({loi:String(e&&e.message||e)})}})();return true});

// Tải file đơn hàng KHÔNG qua hộp "Save As" của Chrome (người dùng bật "Hỏi vị trí lưu từng tệp"): khi tiện ích vừa bấm Tải về trên trang sàn (cờ cho_tai),
// Chrome hỏi tên file -> tiện ích tự lấy nội dung file (theo địa chỉ tải; blob: thì nhờ trang lấy), gửi phần mềm kế toán lưu thẳng ra DESKTOP rồi huỷ lượt tải của Chrome.
// Không lấy được thì để Chrome tải như bình thường (hộp Save As vẫn hiện) và ghi lý do.
const b64Cua=async b=>{const u=new Uint8Array(await b.arrayBuffer());let s='';for(let i=0;i<u.length;i+=0x8000)s+=String.fromCharCode.apply(null,u.subarray(i,i+0x8000));return 'data:;base64,'+btoa(s)};
chrome.downloads.onDeterminingFilename.addListener((it,suggest)=>{(async()=>{let xong=false,o=null;
  try{o=(await chrome.storage.session.get('cho_tai')).cho_tai;
    let ten=String(it.filename||'').split(/[\\/]/).pop();
    const duoi=/\.(xlsx|xls|csv)$/i.test(ten),mime=String(it.mime||'');
    if(o&&o.han>Date.now()&&(duoi||/sheet|excel|csv|octet-stream|zip/i.test(mime))){
      if(!duoi)ten=(ten&&!/^download$/i.test(ten)?ten.replace(/\.[^.]*$/,''):o.san+'_DonHang')+(/csv/i.test(mime)?'.csv':'.xlsx');      // blob không mang tên file -> đặt tên theo sàn
      await chrome.storage.session.remove('cho_tai');
      const u=it.finalUrl||it.url||'';let b64=null,ly='';
      try{
        if(/^data:/.test(u))b64=u;
        else if(/^blob:/.test(u)){const r=o.tabId?await chrome.tabs.sendMessage(o.tabId,{loai:'lay-blob',url:u}):null;b64=r&&r.b64;if(!b64)ly='trang không trả nội dung blob'+(r&&r.loi?' ('+r.loi+')':'')}
        else{const r=await fetch(u,{credentials:'include'});if(!r.ok)ly='HTTP '+r.status;else{const b=await r.blob();if(b.size>0)b64=await b64Cua(b);else ly='file rỗng'}}
      }catch(e){ly=String(e&&e.message||e)}
      let kq={ten,host:(()=>{try{return new URL(u).host}catch(e){return u.slice(0,30)}})()};
      if(b64){const cong=(await chrome.storage.local.get('cong')).cong||8686;
        try{const r=await fetch('http://127.0.0.1:'+cong+'/api/san-tmdt/luu-file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({san:o.san,ten,b64})});
          if(r.ok){Object.assign(kq,await r.json());xong=true}else ly='phần mềm kế toán trả lỗi '+r.status}catch(e){ly='không kết nối được phần mềm kế toán ('+String(e&&e.message||e)+')'}}
      if(xong){try{await chrome.downloads.cancel(it.id)}catch(e){}try{await chrome.downloads.erase({id:it.id})}catch(e){}}
      else kq.loi=ly||'không lấy được nội dung file';
      await chrome.storage.session.set({['kq_tai_'+o.san]:Object.assign(kq,{luc:Date.now()})})}
  }catch(e){}
  try{suggest()}catch(e){}})();return true});
