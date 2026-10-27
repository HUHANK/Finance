# -*- coding: utf-8 -*-
"""东财数据源：涨停/炸板/跌停池 + 行业/概念主力资金流。
铁律：所有 eastmoney.com 请求一律走 em_get() —— 串行限流（1.2s + 抖动）+
会话复用 + 429/5xx 退避重试（403 是风控信号，不重试）。
摘自 .scratch/step4_etf_screen.py 已验证代码。
"""
import random
import time

import requests

EM_SESSION = requests.Session()
EM_SESSION.trust_env = False
EM_SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
EM_MIN_INTERVAL = 1.2
_em_last = [0.0]


def em_get(url, params=None, headers=None, timeout=15, retries=2):
    wait = EM_MIN_INTERVAL - (time.time() - _em_last[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.4))
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = EM_SESSION.get(url, params=params, headers=headers, timeout=timeout)
            _em_last[0] = time.time()
            if resp.status_code == 403:
                resp.raise_for_status()
            if resp.status_code == 429 or resp.status_code >= 500:
                resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exc = e
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 403 or attempt >= retries:
                raise
            time.sleep(2 ** (attempt + 1) + random.uniform(0, 1))
    raise last_exc


# ---------- 涨停情绪（打板池） ----------
ZTB_UT = "7eea3edcaed734bea9cbfc24409ed989"


def _em_zt_api(endpoint, sort, date):
    url = "https://push2ex.eastmoney.com/%s" % endpoint
    params = {"ut": ZTB_UT, "dpt": "wz.ztzt", "Pageindex": 0,
              "pagesize": 10000, "sort": sort, "date": date}
    r = em_get(url, params=params,
               headers={"Referer": "https://quote.eastmoney.com/"}, timeout=10)
    return (r.json().get("data") or {}).get("pool") or []


def _hhmm(v):
    s = str(v or "")
    return "%s:%s" % (s[:2], s[2:4]) if len(s) >= 4 else ""


def limit_up_sentiment(date_ymd):
    """date_ymd: YYYYMMDD。返回涨停情绪聚合 + 连板股列表。"""
    zt = _em_zt_api("getTopicZTPool", "fbt:asc", date_ymd)
    zb = _em_zt_api("getTopicZBPool", "fbt:asc", date_ymd)
    dt = _em_zt_api("getTopicDTPool", "fbt:asc", date_ymd)
    ladder = {}
    for s in zt:
        lbc = s.get("lbc", 0)
        ladder[lbc] = ladder.get(lbc, 0) + 1
    zt_n, zb_n = len(zt), len(zb)
    top = sorted(zt, key=lambda s: s.get("lbc") or 0, reverse=True)[:20]
    return {
        "date": date_ymd,
        "zt": zt_n, "zb": zb_n, "dt": len(dt),
        "break_rate": round(zb_n / (zt_n + zb_n) * 100, 1) if (zt_n + zb_n) else 0,
        "max_height": max((s.get("lbc", 0) for s in zt), default=0),
        "ladder": {str(k): v for k, v in sorted(ladder.items())},
        "zt_industry": _top_industries(zt),
        "zt_stocks": [{"code": s.get("c"), "name": s.get("n"), "lbc": s.get("lbc", 0),
                       "hybk": s.get("hybk", ""), "first_time": _hhmm(s.get("fbt"))}
                      for s in top],
    }


def _top_industries(zt_pool, n=8):
    counts = {}
    for s in zt_pool:
        hy = s.get("hybk", "")
        if hy:
            counts[hy] = counts.get(hy, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1])[:n])


# ---------- 板块资金流 ----------
_BOARD_FS = {"industry": "m:90+t:2", "concept": "m:90+t:3"}
_BOARD_PERIOD = {"today": ("f62", "f62", "f184", "f3", "f204"),
                 "5d": ("f164", "f164", "f165", "f109", "f257")}


def board_fund_flow(board_type, period, top_n=30):
    """行业/概念主力资金流（净额降序）。返回完整列表，前端再切片。"""
    fid, f_main, f_pct, f_chg, f_leader = _BOARD_PERIOD[period]
    fields = ["f12", "f14", f_chg, f_main, f_pct]
    if f_leader:
        fields.append(f_leader)
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    base = {"pz": "200", "po": "1", "np": "1", "fltt": "2", "invt": "2",
            "fid": fid, "fs": _BOARD_FS[board_type],
            "fields": ",".join(dict.fromkeys(fields)), "pn": "1"}
    r = em_get(url, params=base, timeout=15)
    d = r.json().get("data") or {}
    items = d.get("diff") or []
    items = sorted(items, key=lambda x: x.get(f_main) or 0, reverse=True)
    out = []
    for it in items[:top_n]:
        out.append({"code": it.get("f12"), "name": it.get("f14", ""),
                    "pct": it.get(f_chg),
                    "main_net_yi": round((it.get(f_main) or 0) / 1e8, 1),
                    "main_pct": it.get(f_pct)})
    return out
