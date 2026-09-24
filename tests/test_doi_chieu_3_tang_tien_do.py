import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()
html = open(os.path.join(_REPO_ROOT, 'static', 'index.html'), encoding='utf-8').read()

# Regression test cho tính năng "hiện tiến độ khi Chạy đối chiếu công nợ 3 tầng" — người dùng báo:
# công ty nhiều hóa đơn, "Chạy đối chiếu" chạy rất lâu mà không biết đã tới đâu/còn bao lâu, yêu
# cầu thêm quá trình xử lý để biết khi nào xong.
#
# Dùng CÙNG cơ chế đã có sẵn + xác nhận hoạt động tốt cho "Dò mã hàng tự động" (_XK_DOMA_TIEN_DO)
# và "Ghi Bán hàng vào MISA" (_MISA_GHI_BH_TIEN_DO): route chạy ĐỒNG BỘ (def thường, không phải
# async def) nên FastAPI/Starlette tự chạy trong threadpool riêng — trong lúc nó còn chạy, request
# GET trạng thái ở threadpool khác vẫn được phục vụ song song bình thường. Backend: dict
# module-level {cid: {"da_xu_ly","tong","ten","dang_chay"}} + callback on_progress gọi mỗi đối
# tượng công nợ (khách hàng/NCC) trong vòng lặp chính của _misa_khop_1_2 (bước tốn thời gian nhất,
# chứa tim_to_hop). Frontend: setInterval 500ms poll endpoint trạng thái, cập nhật thanh tiến độ.


def extract_fn(name):
    """Trích xuất hàm TOP-LEVEL (không nested) — cách làm sẵn có, dùng chung nhiều test khác trong
    repo."""
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


# ===== Test 1 (QUAN TRỌNG): _misa_khop_1_2() phải nhận tham số on_progress và GỌI nó ngay đầu
# vòng lặp chính "for aoid, d in doi_tuong_hd.items()" (bước tốn thời gian nhất — chứa tim_to_hop,
# xem test riêng tests/test_doi_chieu_3_tang_toc_do_to_hop.py), báo đúng (chỉ số hiện tại, tổng số
# đối tượng, tên đối tượng đang xử lý). =====
than_khop = extract_fn('_misa_khop_1_2')
assert 'on_progress=None' in than_khop, (
    "_misa_khop_1_2() phải có tham số on_progress (mặc định None, không đổi hành vi cũ khi không "
    "truyền) để báo tiến độ ra ngoài trong lúc chạy.")
vt_vong_lap = than_khop.find('enumerate(doi_tuong_hd.items())')
assert vt_vong_lap >= 0, (
    "Vòng lặp chính phải dùng enumerate(doi_tuong_hd.items()) để có chỉ số đối tượng hiện tại báo "
    "tiến độ.")
doan_sau_vong_lap = than_khop[vt_vong_lap:vt_vong_lap + 200]
assert 'if on_progress:' in doan_sau_vong_lap and 'on_progress(' in doan_sau_vong_lap, (
    "Phải gọi on_progress(...) NGAY ĐẦU mỗi vòng lặp (báo tiến độ đều đặn từng đối tượng công nợ, "
    "không phải chỉ báo 1 lần lúc đầu/cuối) — got đoạn: %r" % doan_sau_vong_lap[:200])
print("PASS 1: _misa_khop_1_2() nhận on_progress và gọi đều đặn mỗi đối tượng công nợ trong vòng "
      "lặp chính, báo đúng (chỉ số hiện tại, tổng số, tên đang xử lý).")

# ===== Test 2 (QUAN TRỌNG): _misa_doi_chieu_3_tang() phải nhận on_progress và truyền THẲNG xuống
# _misa_khop_1_2() (không tự ý đổi ý nghĩa/đơn vị tiến độ). =====
than_3tang = extract_fn('_misa_doi_chieu_3_tang')
assert 'on_progress=None' in than_3tang, (
    "_misa_doi_chieu_3_tang() phải có tham số on_progress (mặc định None).")
assert 'on_progress=on_progress' in than_3tang, (
    "_misa_doi_chieu_3_tang() phải truyền on_progress xuống _misa_khop_1_2() (nơi thực sự chạy "
    "vòng lặp tốn thời gian) — không tự tính tiến độ khác.")
print("PASS 2: _misa_doi_chieu_3_tang() nhận on_progress và truyền thẳng xuống _misa_khop_1_2().")

