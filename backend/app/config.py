# -*- coding: utf-8 -*-
"""全局配置：路径、常量"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "finance.db")
FRONTEND_DIST = os.path.join(os.path.dirname(BASE_DIR), "frontend", "dist")

os.makedirs(DATA_DIR, exist_ok=True)

# 盯盘页顶部的指数一览
INDEX_OVERVIEW = [
    ("sh000001", "上证指数"),
    ("sz399001", "深证成指"),
    ("sz399006", "创业板指"),
    ("sh000688", "科创50"),
    ("sh000300", "沪深300"),
]

# 估值页预设指数（中证/上证官方 xls 覆盖的代码）
VALUATION_PRESETS = [
    ("000300", "沪深300"),
    ("000905", "中证500"),
    ("000688", "科创50"),
    ("000510", "中证A500"),
    ("931079", "5G通信"),
    ("930713", "CS人工智"),
]

# 美股：指数（SOXX/IWM 用 ETF 代表费半/罗素2000）
US_INDICES = [
    ("DJI", "道琼斯"),
    ("IXIC", "纳斯达克"),
    ("INX", "标普500"),
    ("SOXX", "费城半导体"),
    ("IWM", "罗素2000"),
]

# 美股热门板块：SPDR 行业 ETF + 半导体/中概主题
US_SECTORS = [
    ("XLK", "科技"), ("XLC", "通信服务"), ("XLF", "金融"), ("XLE", "能源"),
    ("XLV", "医疗保健"), ("XLY", "可选消费"), ("XLP", "必需消费"), ("XLI", "工业"),
    ("XLU", "公用事业"), ("XLB", "基础材料"), ("XLRE", "房地产"),
    ("SOXX", "半导体"), ("KWEB", "中概互联"),
]

US_GIANTS = ["AAPL", "MSFT", "NVDA", "GOOG", "AMZN", "META", "TSLA"]
US_CHINA = ["BABA", "PDD", "JD", "BIDU", "NIO", "LI", "XPEV"]

# 腾讯行情单次批量上限（qt.gtimg.cn 一次 ~60 只稳妥）
QUOTE_BATCH = 60
