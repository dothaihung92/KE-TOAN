"""
Client gọi Facebook Graph API (đăng bài Fanpage) và Marketing API (quảng cáo).

Chỉ dùng endpoint chính thức của Meta (graph.facebook.com). Không có bất kỳ
hành vi giả lập trình duyệt hay bot tương tác nào ở đây — mọi thao tác đều
đi qua API được Meta cấp phép cho Page Access Token / Ad Account tương ứng.

Tài liệu tham khảo:
    - Graph API (Page):       https://developers.facebook.com/docs/pages-api
    - Marketing API (Ads):    https://developers.facebook.com/docs/marketing-apis
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests

GRAPH_API_URL = os.environ.get("FB_GRAPH_API_URL", "https://graph.facebook.com")
GRAPH_API_VERSION = os.environ.get("FB_GRAPH_API_VERSION", "v19.0")


class FacebookApiError(RuntimeError):
    """Lỗi khi gọi Graph API / Marketing API của Facebook."""


class FacebookClient:
    """Bọc các endpoint cần thiết để đăng bài Fanpage và chạy quảng cáo."""

    def __init__(self, access_token: str, timeout: int = 30):
        if not access_token:
            raise FacebookApiError("Thiếu access token")
        self.access_token = access_token
        self.timeout = timeout
        self.base_url = f"{GRAPH_API_URL}/{GRAPH_API_VERSION}"

    # ------------------------------------------------------------------ #
    # Nội bộ
    # ------------------------------------------------------------------ #
    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        params = kwargs.pop("params", {}) or {}
        params.setdefault("access_token", self.access_token)
        try:
            resp = requests.request(
                method, f"{self.base_url}/{path}",
                params=params, timeout=self.timeout, **kwargs,
            )
        except requests.RequestException as exc:
            raise FacebookApiError(f"Lỗi kết nối tới Facebook: {exc}") from exc

        try:
            data = resp.json()
        except ValueError:
            raise FacebookApiError(f"Facebook trả về dữ liệu không hợp lệ (HTTP {resp.status_code})")

        if "error" in data:
            err = data["error"]
            msg = err.get("message", "Lỗi không rõ")
            code = err.get("code")
            raise FacebookApiError(f"Facebook API lỗi [{code}]: {msg}")
        return data

    # ------------------------------------------------------------------ #
    # Fanpage: thông tin & đăng bài
    # ------------------------------------------------------------------ #
    def get_page_info(self, page_id: str) -> Dict[str, Any]:
        return self._request(
            "GET", page_id,
            params={"fields": "id,name,fan_count,link,category"},
        )

    def publish_post(
        self,
        page_id: str,
        message: str,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
        scheduled_publish_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Đăng bài lên Fanpage. Nếu có scheduled_publish_time (unix time,
        cách hiện tại >=10 phút), Facebook sẽ tự đăng vào thời điểm đó."""
        if image_url:
            path = f"{page_id}/photos"
            params: Dict[str, Any] = {"url": image_url, "caption": message}
        else:
            path = f"{page_id}/feed"
            params = {"message": message}
            if link:
                params["link"] = link

        if scheduled_publish_time:
            params["published"] = "false"
            params["scheduled_publish_time"] = scheduled_publish_time

        return self._request("POST", path, params=params)

    def delete_post(self, post_id: str) -> Dict[str, Any]:
        return self._request("DELETE", post_id)

    def get_page_insights(self, page_id: str, metric: str = "page_fans,page_impressions",
                          period: str = "day") -> Dict[str, Any]:
        return self._request(
            "GET", f"{page_id}/insights",
            params={"metric": metric, "period": period},
        )

    def list_recent_posts(self, page_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        data = self._request(
            "GET", f"{page_id}/posts",
            params={"fields": "id,message,created_time,permalink_url", "limit": limit},
        )
        return data.get("data", [])

    # ------------------------------------------------------------------ #
    # Marketing API: chiến dịch quảng cáo sản phẩm
    # ------------------------------------------------------------------ #
    def create_campaign(
        self,
        ad_account_id: str,
        name: str,
        objective: str = "OUTCOME_TRAFFIC",
        status: str = "PAUSED",
        daily_budget_cents: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Tạo chiến dịch. status mặc định PAUSED để người dùng tự bấm chạy
        sau khi kiểm tra — tránh AI tự ý tiêu tiền quảng cáo ngoài ý muốn."""
        params: Dict[str, Any] = {
            "name": name,
            "objective": objective,
            "status": status,
            "special_ad_categories": "[]",
        }
        if daily_budget_cents:
            params["daily_budget"] = daily_budget_cents
        return self._request("POST", f"act_{ad_account_id}/campaigns", params=params)

    def create_ad_set(
        self,
        ad_account_id: str,
        campaign_id: str,
        name: str,
        daily_budget_cents: int,
        targeting: Dict[str, Any],
        optimization_goal: str = "LINK_CLICKS",
        billing_event: str = "IMPRESSIONS",
        status: str = "PAUSED",
    ) -> Dict[str, Any]:
        import json as _json
        params = {
            "name": name,
            "campaign_id": campaign_id,
            "daily_budget": daily_budget_cents,
            "billing_event": billing_event,
            "optimization_goal": optimization_goal,
            "targeting": _json.dumps(targeting),
            "status": status,
        }
        return self._request("POST", f"act_{ad_account_id}/adsets", params=params)

    def create_ad_creative(
        self,
        ad_account_id: str,
        page_id: str,
        name: str,
        message: str,
        link: str,
        image_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        import json as _json
        link_data: Dict[str, Any] = {"message": message, "link": link}
        if image_hash:
            link_data["image_hash"] = image_hash
        object_story_spec = {"page_id": page_id, "link_data": link_data}
        params = {
            "name": name,
            "object_story_spec": _json.dumps(object_story_spec),
        }
        return self._request("POST", f"act_{ad_account_id}/adcreatives", params=params)

    def create_ad(
        self,
        ad_account_id: str,
        name: str,
        ad_set_id: str,
        creative_id: str,
        status: str = "PAUSED",
    ) -> Dict[str, Any]:
        params = {
            "name": name,
            "adset_id": ad_set_id,
            "creative": {"creative_id": creative_id},
            "status": status,
        }
        import json as _json
        params["creative"] = _json.dumps({"creative_id": creative_id})
        return self._request("POST", f"act_{ad_account_id}/ads", params=params)

    def get_campaign_insights(self, campaign_id: str,
                              fields: str = "impressions,clicks,spend,ctr") -> Dict[str, Any]:
        return self._request("GET", f"{campaign_id}/insights", params={"fields": fields})

    def set_campaign_status(self, campaign_id: str, status: str) -> Dict[str, Any]:
        """status: ACTIVE | PAUSED | ARCHIVED | DELETED"""
        return self._request("POST", campaign_id, params={"status": status})
