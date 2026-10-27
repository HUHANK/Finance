# -*- coding: utf-8 -*-
"""同花顺数据源：个股一致预期（机构 EPS 预测均值）。
摘自 .scratch/step2_val.py 已验证代码（正则解析，不依赖 lxml）。
"""
import re

import requests

SESSION = requests.Session()
SESSION.trust_env = False
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S | re.I)
ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S | re.I)


def _clean(cell):
    return re.sub(r"<[^>]+>", "", cell).replace("&nbsp;", " ").strip()


def eps_forecast(code):
    """返回 [{year, eps, orgs}]（年份升序）或 None（无预期数据/解析失败）。"""
    from .tencent import norm_ticker
    code = norm_ticker(code)
    url = "https://basic.10jqka.com.cn/new/%s/worth.html" % code
    r = SESSION.get(url, headers={"User-Agent": UA,
                                  "Referer": "https://basic.10jqka.com.cn/"}, timeout=15)
    r.encoding = "gbk"
    target = None
    for m in TABLE_RE.finditer(r.text):
        before = r.text[max(0, m.start() - 300):m.start()]
        rows = []
        for rm in ROW_RE.findall(m.group(1)):
            cells = [_clean(c) for c in CELL_RE.findall(rm)]
            if cells:
                rows.append(cells)
        if not rows:
            continue
        header = rows[0]
        if "均值" in "".join(header) and "每股收益" in before:
            target = rows
            break
    if target is None:  # 兜底：任何含"均值"的表
        for m in TABLE_RE.finditer(r.text):
            rows = []
            for rm in ROW_RE.findall(m.group(1)):
                cells = [_clean(c) for c in CELL_RE.findall(rm)]
                if cells:
                    rows.append(cells)
            if rows and "均值" in "".join(rows[0]):
                target = rows
                break
    if target is None:
        return None
    header = target[0]
    try:
        mean_i = next(i for i, c in enumerate(header) if "均值" in c)
        org_i = next((i for i, c in enumerate(header) if "机构" in c), None)
    except StopIteration:
        return None
    out = []
    for row in target[1:]:
        if len(row) <= mean_i:
            continue
        year_m = re.search(r"(20\d{2})", row[0])
        if not year_m:
            continue
        try:
            mean_v = float(row[mean_i])
        except ValueError:
            continue
        orgs = None
        if org_i is not None and len(row) > org_i:
            om = re.search(r"\d+", row[org_i])
            orgs = int(om.group()) if om else None
        out.append({"year": int(year_m.group(1)), "eps": mean_v, "orgs": orgs})
    return sorted(out, key=lambda x: x["year"]) or None
