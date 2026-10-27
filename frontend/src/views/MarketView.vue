<template>
  <div>
    <!-- 指数概览 -->
    <div class="idx-strip">
      <div v-for="c in idxOrder" :key="c" class="stat-card idx">
        <div class="k">{{ idxNames[c] || c }}</div>
        <div class="v" :style="{ color: qColor(idxQuotes[c]) }">{{ q(idxQuotes[c]) }}</div>
        <div :style="{ color: qColor(idxQuotes[c]) }" class="muted">{{ pct(idxQuotes[c]) }}</div>
      </div>
    </div>

    <div class="body-row">
      <!-- 自选列表：固定窄列 -->
      <div class="left-pane">
        <div class="toolbar">
          <el-input v-model="newCode" placeholder="代码，如 600519"
                    size="small" style="width: 118px" @keyup.enter="add" clearable />
          <el-button size="small" type="primary" @click="add">加自选</el-button>
          <el-button size="small" @click="loadAll">刷新</el-button>
          <span class="muted">{{ polling ? '3 秒轮询中' : '休市（收盘价）' }}</span>
        </div>
        <QuoteTable :items="watchlist" deletable @select="select" @remove="remove" />
      </div>

      <!-- 图表区 -->
      <div class="chart-panel">
        <div class="chart-head">
          <span class="sel-name">{{ selName }}</span>
          <span class="sel-price" :style="{ color: selColor }">{{ selPrice }}</span>
          <span :style="{ color: selColor }">{{ selPct }}</span>
          <span class="muted sel-time">{{ selTime }}</span>
          <el-radio-group v-model="period" size="small" class="period">
            <el-radio-button value="timeline">分时</el-radio-button>
            <el-radio-button value="day">日K</el-radio-button>
            <el-radio-button value="week">周K</el-radio-button>
            <el-radio-button value="month">月K</el-radio-button>
          </el-radio-group>
          <el-select v-model="fq" size="small" style="width: 92px" v-if="period !== 'timeline'">
            <el-option value="qfq" label="前复权" />
            <el-option value="hfq" label="后复权" />
            <el-option value="none" label="不复权" />
          </el-select>
        </div>
        <div class="chart-box">
          <TimelineChart v-if="period === 'timeline'" :data="timeline" />
          <KLineChart v-else :bars="bars" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import QuoteTable from '../components/QuoteTable.vue'
import KLineChart from '../components/KLineChart.vue'
import TimelineChart from '../components/TimelineChart.vue'
import { http, errMsg } from '../api/client'
import {
  type Quote, type Bar, type TimelineData, type WatchItem,
  pctColor, fmtNum, fmtPct, isTradingTimeNow,
} from '../types'

// ---------- 指数概览 ----------
const idxOrder = ref<string[]>([])
const idxNames = ref<Record<string, string>>({})
const idxQuotes = ref<Record<string, Quote>>({})

// ---------- 自选 ----------
const watchlist = ref<WatchItem[]>([])
const newCode = ref('')
const polling = ref(false)

// ---------- 图表 ----------
// 周期/复权/选中标的持久化：刷新页面后保持
const selected = ref(localStorage.getItem('chart.selected') || '')
const period = ref<'timeline' | 'day' | 'week' | 'month'>(
  (localStorage.getItem('chart.period') as any) || 'timeline')
const fq = ref(localStorage.getItem('chart.fq') || 'qfq')
const bars = ref<Bar[]>([])
const timeline = ref<TimelineData | null>(null)

let timer: number | undefined

const selQuote = computed(() => watchlist.value.find((w) => w.code === selected.value)?.quote)
const selName = computed(() => selQuote.value?.name || selected.value || '选择左侧标的')
const selPrice = computed(() => (selQuote.value ? fmtNum(selQuote.value.price) : '-'))
const selPct = computed(() => (selQuote.value ? fmtPct(selQuote.value.pct) : ''))
const selColor = computed(() => pctColor(selQuote.value?.pct))
const selTime = computed(() => {
  const t = selQuote.value?.time || ''
  return t.length >= 14 ? `${t.slice(4, 6)}-${t.slice(6, 8)} ${t.slice(8, 10)}:${t.slice(10, 12)}` : ''
})

