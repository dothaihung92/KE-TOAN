import base64, io, os, sys, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import docx
from PIL import Image, ImageDraw
import gpkd_soan as g

# Ca thật (SOL AGENCY, TNHH 1 thành viên): Mẫu 12 ký bằng tư cách Chủ sở hữu nhưng chữ ký trong Kho chữ ký chỉ lưu ở mục Giám đốc (cùng 1 người)
# -> Mẫu 12 không gắn chữ ký. Nay: cùng họ tên với người đại diện (hoặc chủ sở hữu) thì dùng chữ ký đã có.
im = Image.new("RGBA", (300, 120), (255, 255, 255, 0)); ImageDraw.Draw(im).line((10, 100, 150, 20, 290, 90), fill=(0, 0, 160, 255), width=5)
bio = io.BytesIO(); im.save(bio, "PNG")
ANH = "data:image/png;base64," + base64.b64encode(bio.getvalue()).decode()

def mau12(loai_hinh, chu_ky):
    du = {"loai": ["cap_nhat"], "cap_nhat": {"dia_chi": {"so_nha": "34 Bùi Thế Mỹ", "xa": "Phường Bảy Hiền", "tinh": "Hồ Chí Minh"}, "nguoi": []},
          "dn": {"ten": "CÔNG TY TNHH SOL AGENCY", "ma_so": "0318807606", "loai_hinh": loai_hinh},
          "hien_tai": {"dd_ho_ten": "Nguyễn Thị Ánh Nguyệt", "dd_chuc_danh": "Giám đốc", "chu_so_huu": "NGUYỄN THỊ ÁNH NGUYỆT", "dia_chi": "34 Bùi Thế Mỹ"}}
    zb = g.tao_ho_so(du, chu_ky)[0]
    z = zipfile.ZipFile(io.BytesIO(zb))
    n = next(x for x in z.namelist() if x.startswith("Mau12"))
    return z.read(n)

def co_chu_ky(b):
    return b"<w:drawing" in b and b"image" in b
import re
def so_anh(b):
    z = zipfile.ZipFile(io.BytesIO(b))
    return len([x for x in z.namelist() if x.startswith("word/media/")])

for lh in ("Công ty trách nhiệm hữu hạn một thành viên", "Công ty trách nhiệm hữu hạn hai thành viên trở lên"):
    assert so_anh(mau12(lh, {"giam_doc": ANH})) >= 1, lh                   # chỉ có chữ ký ở mục Giám đốc, cùng người -> vẫn gắn
    assert so_anh(mau12(lh, {})) == 0
print("PASS: Mẫu 12 gắn chữ ký khi người ký (Chủ sở hữu/Chủ tịch HĐTV) cũng là người đại diện có chữ ký ở mục Giám đốc; không có chữ ký nào thì không gắn.")
print("ALL DONE")
