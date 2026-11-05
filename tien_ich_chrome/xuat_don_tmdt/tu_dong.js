// Trang do phần mềm kế toán mở (cờ do dau.js ghi) thì tự chạy 1 lần; luôn có nút nhỏ để bấm tay.
(()=>{let c='';try{c=sessionStorage.getItem('ketoanXuat')||'';sessionStorage.removeItem('ketoanXuat')}catch(e){}
 const misa=/meinvoice\.vn$/.test(location.host);
 const nut=document.createElement('button');nut.textContent=misa?'▶ Lấy số HĐ (Kế toán)':'▶ Xuất đơn (Kế toán)';
 nut.style.cssText='position:fixed;left:12px;bottom:56px;z-index:2147483647;padding:6px 12px;border:0;border-radius:8px;background:'+(misa?'#1976d2':'#ee4d2d')+';color:#fff;font:13px Arial,sans-serif;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.3)';
 nut.onclick=()=>misa?__ketoanMisa(false):__ketoanXuat(false,'');(document.body||document.documentElement).appendChild(nut);
 if(misa&&c.indexOf('ketoan-lay-so-hd')>=0){__ketoanMisa(true)}
 else if(!misa&&c.indexOf('ketoan-xuat')>=0){if(typeof __ketoanXuat==='function')__ketoanXuat(true,c)}
 else{__ketoanBao('tiện ích đã hoạt động (không có lệnh từ phần mềm — bấm nút ▶ để chạy tay)','#555')}})();
