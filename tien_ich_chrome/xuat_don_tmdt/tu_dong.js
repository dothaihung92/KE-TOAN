// Trang do phần mềm kế toán mở (cờ do dau.js ghi) thì tự chạy 1 lần; luôn có nút nhỏ để bấm tay.
// Nếu công ty có lưu tài khoản sàn (địa chỉ có &kt=<mã dùng 1 lần>): kiểm tra Chrome đang mở đúng shop chưa; chưa đúng thì đăng xuất (xoá cookie sàn),
// trang đăng nhập hiện ra thì tự điền tài khoản công ty, đăng nhập xong tự quay về Quản lý đơn hàng và chạy xuất đơn.
(async()=>{let c='';try{c=sessionStorage.getItem('ketoanXuat')||'';sessionStorage.removeItem('ketoanXuat')}catch(e){}
 const misa=/meinvoice\.vn$/.test(location.host),host=location.host;
 const sl=ms=>new Promise(r=>setTimeout(r,ms));
 const ORDER={'banhang.shopee.vn':'https://banhang.shopee.vn/portal/sale/order','seller-vn.tiktok.com':'https://seller-vn.tiktok.com/order','sellercenter.lazada.vn':'https://sellercenter.lazada.vn/apps/order/list'};
 const hien=e=>{if(!e)return false;const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'};
 const oMk=()=>[...document.querySelectorAll('input[type=password]')].find(hien);
 const gui=m=>new Promise(r=>{try{chrome.runtime.sendMessage(m,x=>{void chrome.runtime.lastError;r(x||{})})}catch(e){r({})}});
 const nut=document.createElement('button');nut.textContent=misa?'▶ Lấy số HĐ (Kế toán)':'▶ Xuất đơn (Kế toán)';
 nut.style.cssText='position:fixed;left:12px;bottom:56px;z-index:2147483647;padding:6px 12px;border:0;border-radius:8px;background:'+(misa?'#1976d2':'#ee4d2d')+';color:#fff;font:13px Arial,sans-serif;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.3)';
 nut.onclick=()=>misa?__ketoanMisa(false):__ketoanXuat(false,'');(document.body||document.documentElement).appendChild(nut);
 if(!misa){
  // (a) trang đăng nhập: nền đang giữ tài khoản công ty cho thẻ này -> tự điền và bấm Đăng nhập
  let cho=false;try{cho=!!sessionStorage.getItem('ketoanCho')}catch(e){}
  if(cho||(await gui({loai:'co-tk'})).co)for(let i=0;i<10&&!oMk();i++)await sl(800);      // chỉ chờ ô mật khẩu khi đang đổi tài khoản
  const mk=oMk();
  if(mk){const t=await gui({loai:'tk-cho-tab'});
    if(t.user){const dat=(e,v)=>{const pr=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value');e.focus();pr.set.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))};
      const o=[...document.querySelectorAll('input')].filter(e=>hien(e)&&/^(text|email|tel|)$/i.test(e.getAttribute('type')||'')&&(e.compareDocumentPosition(mk)&Node.DOCUMENT_POSITION_FOLLOWING));
      const u=o[o.length-1];
      if(u){dat(u,t.user);await sl(300);dat(mk,t.pass);await sl(600);
        const b=[...document.querySelectorAll('button,[role=button],input[type=submit]')].filter(hien).find(e=>/^(Đăng nhập|Log in|Login|Sign in|Đăng Nhập)$/i.test((e.innerText||e.value||'').trim()));
        if(b)b.click();else if(mk.form)mk.form.requestSubmit?mk.form.requestSubmit():mk.form.submit();
        __ketoanBao('đã điền tài khoản '+t.user+' và bấm Đăng nhập — nếu sàn hỏi mã OTP/captcha, bạn nhập tay; đăng nhập xong tiện ích tự quay lại xuất đơn','#1565c0')}
      else __ketoanBao('không tìm thấy ô tên đăng nhập — hãy tự đăng nhập tài khoản '+t.user+', xong tiện ích tự xuất đơn','#b00020')}
    else if(sessionStorage.getItem('ketoanCho'))__ketoanBao('hãy đăng nhập tài khoản sàn của công ty — xong tiện ích tự quay lại xuất đơn','#b00020');
    return}
  // (b) vừa đăng nhập xong: còn việc chờ -> về trang Quản lý đơn hàng rồi chạy
  if(!c){try{const p=JSON.parse(sessionStorage.getItem('ketoanCho')||'null');
    if(p&&p.han>Date.now()&&ORDER[host]){if(location.href.startsWith(ORDER[host])){sessionStorage.removeItem('ketoanCho');c=p.c;gui({loai:'xoa-tk'})}else{__ketoanBao('đã đăng nhập — đang chuyển tới Quản lý đơn hàng…');location.href=ORDER[host];return}}
    else sessionStorage.removeItem('ketoanCho')}catch(e){}}
  // (c) lệnh từ phần mềm có mã tài khoản: đúng shop thì chạy luôn, sai thì đăng xuất để đăng nhập tài khoản công ty
  const kt=/[&]kt=([\w-]+)/.exec(c),po=/[&]p=(\d+)/.exec(c);
  if(kt){c=c.replace(/&kt=[\w-]+/,'').replace(/&p=\d+/,'');
    const r=await gui({loai:'lay-tk',kt:kt[1],p:po&&po[1]});
    if(r.loi)__ketoanBao(r.loi,'#b00020');
    else if(r.user){__ketoanBao('đang kiểm tra tài khoản đang mở trên Chrome…');
      for(let i=0;i<20;i++){if(oMk()||[...document.querySelectorAll('button,a,[role=button]')].some(e=>hien(e)&&/^(Xuất|Export)$/.test((e.innerText||'').trim())))break;await sl(1000)}
      const chu=(document.body.innerText||'').toLowerCase(),can=(r.ten_shop||r.user).toLowerCase();
      if(oMk()||!chu.includes(can)){
        try{sessionStorage.setItem('ketoanCho',JSON.stringify({c,han:Date.now()+900000}))}catch(e){}
        __ketoanBao('Chrome đang mở tài khoản khác — đang đăng xuất để đăng nhập '+r.user+'…','#1565c0');
        await gui({loai:'dang-xuat',host});await sl(500);location.replace(ORDER[host]||location.href);return}
      gui({loai:'xoa-tk'})}}
 }
 if(misa&&c.indexOf('ketoan-lay-so-hd')>=0){__ketoanMisa(true)}
 else if(!misa&&c.indexOf('ketoan-xuat')>=0){if(typeof __ketoanXuat==='function')__ketoanXuat(true,c)}
 else{__ketoanBao('tiện ích đã hoạt động (không có lệnh từ phần mềm — bấm nút ▶ để chạy tay)','#555')}})();
