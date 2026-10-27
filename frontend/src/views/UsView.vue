<template>
  <div>
    <div class="us-head">
      <span class="muted">美东时间 {{ usTime }}</span>
      <el-tag size="small" :type="marketOpen ? 'success' : 'info'" effect="plain">
        {{ marketOpen ? '盘中' : '已收盘' }}
      </el-tag>
      <span class="muted">{{ polling ? '1 秒轮询中' : '' }}</span>
    </div>

    <!-- 指数 -->
    <div class="cards">
      <div v-for="it in indices" :key="it.code" class="stat-card idx-card"
           :title="`双击查看 ${it.label} K线`" @dblclick="openChart(it)">
        <div class="k">{{ it.label }}</div>
        <div class="v" :style="{ color: cc(it.pct) }">{{ it.price?.toLocaleString('en-US') }}</div>
        <div :style="{ color: cc(it.pct) }">{{ pct(it.pct) }} <span class="muted">{{ chg(it.chg) }}</span></div>
      </div>
    </div>

    <!-- 热门板块 -->
    <div class="section-title">热门板块（行业 ETF，按涨跌幅，双击看K线）</div>
    <div class="sector-grid">
      <div v-for="s in sectors" :key="s.code" class="sector-chip" :style="chipStyle(s.pct)"
           title="双击查看K线" @dblclick="openChart(s)">
        <div class="s-label">{{ s.label }}</div>
        <div class="s-pct" :style="{ color: cc(s.pct) }">{{ pct(s.pct) }}</div>
        <div class="muted s-price">${{ s.price }}</div>
      </div>
    </div>

    <!-- 热门个股 -->
    <div class="section-title">七巨头（双击看K线）</div>
    <QuoteTable :items="asItems(giants)" style="max-width: 560px" @dblclick="stockDbl" />
    <div class="section-title">热门中概（双击看K线）</div>
    <QuoteTable :items="asItems(china)" style="max-width: 560px" @dblclick="stockDbl" />

    <!-- 指数 K线弹窗 -->
    <el-dialog v-model="dlg" :title="dlgLabel + ' · K线'" width="940px" destroy-on-close>
      <div class="dlg-head">
        <span class="dlg-price" :style="{ color: cc(live?.pct) }">{{ live?.price?.toLocaleString('en-US') ?? '-' }}</span>
        <span :style="{ color: cc(live?.pct) }">{{ pct(live?.pct) }}</span>
        <span class="muted">美东 {{ live?.time }}</span>
        <el-radio-group v-model="dlgPeriod" size="small" class="dlg-period">
          <el-radio-button v-if="dlgHasTimeline" value="timeline">分时</el-radio-button>
          <el-radio-button value="day">日K</el-radio-button>
          <el-radio-button value="week">周K</el-radio-button>
          <el-radio-button value="month">月K</el-radio-button>
        </el-radio-group>
      </div>
      <div class="dlg-chart">
        <TimelineChart v-if="dlgPeriod === 'timeline'" :data="dlgTimelineLive" />
        <KLineChart v-else :bars="dlgBars" />
      </div>
      <div class="muted dlg-tip">价格随页面轮询实时更新；分时每 15 秒拉取分钟线，尾部实时价每秒跟随（美东时间）</div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import QuoteTable from '../components/QuoteTable.vue'
import KLineChart from '../components/KLineChart.vue'
import TimelineChart from '../components/TimelineChart.vue'
import { http } from '../api/client'
import { type Bar, type TimelineData, pctColor, fmtPct } from '../types'

interface UsQuote {
  code: string; symbol: string; name: string
  price: number; last_close: number; pct: number | null; chg: number | null
  time: string; label?: string; has_timeline?: boolean
}

const indices = ref<UsQuote[]>([])
const sectors = ref<UsQuote[]>([])
const giants = ref<UsQuote[]>([])
const china = ref<UsQuote[]>([])
const usTime = ref('')
const polling = ref(false)
let timer: number | undefined

const marketOpen = computed(() => {
  // usTime 形如 2026-10-27 11:22:20（美东）；9:30-16:00 且周一~五
  const m = usTime.value.match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})/)
  if (!m) return false
  const [, y, mo, d, h, mi] = m.map(Number)
  const day = new Date(Date.UTC(y, mo - 1, d)).getUTCDay()
  if (day === 0 || day === 6) return false
  const minutes = h * 60 + mi
  return minutes >= 570 && minutes < 960
})

function cc(v: number | null | undefined) { return pctColor(v) }
function pct(v: number | null | undefined) { return fmtPct(v) }
function chg(v: number | null | undefined) {
  if (v == null) return ''
  return (v > 0 ? '+' : '') + v.toFixed(2)
}
function chipStyle(v: number | null | undefined) {
  const bg = (v ?? 0) > 0 ? 'rgba(230,83,78,0.12)' : (v ?? 0) < 0 ? 'rgba(46,163,107,0.12)' : 'transparent'
  return { background: bg }
}
function asItems(list: UsQuote[]) {
  return list.map((x) => ({ code: x.code, name: x.name, quote: x as any }))
}

