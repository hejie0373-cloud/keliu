"""微信服务器签名验证。"""
import hashlib
from app.core.config import settings


def verify_wechat_signature(signature: str, timestamp: str, nonce: str) -> bool:
    """验证微信服务器签名。"""
    token = settings.WECHAT_TOKEN or "keliu2025"
    tmp_list = sorted([token, timestamp, nonce])
    tmp_str = "".join(tmp_list)
    expected = hashlib.sha1(tmp_str.encode()).hexdigest()
    return signature == expected
