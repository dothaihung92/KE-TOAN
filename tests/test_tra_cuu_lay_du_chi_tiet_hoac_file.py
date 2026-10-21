import io, json, os, sqlite3, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật: tra cứu báo "4556/4556 (đã lấy đủ)" nhưng Kết xuất Excel báo 2 hóa đơn (C25TSG số 254, 274) "thiếu cả detail lẫn file".
# Nay ở bước tra cứu: không lấy được chi tiết thì TẢI BÙ FILE XML; vẫn không được thì trả danh sách còn thiếu KÈM LÝ DO (HTTP …) để
# màn hình kết quả KHÔNG báo "đã lấy đủ".
server.time.sleep = lambda s: None
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY, company_id, khmshdon, khhdon, shdon, loai, he_thong, tdlap, nbmst, ttxly, detail_json)")
for i, so in ((1, 254), (2, 274)):
    conn.execute("INSERT INTO invoices VALUES (?,7,'1','C25TSG',?,'sold','query','2025-09-01T00:00:00','0317489936','5',NULL)", (i, so))
conn.commit()


class KhongDong:
    def __init__(self, c): self.c = c
    def execute(self, *a): return self.c.execute(*a)
    def commit(self): self.c.commit()
    def close(self): pass


server.db = lambda: KhongDong(conn)


def zip_hd(so):
    b = io.BytesIO()
    zipfile.ZipFile(b, "w").writestr("invoice.xml", f"<HDon><DLHDon><TTChung><KHHDon>C25TSG</KHHDon><SHDon>{so}</SHDon></TTChung></DLHDon></HDon>")
    return b.getvalue()


class Client(server.GDTClient):
    def __init__(self):
        self.token = "T"
    def get_detail(self, nbmst, khhdon, khmshdon, shdon, he_thong="query", max_retry=None, cho_khi_429=True, loai=None):
        self._ghi_loi_chi_tiet("HTTP 500: Internal Server Error")
        return None
    def download_xml(self, nbmst, khhdon, khmshdon, shdon, loai="purchase", he_thong="query", max_retry=None):
        return zip_hd(shdon) if str(shdon) == "254" else None


d = tempfile.mkdtemp()
tb = []
kq = server._dam_bao_du_chi_tiet_hoa_don(7, Client(), d, lambda **k: tb.append(k), chi_ids=[1, 2])
assert os.path.isfile(os.path.join(d, "Tai_bu_hoa_don_thieu", "C25TSG_254_0317489936.zip")), os.listdir(d)
assert [str(x["shdon"]) for x in kq] == ["274"] and "HTTP 500" in kq[0]["ly_do"] and "file[" in kq[0]["ly_do"], kq
canh_bao = [k["text"] for k in tb if k.get("stage") == "warn"]
assert canh_bao and "C25TSG số 274" in canh_bao[-1] and "HTTP 500" in canh_bao[-1] and "C25TSG số 254" not in canh_bao[-1], canh_bao
assert conn.execute("SELECT detail_json FROM invoices WHERE id=1").fetchone()[0] is None      # tải bù được file: không ghi chữ "FILE" vào detail_json
print("PASS 1: không lấy được chi tiết -> tải bù file XML (HĐ 254 có file); HĐ 274 vẫn thiếu -> trả về kèm lý do HTTP 500.")

class ClientOk(Client):
    def get_detail(self, *a, **k):
        return {"nbmst": "0317489936", "hdhhdvu": [{"ten": "Hàng"}]}
conn.execute("UPDATE invoices SET detail_json=NULL"); conn.commit()
assert server._dam_bao_du_chi_tiet_hoa_don(7, ClientOk(), tempfile.mkdtemp(), lambda **k: None, chi_ids=[1, 2]) == []
assert all(json.loads(r[0])["hdhhdvu"] for r in conn.execute("SELECT detail_json FROM invoices"))
print("PASS 2: lấy đủ chi tiết -> trả danh sách rỗng.")

src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
assert "loi_tra_cuu=co_loi, thieu_chi_tiet=thieu_chi_tiet[:50])" in src
html = open(os.path.join(os.path.dirname(server.__file__), "static", "index.html"), encoding="utf-8").read()
i = html.index("function hienKetQua(m)")
assert "thieu_chi_tiet" in html[i:i + 3000] and "chưa lấy được chi tiết dòng hàng lẫn file XML" in html[i:i + 3000]
print("PASS 3: kết quả tra cứu mang danh sách hóa đơn thiếu chi tiết -> màn hình không báo 'đã lấy đủ'.")
print("ALL DONE")
