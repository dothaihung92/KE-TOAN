// Phần mềm kế toán mở trang với "#ketoan-xuat=<từ>_<đến>" -> ghi nhớ (trang có thể tự đổi địa chỉ khi tải) để tu_dong.js chạy xuất đơn 1 lần.
try{if(location.hash.indexOf('ketoan-xuat')>=0){sessionStorage.setItem('ketoanXuat',location.hash);history.replaceState(null,'',location.pathname+location.search)}}catch(e){}
