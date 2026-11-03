import io, os, sys, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import docx
import gpkd_soan as g

# DỮ LIỆU GIẢ hoàn toàn (không phải người/công ty thật)
def ng(ten, von, cc, gt="Nam"):
    return {"ho_ten": ten, "von": von, "cccd": cc, "ngay_sinh": "01/02/1980", "gioi_tinh": gt, "quoc_tich": "Việt Nam", "dan_toc": "Kinh",
            "dia_chi": "1 Đường A, Phường B, TP C", "noi_cap": "Cục X", "ngay_cap": "01/01/2021"}

BASE = {"loai": ["chuyen_doi"], "dn": {"ten": "CÔNG TY TNHH GIẢ", "ma_so": "0300000001", "loai_hinh": "Công ty TNHH hai thành viên trở lên",
        "co_quan": "Phòng ĐKKD", "so_vb": "01", "ngay_lap": "03/11/2026"},
        "hien_tai": {"dd_ho_ten": "NGUYỄN AAA", "dd_chuc_danh": "Giám đốc", "ngay_cap_gcn": "01/01/2020"},
        "ht_nganh": [{"ma": "4610", "ten": "Đại lý"}, {"ma": "6201", "ten": "Lập trình"}], "ht_von": "1000000000",
        "ht_dia_chi": {"so_nha": "1 Đường A", "xa": "Phường B", "tinh": "TP C"}}


def tao(du):
    z, ten, cb = g.tao_ho_so(du, None, False)
    zf = zipfile.ZipFile(io.BytesIO(z))
    return {n: docx.Document(io.BytesIO(zf.read(n))) for n in zf.namelist()}, cb


def van_ban(d):
    t = [p.text for p in d.paragraphs]
    for b in d.tables:
        for r in b.rows:
            t += [c.text for c in r.cells]
    return "\n".join(t)

# 1) 2 TV -> 1 TV
du = dict(BASE, chuyen_doi={"den": "1tv", "nganh_chinh": "4610"},
          thanh_vien={"ht": [ng("NGUYỄN AAA", "600000000", "079000000001"), dict(ng("TRẦN BBB", "400000000", "079000000002", "Nữ"), bo=True, chuyen_cho="h0")], "moi": []})
f, cb = tao(du)
ten = sorted(f)
assert any(n.startswith("1_Mau2_") for n in ten) and any(n.startswith("2_Dieu_le_TNHH_1TV") for n in ten) and any(n.startswith("3_Hop_dong") for n in ten) \
    and any(n.startswith("4_Mau10") for n in ten) and any(n.startswith("5_Quyet_dinh") for n in ten), ten
gd = van_ban(next(v for k, v in f.items() if k.startswith("1_")))
assert "chuyển đổi loại hình doanh nghiệp ☒" in gd.replace("\n", " ").replace(" | ", " ") or "☒" in gd
qd = van_ban(next(v for k, v in f.items() if k.startswith("5_")))
assert "từ loại hình công ty trách nhiệm hữu hạn hai thành viên trở lên sang công ty trách nhiệm hữu hạn một thành viên" in qd and "400.000.000" in qd and "100%" in qd, qd[:600]
hd = van_ban(next(v for k, v in f.items() if k.startswith("3_")))
assert "TRẦN BBB" in hd and "NGUYỄN AAA" in hd
print("PASS 1: 2 TV -> 1 TV ra Mẫu 2 + Điều lệ 1TV + Hợp đồng + Mẫu 10 + Quyết định, đúng nội dung chuyển nhượng.")

# 2) 1 TV -> 2 TV (thêm thành viên mới, chuyển một phần vốn)
du = dict(BASE, dn=dict(BASE["dn"], loai_hinh="Công ty TNHH một thành viên"), chuyen_doi={"den": "2tv", "nganh_chinh": "4610"},
          thanh_vien={"ht": [dict(ng("NGUYỄN AAA", "1000000000", "079000000001"), cn=[{"den": "m0", "tien": "400000000"}])], "moi": [ng("TRẦN BBB", "", "079000000002", "Nữ")]})
f, cb = tao(du)
ten = sorted(f)
assert any(n.startswith("1_Mau3_") for n in ten) and any(n.startswith("2_Dieu_le_TNHH_2TV") for n in ten) and any(n.startswith("6_Mau6") for n in ten), ten
dl = van_ban(next(v for k, v in f.items() if k.startswith("2_")))
assert "Hội đồng thành viên" in dl and "TRẦN BBB" in dl
print("PASS 2: 1 TV -> 2 TV ra Mẫu 3 + Điều lệ 2TV + Mẫu 6.")

