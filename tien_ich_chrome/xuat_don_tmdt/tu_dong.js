// Luôn hiện nút nhỏ "▶ Xuất đơn (Kế toán)" ở góc dưới trái trang người bán (bấm tay khi tiện ích chưa tự chạy); trang do phần mềm mở (cờ từ dau.js) thì tự chạy 1 lần.
(()=>{let c='';try{c=sessionStorage.getItem('ketoanXuat')||'';sessionStorage.removeItem('ketoanXuat')}catch(e){}
 const nut=document.createElement('button');nut.textContent='▶ Xuất đơn (Kế toán)';nut.style.cssText='position:fixed;left:12px;bottom:56px;z-index:2147483647;padding:6px 12px;border:0;border-radius:8px;background:#ee4d2d;color:#fff;font:13px Arial,sans-serif;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.3)';
 nut.onclick=()=>__ketoanXuat(false,'');(document.body||document.documentElement).appendChild(nut);
 if(c){if(typeof __ketoanXuat==='function')__ketoanXuat(true,c)}else{__ketoanBao('tiện ích đã hoạt động (không có lệnh từ phần mềm — bấm ▶ Xuất đơn để chạy tay)','#555')}})();
