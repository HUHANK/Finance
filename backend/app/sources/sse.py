# -*- coding: utf-8 -*-
"""上交所官方数据源：ETF 份额日快照。
摘自 .scratch/step4_etf_screen.py 已验证代码（含 total 分页校验）。
"""
import requests

SESSION = requests.Session()
SESSION.trust_env = False
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def etf_shares_sh(day):
    """上交所全部 ETF 某日份额（万份）。返回 {6位代码: {name, shares}}。

    交易所接口只发布历史交易日；请求非交易日会无数据，抛 ValueError。
    """
    url = "https://query.sse.com.cn/commonQuery.do"
    params = {"sqlId": "COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L", "STAT_DATE": day,
              "isPagination": "true", "pageHelp.pageSize": 10000, "pageHelp.pageNo": 1,
              "pageHelp.beginPage": 1, "pageHelp.cacheSize": 1, "pageHelp.endPage": 1}
    r = SESSION.get(url, params=params,
                    headers={"User-Agent": UA, "Referer": "https://www.sse.com.cn/"},
                    timeout=30)
    payload = r.json()
    result = payload.get("result") or []
    total = payload.get("pageHelp", {}).get("total")
    if total is not None and len(result) != int(total):
        raise RuntimeError("SSE ETF %s: %d条 != total %s" % (day, len(result), total))
    if not result:
        raise ValueError("SSE %s 无数据（可能非交易日）" % day)
    return {rec["SEC_CODE"]: {"name": rec["SEC_NAME"],
                              "shares": float(rec["TOT_VOL"].replace(",", ""))}
            for rec in result if rec.get("STAT_DATE") == day}