# 3) TNHH -> cổ phần (đổi tiền tố tên, Mẫu 4, Mẫu 7)
du = dict(BASE, chuyen_doi={"den": "cp", "nganh_chinh": "4610", "menh_gia": "10000"},
          thanh_vien={"ht": [ng("NGUYỄN AAA", "500000000", "079000000001"), ng("TRẦN BBB", "300000000", "079000000002", "Nữ")], "moi": [ng("LÊ CCC", "200000000", "079000000003")]})
f, cb = tao(du)
ten = sorted(f)
assert any(n.startswith("1_Mau4_") for n in ten) and any(n.startswith("2_Dieu_le_Co_phan") for n in ten) and any(n.startswith("6_Mau7") for n in ten), ten
qd = van_ban(next(v for k, v in f.items() if k.startswith("5_")))
assert "CÔNG TY CỔ PHẦN GIẢ" in qd and "50.000" in qd, qd[:800]
assert any("CÔNG TY TNHH GIẢ → CÔNG TY CỔ PHẦN GIẢ" in c for c in cb)
print("PASS 3: TNHH -> cổ phần: Mẫu 4, Điều lệ CP, Mẫu 7, tên đổi tiền tố, cổ phần = vốn / mệnh giá.")

# 4) cảnh báo: sang 1TV mà còn 2 người; thiếu dữ liệu -> báo thiếu, không bịa
du = dict(BASE, chuyen_doi={"den": "1tv"}, thanh_vien={"ht": [ng("A", "1", "1"), ng("B", "1", "2")], "moi": []})
f, cb = tao(du)
assert any("chỉ có 1 chủ sở hữu" in c for c in cb) and any("Còn thiếu" in c for c in cb), cb
print("PASS 4: cảnh báo khi danh sách sau chuyển đổi không hợp loại hình.")

# 5) mục khác không bị ảnh hưởng: không tick chuyen_doi thì đi đường cũ
z, ten, cb = g.tao_ho_so(dict(BASE, loai=["ten"], ten={"viet": "CÔNG TY MỚI"}), None, False)
assert ten.startswith("Ho_so_thay_doi_DKDN_")
print("PASS 5: hồ sơ thay đổi thông thường vẫn chạy như cũ.")

# 6) ngành: bỏ ngành bị tô màu, tên trống tra theo mã, chi tiết giữ nguyên, trùng mã gộp
du = dict(BASE, chuyen_doi={"den": "1tv"}, ht_nganh=[{"ma": "4610", "ten": "", "chi_tiet": "Đại lý, môi giới", "chinh": True}, {"ma": "2029", "ten": "X", "mau": "red"}, {"ma": "6201", "ten": "Lập trình"}],
          nganh={"them": [{"ma": "4610", "ten": "", "chi_tiet": "Đại lý, môi giới"}], "bo": [], "sua": []}, loai=["chuyen_doi", "nganh"],
          thanh_vien={"ht": [ng("NGUYỄN AAA", "1000000000", "079000000001")], "moi": []})
tt = __import__("gpkd_chuyen_doi").thong_tin_sau(du)
mas = [x["ma"] for x in tt["nganh"]]
assert mas == ["4610", "6201"], mas
assert tt["nganh"][0]["ten"] and tt["nganh"][0]["chi_tiet"] == "Đại lý, môi giới" and tt["nganh"][0].get("chinh"), tt["nganh"][0]
print("PASS 6: ngành tô màu bị loại, tên trống tra theo mã, trùng mã gộp, giữ ngành chính.")

# 7) ô "Loại hình" gom sai (ghi một thành viên) nhưng giao diện gửi tu=2tv theo số thành viên -> Quyết định ghi đúng loại hình hiện tại
du = dict(BASE, dn=dict(BASE["dn"], loai_hinh="Công ty trách nhiệm hữu hạn một thành viên"), chuyen_doi={"tu": "2tv", "den": "1tv"},
          thanh_vien={"ht": [ng("NGUYỄN AAA", "600000000", "079000000001"), dict(ng("TRẦN BBB", "400000000", "079000000002", "Nữ"), bo=True, chuyen_cho="h0")], "moi": []})
