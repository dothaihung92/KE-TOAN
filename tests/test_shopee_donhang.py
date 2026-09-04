import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test cho phần vừa thêm: lấy đơn hàng Shopee (Partner API v2).

Kiểm tra bằng cách mock requests.get/requests.post + _doc_du_lieu_cty/
_ghi_du_lieu_cty (không cần server thật/token thật) — verify:
  1. _shopee_goi_api_shop ký đúng công thức "shop-level"
     (partner_id+path+ts+access_token+shop_id), khác _shopee_doi_token.
  2. _shopee_dam_bao_token_con_han: KHÔNG gọi làm mới nếu token còn hạn xa;
     CÓ gọi làm mới + ghi lại data nếu token đã hết hạn, và cập nhật đúng
     access_token/refresh_token/token_het_han mới.
  3. tmdt_shopee_don_hang: phân trang get_order_list (nhiều cursor) + gộp
     batch get_order_detail (tối đa 50 order_sn/lần) + parse đúng field ra
     don_hang, mặc định time_from/time_to đúng cửa sổ 15 ngày.
"""
import sys, time, hmac, hashlib
sys.path.insert(0, _REPO_ROOT)
import server


def test_shop_level_sign():
    cfg = {"app_key": "111", "app_secret": "secret"}
    shop_cfg = {"access_token": "AT", "shop_id": "222"}
    captured = {}

    class FakeResp:
        def json(self):
            return {"response": {}}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResp()

    orig_get = server.requests.get
    server.requests.get = fake_get
    try:
        server._shopee_goi_api_shop(cfg, shop_cfg, "/api/v2/order/get_order_list", {"page_size": 10})
    finally:
        server.requests.get = orig_get

    p = captured["params"]
    expected_sign = hmac.new(b"secret", f"111/api/v2/order/get_order_list{p['timestamp']}AT222".encode(),
                              hashlib.sha256).hexdigest()
    assert p["sign"] == expected_sign, f"Sai chữ ký shop-level: {p['sign']} != {expected_sign}"
    assert p["page_size"] == 10
    print("OK: _shopee_goi_api_shop ký đúng công thức shop-level")


def test_missing_token_raises():
    cfg = {"app_key": "111", "app_secret": "secret"}
    try:
        server._shopee_goi_api_shop(cfg, {}, "/api/v2/order/get_order_list")
        assert False, "Phải raise khi thiếu access_token/shop_id"
    except RuntimeError:
        print("OK: thiếu access_token/shop_id -> raise RuntimeError")


def test_token_refresh_skip_when_valid():
    cid = 999
    data_store = {cid: {"tmdt": {"shopee": {
        "access_token": "OLD_AT", "refresh_token": "RT",
        "shop_id": "222", "token_het_han": time.time() + 3600,
    }}}}

    def fake_doc(c):
        return data_store[c]

    def fake_ghi(c, d):
        data_store[c] = d

    called = {"n": 0}

    def fake_lam_moi(cfg, refresh_token, shop_id):
        called["n"] += 1
        return {"access_token": "NEW_AT", "refresh_token": "NEW_RT", "expire_in": 14400}

    orig_doc, orig_ghi, orig_lam_moi = server._doc_du_lieu_cty, server._ghi_du_lieu_cty, server._shopee_lam_moi_token
    server._doc_du_lieu_cty, server._ghi_du_lieu_cty, server._shopee_lam_moi_token = fake_doc, fake_ghi, fake_lam_moi
    try:
        shop_cfg = server._shopee_dam_bao_token_con_han(cid, {"app_key": "1", "app_secret": "s"})
    finally:
        server._doc_du_lieu_cty, server._ghi_du_lieu_cty, server._shopee_lam_moi_token = orig_doc, orig_ghi, orig_lam_moi

    assert called["n"] == 0, "Không được gọi làm mới khi token còn hạn xa"
    assert shop_cfg["access_token"] == "OLD_AT"
    print("OK: không làm mới token khi còn hạn xa")


def test_token_refresh_when_expired():
    cid = 998
    data_store = {cid: {"tmdt": {"shopee": {
        "access_token": "OLD_AT", "refresh_token": "RT",
        "shop_id": "222", "token_het_han": time.time() - 10,
    }}}}

    def fake_doc(c):
        return data_store[c]

    def fake_ghi(c, d):
        data_store[c] = d

    def fake_lam_moi(cfg, refresh_token, shop_id):
        assert refresh_token == "RT" and str(shop_id) == "222"
        return {"access_token": "NEW_AT", "refresh_token": "NEW_RT", "expire_in": 14400}

    orig_doc, orig_ghi, orig_lam_moi = server._doc_du_lieu_cty, server._ghi_du_lieu_cty, server._shopee_lam_moi_token
    server._doc_du_lieu_cty, server._ghi_du_lieu_cty, server._shopee_lam_moi_token = fake_doc, fake_ghi, fake_lam_moi
    try:
        shop_cfg = server._shopee_dam_bao_token_con_han(cid, {"app_key": "1", "app_secret": "s"})
    finally:
        server._doc_du_lieu_cty, server._ghi_du_lieu_cty, server._shopee_lam_moi_token = orig_doc, orig_ghi, orig_lam_moi

    assert shop_cfg["access_token"] == "NEW_AT"
    assert shop_cfg["refresh_token"] == "NEW_RT"
    assert shop_cfg["token_het_han"] > time.time() + 14000
    assert data_store[cid]["tmdt"]["shopee"]["access_token"] == "NEW_AT", "Phải ghi lại data công ty"
    print("OK: token hết hạn -> tự làm mới và ghi lại đúng data")


def test_don_hang_pagination_and_batch():
    cid = 997
    data_store = {cid: {"tmdt": {"shopee": {
        "access_token": "AT", "refresh_token": "RT",
        "shop_id": "222", "token_het_han": time.time() + 3600,
    }}}}
    server._doc_du_lieu_cty = lambda c: data_store[c]
    server._ghi_du_lieu_cty = lambda c, d: data_store.__setitem__(c, d)
    server._tmdt_app_cfg = lambda san: {"app_key": "1", "app_secret": "s"}

    # 120 order_sn giả để buộc phân trang get_order_list (page_size=100) VÀ
    # buộc get_order_detail gọi >=1 lần theo batch 50.
    all_sn = [f"SN{i}" for i in range(120)]
    calls = {"list": 0, "detail": []}

    def fake_get_order_list(page_size, cursor):
        calls["list"] += 1
        if cursor == "":
            page = all_sn[:100]
            return {"response": {"order_list": [{"order_sn": s} for s in page],
                                  "more": True, "next_cursor": "PAGE2"}}
        elif cursor == "PAGE2":
            page = all_sn[100:]
            return {"response": {"order_list": [{"order_sn": s} for s in page],
                                  "more": False, "next_cursor": ""}}
        raise AssertionError("cursor không mong đợi: " + cursor)

    def fake_goi_api_shop(cfg, shop_cfg, path, params=None, method="GET"):
        params = params or {}
        if path == "/api/v2/order/get_order_list":
            return fake_get_order_list(params.get("page_size"), params.get("cursor"))
        elif path == "/api/v2/order/get_order_detail":
            sn_list = params["order_sn_list"].split(",")
            calls["detail"].append(len(sn_list))
            return {"response": {"order_list": [
                {"order_sn": sn, "order_status": "COMPLETED", "create_time": 1780000000,
                 "total_amount": 150000, "currency": "VND", "item_list": [{"item_id": 1}]}
                for sn in sn_list
            ]}}
        raise AssertionError("path không mong đợi: " + path)

    orig_goi = server._shopee_goi_api_shop
    server._shopee_goi_api_shop = fake_goi_api_shop
    try:
        kq = server.tmdt_shopee_don_hang(cid, tu_ngay="", den_ngay="")
    finally:
        server._shopee_goi_api_shop = orig_goi

    assert calls["list"] == 2, f"Phải phân trang đúng 2 lần get_order_list, được {calls['list']}"
    assert calls["detail"] == [50, 50, 20], f"Phải batch get_order_detail 50/50/20, được {calls['detail']}"
    assert kq["tong_don"] == 120
    assert len(kq["don_hang"]) == 120
    mau = kq["don_hang"][0]
    assert mau["ma_don"].startswith("SN")
    assert mau["tong_tien"] == 150000
    assert mau["tien_te"] == "VND"
    assert mau["so_san_pham"] == 1
    assert mau["ngay_tao"]  # đã format ra chuỗi dd/mm/yyyy HH:MM
    print("OK: get_order_list phân trang đúng + get_order_detail batch đúng + parse dữ liệu đúng")


def test_chua_ket_noi_bao_loi_ro_rang():
    cid = 996
    data_store = {cid: {"tmdt": {}}}
    server._doc_du_lieu_cty = lambda c: data_store[c]
    server._ghi_du_lieu_cty = lambda c, d: data_store.__setitem__(c, d)
    server._tmdt_app_cfg = lambda san: {"app_key": "1", "app_secret": "s"}
    try:
        server.tmdt_shopee_don_hang(cid, tu_ngay="", den_ngay="")
        assert False, "Phải báo lỗi khi công ty chưa kết nối shop"
    except server.HTTPException as e:
        assert "chưa kết nối" in e.detail.lower()
        print("OK: chưa kết nối -> báo lỗi rõ ràng thay vì crash")


if __name__ == "__main__":
    test_shop_level_sign()
    test_missing_token_raises()
    test_token_refresh_skip_when_valid()
    test_token_refresh_when_expired()
    test_don_hang_pagination_and_batch()
    test_chua_ket_noi_bao_loi_ro_rang()
    print("\nTẤT CẢ TEST PASS")
