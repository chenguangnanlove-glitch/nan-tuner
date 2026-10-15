#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络访问助手 —— 让所有脚本可靠地访问 HTTPS。

背景：这台 Mac 上 python.org 装的 Python 3.14，默认证书路径是空的
（ssl.get_default_verify_paths() 返回 None），直接联网会报
CERTIFICATE_VERIFY_FAILED。但 certifi 装了且可用。

所以统一从这里拿 SSL context，不要各自造轮子。
"""

import json
import ssl
import urllib.error
import urllib.request

__all__ = ["ssl_context", "get", "get_json", "head"]

_CTX = None


def ssl_context():
    """返回一个能验证证书的 SSL context。"""
    global _CTX
    if _CTX is not None:
        return _CTX

    try:
        import certifi
        _CTX = ssl.create_default_context(cafile=certifi.where())
        return _CTX
    except ImportError:
        pass

    # 退路：系统默认
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats().get("x509_ca", 0) > 0:
        _CTX = ctx
        return _CTX

    raise RuntimeError(
        "没有可用的根证书。请运行：pip3 install certifi"
    )


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ShiXinTuner/1.0"


def get(url, timeout=20, headers=None):
    """GET 一个 URL，返回 (status, headers, body_bytes)。"""
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as r:
        return r.status, dict(r.headers), r.read()


def get_json(url, timeout=20, headers=None):
    """GET 一个 JSON 接口，返回解析后的对象。"""
    _, _, body = get(url, timeout, headers)
    return json.loads(body.decode("utf-8"))


def head(url, timeout=20):
    """只取响应头。"""
    h = {"User-Agent": UA}
    req = urllib.request.Request(url, headers=h, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as r:
            return r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)
