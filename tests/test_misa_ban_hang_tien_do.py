import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()
html = open(os.path.join(_REPO_ROOT, 'static', 'index.html'), encoding='utf-8').read()

# Regression test cho tính năng "hiện tiến độ khi ghi Bán hàng vào MISA" —
# người dùng báo: đang xem màn xem trước "Sẽ thêm: 4356 chứng từ" rồi bấm
# "⬆ Ghi 4356 chứng từ mới vào MISA" — "nhiều dữ liệu quá không biết đã
# import hay chưa" (không có gì hiện ra trong lúc ghi từng chứng từ 1 qua
# ODBC, có thể mất khá lâu với hàng nghìn dòng).
#
# Dùng CÙNG cơ chế đã có sẵn + xác nhận hoạt động tốt cho "Dò mã hàng tự
# động" (Xuất Kho, _XK_DOMA_TIEN_DO/xkDoMa): route ghi chạy ĐỒNG BỘ (def
# thường, không phải async def) nên FastAPI/Starlette tự chạy trong
# threadpool riêng — trong lúc nó còn chạy, request GET trạng thái ở
# threadpool khác vẫn được phục vụ song song bình thường, không cần dựng
# hẳn 1 hệ thống job nền/queue riêng chỉ để có thanh tiến độ. Backend: dict
# module-level {cid: {"da_xu_ly","tong","dang_chay"}} + callback on_progress
# gọi mỗi dòng trong vòng lặp ghi chính. Frontend: setInterval 500ms poll
# endpoint trạng thái, cập nhật thanh tiến độ trong modal xem trước.


def extract_fn(name):
    """Trích xuất hàm TOP-LEVEL (không nested) — cách làm sẵn có, dùng chung
    nhiều test khác trong repo."""
    idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i + 1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln)
            continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i + 1] + '\n'.join(body)


# ===== Test 1 (QUAN TRỌNG): _misa_ghi_ban_hang() phải nhận tham số
# on_progress và GỌI nó bên trong vòng lặp ghi chính ("for ... in
# enumerate(rows)"), báo đúng (chỉ số hiện tại, tổng số dòng) — để endpoint
# có thể cập nhật tiến độ cho client poll trong lúc ghi hàng nghìn dòng. =====
than_ghi = extract_fn('_misa_ghi_ban_hang')
assert 'on_progress=None' in than_ghi, (
    "_misa_ghi_ban_hang() phải có tham số on_progress (mặc định None, không đổi hành vi cũ khi không "
    "truyền) để báo tiến độ ra ngoài trong lúc ghi.")
vt_vong_lap = than_ghi.find('for _idx_pgs, r in enumerate(rows):')
assert vt_vong_lap >= 0, (
    "Vòng lặp ghi chính phải dùng enumerate(rows) để có chỉ số dòng hiện tại báo tiến độ, không phải "
    "'for r in rows:' như trước (không có chỉ số để báo).")
doan_sau_vong_lap = than_ghi[vt_vong_lap:vt_vong_lap + 300]
assert 'if on_progress:' in doan_sau_vong_lap and 'on_progress(_idx_pgs, _tong_r_pgs)' in doan_sau_vong_lap, (
    "Phải gọi on_progress(_idx_pgs, _tong_r_pgs) NGAY ĐẦU mỗi vòng lặp (báo tiến độ đều đặn từng dòng, "
    "không phải chỉ báo 1 lần lúc đầu/cuối) — got đoạn: %r" % doan_sau_vong_lap[:200])
print("PASS 1: _misa_ghi_ban_hang() nhận on_progress và gọi đều đặn mỗi dòng trong vòng lặp ghi chính, "
      "báo đúng (chỉ số hiện tại, tổng số dòng).")

# ===== Test 2 (QUAN TRỌNG): endpoint /api/misa-sql/import-ban-hang/{cid}
# phải khởi tạo _MISA_GHI_BH_TIEN_DO[cid], truyền callback on_progress vào
# _misa_ghi_ban_hang(), và LUÔN đặt dang_chay=False khi xong (kể cả lỗi —
# qua finally) để client không bị kẹt chờ mãi nếu ghi thất bại giữa chừng. =====
vt_post = src.index('@app.post("/api/misa-sql/import-ban-hang/{cid}")')
vt_get_status = src.index('@app.get("/api/misa-sql/import-ban-hang-status/{cid}")')
than_post = src[vt_post:vt_get_status]
assert '_MISA_GHI_BH_TIEN_DO[cid] = {"da_xu_ly": 0, "tong": 0, "dang_chay": True}' in than_post, (
    "Endpoint POST phải khởi tạo _MISA_GHI_BH_TIEN_DO[cid] TRƯỚC khi bắt đầu ghi.")