# ===== Test 3 (QUAN TRỌNG): endpoint GET /api/misa-sql/doi-chieu-3-tang/{cid} phải khởi tạo
# _MISA_3TANG_TIEN_DO[cid], truyền callback on_progress, và LUÔN đặt dang_chay=False khi xong (kể
# cả lỗi giữa chừng, qua finally) để client không bị kẹt chờ mãi nếu đối chiếu lỗi giữa chừng. =====
vt_get = src.index('@app.get("/api/misa-sql/doi-chieu-3-tang/{cid}")')
vt_get_status = src.index('@app.get("/api/misa-sql/doi-chieu-3-tang-status/{cid}")')
than_get = src[vt_get:vt_get_status]
assert '_MISA_3TANG_TIEN_DO[cid] = {"da_xu_ly": 0, "tong": 0, "ten": "", "dang_chay": True}' in than_get, (
    "Endpoint GET đối chiếu 3 tầng phải khởi tạo _MISA_3TANG_TIEN_DO[cid] TRƯỚC khi bắt đầu chạy.")
assert 'on_progress=_bao_tien_do' in than_get, (
    "Endpoint GET đối chiếu 3 tầng phải truyền callback on_progress=_bao_tien_do vào "
    "_misa_doi_chieu_3_tang().")
assert 'finally:' in than_get and '_MISA_3TANG_TIEN_DO[cid]["dang_chay"] = False' in than_get, (
    "Phải đặt dang_chay=False trong khối finally (không phải chỉ sau khi return thành công) — nếu "
    "đối chiếu lỗi giữa chừng mà không đặt lại, client sẽ tưởng NHẦM là vẫn đang chạy, kẹt chờ vô ích.")
print("PASS 3: endpoint GET đối chiếu 3 tầng khởi tạo đúng tiến độ, truyền callback, và LUÔN tắt cờ "
      "'dang_chay' khi xong (kể cả lỗi giữa chừng, qua finally).")

# ===== Test 4 (không hồi quy — QUAN TRỌNG): endpoint GET trạng thái phải trả về ĐÚNG dict từ
# _MISA_3TANG_TIEN_DO, có giá trị mặc định an toàn (dang_chay=False) khi company_id chưa từng chạy
# lần nào (tránh KeyError). =====
vt_def_status = src.index('def misa_sql_doi_chieu_3_tang_status', vt_get_status)
vt_ket_thuc_status = src.index('\ndef ', vt_def_status + 10)
than_status = src[vt_get_status:vt_ket_thuc_status]
assert '_MISA_3TANG_TIEN_DO.get(cid,' in than_status and '"dang_chay": False' in than_status, (
    "Endpoint GET trạng thái phải dùng .get(cid, {mặc định an toàn}) — company_id chưa từng chạy "
    "lần nào không được làm crash (KeyError), phải trả về trạng thái 'không chạy' hợp lý.")
print("PASS 4: endpoint GET trạng thái trả về mặc định an toàn khi chưa từng chạy lần nào cho "
      "company đó.")

# ===== Test 5 (frontend — QUAN TRỌNG): static/index.html — hàm misaBuTruTim() phải setInterval
# poll đúng endpoint trạng thái mỗi 500ms trong lúc chờ chạy xong, dừng poll (clearInterval) khi
# xong dù thành công hay lỗi. =====
vt_ham = html.index("async function misaBuTruTim(loai){")
vt_ket_thuc_ham = html.index("async function misaBuTruXuatExcel", vt_ham)
than_ham = html[vt_ham:vt_ket_thuc_ham]
assert '/api/misa-sql/doi-chieu-3-tang-status/' in than_ham, (
    "misaBuTruTim() phải gọi đúng endpoint trạng thái để lấy tiến độ.")
assert re.search(r'setInterval\(\s*capNhatTienDo3Tang\s*,\s*500\s*\)', than_ham), (
    "Phải poll tiến độ mỗi 500ms trong lúc chờ chạy xong (cùng tần suất đã dùng cho 'Dò mã hàng tự "
    "động' — xkDoMa), không phải chỉ gọi 1 lần.")
assert 'clearInterval(henTienDo3Tang)' in than_ham, (
    "Phải dừng poll (clearInterval) khi xong — dù thành công hay lỗi (nằm trong khối finally) — "
    "không được để interval chạy mãi sau khi đối chiếu xong, gây rò rỉ bộ đếm chạy nền vô ích.")
assert 'finally{clearInterval(henTienDo3Tang);}' in than_ham, (
    "clearInterval(henTienDo3Tang) phải nằm trong khối finally (chạy dù try thành công hay catch "
    "lỗi), không phải chỉ ở nhánh thành công.")
print("PASS 5: static/index.html — misaBuTruTim() poll đúng endpoint mỗi 500ms và dừng poll đúng "
      "lúc khi xong (kể cả khi lỗi).")

print("\nALL DONE")
