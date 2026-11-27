import io, os, sys, zipfile, base64, re
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import gpkd_soan as g
from docx import Document

# 1TV đổi chủ sở hữu + đổi giám đốc (theo bộ hồ sơ tự soạn): Quyết định/UQ/Mẫu 10/13/15 do chủ sở hữu MỚI ký; chủ cũ ký Hợp đồng chuyển nhượng + ô "Chủ sở hữu cũ" Mẫu 15.
PNG = "data:image/png;base64," + ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
cu = {"ho_ten": "NGUYỄN VĂN CŨ", "cccd": "079111111111"}
moi = {"ho_ten": "TRẦN THỊ MỚI", "cccd": "079222222222", "ngay_sinh": "01/01/1990", "gioi_tinh": "Nữ", "so_nha": "1 A", "xa": "P1", "tinh": "TP.HCM",
       "von": "1.000.000.000"}
du = {"loai": ["chu_so_huu", "dai_dien", "cshhl"], "tao_uy_quyen": True,
      "dn": {"ten": "CÔNG TY TNHH DRAGON", "ma_so": "0300000001", "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên"},
      "hien_tai": {"chu_so_huu": cu["ho_ten"], "chu_so_huu_cccd": cu["cccd"], "dd_ho_ten": "NGUYỄN VĂN CŨ", "dd_chuc_danh": "GIÁM ĐỐC",
                   "ngay_cap_gcn": "01/01/2020", "dia_chi": "x"},
      "chu_so_huu_moi": moi,
      "dai_dien": [{"ho_ten": "TRẦN THỊ MỚI", "cccd": "079222222222", "chuc_danh": "GIÁM ĐỐC"}],
      "thanh_vien": {"ht": [dict(cu, von="1.000.000.000", bo=True, chuyen_cho="m0")], "moi": [moi]},
      "uy_quyen": {"ho_ten": "LÊ UỶ QUYỀN", "so_giay_to": "079333333333"}}
ck = {"giam_doc": PNG, "chu_so_huu": PNG, "cccd:079222222222": PNG, "cccd:079111111111": PNG}

assert g._chu_so_huu_moi_1tv(du)["ho_ten"] == "TRẦN THỊ MỚI"
assert g._chu_so_huu_moi_1tv(dict(du, loai=["dai_dien"])) is None
assert g._chu_so_huu_moi_1tv(dict(du, dn={"loai_hinh": "Công ty TNHH hai thành viên trở lên"})) is None
print("PASS 1: chỉ 1TV có tick đổi chủ sở hữu mới coi chủ mới là người ký.")

k = g._nguoi_ky_2tv(du, ck)
assert k and k[1] == "TRẦN THỊ MỚI" and k[2] == PNG, k
print("PASS 2: người ký 1TV = chủ sở hữu MỚI (không phải chủ cũ).")

zb, _, _ = g.tao_ho_so(du, ck)
z = zipfile.ZipFile(io.BytesIO(zb))
ten = z.namelist()
assert any(n.startswith("Mau15_") for n in ten) and any(n.startswith("Hop_dong_chuyen_nhuong_phan_von_gop_1_") for n in ten), ten
print("PASS 3: có Mẫu 15 + Hợp đồng chuyển nhượng phần vốn góp.")

def doc(pref):
    n = next(n for n in ten if n.startswith(pref))
    return Document(io.BytesIO(z.read(n))), z.read(n)

def n_anh(b):
    return zipfile.ZipFile(io.BytesIO(b)).read("word/document.xml").decode("utf8").count("<w:drawing")

d15, b15 = doc("Mau15_")
assert n_anh(b15) == 2, n_anh(b15)        # chủ mới + chủ cũ
t15 = "\n".join(c.text for tb in d15.tables for r in tb.rows for c in r.cells)
assert "TRẦN THỊ MỚI" in t15 and "NGUYỄN VĂN CŨ" in t15
assert "Mẫu số 15" not in "\n".join(p.text for p in d15.paragraphs)
print("PASS 4: Mẫu 15 gắn chữ ký cả chủ sở hữu mới (ô trái) và chủ cũ (ô phải), bỏ tiêu đề mẫu.")

_, bhd = doc("Hop_dong_chuyen_nhuong_phan_von_gop_1_")
assert n_anh(bhd) >= 1, n_anh(bhd)
print("PASS 5: Hợp đồng chuyển nhượng có chữ ký các bên.")

for pref in ("Mau13_", "Mau10_"):
    dd, bb = doc(pref)
    assert n_anh(bb) >= 1, (pref, n_anh(bb))
    assert "TRẦN THỊ MỚI" in "\n".join(c.text for tb in dd.tables for r in tb.rows for c in r.cells) + "\n".join(p.text for p in dd.paragraphs), pref
print("PASS 6: Mẫu 13 và Mẫu 10 do người mới ký (có ảnh).")

uq = [n for n in ten if "uy_quyen" in n.lower() or "Uy_quyen" in n]
assert uq, ten
t = "\n".join(p.text for p in Document(io.BytesIO(z.read(uq[0]))).paragraphs)
assert "Chủ sở hữu mới của CÔNG TY TNHH DRAGON" in t and "TRẦN THỊ MỚI" in t, t
print("PASS 7: Giấy ủy quyền Bên A = chủ sở hữu mới của công ty.")
