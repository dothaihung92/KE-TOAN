"""Kiểm thử cơ bản không cần mạng cho hddt.client / exporter."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hddt.client import HoaDonDienTuClient, HddtError  # noqa: E402
from hddt import exporter  # noqa: E402


def test_format_date():
    assert HoaDonDienTuClient._format_date("01/02/2024") == "01/02/2024"
    assert HoaDonDienTuClient._format_date("2024-02-01") == "01/02/2024"


def test_format_date_invalid():
    try:
        HoaDonDienTuClient._format_date("ngay-khong-hop-le")
    except HddtError:
        pass
    else:
        raise AssertionError("Phải raise HddtError với ngày không hợp lệ")


def test_build_search():
    c = HoaDonDienTuClient()
    s = c._build_search("01/01/2024", "31/03/2024", ttxly=5)
    assert "tdlap=ge=01/01/2024T00:00:00" in s
    assert "tdlap=le=31/03/2024T23:59:59" in s
    assert "ttxly==5" in s


def test_auth_headers_requires_token():
    c = HoaDonDienTuClient()
    try:
        c._auth_headers()
    except HddtError:
        pass
    else:
        raise AssertionError("Phải báo lỗi khi chưa có token")
    c.token = "abc"
    assert c._auth_headers()["Authorization"] == "Bearer abc"


def test_export_csv_and_json():
    rows = [
        {"nbmst": "0312345678", "shdon": "1", "tgtttbso": 1000, "extra": "x"},
        {"nbmst": "0312345678", "shdon": "2", "tgtttbso": 2000},
    ]
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "out.csv")
        json_path = os.path.join(d, "out.json")
        exporter.to_csv(rows, csv_path)
        exporter.to_json(rows, json_path)
        assert os.path.getsize(csv_path) > 0
        assert os.path.getsize(json_path) > 0


def test_export_excel():
    rows = [{"nbmst": "0312345678", "shdon": "1", "tgtttbso": 1000}]
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "out.xlsx")
        exporter.to_excel({"Mua vao": rows, "Ban ra": []}, path)
        assert os.path.getsize(path) > 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("Tất cả test đã chạy.")
