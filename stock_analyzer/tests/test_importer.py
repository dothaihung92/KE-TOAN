import io

import pytest

from stock_analyzer.portfolio.importer import PortfolioImportError, parse_portfolio_file


def test_parse_simple_csv():
    content = "Mã CK,Số lượng,Giá vốn TB\nVCB,100,85000\nFPT,50,120000\n".encode("utf-8-sig")
    rows = parse_portfolio_file(content, "danh_muc.csv")
    assert len(rows) == 2
    assert rows[0].symbol == "VCB"
    assert rows[0].quantity == 100
    assert rows[0].avg_cost == 85000


def test_parse_csv_unaccented_headers():
    content = "Ma CK,So luong,Gia von\nHPG,200,25000\n".encode("utf-8")
    rows = parse_portfolio_file(content, "sao_ke.csv")
    assert rows[0].symbol == "HPG"
    assert rows[0].quantity == 200


def test_header_not_on_first_row():
    content = (
        "Sao kê danh mục,,\n"
        "Ngày xuất: 01/01/2026,,\n"
        "Mã CK,Số lượng,Giá vốn TB\n"
        "MWG,30,55000\n"
    ).encode("utf-8-sig")
    rows = parse_portfolio_file(content, "sao_ke.csv")
    assert len(rows) == 1
    assert rows[0].symbol == "MWG"


def test_missing_required_columns_raises():
    content = "Tên,Giá trị\nA,1\n".encode("utf-8")
    with pytest.raises(PortfolioImportError):
        parse_portfolio_file(content, "invalid.csv")


def test_empty_file_raises():
    with pytest.raises(PortfolioImportError):
        parse_portfolio_file(b"", "empty.csv")


def test_skips_rows_without_quantity():
    content = "Mã CK,Số lượng,Giá vốn TB\nVCB,100,85000\nFPT,,120000\n".encode("utf-8-sig")
    rows = parse_portfolio_file(content, "danh_muc.csv")
    assert len(rows) == 1
    assert rows[0].symbol == "VCB"
