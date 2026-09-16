import os
import asyncio
import sqlite3
import tempfile
import datetime

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho tính năng "Nhập từ file tờ khai đã nộp (XML)"
# (_parse_tkhai_xml_htkk / import_tkhai_xml trong server.py) — người dùng
# báo vẫn còn thiếu "Mã CQT nơi nộp (HTKK)" và "Tên người ký tờ khai" sau
# khi đã có tính năng tự điền qua API XInvoice (API đó không có Mã CQT),
# rồi gửi ảnh chụp thư mục cài HTKK (D:\HTKK\DataFiles...) hỏi "đây là file
# gốc HTKK hãy xem có file nào chứ mã CQT không" và tải lên 1 file tờ khai
# ĐÃ NỘP THÀNH CÔNG thật (01_GTGT_TT80-Q12026-L00.xml) để kiểm tra.
#
# File thật đó CÓ đủ dữ liệu cần: <maCQTNoiNop>70129</maCQTNoiNop>,
# <tenCQTNoiNop>Thuế cơ sở 14 Thành phố Hồ Chí Minh</tenCQTNoiNop>,
# <nguoiKy>NGUYỄN XUÂN LÂM</nguoiKy> — cùng <mst>/<tenNNT>/<dchiNNT> trong
# <NNT> — và các thẻ này KHÔNG có tiền tố namespace dù root khai xmlns mặc
# định, đúng cấu trúc mà set_tag() ở export_htkk() đã dùng để GHI các thẻ
# này (đối xứng đọc/ghi). Vì đây là tờ khai ĐÃ ĐƯỢC CQT CHẤP NHẬN, dữ liệu
# chắc chắn đúng hơn API tra cứu ngoài hoặc người tự gõ — nên khi nhập,
# phần mềm phải ghi thẳng luôn cặp Mã+Tên CQT vào bảng "học" cqt_ma_ten.

# Nội dung THẬT (rút gọn phần không liên quan tới việc trích xuất, giữ
# NGUYÊN VĂN toàn bộ khối TTinTKhaiThue/TKhaiThue/NNT người dùng đã gửi).
XML_THAT = """<?xml version="1.0" encoding="UTF-8"?>
<HSoThueDTu xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://kekhaithue.gdt.gov.vn/TKhaiThue">
  <HSoKhaiThue id="ID_1">
    <TTinChung>
      <TTinDVu>
        <maDVu>HTKK</maDVu>
        <tenDVu>HỖ TRỢ KÊ KHAI THUẾ</tenDVu>
        <pbanDVu>5.6.7</pbanDVu>
        <ttinNhaCCapDVu>102DC90280BF81876F42303B4AD01FB4</ttinNhaCCapDVu>
      </TTinDVu>
      <TTinTKhaiThue>
        <TKhaiThue>
          <maTKhai>842</maTKhai>
          <tenTKhai>TỜ KHAI THUẾ GIÁ TRỊ GIA TĂNG (Mẫu số 01/GTGT)</tenTKhai>
          <moTaBMau>(Ban hành kèm theo Thông tư số 80/2021/TT-BTC ngày 29 tháng 9 năm 2021 của Bộ trưởng Bộ Tài chính)</moTaBMau>
          <pbanTKhaiXML>2.8.3</pbanTKhaiXML>
          <loaiTKhai>C</loaiTKhai>
          <soLan>0</soLan>
          <KyKKhaiThue>
            <kieuKy>Q</kieuKy>
            <kyKKhai>1/2026</kyKKhai>
            <kyKKhaiTuNgay>01/01/2026</kyKKhaiTuNgay>
            <kyKKhaiDenNgay>31/03/2026</kyKKhaiDenNgay>
            <kyKKhaiTuThang />
            <kyKKhaiDenThang />
          </KyKKhaiThue>
          <maCQTNoiNop>70129</maCQTNoiNop>
          <tenCQTNoiNop>Thuế cơ sở 14 Thành phố Hồ Chí Minh</tenCQTNoiNop>
          <ngayLapTKhai>2026-04-25</ngayLapTKhai>
          <GiaHan>
            <maLyDoGiaHan />
            <lyDoGiaHan />
          </GiaHan>
          <nguoiKy>NGUYỄN XUÂN LÂM</nguoiKy>
          <ngayKy>2026-04-25</ngayKy>
          <nganhNgheKD />
        </TKhaiThue>
        <NNT>
          <mst>0313829148</mst>
          <tenNNT>CÔNG TY TNHH ĐẦU TƯ KHÁCH SẠN HẢI THÀNH</tenNNT>
          <dchiNNT>Số 174/21 Điện Biên Phủ, Phường 17</dchiNNT>
          <phuongXa />
          <maHuyenNNT />
          <tenHuyenNNT />
          <maTinhNNT>701</maTinhNNT>
          <tenTinhNNT>Thành phố Hồ Chí Minh</tenTinhNNT>
          <dthoaiNNT />
          <faxNNT />
          <emailNNT />
        </NNT>
      </TTinTKhaiThue>
    </TTinChung>
  </HSoKhaiThue>
</HSoThueDTu>
"""


