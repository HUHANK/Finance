# -*- coding: utf-8 -*-
"""中证/上证指数官方数据源：估值历史(PEx/股息率) + 成份权重 xls。
摘自 .scratch/step2_val.py 已验证代码。xls 为全量历史，一次拉全入库即可。
"""
import re
from io import BytesIO

import pandas as pd
import requests

SESSION = requests.Session()
SESSION.trust_env = False
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

_BASE = ("https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/"
         "autofile/%s/%s%s.xls")

_SITE = "https://www.csindex.com.cn/csindex-home/"


def _official_code(index_code):
    code = str(index_code).strip()
    return code[2:] if code.lower().startswith(("sh", "sz")) else code


def _site_get(path, params=None):
    r = SESSION.get(_SITE + path, params=params,
                    headers={"User-Agent": UA, "Referer": "https://www.csindex.com.cn/"},
                    timeout=(10, 40))
    r.raise_for_status()
    payload = r.json()
    if payload.get("code") != "200":
        raise RuntimeError("csindex API %s: %s" % (path, payload.get("msg")))
    return payload


def index_pe_history(index_code, start=None, end=None):
    """官网日频 PE 长序列（indexCsiDsPe，多数指数可回溯至 2011，口径以官网为准）。
    返回按日期升序 [{date, pe}]。"""
    code = _official_code(index_code)
    params = {"indexCode": code}
    if start:
        params["startDate"] = str(start).replace("-", "")
    if end:
        params["endDate"] = str(end).replace("-", "")
    rows = _site_get("perf/indexCsiDsPe", params).get("data") or []
    out = []
    for rec in rows:
        d = str(rec.get("tradeDate") or "")
        if len(d) != 8:
            continue
        out.append({"date": "%s-%s-%s" % (d[:4], d[4:6], d[6:]),
                    "pe": rec.get("peg")})
    return sorted(out, key=lambda r: r["date"])


def _official_get(url):
    r = SESSION.get(url, headers={"User-Agent": UA, "Referer": url}, timeout=(10, 40))
    r.raise_for_status()
    return r


def _official_excel(response):
    frame = pd.read_excel(BytesIO(response.content), dtype=str)
    frame.columns = [re.sub(r"\s+", "", str(c)) for c in frame.columns]
    return frame


def index_valuation(index_code):
    """估值全量历史。返回按日期升序 [{date, pe_total, pe_calc, dy_total, dy_calc}]。"""
    url = _BASE % ("indicator", index_code, "indicator")
    data = _official_excel(_official_get(url))
    mapping = {"市盈率1（总股本）P/E1": "pe_total",
               "市盈率2（计算用股本）P/E2": "pe_calc",
               "股息率1（总股本）D/P1": "dy_total",
               "股息率2（计算用股本）D/P2": "dy_calc"}
    missing = [c for c in mapping if c not in data.columns]
    if missing:
        raise RuntimeError("估值列缺失: %s" % ",".join(missing))
    rows = []
    for rec in data.to_dict("records"):
        row = {"date": str(rec["日期Date"]).strip()}
        for src, dest in mapping.items():
            v = rec.get(src)
            row[dest] = (float(str(v).replace(",", ""))
                         if v and str(v).strip() not in ("", "-", "--") else None)
        rows.append(row)
    return sorted(rows, key=lambda r: r["date"])


def index_weights(index_code):
    """成份权重快照（官方月度文件，取文件里最新一期）。返回 [{date, code, name, weight}]。"""
    url = _BASE % ("closeweight", index_code, "closeweight")
    data = _official_excel(_official_get(url))
    cols = ["日期Date", "指数代码IndexCode", "成份券代码ConstituentCode",
            "成份券名称ConstituentName", "权重(%)weight"]
    missing = [c for c in cols if c not in data.columns]
    if missing:
        raise RuntimeError("权重列缺失: %s" % ",".join(missing))
    rows = []
    for rec in data.to_dict("records"):
        rows.append({"date": str(rec["日期Date"]).strip(),
                     "code": str(rec["成份券代码ConstituentCode"]).zfill(6),
                     "name": rec["成份券名称ConstituentName"],
                     "weight": float(str(rec["权重(%)weight"]).replace(",", ""))})
    return rows
