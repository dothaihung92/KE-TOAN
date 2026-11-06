import base64, io, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
import gpkd_soan as g

# Giấy đề nghị Mẫu 12 (TNHH 1 thành viên): hồ sơ KHÔNG đổi giám đốc / chủ sở hữu (vd chỉ đổi tên tiếng nước ngoài + địa chỉ) -> ký bằng
# chữ ký CÓ CON DẤU của giám đốc (Kho chữ ký - mục Giám đốc), không dùng chữ ký tay của chủ sở hữu. Có đổi giám đốc/chủ thì giữ cách cũ.
def anh(mau):
    b = io.BytesIO(); Image.new("RGB", (300, 120), mau).save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
GD, CSH = anh((200, 0, 0)), anh((0, 0, 200))           # đỏ = chữ ký có dấu của giám đốc, xanh = chữ ký tay chủ sở hữu
du = {"loai": ["ten", "dia_chi"], "dn": {"ten": "CÔNG TY TNHH DỊCH VỤ FXC", "ma_so": "0316627693", "co_quan": "Phòng Đăng ký kinh doanh",
                                       "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên"},
      "hien_tai": {"chu_so_huu": "TRẦN ĐỨC HOÀNG", "dd_ho_ten": "TRẦN ĐỨC HOÀNG", "dd_chuc_danh": "Giám đốc"},
      "ten": {"nuoc_ngoai": "FXC SERVICES COMPANY LIMITED", "viet_tat": "CTY TNHH DV FXC"},
      "dia_chi": {"so_nha": "78/3 Bình Lợi", "xa": "Phường Bình Lợi Trung", "tinh": "TP Hồ Chí Minh"}}

def mau_anh(d):
    out = []
    for rel in d.part.rels.values():
        if "image" in rel.reltype:
            im = Image.open(io.BytesIO(rel.target_part.blob)).convert("RGB")
            out.append("do" if im.getpixel((im.width // 2, im.height // 2))[0] > 150 else "xanh")
    return out

d = g.soan_mau12(du, {"giam_doc": GD, "chu_so_huu": CSH})
assert mau_anh(d) == ["do"], mau_anh(d)
assert "TRẦN ĐỨC HOÀNG" in "\n".join(c.text for t in d.tables for r in t.rows for c in r.cells)
print("PASS 1: không đổi giám đốc/chủ -> Mẫu 12 ký bằng chữ ký có con dấu của giám đốc.")

d = g.soan_mau12(dict(du, loai=["ten", "dia_chi", "chu_so_huu"], chu_so_huu_moi={"ho_ten": "NGUYỄN VĂN B"}), {"giam_doc": GD, "chu_so_huu": CSH})
assert "do" not in mau_anh(d), mau_anh(d)
d = g.soan_mau12(dict(du, loai=["ten", "dai_dien"], dai_dien=[{"ho_ten": "LÊ VĂN C"}]), {"giam_doc": GD, "chu_so_huu": CSH})
assert "do" not in mau_anh(d), mau_anh(d)
print("PASS 2: có đổi chủ sở hữu / giám đốc -> không dùng chữ ký có dấu của giám đốc cũ.")

d = g.soan_mau12(du, {"chu_so_huu": CSH})                 # Kho chưa có chữ ký giám đốc -> như cũ (chữ ký chủ sở hữu)
assert mau_anh(d) == ["xanh"], mau_anh(d)
print("PASS 3: chưa có chữ ký giám đốc trong Kho -> dùng chữ ký chủ sở hữu như cũ.")
