import os
import pytest


def _has_fb_env():
    required = ["FB_APP_ID", "FB_APP_SECRET", "FB_ACCESS_TOKEN", "FB_AD_ACCOUNT_ID"]
    return all(os.getenv(v) for v in required)


@pytest.mark.e2e
@pytest.mark.skipif(not _has_fb_env(), reason="Missing FB_* env vars for live E2E")
def test_facebook_api_direct_requests():
    import requests
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    ad_account_id = os.getenv("FB_AD_ACCOUNT_ID")
    if not ad_account_id.startswith("act_"):
        ad_account_id = f"act_{ad_account_id}"

    url = f"https://graph.facebook.com/v19.0/{ad_account_id}"
    params = {
        "access_token": os.getenv("FB_ACCESS_TOKEN"),
        "fields": "id,name,account_status",
    }

    resp = requests.get(url, params=params, verify=False, timeout=30)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "id" in data and "name" in data