assert 'on_progress=_bao_tien_do' in than_post, (
    "Endpoint POST phải truyền callback on_progress=_bao_tien_do vào _misa_ghi_ban_hang().")
assert 'finally:' in than_post and '_MISA_GHI_BH_TIEN_DO[cid]["dang_chay"] = False' in than_post, (
    "Phải đặt dang_chay=False trong khối finally (không phải chỉ sau khi return thành công) — nếu ghi "
    "lỗi giữa chừng mà không đặt lại, client sẽ tưởng NHẦM là vẫn đang chạy, kẹt chờ vô ích.")
print("PASS 2: endpoint ghi Bán hàng khởi tạo đúng tiến độ, truyền callback, và LUÔN tắt cờ 'dang_chay' "
      "khi xong (kể cả lỗi giữa chừng, qua finally).")

# ===== Test 3 (không hồi quy — QUAN TRỌNG): endpoint GET trạng thái phải
# trả về ĐÚNG dict từ _MISA_GHI_BH_TIEN_DO, có giá trị mặc định an toàn
# (dang_chay=False) khi company_id chưa từng ghi lần nào (tránh KeyError). =====
vt_def_status = src.index('def misa_sql_import_ban_hang_status', vt_get_status)
vt_ket_thuc_status = src.index('\ndef ', vt_def_status + 10)
than_status = src[vt_get_status:vt_ket_thuc_status]
assert '_MISA_GHI_BH_TIEN_DO.get(cid,' in than_status and '"dang_chay": False' in than_status, (
    "Endpoint GET trạng thái phải dùng .get(cid, {mặc định an toàn}) — company_id chưa từng ghi lần nào "
    "không được làm crash (KeyError), phải trả về trạng thái 'không chạy' hợp lý.")
print("PASS 3: endpoint GET trạng thái trả về mặc định an toàn khi chưa từng ghi lần nào cho company đó.")

# ===== Test 4 (frontend — QUAN TRỌNG): static/index.html phải có thanh
# tiến độ (misaGhiTienDoBox/Text/Bar) trong modal xem trước Bán hàng, VÀ
# hàm banHangImportMisaGhi() phải setInterval poll đúng endpoint trạng thái
# mỗi 500ms trong lúc chờ ghi xong, dừng poll (clearInterval) khi xong dù
# thành công hay lỗi. =====
assert 'id="misaGhiTienDoBox"' in html and 'id="misaGhiTienDoText"' in html and 'id="misaGhiTienDoBar"' in html, (
    "Modal xem trước Bán hàng phải có sẵn khung thanh tiến độ (misaGhiTienDoBox/Text/Bar), ẩn mặc định, "
    "để banHangImportMisaGhi() hiện ra khi đang ghi.")
vt_ham_ghi = html.index('async function banHangImportMisaGhi(ghiDe){')
vt_ket_thuc_ham = html.index('\n}', vt_ham_ghi)
than_ham_ghi = html[vt_ham_ghi:vt_ket_thuc_ham]
assert '/api/misa-sql/import-ban-hang-status/' in than_ham_ghi, (
    "banHangImportMisaGhi() phải gọi đúng endpoint trạng thái để lấy tiến độ.")
assert 'setInterval(capNhatTienDo,500)' in than_ham_ghi, (
    "Phải poll tiến độ mỗi 500ms trong lúc chờ ghi xong (cùng tần suất đã dùng cho 'Dò mã hàng tự động' "
    "— xkDoMa), không phải chỉ gọi 1 lần.")
assert 'clearInterval(hen)' in than_ham_ghi, (
    "Phải dừng poll (clearInterval) khi xong — dù thành công hay lỗi (nằm trong khối finally) — không "
    "được để interval chạy mãi sau khi ghi xong/đóng modal, gây rò rỉ bộ đếm chạy nền vô ích.")
print("PASS 4: static/index.html có thanh tiến độ trong modal Bán hàng, banHangImportMisaGhi() poll "
      "đúng endpoint mỗi 500ms và dừng poll đúng lúc khi xong.")

print("\nALL DONE")
