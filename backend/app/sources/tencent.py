# -*- coding: utf-8 -*-
"""腾讯财经数据源：批量实时行情 + 日/周/月K线（前后复权）+ 当日分时。
摘自 .scratch/step2_val.py、step4_etf_screen.py 已验证代码。
"""
import re

import requests

SESSION = requests.Session()
SESSION.trust_env = False  # 铁律：绕过系统代理（Clash），国内源直连
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# 沪市指数白名单：与深市 000xxx 同段，需区分
SH_INDEX = {"000300", "000905", "000016", "000688", "000852", "000010", "000180"}


def get_prefix(code):
    c = str(code).lower().strip()
    if c.endswith((".sh", ".sz", ".bj")):
        return c[-2:]
    if c.startswith(("sh", "sz", "bj")):
        return c[:2]
    if c.startswith("92"):
        return "bj"
    if c.startswith(("5", "6", "9")):
        return "sh"
    if c.startswith(("4", "8")):
        return "bj"
    if c in SH_INDEX:
        return "sh"
    return "sz"


def norm_ticker(code):
    """提取 6 位代码。锚定匹配，避免从任意串里"捞"出错误代码。"""
    c = str(code).strip().lower()
    m = re.match(r"^(?:(sh|sz|bj))?(\d{6})(?:\.(sh|sz|bj|xshg|xshe))?$", c)
    if not m:
        raise ValueError("bad ticker %s" % code)
    return m.group(2)


def with_market(code):
    """转成腾讯带市场前缀的写法：sh000001 / sz159994。"""
    c = str(code).strip().lower()
    m = re.match(r"^(?:(sh|sz|bj))?(\d{6})(?:\.(sh|sz|bj|xshg|xshe))?$", c)
    if not m:
        raise ValueError("bad ticker %s" % code)
    return (m.group(1) or get_prefix(m.group(2))) + m.group(2)


def tencent_quote(codes):
    """批量实时行情（一次最多 ~60 只）。返回按「请求时原始代码」作键的 dict。
    键不取响应里的 6 位码：sh000001(上证指数) 与 sz000001(平安银行) 会撞键。
    取不到的代码不在结果里。
    """
    codes = [str(c).strip() for c in codes if str(c).strip()]
    out = {}
    for i in range(0, len(codes), 60):
        chunk = codes[i:i + 60]
        try:
            rev = {with_market(c): c for c in chunk}
        except ValueError:
            continue
        url = "https://qt.gtimg.cn/q=" + ",".join(rev.keys())
        try:
            # 必须走 trust_env=False 的会话：urllib 默认走系统代理(Clash)，慢 15 倍
            r = SESSION.get(url, headers={"User-Agent": UA,
                                          "Referer": "https://gu.qq.com/"}, timeout=10)
            data = r.content.decode("gbk")
        except Exception:
            continue
        for line in data.strip().split(";"):
            line = line.strip()  # 分号分隔的第二行起带前导换行
            if "=" not in line or '"' not in line:
                continue
            sym = line.split("=")[0][2:]  # v_sh000001 -> sh000001
            vals = line.split('"')[1].split("~")
            if len(vals) < 47:
                continue

            def f(idx):
                try:
                    return float(vals[idx]) if vals[idx] else None
                except (ValueError, TypeError):
                    return None

            out[rev.get(sym, sym)] = {
                "symbol": sym,
                "code": vals[2],
                "name": vals[1],
                "price": f(3) or 0,
                "last_close": f(4) or 0,
                "open": f(5),
                "volume_hand": f(36),
                "amount_wan": f(37),
                "pct": f(32),
                "chg": f(31),
                "high": f(33),
                "low": f(34),
                "turnover": f(38),
                "pe_ttm": f(39) if (f(39) or 0) > 0 else None,
                "pb": f(46) if (f(46) or 0) > 0 else None,
                "mcap_total_yi": f(45),
                "mcap_float_yi": f(44),
                "time": vals[30],
            }
    return out


def kline(code, period="day", count=320, fq="qfq"):
    """日/周/月K线。fq: qfq|hfq|none。返回按日期升序的 [{date,open,close,high,low,volume}]。"""
    sym = with_market(str(code))
    fq_param = fq if fq in ("qfq", "hfq") else ""
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    r = SESSION.get(url, params={"param": "%s,%s,,,%d,%s" % (sym, period, int(count), fq_param)},
                    headers={"User-Agent": UA, "Referer": "https://gu.qq.com/"}, timeout=15)
    node = (r.json().get("data") or {}).get(sym) or {}
    rows = node.get(period) or node.get(fq_param + period) or []
    out = []
    for row in rows:
        try:
            out.append({"date": row[0], "open": float(row[1]), "close": float(row[2]),
                        "high": float(row[3]), "low": float(row[4]), "volume": float(row[5] or 0)})
        except (ValueError, IndexError, TypeError):
            continue
    return out


def minute_line(code):
    """当日分时。返回 {date, last_close, points:[{time, price, cum_vol}]}。
    非交易日返回最近一个交易日的分时。
    """
    sym = with_market(str(code))
    url = "https://web.ifzq.gtimg.cn/appstock/app/minute/query"
    r = SESSION.get(url, params={"code": sym},
                    headers={"User-Agent": UA, "Referer": "https://gu.qq.com/"}, timeout=15)
    node = (r.json().get("data") or {}).get(sym) or {}
    d = node.get("data") or {}
    points = []
    for item in d.get("data") or []:
        parts = str(item).split()
        if len(parts) < 3:
            continue
        try:
            points.append({"time": parts[0], "price": float(parts[1]), "cum_vol": float(parts[2])})
        except (ValueError, TypeError):
            continue
    last_close = None
    qt = node.get("qt") or {}
    qv = qt.get(sym)
    if isinstance(qv, list) and len(qv) > 4:
        try:
            last_close = float(qv[4])
        except (ValueError, TypeError):
            pass
    return {"date": d.get("date", ""), "last_close": last_close, "points": points}