def extract_fn(name):
    try:
        idx = src.index('async def ' + name + '(')
    except ValueError:
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


class _FakeHTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class _FakeUploadFile:
    """Giả UploadFile của FastAPI — chỉ cần .read() async trả bytes, đúng
    những gì import_tkhai_xml() thật sự dùng."""
    def __init__(self, content_bytes):
        self._content = content_bytes

    async def read(self):
        return self._content


_tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp_db.close()


def _fresh_db():
    conn = sqlite3.connect(_tmp_db.name, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS cqt_ma_ten (
        ten_cqt TEXT PRIMARY KEY, ma_cqt TEXT, cap_nhat_at TEXT
    )""")
    return conn


ns = {'datetime': datetime}
ns['db'] = _fresh_db
ns['HTTPException'] = _FakeHTTPException
ns['File'] = lambda *a, **k: None
ns['UploadFile'] = object
exec(extract_fn('_parse_tkhai_xml_htkk'), ns)
exec(extract_fn('_ghi_nho_ma_cqt'), ns)
exec(extract_fn('import_tkhai_xml'), ns)
_parse_tkhai_xml_htkk = ns['_parse_tkhai_xml_htkk']
_ghi_nho_ma_cqt = ns['_ghi_nho_ma_cqt']
import_tkhai_xml = ns['import_tkhai_xml']

_conn0 = _fresh_db()
_conn0.execute("DELETE FROM cqt_ma_ten")
_conn0.commit()
_conn0.close()

# ===== Test 1 (QUAN TRỌNG — đúng dữ liệu THẬT người dùng đã tải lên):
# _parse_tkhai_xml_htkk() phải trích đúng maCQTNoiNop/tenCQTNoiNop/nguoiKy
# và mst/tenNNT/dchiNNT trong <NNT> — đúng NGUYÊN VĂN cấu trúc thẻ thật,
# không đoán tên thẻ khác. =====
info = _parse_tkhai_xml_htkk(XML_THAT)
assert info["mst"] == "0313829148", f"got {info}"
assert info["ten"] == "CÔNG TY TNHH ĐẦU TƯ KHÁCH SẠN HẢI THÀNH", f"got {info}"
assert info["dia_chi"] == "Số 174/21 Điện Biên Phủ, Phường 17", f"got {info}"
assert info["ma_cqt"] == "70129", f"got {info}"
assert info["ten_cqt"] == "Thuế cơ sở 14 Thành phố Hồ Chí Minh", f"got {info}"
assert info["nguoi_ky"] == "NGUYỄN XUÂN LÂM", f"got {info}"
print("PASS 1: _parse_tkhai_xml_htkk() trích đúng mst/ten/dia_chi/ma_cqt/ten_cqt/nguoi_ky từ file tờ "
      "khai HTKK thật đã nộp thành công (01_GTGT_TT80-Q12026-L00.xml).")

# ===== Test 2 (không hồi quy): file không phải tờ khai HTKK (không có các
# thẻ mong đợi) -> mọi field trả về rỗng, KHÔNG lỗi/crash. =====
info2 = _parse_tkhai_xml_htkk("<root><khac>khong lien quan</khac></root>")
assert all(v == "" for v in info2.values()), f"File lạ -> phải trả rỗng an toàn — got {info2}"
print("PASS 2: file không phải tờ khai HTKK -> trả rỗng an toàn ở mọi field, không lỗi.")

# ===== Test 3 (không hồi quy): thẻ chứa ký tự đặc biệt đã escape (vd '&amp;')
# -> phải được giải mã lại đúng (unescape), không giữ nguyên '&amp;'. =====
info3 = _parse_tkhai_xml_htkk("<tenNNT>CÔNG TY A &amp; B</tenNNT>")
assert info3["ten"] == "CÔNG TY A & B", f"Phải unescape HTML entity — got {info3}"
print("PASS 3: thẻ có HTML entity (&amp;) được giải mã đúng lại thành '&'.")

# ===== Test 4 (QUAN TRỌNG — endpoint import_tkhai_xml): tải lên file tờ
# khai thật -> trả đúng thông tin đã trích, ĐỒNG THỜI ghi thẳng luôn cặp
# Mã+Tên CQT vào bảng "học" cqt_ma_ten (không cần đợi người dùng tự nhập
# xác nhận lại như luồng XInvoice, vì đây là dữ liệu ĐÃ ĐƯỢC CQT CHẤP
# NHẬN, đáng tin hơn). =====
fake_file = _FakeUploadFile(XML_THAT.encode("utf-8"))
ket_qua4 = asyncio.run(import_tkhai_xml(fake_file))
assert ket_qua4["ma_cqt"] == "70129" and ket_qua4["ten_cqt"] == "Thuế cơ sở 14 Thành phố Hồ Chí Minh", (
    f"got {ket_qua4}")
assert ket_qua4["nguoi_ky"] == "NGUYỄN XUÂN LÂM", f"got {ket_qua4}"
conn4 = _fresh_db()
row4 = conn4.execute("SELECT ma_cqt FROM cqt_ma_ten WHERE ten_cqt=?",
                      ("Thuế cơ sở 14 Thành phố Hồ Chí Minh",)).fetchone()
conn4.close()
assert row4 is not None and row4["ma_cqt"] == "70129", (
    f"import_tkhai_xml() phải tự ghi cặp Mã+Tên CQT (dữ liệu đã được CQT chấp nhận) vào bảng học ngay "
    f"khi nhập file, không cần đợi add_company/update_company — got {dict(row4) if row4 else None}")
print("PASS 4: import_tkhai_xml() trả đúng thông tin trích từ file VÀ tự ghi thẳng cặp Mã+Tên CQT vào "
      "bảng 'học' cqt_ma_ten ngay khi nhập (dữ liệu đã được CQT chấp nhận, đáng tin cậy nhất).")

# ===== Test 5 (không hồi quy): file không đọc được thông tin gì (rỗng hết)
# -> báo lỗi rõ ràng (400), không âm thầm trả dữ liệu rỗng khiến giao diện
# tưởng đã nhập xong. =====
fake_file2 = _FakeUploadFile(b"<root><khac>khong lien quan</khac></root>")
loi5 = None
try:
    asyncio.run(import_tkhai_xml(fake_file2))
except _FakeHTTPException as e:
    loi5 = e
assert loi5 is not None and loi5.status_code == 400, f"File không đọc được gì -> phải báo lỗi 400 rõ ràng — got {loi5}"
print("PASS 5: file không đọc được thông tin gì -> báo lỗi 400 rõ ràng, không âm thầm trả rỗng.")

os.unlink(_tmp_db.name)
print("\nALL DONE")
