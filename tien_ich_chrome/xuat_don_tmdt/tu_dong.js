// Chỉ chạy khi trang được phần mềm kế toán mở (cờ do dau.js ghi); chạy 1 lần rồi xoá cờ.
(()=>{let c='';try{c=sessionStorage.getItem('ketoanXuat')||'';sessionStorage.removeItem('ketoanXuat')}catch(e){}
 if(c&&typeof __ketoanXuat==='function')__ketoanXuat(true);})();
