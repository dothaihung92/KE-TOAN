import os, sys, io, re, base64
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gpkd_soan as g
from PIL import Image, ImageDraw

# Ca thật (Phụ lục I-6 BIOGREEN): chữ ký thành viên bị đẩy LÊN 1 hàng (chữ ký người 1 nằm ở hàng tiêu đề, người 2 nằm ở hàng người 1)
# vì ảnh nổi neo theo đoạn lại lùi lên như có khoảng chừa ký; khối ký giám đốc bị tách sang trang 2; dấu giám đốc nhỏ.


def uri(im):
    b = io.BytesIO(); im.save(b, "PNG"); return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def ky(w, h, le):
    im = Image.new("RGB", (w, h), "white"); d = ImageDraw.Draw(im)
    d.line([(le, h - le), (w // 2, le), (w - le, h // 2)], fill=(20, 30, 140), width=6); return im


tv = {"ht": [{"ho_ten": "Dương Ngọc Bảo Châu", "cccd": "079197029102", "von": "2450000000"},
             {"ho_ten": "Trần Khả Vy", "cccd": "093199002120", "von": "2550000000"},
             {"ho_ten": "Người C", "cccd": "", "von": "100"}]}
du = {"dn": {"ten": "Cty B", "ma_so": "0315253276", "loai_hinh": "Công ty trách nhiệm hữu hạn hai thành viên trở lên"},
      "hien_tai": {"dd_ho_ten": "Trần Khả Vy"}, "thanh_vien": tv}
ck = {"cccd:079197029102": uri(ky(600, 300, 20)), "cccd:093199002120": uri(ky(1500, 1200, 400)), "giam_doc": uri(ky(900, 500, 60))}
d = g.soan_phu_luc_i6(du, ck)
g._bo_dong_trong_thua(d)
tb = d.tables[0]

# 1) chữ ký thành viên: ảnh NẰM TRONG DÒNG ở đúng hàng của người đó (không nổi, không lệch hàng), canh giữa ô
for i, r in enumerate(tb.rows):
    x = r.cells[12]._tc.xml
    assert "<wp:inline" not in x, ("mọi chữ ký đều để phía sau chữ", i)
    assert x.count("<wp:anchor") == (1 if i in (3, 4) else 0), (i, x.count("<wp:anchor"))
    if i in (3, 4):
        assert 'behindDoc="1"' in x and 'layoutInCell="1"' in x
        voff = int(re.search(r"positionV.*?posOffset>\s*(-?\d+)", x, re.S).group(1))
        cy = int(re.search(r'<wp:extent cx="\d+" cy="(\d+)"', x).group(1))
        assert 0 <= voff <= 0.1 * 360000 + 1, ("neo từ đỉnh ô xuống, không lùi lên hàng trên", voff)
        trh = r._tr.xpath("./w:trPr/w:trHeight")[0]
        assert trh.get(g.qn("w:hRule")) == "atLeast" and int(trh.get(g.qn("w:val"))) * 635 >= voff + cy, "hàng đủ cao chứa trọn ảnh"
print("PASS 1: chữ ký thành viên để phía sau chữ, nằm trọn trong đúng hàng người ký (hàng 1 = Châu, hàng 2 = Vy).")

# 2) ảnh có lề trắng to (chữ ký Vy: 1500x1200, nét chỉ ở giữa) được cắt lề -> cùng cỡ với chữ ký không có lề
kt = [tuple(int(v) for v in re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"', tb.rows[i].cells[12]._tc.xml).groups()) for i in (3, 4)]
assert all(cx <= 2.4 * 0.9 * 360000 * 1.06 and cy <= 1.4 * 360000 + 100 for cx, cy in kt), kt
assert kt[1][0] > 1.5 * 360000, ("chữ ký có lề trắng to không bị thu nhỏ", kt)
raw = base64.b64decode(ck["cccd:093199002120"].split(",", 1)[1])
_, w, h = g._cat_vien_anh(raw)
assert w < 800 and h < 500, (w, h)
trong = Image.new("RGBA", (50, 50), (0, 0, 0, 0)); b = io.BytesIO(); trong.save(b, "PNG")
assert g._cat_vien_anh(b.getvalue())[1:] == (50, 50), "ảnh trống giữ nguyên"
print("PASS 2: tự cắt lề trắng/trong suốt -> mọi mẫu chữ ký co theo đúng phần nét, cỡ đồng đều.")

# 3) khối ký (bảng của chính biểu mẫu Mẫu số 6 TT68): có dòng ngày tháng, họ tên người đại diện, dấu giám đốc cỡ ≤ 3,6 cm (đã làm trên file mẫu của Thông tư)
ky = next(t for t in d.tables if "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT" in t.rows[0].cells[1].text)
c = ky.rows[0].cells[1]
assert re.search(r"ngày \d+ tháng \d+ năm \d{4}", c.paragraphs[0].text), c.paragraphs[0].text      # ngày đã điền (địa danh để dấu chấm nếu chưa nhập)
assert c.paragraphs[-1].text == "TRẦN KHẢ VY"
cy = int(re.search(r'<wp:extent cx="\d+" cy="(\d+)"', c.paragraphs[-1]._p.xml).group(1))
assert 3.0 * 360000 < cy <= 3.6 * 360000 + 100, cy / 360000
assert d.sections[0].page_width > d.sections[0].page_height
print("PASS 3: khối ký trong bảng biểu mẫu Mẫu số 6: ngày, họ tên, dấu giám đốc (≈3,6 cm), trang ngang.")
print("ALL DONE")
