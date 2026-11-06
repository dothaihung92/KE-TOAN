// Chạy trong trang sàn (Shopee/TikTok/Lazada): trang thường thu hồi địa chỉ blob: của file vừa tải NGAY sau khi bấm tải,
// khiến tiện ích không kịp lấy nội dung file để lưu thẳng ra Desktop (thay cho hộp "Save As"). Giữ blob thêm 2 phút rồi mới thu hồi.
(()=>{try{const goc=URL.revokeObjectURL.bind(URL);URL.revokeObjectURL=u=>{setTimeout(()=>{try{goc(u)}catch(e){}},120000)}}catch(e){}})();
