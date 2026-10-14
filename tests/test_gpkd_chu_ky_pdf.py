import base64
import io
import os
import sys
import tempfile
import zipfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server
import gpkd_soan as g
from PIL import Image, ImageDraw

# Kho chữ ký có thêm CHỦ SỞ HỮU (riêng từng công ty); chữ ký giám đốc + chủ sở hữu gắn được vào hồ sơ GPKD; xuất PDF có viền.
td = tempfile.mkdtemp()
server.DB_PATH = os.path.join(td, "t.db")
server.DATA_DIR = td
server.init_db()
c = server.db()
c.execute("INSERT INTO companies (id, ten, mst) VALUES (1, 'CTY A', '0300000001')")
c.commit()
c.close()


def anh(mau):
    im = Image.new("RGB", (300, 100), "white")
    ImageDraw.Draw(im).line([(10, 80), (120, 20), (200, 70), (290, 30)], fill=mau, width=5)
    b = io.BytesIO()
    im.save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


conn = server.db()
server._ck_dam_bao_bang(conn)
server._ck_luu_1(conn, 1, "giam_doc", "Đỗ Thị Ánh Tuyết", anh((0, 0, 200)), True)
server._ck_luu_1(conn, 1, "chu_so_huu", "Đỗ Thị Ánh Tuyết", anh((200, 0, 0)), True)
conn.commit()
conn.close()
d = server._vb_chu_ky_dict(1)
assert d.get("giam_doc") and d.get("chu_so_huu") and d["giam_doc"] != d["chu_so_huu"]
ds = server.chu_ky_danh_sach(1)
assert ds["chu_so_huu"]["la_cs"] and ds["chu_so_huu"]["co_anh"] and ds["chu_so_huu"]["khoa"] == "cs:cty1"
assert all(m["khoa"] != "cs:cty1" for m in ds["da_luu"])
assert server.chu_ky_cho_in(1)["chu_so_huu"]
print("PASS 1: kho chữ ký có thêm chủ sở hữu (riêng từng công ty), tách khỏi giám đốc.")

# chữ ký chưa tick đồng ý -> không dùng
conn = server.db()
conn.execute("UPDATE chu_ky_chung SET xac_nhan=0 WHERE khoa='cs:cty1'")
conn.commit()
conn.close()
assert not server._vb_chu_ky_dict(1).get("chu_so_huu")
conn = server.db()
conn.execute("UPDATE chu_ky_chung SET xac_nhan=1 WHERE khoa='cs:cty1'")
conn.commit()
conn.close()
print("PASS 2: chữ ký chưa xác nhận đồng ý thì không được dùng.")

DU = {"loai": ["dia_chi"], "tao_uy_quyen": True, "dn": {"ten": "Cty A", "ma_so": "0300000001", "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên"},
      "dia_chi": {"so_nha": "x", "doi_thue": True}, "hien_tai": {"dd_ho_ten": "Đỗ Thị Ánh Tuyết", "chu_so_huu": "Đỗ Thị Ánh Tuyết"},
      "uy_quyen": {"ho_ten": "Nguyễn Văn B"}}


def so_anh(z, tien_to):
    n = [x for x in z.namelist() if x.startswith(tien_to)][0]
    zz = zipfile.ZipFile(io.BytesIO(z.read(n)))
    xml = zz.read("word/document.xml").decode("utf-8")
    if "word/media/" in " ".join(zz.namelist()):
        assert 'behindDoc="1"' in xml and "<wp:anchor" in xml and "<wp:inline" not in xml     # ảnh nổi phía sau chữ
    return len([x for x in zz.namelist() if x.startswith("word/media/")])


