import os, sys, tempfile, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server, goi_claude_cong_no as g
from openpyxl import load_workbook, Workbook
# 1) dữ liệu gốc thuần từ cấu trúc nội bộ của đối chiếu 3 tầng
dt = datetime.datetime(2026, 3, 5)
hd = {"A1": {"ma": "0101", "ten": "CÔNG TY A", "hoa_don": [{"ref_id": "r1", "inv_no": "11", "inv_date": dt, "so_tien": 1000000.0, "matched": False, "phan_dung": set()}]},
      "B1": {"ma": "0202", "ten": "CÔNG TY B", "hoa_don": [{"ref_id": "r2", "inv_no": "22", "inv_date": dt, "so_tien": 500000.0, "matched": True, "phan_dung": {"full"}}]}}
tt = {"A1": [{"ref_id": "t1", "date": dt, "so_tien": 500000.0, "nguon": "ngan_hang", "so_ct": "UNC1", "mo_ta": "CTY B tt hd 22", "matched": False}], "B1": []}
goc = server._misa_goc_cong_no(hd, tt, {"A1": 1000000.0, "B1": 0.0})
assert [x["ma"] for x in goc] == ["0101", "0202"] and goc[0]["so_du_cuoi_ky"] == 1000000 and goc[0]["thanh_toan"][0]["date"] and goc[0]["hoa_don"][0]["inv_date"], goc
res = {"goc": goc, "goi_y_chuyen": [{"tu_ma": "0101", "tu_ten": "CÔNG TY A", "tt_ngay": "2026-03-05", "tt_so_ct": "UNC1", "tt_ref_id": "t1", "so_tien": 500000, "den_ma": "0202", "den_ten": "CÔNG TY B", "inv_no": "22", "hd_so_tien": 500000, "chenh_lech": 0, "mo_ta": "CTY B"}],
       "tang1": [{"ma": "0202", "inv_no": "22", "so_tien": 500000}], "tang2": [], "tam_ung": [], "khong_ro": [], "tang3": [], "thu_2_lan": [], "nghi_sai_doi_tuong": []}
sheets = g.tao_goi({"ten_cty": "CTY TEST", "tu_ngay": "2026-01-01", "den_ngay": "2026-12-31", "hd_dau_ra": [{"so_hd": "11", "ky_hieu": "C26T", "ngay": "2026-03-05", "mst": "0101", "ten": "A", "chua_thue": 900000, "thue": 100000, "tong": 1000000, "trang_thai": "Mới"}],
                    "hd_dau_vao": [], "cong_no": {"kh": res, "ncc": None}})
assert list(sheets) == ["PROMPT", "HUONG_DAN", "HD_DAU_RA", "HD_DAU_VAO", "TONG_HOP_PHAI_THU", "TONG_HOP_PHAI_TRA", "CT_HOA_DON", "CT_THANH_TOAN", "GOI_Y_CHUYEN", "KET_QUA_PHAN_MEM", "KET_QUA"], list(sheets)
p = "\n".join(r[0] for r in sheets["PROMPT"])
for k in ("CHUYEN_CONG_NO", "KET_QUA", "GẮN SAI ĐỐI TƯỢNG", "bảng kê", "LOAI_XU_LY"):
    assert k in p, k
th = sheets["TONG_HOP_PHAI_THU"]
assert th[1][:5] == ["0101", "CÔNG TY A", 1000000, 500000, 1000000] and th[1][6] == 1 and th[1][7] == 1, th
assert sheets["CT_HOA_DON"][1][-1] == "TREO" and sheets["CT_HOA_DON"][2][-1] == "KHOP"
assert sheets["CT_THANH_TOAN"][1][-2] == "CHUA_KHOP" and sheets["GOI_Y_CHUYEN"][1][7] == "0202"
# 2) ghi + đọc lại xlsx
tmp = os.path.join(tempfile.mkdtemp(), "x.xlsx"); g.ghi_xlsx(sheets, tmp)
assert load_workbook(tmp).sheetnames == list(sheets)
# 3) đọc kết quả Claude
wb = Workbook(); ws = wb.active; ws.title = "KET_QUA"
ws.append(g.COT_KET_QUA)
ws.append(["CHUYEN_CONG_NO", "KH", "0101", "CÔNG TY A", "0202", "CÔNG TY B", "05/03/2026", "UNC1", "t1", "22", "500,000", "MO_TA nêu CTY B"])
ws.append(["CHUYEN_CONG_NO", "NCC", "0101", "A", "0101", "A", "2026-03-05", "", "", "", 1000, ""])  # TU=DEN -> lỗi
ws.append(["CHUYEN_CONG_NO", "KH", "0101", "A", "0202", "B", "", "", "", "", 1000, ""])           # thiếu ngày -> lỗi
ws.append(["DE_XUAT_KHAC", "KH", "0303", "C", "", "", "", "", "", "33", "2000000", "HĐ thiếu trong sổ"])
ws.append(["KHOP_THANH_TOAN", "NCC", "0404", "D", "", "", "", "", "", "1;2", 3000, "tổ hợp"])
ws.append(["LINH_TINH", "KH"])
kq = os.path.join(tempfile.mkdtemp(), "kq.xlsx"); wb.save(kq)
d = g.doc_ket_qua(kq)
assert len(d["chuyen"]) == 1 and d["chuyen"][0]["tt_ngay"] == "2026-03-05" and d["chuyen"][0]["so_tien"] == 500000 and d["chuyen"][0]["loai_cn"] == "kh" and d["chuyen"][0]["den_ma"] == "0202", d
assert len(d["khac"]) == 2 and len(d["loi"]) == 3, d["loi"]
# 4) nối dây
sv = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf8").read()
assert '"/api/misa-sql/goi-claude-cong-no/{cid}"' in sv and '"/api/misa-sql/doc-ket-qua-claude-cong-no"' in sv and "tra_goc=True" in sv
ix = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "index.html"), encoding="utf8").read()
assert "misaCnXuatClaude" in ix and "misaCnNhapClaude" in ix and "xuat-chuyen-cong-no" in ix and "Xuất gói công nợ cho Claude" in ix
print("PASS: gói công nợ cho Claude — dữ liệu gốc, 11 sheet + PROMPT, tổng hợp phải thu/phải trả, đọc KET_QUA (chuyển công nợ/đề xuất/lỗi), nối server + giao diện")
