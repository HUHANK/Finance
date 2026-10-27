# -*- coding: utf-8 -*-
"""央视新闻联播数据源：当日条目 + 文字稿。
摘自 .scratch/step3_cctv.py 已验证代码（直连会话绕过系统代理）。
"""
import html as _html
import re
import time

import requests

SESSION = requests.Session()
SESSION.trust_env = False
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

CCTV_DAY_URL = "https://tv.cctv.com/lm/xwlb/day/{ymd}.shtml"


def _http(url, allow_status=()):
    response = SESSION.request("GET", url, headers={"User-Agent": UA},
                               timeout=(10, 40), allow_redirects=True)
    if response.status_code not in allow_status:
        response.raise_for_status()
    return response


def _cctv_body(url):
    text = _http(url).content.decode("utf-8", "replace")
    if len(text) < 1000 and "error.html" in text:
        return None
    match = (re.search(r'<div class="content_area"[^>]*>(.*?)</div>', text, re.S)
             or re.search(r'<div class="cnt_bd"[^>]*>(.*?)</div>', text, re.S))
    if not match:
        return None
    body = re.sub(r"</p>|<br\s*/?>", "\n", match.group(1))
    body = _html.unescape(re.sub(r"<[^>]+>", "", body))
    body = "\n".join(line.strip() for line in body.splitlines() if line.strip())
    return re.sub(r"^央视网消息\s*[（(]新闻联播[)）]\s*[：:]", "", body)


def cctv_news(date, with_content=True):
    """某日新闻联播条目。返回 [{date, title, url, content?}]，未发布返回 None。"""
    ymd = date.replace("-", "")
    url = CCTV_DAY_URL.format(ymd=ymd)
    response = _http(url, allow_status=(404,))
    if response.status_code == 404:
        return None
    text = response.content.decode("utf-8", "replace")
    rows = []
    for chunk in text.split("<li")[1:]:
        link = re.search(r'href="([^"]*/VIDE[^"]+)"', chunk)
        if not link:
            continue
        href = link.group(1)
        title = (re.search(r'title="([^"]+)"', chunk)
                 or re.search(r'class="title">(.*?)</div>', chunk, re.S)
                 or re.search(r"<a[^>]*>(.*?)</a>", chunk, re.S))
        title = _html.unescape(re.sub(r"<[^>]+>", "", title.group(1))).strip() if title else ""
        if not title or re.match(r"《新闻联播》\s*\d{8}|新闻联播完整版", title):
            continue
        title = re.sub(r"^\[视频\]", "", title).strip()
        rows.append({"date": date, "title": title,
                     "url": ("https:" + href) if href.startswith("//") else href})
    if with_content:
        for row in rows:
            row["content"] = _cctv_body(row["url"])
            time.sleep(0.2)
    return rows
