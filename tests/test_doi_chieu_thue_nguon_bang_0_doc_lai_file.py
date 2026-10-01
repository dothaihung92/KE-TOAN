import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf-8").read()

# Ca thật HĐ chiết khấu 6036 (Satori): API danh sách trả tgtthue=0, tổng thanh toán = chưa thuế, nhưng chi tiết/MISA có VAT -1.067.237 ->
# Đối chiếu báo LỆCH +1.067.237 dù MISA đúng. Khi tgtthue=0 mà tgtcthue != 0, đọc lại TgTThue từ chi tiết đã lưu / file XML gốc.
def nested(name):
    idx = src.index("def " + name + "(")
    ls = src.rfind("\n", 0, idx) + 1
    ind = idx - ls
    i = src.index(":", idx)
    body, st = [], False
    for ln in src[i + 1:].split("\n"):
        if ln.strip() == "":
            body.append(ln); continue
        if len(ln) - len(ln.lstrip(" ")) <= ind and st:
            break
        st = True
        body.append(ln)
    return src[idx:i + 1] + "\n".join(body)

xml = "<HDon><DLHDon><NDHDon><TToan><TgTCThue>-13340460</TgTCThue><TgTThue>-1067237</TgTThue></TToan></NDHDon></DLHDon></HDon>"
f = tempfile.mktemp(suffix=".xml")
open(f, "w", encoding="utf-8").write(xml)
ns = {"_json": json, "_to_num": server._to_num, "_extract_invoice_xml": server._extract_invoice_xml, "_tim_file_hoa_don": lambda r: f}
exec(nested("_thue_tu_chi_tiet_hd"), ns)
fn = ns["_thue_tu_chi_tiet_hd"]
assert fn({"detail_json": None}) == -1067237
assert fn({"detail_json": json.dumps({"tgtthue": -5})}) == -5, "ưu tiên chi tiết đã lưu"
ns["_tim_file_hoa_don"] = lambda r: None
assert fn({"detail_json": None}) is None, "không đọc được -> None (giữ nguyên số của API)"
assert "thue_file = _thue_tu_chi_tiet_hd(r)" in src and "if not thue_r and _snum(r[\"tgtcthue\"])" in src
print("PASS: tgtthue=0 mà có tiền chưa thuế -> đọc lại TgTThue từ chi tiết/file XML gốc (HĐ 6036 -> -1.067.237).")
print("\nALL DONE")