ky = {k: server._vb_chu_ky_dict(1).get(k) for k in ("giam_doc", "chu_so_huu")}
ky["ben_b"] = anh((0, 120, 0))
z = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(DU, None, ky)[0]))
assert so_anh(z, "Mau12") == 1 and so_anh(z, "Quyet_dinh") == 1 and so_anh(z, "Giay_uy_quyen") == 2      # UQ: giám đốc (Bên A) + bên nhận ủy quyền (Bên B)
z0 = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(DU)[0]))
assert so_anh(z0, "Mau12") == 0 and so_anh(z0, "Quyet_dinh") == 0 and so_anh(z0, "Giay_uy_quyen") == 0
# đổi người đại diện: người ký Mẫu 12 là người MỚI -> không gắn chữ ký người đại diện cũ
du2 = dict(DU, loai=["dia_chi", "dai_dien"], dai_dien=[{"ho_ten": "Người Mới"}])
z2 = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du2, None, ky)[0]))
assert so_anh(z2, "Mau12") == 1 and so_anh(z2, "Quyet_dinh") == 1      # công ty 1TV: Chủ tịch công ty (chủ sở hữu) ký Mẫu 12 bằng chữ ký của chính mình, không dùng chữ ký giám đốc cũ
print("PASS 3: gắn chữ ký giám đốc (Mẫu 12, Giấy ủy quyền) và chủ sở hữu (Quyết định); không gắn chữ ký người đại diện cũ cho người mới.")

# khối chữ ký không bị tách trang; "đề nghị cấp Giấy xác nhận" luôn tick
import docx as _d
for tien in ("Mau12", "Quyet_dinh", "Giay_uy_quyen"):
    n = [x for x in z.namelist() if x.startswith(tien)][0]
    xml = zipfile.ZipFile(io.BytesIO(z.read(n))).read("word/document.xml").decode("utf-8")
    assert "<w:cantSplit" in xml and "<w:keepNext" in xml, tien
n12 = [x for x in z.namelist() if x.startswith("Mau12")][0]
assert "☒ Đề nghị Quý Cơ quan cấp Giấy xác nhận" in "\n".join(p.text for p in _d.Document(io.BytesIO(z.read(n12))).paragraphs)
print("PASS 3b: ảnh chữ ký nổi phía sau chữ; khối chữ ký giữ 1 trang; luôn tick đề nghị cấp Giấy xác nhận.")

# PDF có viền: mỗi trang thành ảnh + khung viền
import pymupdf
src = pymupdf.open()
pg = src.new_page()
pg.insert_text((72, 100), "Hello scan", fontsize=14)
pdf = g.pdf_vien_scan(src.tobytes())
o = pymupdf.open(stream=pdf, filetype="pdf")
assert len(o) == 1 and len(o[0].get_images()) == 1 and not o[0].get_text().strip()
px = o[0].get_pixmap(dpi=72, alpha=False)
cx, cy = px.width // 2, px.height // 2
sang = lambda x, y: sum(px.pixel(x, y)[:3]) / 3
assert sang(cx, 2) < sang(cx, cy) - 8 and sang(px.width - 2, cy) < sang(cx, cy) - 8, "mép trên/phải phải tối hơn giữa trang"
assert sang(cx, cy) > 240
print("PASS 4: PDF xuất dạng ảnh từng trang, mép trang tối nhẹ như bản scan.")

# không có Word/LibreOffice -> cảnh báo rõ, vẫn trả zip
goc = g._timn_trinh_chuyen_pdf
g._timn_trinh_chuyen_pdf = lambda: None
try:
    b, _t, cb = g.tao_ho_so(DU, None, ky, True)
finally:
    g._timn_trinh_chuyen_pdf = goc
assert any("Chưa xuất PDF được" in x and "Word" in x for x in cb), cb
assert zipfile.ZipFile(io.BytesIO(b)).namelist()
print("PASS 5: máy thiếu Word/LibreOffice thì báo rõ, vẫn tạo file Word.")

# giao diện
h = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "la_cs" in h and 'id="ss_gan_ky"' in h and 'id="ss_xuat_pdf"' in h and "gan_chu_ky:du.gan_chu_ky" in h
print("PASS 6: giao diện có dòng chủ sở hữu trong Kho chữ ký và các lựa chọn gắn chữ ký/xuất PDF.")
print("\nALL DONE")
