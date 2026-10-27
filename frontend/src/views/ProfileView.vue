<template>
  <div>
    <div class="toolbar">
      <el-input v-model="code" size="small" placeholder="代码：600519 / sh000001 / 159994 / 931079"
                style="width: 260px" @keyup.enter="query" clearable />
      <el-button size="small" type="primary" :loading="loading" @click="query">查询</el-button>
      <el-button size="small" @click="addWatch" v-if="prof">加入自选</el-button>
    </div>

    <el-alert v-if="error" type="error" :closable="false" :title="error" style="margin-top: 10px" />

    <template v-if="prof && prof.quote">
      <!-- 行情头 -->
      <div class="cards">
        <div class="stat-card wide">
          <div class="k">{{ prof.quote.name }}
            <span class="muted">{{ prof.symbol }} · {{ kindLabel }}</span></div>
          <div class="v" :style="{ color: pctColor(prof.quote.pct) }">{{ prof.quote.price }}</div>
          <div :style="{ color: pctColor(prof.quote.pct) }">{{ fmtPct(prof.quote.pct) }}
            <span class="muted">{{ quoteTime }}</span></div>
        </div>
        <div class="stat-card"><div class="k">今开</div><div class="v small">{{ prof.quote.open ?? '-' }}</div>
          <div class="muted">昨收 {{ prof.quote.last_close }}</div></div>
        <div class="stat-card"><div class="k">最高/最低</div><div class="v small">
          {{ prof.quote.high ?? '-' }} / {{ prof.quote.low ?? '-' }}</div>
          <div class="muted">换手 {{ prof.quote.turnover ?? '-' }}%</div></div>
        <div class="stat-card"><div class="k">成交额</div><div class="v small">{{ amt }}</div>
          <div class="muted">量 {{ vol }}</div></div>
        <div class="stat-card"><div class="k">PE-TTM / PB</div>
          <div class="v small">{{ prof.quote.pe_ttm ?? '-' }} / {{ prof.quote.pb ?? '-' }}</div>
          <div class="muted">总市值 {{ prof.quote.mcap_total_yi ?? '-' }}亿</div></div>
      </div>

      <!-- 指数：估值摘要 -->
      <template v-if="prof.kind === 'index' && prof.valuation">
        <div class="section-title">指数估值</div>
        <div class="cards">
          <div class="stat-card"><div class="k">PE（官网日频）</div><div class="v">{{ prof.valuation.pe_last }}</div>
            <div class="muted">{{ prof.valuation.date }}</div></div>
          <div class="stat-card"><div class="k">全历史分位</div>
            <div class="v" :style="{ color: pctColor(prof.valuation.pct_all) }">{{ prof.valuation.pct_all }}%</div></div>
          <div class="stat-card"><div class="k">3 年 / 5 年分位</div>
            <div class="v small">{{ prof.valuation.pct_3y ?? '-' }}% / {{ prof.valuation.pct_5y ?? '-' }}%</div></div>
          <div class="stat-card"><div class="k">官方 PE1/PE2</div>
            <div class="v small">{{ prof.valuation.pe1_official ?? '-' }} / {{ prof.valuation.pe2_official ?? '-' }}</div>
            <div class="muted">股息率 {{ prof.valuation.dy_official ?? '-' }}%</div></div>
        </div>
      </template>

      <!-- 个股：一致预期 -->
      <template v-if="prof.kind === 'stock'">
        <div class="section-title">机构一致预期（同花顺）</div>
        <el-alert v-if="!prof.eps_forecast" type="info" :closable="false" title="暂无一致预期数据" />
        <el-table v-else :data="prof.eps_forecast" size="small" style="max-width: 480px">
          <el-table-column prop="year" label="年度" width="90" />
          <el-table-column prop="eps" label="EPS 均值" width="110" align="right" />
          <el-table-column prop="orgs" label="机构数" width="90" align="right" />
        </el-table>
      </template>

      <template v-if="prof.kind === 'etf'">
        <div class="muted" style="margin-top: 10px">
          ETF 概要：联接指数估值可到「估值」页查询对应指数；份额变动见「复盘」页。
        </div>
      </template>

      <!-- K线 -->
      <div class="section-title">日K（前复权，近 120 日）</div>
      <div class="kline-box">
        <KLineChart :bars="bars" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import KLineChart from '../components/KLineChart.vue'
import { http, errMsg } from '../api/client'
import { type Bar, type Quote, fmtAmountYi, fmtHand, fmtPct, pctColor } from '../types'

interface Profile {
  code: string; symbol: string; code6: string; kind: 'index' | 'etf' | 'stock'
  quote: Quote | null
  eps_forecast: { year: number; eps: number; orgs: number | null }[] | null
  valuation: any | null
}

const code = ref('')
const prof = ref<Profile | null>(null)
const bars = ref<Bar[]>([])
const loading = ref(false)
const error = ref('')

const kindLabel = computed(() =>
  ({ index: '指数', etf: 'ETF/基金', stock: '个股' }[prof.value?.kind || 'stock']))
const quoteTime = computed(() => {
  const t = prof.value?.quote?.time || ''
  return t.length >= 14 ? `${t.slice(4, 6)}-${t.slice(6, 8)} ${t.slice(8, 10)}:${t.slice(10, 12)}` : ''
})
const amt = computed(() => fmtAmountYi(prof.value?.quote?.amount_wan))
const vol = computed(() => fmtHand(prof.value?.quote?.volume_hand))

async function query() {
  const c = code.value.trim()
  if (!c) return
  loading.value = true
  error.value = ''
  prof.value = null
  bars.value = []
  try {
    const { data } = await http.get('/profile', { params: { code: c } })
    prof.value = data
    if (data.quote) {
      const k = await http.get('/kline', { params: { code: c, period: 'day', fq: 'qfq', count: 120 } })
      bars.value = k.data.bars
    }
  } catch (e) { error.value = errMsg(e) } finally { loading.value = false }
}

async function addWatch() {
  if (!code.value.trim()) return
  try {
    await http.post('/watchlist', { code: code.value.trim() })
    ElMessage.success('已加入自选')
  } catch (e) { ElMessage.error(errMsg(e)) }
}
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 8px; }
.cards { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
.stat-card { flex: 1; min-width: 150px; }
.stat-card.wide { flex: 1.4; }
.v.small { font-size: 17px; }
.kline-box {
  height: 420px; background: #14161a;
  border: 1px solid #23262d; border-radius: 8px; padding: 6px;
}
</style>
