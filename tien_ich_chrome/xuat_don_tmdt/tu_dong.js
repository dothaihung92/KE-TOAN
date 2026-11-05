// Trang do phần mềm kế toán mở (cờ do dau.js ghi) thì tự chạy 1 lần; luôn có nút nhỏ để bấm tay.
// Nếu công ty có lưu tài khoản sàn (địa chỉ có &kt=<mã dùng 1 lần>): kiểm tra Chrome đang mở đúng shop chưa; chưa đúng thì đăng xuất (xoá cookie sàn),
// trang đăng nhập hiện ra thì tự điền tài khoản công ty, đăng nhập xong tự quay về Quản lý đơn hàng và chạy xuất đơn.
(async()=>{let c='';try{c=sessionStorage.getItem('ketoanXuat')||'';sessionStorage.removeItem('ketoanXuat')}catch(e){}
 const misa=/meinvoice\.vn$/.test(location.host),host=location.host;
 const sl=ms=>new Promise(r=>setTimeout(r,ms));
 const ORDER={'banhang.shopee.vn':'https://banhang.shopee.vn/portal/sale/order','seller-vn.tiktok.com':'https://seller-vn.tiktok.com/order?selected_sort=6&tab=all','sellercenter.lazada.vn':'https://sellercenter.lazada.vn/apps/order/list'};
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
    if(t.user){
      const dat=async(e,v)=>{const pr=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value');e.focus();pr.set.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));
        await sl(150);if(e.value!==v){e.focus();e.select();document.execCommand('insertText',false,v)}};      // ô không nhận gán trực tiếp -> gõ như bàn phím
      const laEmail=/@/.test(t.user);
      const oDn=()=>{const m=oMk();if(!m)return null;const ds=[...document.querySelectorAll('input')].filter(e=>hien(e)&&e!==m&&/^(text|email|tel|number|)$/i.test(e.getAttribute('type')||'')&&(e.compareDocumentPosition(m)&Node.DOCUMENT_POSITION_FOLLOWING));
        return ds.find(e=>/điện thoại|phone|email|tên đăng nhập|username|tài khoản|account|số/i.test((e.placeholder||'')+' '+(e.name||'')))||ds[ds.length-1]};
      let u=oDn();
      const laOSdt=e=>e&&(/điện thoại|phone/i.test(e.placeholder||'')||e.type==='tel');
      if(u&&laEmail&&laOSdt(u)){      // tài khoản là email mà trang đang ở chế độ số điện thoại -> chuyển sang "Đăng nhập bằng email"
        const l=[...document.querySelectorAll('a,span,div,button')].filter(e=>hien(e)&&e.children.length===0).find(e=>/^(Đăng nhập bằng email|Log in with email|Sử dụng email|Use email)/i.test((e.innerText||'').trim()));
        if(l){l.click();await sl(1500);u=oDn()}}
      else if(u&&!laEmail&&/@|email/i.test(u.placeholder||'')&&!laOSdt(u)){
        const l=[...document.querySelectorAll('a,span,div,button')].filter(e=>hien(e)&&e.children.length===0).find(e=>/^(Đăng nhập bằng số điện thoại|Log in with phone|Sử dụng số điện thoại)/i.test((e.innerText||'').trim()));
        if(l){l.click();await sl(1500);u=oDn()}}
      let gt=t.user.trim();
      if(u&&laOSdt(u)&&/\+\s*84/.test((u.parentElement&&u.parentElement.parentElement&&u.parentElement.parentElement.innerText)||'')){gt=gt.replace(/[\s.\-]/g,'').replace(/^(\+?84|0)/,'')}      // đã có sẵn mã vùng +84 -> bỏ 0 / +84 ở đầu
      const mk2=oMk();
      if(u&&mk2){await dat(u,gt);await sl(300);await dat(mk2,t.pass);await sl(700);
        const b=[...document.querySelectorAll('button,[role=button],input[type=submit]')].filter(hien).find(e=>/^(Đăng nhập|Log in|Login|Sign in)$/i.test((e.innerText||e.value||'').trim()));
        if(b)b.click();else if(mk2.form)mk2.form.requestSubmit?mk2.form.requestSubmit():mk2.form.submit();
        __ketoanBao('đã điền tài khoản '+t.user+' và bấm Đăng nhập — nếu sàn hỏi mã OTP/captcha/xác minh, bạn làm tay; đăng nhập xong tiện ích tự quay lại xuất đơn','#1565c0')}
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