// ---------- 指数 K线弹窗 ----------
const dlg = ref(false)
const dlgCode = ref('')
const dlgLabel = ref('')
const dlgPeriod = ref<'timeline' | 'day' | 'week' | 'month'>('timeline')
const dlgHasTimeline = ref(true)
const dlgBars = ref<Bar[]>([])
const dlgTimeline = ref<TimelineData | null>(null)
let dlgTimer: number | undefined

// 弹窗头部的实时价：从页面的 1 秒轮询数据里取，天然实时（指数/板块/个股都在内）
const live = computed<UsQuote | undefined>(() =>
  indices.value.find((x) => x.code === dlgCode.value)
  || sectors.value.find((x) => x.code === dlgCode.value)
  || giants.value.find((x) => x.code === dlgCode.value)
  || china.value.find((x) => x.code === dlgCode.value))

function stockDbl(code: string) {
  const q = giants.value.find((x) => x.code === code) || china.value.find((x) => x.code === code)
  if (q) openChart(q)
}

// 分时图实时尾巴：分钟线只到上一个完整分钟，用 1 秒轮询的实时价把当前分钟补上，
// 使曲线尾部每秒跟随最新价（q.time 为美东 "YYYY-MM-DD HH:MM:SS"）
const dlgTimelineLive = computed<TimelineData | null>(() => {
  const tl = dlgTimeline.value
  const q = live.value
  if (!tl || !q || !tl.points.length) return tl
  const day = (q.time || '').slice(0, 10)
  const hhmm = (q.time || '').slice(11, 13) + (q.time || '').slice(14, 16)
  if (day !== tl.date || !hhmm || !q.price) return tl
  const pts = tl.points.filter((p) => p.time <= hhmm)
  if (!pts.length) return tl
  const tail = { time: hhmm, price: q.price, cum_vol: pts[pts.length - 1].cum_vol }
  return { ...tl, points: [...pts.slice(0, -1), tail] }
})

function openChart(q: UsQuote) {
  dlgCode.value = q.code
  dlgLabel.value = q.label || q.name
  dlgHasTimeline.value = q.has_timeline !== false
  dlgPeriod.value = dlgHasTimeline.value ? 'timeline' : 'day'
  dlg.value = true
}

async function loadDlg() {
  const code = dlgCode.value
  if (!code) return
  try {
    if (dlgPeriod.value === 'timeline') {
      const { data } = await http.get('/us/timeline', { params: { code } })
      if (code === dlgCode.value) dlgTimeline.value = data
    } else {
      const { data } = await http.get('/us/kline', { params: { code, period: dlgPeriod.value, count: 250 } })
      if (code === dlgCode.value) dlgBars.value = data.bars
    }
  } catch (e) { console.warn(e) }
}

watch(dlgPeriod, loadDlg)
watch(dlg, (v) => { if (v) loadDlg() })
// 分时模式下每 15 秒拉一次分钟线（尾部实时价由 dlgTimelineLive 每秒跟随）
watch([dlg, dlgPeriod], ([open, p]) => {
  if (dlgTimer) { window.clearInterval(dlgTimer); dlgTimer = undefined }
  if (open && p === 'timeline') {
    dlgTimer = window.setInterval(() => { if (!document.hidden) loadDlg() }, 15000)
  }
})

onUnmounted(() => { if (dlgTimer) window.clearInterval(dlgTimer) })

async function load() {
  if (document.hidden) return
  try {
    const { data } = await http.get('/us/overview')
    indices.value = data.indices
    sectors.value = data.sectors
    giants.value = data.giants
    china.value = data.china
    usTime.value = data.time
    polling.value = true
  } catch (e) { console.warn(e) }
}

onMounted(() => {
  load()
  timer = window.setInterval(load, 1000)
})
onUnmounted(() => { if (timer) window.clearInterval(timer) })
</script>

<style scoped>
.us-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.cards { display: flex; gap: 10px; flex-wrap: wrap; }
.cards .stat-card { flex: 1; min-width: 150px; }
.sector-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(128px, 1fr));
  gap: 8px;
}
.sector-chip {
  border: 1px solid #23262d; border-radius: 8px; padding: 10px 12px;
  background: #171a20;
}
.s-label { font-size: 13px; font-weight: 500; }
.s-pct { font-size: 17px; font-weight: 600; margin: 2px 0; }
.s-price { font-size: 11px; }
.idx-card { cursor: pointer; }
.idx-card:hover { border-color: #3a4150; }
.dlg-head { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.dlg-price { font-size: 24px; font-weight: 600; }
.dlg-period { margin-left: auto; }
.dlg-chart { height: 440px; }
.dlg-tip { margin-top: 6px; }
</style>