f, cb = tao(du)
qd = van_ban(next(v for k, v in f.items() if k.startswith("5_")))
assert "từ loại hình công ty trách nhiệm hữu hạn hai thành viên trở lên sang công ty trách nhiệm hữu hạn một thành viên" in qd
assert not any("trùng loại hình" in c for c in cb)
print("PASS 7: loại hình hiện tại theo số thành viên (2 TV) dù ô chữ ghi sai.")

# 8) người chuyển hết vốn (còn 0) không còn trong cơ cấu sau; thông tin thuế mặc định
du = dict(BASE, chuyen_doi={"den": "1tv"}, thanh_vien={"ht": [ng("NGUYỄN AAA", "600000000", "079000000001"), dict(ng("TRẦN BBB", "400000000", "079000000002", "Nữ"), cn=[{"den": "h0", "tien": "400000000"}])], "moi": []})
f, cb = tao(du)
qd = van_ban(next(v for k, v in f.items() if k.startswith("5_")))
cau_truc = qd.split("Cơ cấu vốn góp sau khi đổi:")[1].split("1. Tên công ty")[0]
assert "NGUYỄN AAA" in cau_truc and "TRẦN BBB" not in cau_truc, cau_truc
gd = van_ban(next(v for k, v in f.items() if k.startswith("1_")))
flat = gd.replace("\n", " ")
assert "Lao động" in flat or "lao động" in flat
import re as _re
assert "Áp dụng từ ngày 01/01 đến ngày 31/12" in flat and _re.search(r"Tổng số lao động \(dự kiến\):\s*2", flat), flat[-1500:]
x = next(v for k, v in f.items() if k.startswith("1_"))
ticks = "".join(t.text or "" for t in x.element.body.iter(docx.oxml.ns.qn("w:t")))
assert "Không ☒" in ticks and "Khấu trừ" in flat, ticks[-600:]
print("PASS 8: người còn 0 vốn bị loại khỏi cơ cấu sau; thuế mặc định (độc lập, 01/01-31/12, 2 lao động, không BOT, khấu trừ).")

# 9) ngày thông qua Điều lệ lấy từ ô "Ngày cấp GCN = ngày thông qua Điều lệ"; ký bằng tư cách Chủ sở hữu/Chủ tịch HĐTV, không dùng chữ ký Giám đốc
import base64, io as _io
from PIL import Image as _Im
def _png(mau):
    b = _io.BytesIO(); _Im.new("RGB", (60, 30), mau).save(b, "PNG"); return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
A_CSH, A_GD = _png((0, 0, 200)), _png((200, 0, 0))
du = dict(BASE, hien_tai=dict(BASE["hien_tai"], ngay_cap_gcn="19/06/2019", chu_so_huu="NGUYỄN AAA"), chuyen_doi={"den": "1tv"},
          thanh_vien={"ht": [ng("NGUYỄN AAA", "600000000", "079000000001"), dict(ng("TRẦN BBB", "400000000", "079000000002", "Nữ"), bo=True, chuyen_cho="h0")], "moi": []})
z, _t, cb = g.tao_ho_so(du, {"cccd:079000000001": A_CSH, "giam_doc": A_GD}, False)
zf = zipfile.ZipFile(io.BytesIO(z))
def anh_trong(ten):
    x = zf.read(next(n for n in zf.namelist() if n.startswith(ten)))
    zz = zipfile.ZipFile(io.BytesIO(x)); med = [n for n in zz.namelist() if n.startswith("word/media/")]
    return [zz.read(n) for n in med]
qd = docx.Document(io.BytesIO(zf.read(next(n for n in zf.namelist() if n.startswith("5_")))))
assert "thông qua ngày 19/06/2019" in van_ban(qd), van_ban(qd)[:700]
def mau_anh(raw):
    im = _Im.open(_io.BytesIO(raw)).convert("RGB"); return im.getpixel((im.width // 2, im.height // 2))
for pre in ("1_", "4_", "5_"):
    ims = anh_trong(pre)
    assert ims and all(mau_anh(r)[2] > 150 and mau_anh(r)[0] < 80 for r in ims), (pre, [mau_anh(r) for r in ims])   # chỉ ảnh xanh (Chủ sở hữu), không có ảnh đỏ (Giám đốc)
print("PASS 9: ngày Điều lệ điền từ ngày cấp GCN; Mẫu 2 và Quyết định ký bằng chữ ký Chủ sở hữu, không dùng chữ ký Giám đốc.")
