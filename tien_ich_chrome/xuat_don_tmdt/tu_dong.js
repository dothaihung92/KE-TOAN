// Trang do phần mềm kế toán mở (cờ do dau.js ghi) thì tự chạy 1 lần; luôn có nút nhỏ để bấm tay.
// Nếu công ty có lưu tài khoản sàn (địa chỉ có &kt=<mã dùng 1 lần>): kiểm tra Chrome đang mở đúng shop chưa; chưa đúng thì đăng xuất (xoá cookie sàn),
// trang đăng nhập hiện ra thì tự điền tài khoản công ty, đăng nhập xong tự quay về Quản lý đơn hàng và chạy xuất đơn.
(async()=>{let c='';try{c=sessionStorage.getItem('ketoanXuat')||'';sessionStorage.removeItem('ketoanXuat')}catch(e){}
 const misa=/meinvoice\.vn$/.test(location.host),host=location.host;
 const sl=ms=>new Promise(r=>setTimeout(r,ms));
 const ORDER={'banhang.shopee.vn':'https://banhang.shopee.vn/portal/sale/order','seller-vn.tiktok.com':'https://seller-vn.tiktok.com/order?selected_sort=6&tab=all','sellercenter.lazada.vn':'https://sellercenter.lazada.vn/apps/order/list'};
 const hien=e=>{if(!e)return false;const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'};
 const oMk=()=>[...document.querySelectorAll('input[type=password]')].find(hien);
 const gui=m=>new Promise(r=>{const h=setTimeout(()=>r({loi_nen:1}),8000);try{chrome.runtime.sendMessage(m,x=>{void chrome.runtime.lastError;clearTimeout(h);r(x||{})})}catch(e){clearTimeout(h);r({loi_nen:1})}});      // phần nền không trả lời trong 8 giây -> không treo
 const layCho=async()=>(await gui({loai:'lay-cho'})).cho||null,luuCho=o=>gui({loai:'luu-cho',cho:o}),xoaCho=()=>gui({loai:'xoa-cho'});      // việc đang chờ lưu ở phần nền theo SÀN (dùng được cả ở thẻ mới)
 const DANG_NHAP={'sellercenter.lazada.vn':'https://sellercenter.lazada.vn/apps/seller/login?login=1&redirect_url=https%3A%2F%2Fsellercenter.lazada.vn%2Fapps%2Forder%2Flist','seller-vn.tiktok.com':'https://seller-vn.tiktok.com/account/login'};
 const dangXuat=async(c,lan,user)=>{      // xoá cookie sàn + dữ liệu đăng nhập lưu trên trang, rồi mở trang đăng nhập
   __ketoanBao('Chrome đang mở tài khoản khác — đang đăng xuất để đăng nhập '+user+'…','#1565c0');
   const kq=await gui({loai:'dang-xuat',host});
   try{localStorage.clear()}catch(e){}try{sessionStorage.clear()}catch(e){}await luuCho({c,han:Date.now()+900000,dx:lan,user,vedn:0});
   if(kq.loi_nen||!kq.n){__ketoanBao('Tiện ích chưa xoá được cookie đăng nhập ('+(kq.loi_nen?'phần nền không trả lời':'0 cookie')+') — vào chrome://extensions bấm 🔄 tải lại tiện ích rồi bấm Mở trang lại; hoặc tự đăng xuất rồi đăng nhập '+user+'.','#b00020');return}
   await sl(500);location.replace(DANG_NHAP[host]||ORDER[host]||location.href)};
 const nut=document.createElement('button');nut.textContent=misa?'▶ Lấy số HĐ (Kế toán)':'▶ Xuất đơn (Kế toán)';
 nut.style.cssText='position:fixed;left:12px;bottom:56px;z-index:2147483647;padding:6px 12px;border:0;border-radius:8px;background:'+(misa?'#1976d2':'#ee4d2d')+';color:#fff;font:13px Arial,sans-serif;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.3)';
 nut.onclick=()=>misa?__ketoanMisa(false):__ketoanXuat(false,'');(document.body||document.documentElement).appendChild(nut);
 let rTk=null;
 if(!misa){
  // lệnh từ phần mềm có mã tài khoản: đổi mã lấy tài khoản NGAY (mã chỉ dùng 1 lần); nếu trang đang là trang ĐĂNG NHẬP (chưa đăng nhập sẵn) thì điền luôn
  const kt0=/[&]kt=([\w-]+)/.exec(c),po0=/[&]p=(\d+)/.exec(c);
  if(kt0){c=c.replace(/&kt=[\w-]+/,'').replace(/&p=\d+/,'');rTk=await gui({loai:'lay-tk',kt:kt0[1],p:po0&&po0[1]});
    if(rTk.user){for(let i=0;i<6&&!oMk();i++)await sl(800);
      if(oMk())await luuCho({c,han:Date.now()+900000,user:rTk.user,vedn:0})}}
  // (a) trang đăng nhập: nền đang giữ tài khoản công ty cho thẻ này -> tự điền và bấm Đăng nhập
  let choO=await layCho(),cho=!!choO;
  if(cho||(await gui({loai:'co-tk'})).co)for(let i=0;i<10&&!oMk();i++)await sl(800);      // chỉ chờ ô mật khẩu khi đang đổi tài khoản
  // trang ĐĂNG KÝ (vd Lazada tự chuyển sang /apps/register): KHÔNG điền gì, quay về trang đăng nhập
  const laDangKy=/register|signup|sign-up|dang-ky/i.test(location.pathname)||[...document.querySelectorAll('input[type=password]')].filter(hien).length>=2;
  if(laDangKy&&(cho||(await gui({loai:'co-tk'})).co)){
    const n=(choO&&choO.vedn)||0;if(choO)await luuCho(Object.assign(choO,{vedn:n+1}));
    if(n<2){const l=[...document.querySelectorAll('a,span,button')].filter(e=>hien(e)&&e.children.length===0).find(e=>/^(Đăng nhập|Log in|Login|Sign in)$/i.test((e.innerText||'').trim()));
      __ketoanBao('trang đang là ĐĂNG KÝ — chuyển sang trang ĐĂNG NHẬP…','#1565c0');await sl(600);
      location.href=DANG_NHAP[host]||ORDER[host];return}
    __ketoanBao('Sàn cứ mở trang ĐĂNG KÝ — hãy tự bấm "Đăng nhập" rồi đăng nhập tài khoản của công ty; xong tiện ích tự xuất đơn.','#b00020');return}
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
        const l=[...document.querySelectorAll('a,span,div,button')].filter(e=>hien(e)&&e.children.length===0).find(e=>/^(Đăng nhập bằng email|Log in with email|Sử dụng email|Use email|Email)$|^(Đăng nhập bằng email|Log in with email)/i.test((e.innerText||'').trim()));
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
    else if(cho)__ketoanBao('hãy đăng nhập tài khoản sàn của công ty — xong tiện ích tự quay lại xuất đơn','#b00020');
    return}
  // (b) vừa đăng nhập xong: còn việc chờ -> về trang Quản lý đơn hàng rồi chạy
  if(!c){const p=await layCho();
    if(p&&p.han>Date.now()&&ORDER[host]){
      if(p.dx&&(await gui({loai:'co-tk'})).chua_dung){      // vừa đăng xuất nhưng trang KHÔNG hiện ô đăng nhập (tài khoản chưa dùng) -> đăng xuất chưa ăn
        if(p.dx<2){await dangXuat(p.c,p.dx+1,p.user||'');return}
        await xoaCho();gui({loai:'xoa-tk'});
        __ketoanBao('Không tự đăng xuất được tài khoản đang mở trên '+host+' — hãy tự Đăng xuất (góc phải trên), đăng nhập tài khoản '+(p.user||'của công ty')+', rồi bấm Mở trang lại trong phần mềm.','#b00020');return}
      if(location.href.startsWith(ORDER[host].split('?')[0])){await xoaCho();c=p.c;gui({loai:'xoa-tk'})}
      else{__ketoanBao('đã đăng nhập — đang chuyển tới Quản lý đơn hàng…');location.href=ORDER[host];return}}
    }
  // (c) lệnh từ phần mềm có mã tài khoản: đúng shop thì chạy luôn, sai thì đăng xuất để đăng nhập tài khoản công ty
  if(rTk){const r=rTk;
    if(r.loi)__ketoanBao(r.loi,'#b00020');
    else if(r.loi_nen)__ketoanBao('Phần nền của tiện ích không trả lời — vào chrome://extensions bấm 🔄 tải lại tiện ích rồi bấm Mở trang lại.','#b00020');
    else if(r.user){const can=(r.ten_shop||r.user).toLowerCase();
      for(let i=0;i<10;i++){__ketoanBao('đang kiểm tra tài khoản đang mở trên Chrome… ('+(10-i)+' giây)');      // chờ trang tải xong phần đầu trang (tên shop)
        if(oMk()||(document.body.innerText||'').toLowerCase().includes(can)||(i>=4&&(document.body.innerText||'').length>3000))break;await sl(1000)}
      if(oMk()||!(document.body.innerText||'').toLowerCase().includes(can)){await dangXuat(c,1,r.user);return}
      gui({loai:'xoa-tk'})}}
 }
 if(misa&&c.indexOf('ketoan-lay-so-hd')>=0){__ketoanMisa(true)}
 else if(!misa&&c.indexOf('ketoan-xuat')>=0){if(typeof __ketoanXuat==='function')__ketoanXuat(true,c)}
 else{__ketoanBao('tiện ích đã hoạt động (không có lệnh từ phần mềm — bấm nút ▶ để chạy tay)','#555')}})();