function qColor(q?: Quote) { return pctColor(q?.pct) }
function q(qq?: Quote) { return qq ? fmtNum(qq.price) : '-' }
function pct(qq?: Quote) { return qq ? fmtPct(qq.pct) : '' }

async function loadIndices() {
  try {
    const { data } = await http.get('/indices')
    idxOrder.value = data.order
    idxNames.value = data.names
    idxQuotes.value = data.quotes
  } catch (e) { console.warn(e) }
}

async function loadWatchlist() {
  try {
    const { data } = await http.get('/watchlist')
    watchlist.value = data.items
    polling.value = !!data.polling || isTradingTimeNow()
    if (!data.items.length) {
      selected.value = ''
      localStorage.removeItem('chart.selected')
      return
    }
    // 选中为空或标的已从自选删除 → 回落到第一行并加载
    if (!selected.value || !data.items.some((w) => w.code === selected.value)) {
      selected.value = data.items[0].code
      localStorage.setItem('chart.selected', selected.value)
      bars.value = []
      timeline.value = null
      loadChart()
    }
  } catch (e) { console.warn(e) }
}

function loadAll() { loadIndices(); loadWatchlist() }

async function add() {
  const code = newCode.value.trim()
  if (!code) return
  try {
    await http.post('/watchlist', { code })
    ElMessage.success('已加入自选: ' + code)
    newCode.value = ''
    loadWatchlist()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

async function remove(code: string) {
  try {
    await http.delete('/watchlist/' + encodeURIComponent(code))
    loadWatchlist()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

function select(code: string) {
  if (selected.value === code) { loadChart(); return }
  selected.value = code
  localStorage.setItem('chart.selected', code)
  // 保持当前周期（分时/日K/周K/月K）不变，仅清掉旧标的的数据避免闪现
  bars.value = []
  timeline.value = null
  loadChart()
}

async function loadChart() {
  const code = selected.value
  if (!code) return
  try {
    if (period.value === 'timeline') {
      const { data } = await http.get('/timeline', { params: { code } })
      if (code === selected.value) timeline.value = data
    } else {
      const { data } = await http.get('/kline', { params: { code, period: period.value, fq: fq.value, count: 250 } })
      if (code === selected.value) bars.value = data.bars
    }
  } catch (e) { console.warn(e) }
}

watch(period, (v) => localStorage.setItem('chart.period', v))
watch(fq, (v) => localStorage.setItem('chart.fq', v))
watch([period, fq], () => {
  // 切周期/复权时也先清旧数据（v-if 换组件的瞬间不闪现上一个标的）
  bars.value = []
  timeline.value = null
  loadChart()
})
// 盘中自动跟随：轮询时仅刷新列表与指数；分时图每 30 秒跟随一次
watch(polling, (v) => {
  if (timer) window.clearInterval(timer)
  if (v) {
    timer = window.setInterval(() => {
      if (document.hidden) return
      loadWatchlist(); loadIndices()
      if (period.value === 'timeline') loadChart()   // 分时跟随轮询刷新
    }, 3000)
  }
})

onMounted(async () => {
  await loadWatchlist()
  // 刷新恢复场景：选中标的从 localStorage 恢复，这里补一次图表加载
  loadChart()
  loadIndices()
  polling.value = isTradingTimeNow()
})
onUnmounted(() => { if (timer) window.clearInterval(timer) })
</script>

<style scoped>
.idx-strip { display: flex; gap: 10px; flex-wrap: wrap; }
.idx-strip .idx { flex: 1; min-width: 140px; }
.body-row { margin-top: 12px; display: flex; gap: 12px; align-items: stretch; }
.left-pane { width: 280px; flex: none; }
.toolbar { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; flex-wrap: wrap; }
.chart-panel {
  flex: 1; min-width: 0;
  background: #14161a; border: 1px solid #23262d; border-radius: 8px;
  padding: 10px 12px; height: calc(100vh - 210px); display: flex; flex-direction: column;
}
.chart-head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.sel-name { font-weight: 600; }
.sel-price { font-size: 20px; font-weight: 600; }
.period { margin-left: auto; }
.chart-box { flex: 1; min-height: 0; }
</style>
