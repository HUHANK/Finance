/** 与后端对齐的核心类型 */

export interface Quote {
  symbol: string
  code: string
  name: string
  price: number
  last_close: number
  open: number | null
  high: number | null
  low: number | null
  pct: number | null
  chg: number | null
  volume_hand: number | null
  amount_wan: number | null
  turnover: number | null
  pe_ttm: number | null
  pb: number | null
  mcap_total_yi: number | null
  mcap_float_yi: number | null
  time: string
}

export interface WatchItem {
  code: string
  name: string
  quote: Quote | null
}

export interface Bar {
  date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
}

export interface TimelinePoint {
  time: string
  price: number
  cum_vol: number
}

export interface TimelineData {
  date: string
  last_close: number | null
  points: TimelinePoint[]
}

/** 红涨绿跌：>=0 红，<0 绿 */
export function pctColor(v: number | null | undefined): string {
  if (v == null) return 'var(--el-text-color-secondary)'
  return v > 0 ? '#e6534e' : v < 0 ? '#2ea36b' : 'var(--el-text-color-regular)'
}

export function fmtPct(v: number | null | undefined): string {
  if (v == null) return '-'
  return (v > 0 ? '+' : '') + v.toFixed(2) + '%'
}

export function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v == null) return '-'
  return v.toFixed(digits)
}

/** 腾讯行情成交额单位是万元 */
export function fmtAmountYi(wan: number | null | undefined): string {
  if (wan == null) return '-'
  return (wan / 1e4).toFixed(2) + '亿'
}

export function fmtHand(hand: number | null | undefined): string {
  if (hand == null) return '-'
  if (hand >= 1e6) return (hand / 1e6).toFixed(2) + '百万手'
  if (hand >= 1e4) return (hand / 1e4).toFixed(2) + '万手'
  return String(Math.round(hand)) + '手'
}

/** 本地粗判是否 A 股交易时段（节假日不管，由后端数据兜底） */
export function isTradingTimeNow(): boolean {
  const d = new Date()
  const day = d.getDay()
  if (day === 0 || day === 6) return false
  const m = d.getHours() * 60 + d.getMinutes()
  return (m >= 570 && m <= 690) || (m >= 780 && m <= 900) // 9:30-11:30, 13:00-15:00
}
