<template>
  <div>
    <div class="toolbar">
      <el-select v-model="indexCode" size="small" style="width: 180px" @change="load">
        <el-option v-for="p in presets" :key="p.code" :value="p.code" :label="`${p.name} ${p.code}`" />
      </el-select>
      <el-input v-model="custom" size="small" placeholder="或输入中证指数代码" style="width: 170px"
                @keyup.enter="useCustom" clearable />
      <el-button size="small" @click="useCustom">查询</el-button>
      <span class="muted" v-if="summary">PE 序列自 {{ summary.start }}，共 {{ summary.n_days }} 个交易日</span>
    </div>

    <!-- 摘要卡片 -->
    <div class="cards" v-if="summary">
      <div class="stat-card"><div class="k">PE（官网日频）</div><div class="v">{{ summary.pe_last }}</div>
        <div class="muted">{{ summary.date }}</div></div>
      <div class="stat-card"><div class="k">全历史分位</div>
        <div class="v" :style="{ color: pctColor(summary.pct_all) }">{{ summary.pct_all }}%</div></div>
      <div class="stat-card"><div class="k">3 年分位</div>
        <div class="v" :style="{ color: pctColor(summary.pct_3y) }">{{ summary.pct_3y ?? '-' }}%</div></div>
      <div class="stat-card"><div class="k">5 年分位</div>
        <div class="v" :style="{ color: pctColor(summary.pct_5y) }">{{ summary.pct_5y ?? '-' }}%</div></div>
      <div class="stat-card"><div class="k">官方 PE1/PE2</div>
        <div class="v small">{{ summary.pe1_official ?? '-' }} / {{ summary.pe2_official ?? '-' }}</div>
        <div class="muted">股息率 {{ summary.dy_official ?? '-' }}%</div></div>
    </div>

    <!-- PE 曲线 -->
    <div class="section-title">市盈率走势</div>
    <div ref="peChart" class="pe-chart"></div>

    <!-- 权重股 -->
    <div class="section-title">
      前 {{ weights.items.length }} 大权重股
      <span class="muted" v-if="weights.snapshot_date">快照 {{ weights.snapshot_date }}</span>
      <el-button size="small" type="primary" :loading="forecasting" style="margin-left: 16px"
                 @click="forecast">计算一致预期（约 15 秒）</el-button>
    </div>
    <el-table :data="weights.items" size="small" style="max-width: 900px">
      <el-table-column type="index" label="#" width="46" />
      <el-table-column prop="code" label="代码" width="90" />
      <el-table-column prop="name" label="名称" min-width="110" />
      <el-table-column label="权重%" width="80" align="right">
        <template #default="{ row }">{{ row.weight?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="现价" width="84" align="right">
        <template #default="{ row }">{{ row.price ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="PE-TTM" width="84" align="right">
        <template #default="{ row }">{{ row.pe_ttm ?? '-' }}</template>
      </el-table-column>
      <el-table-column v-if="forecastItems.length" label="EPS 26E" width="90" align="right">
        <template #default="{ row }">{{ fc(row.code)?.eps26 ?? '-' }}</template>
      </el-table-column>
      <el-table-column v-if="forecastItems.length" label="EPS 27E" width="90" align="right">
        <template #default="{ row }">{{ fc(row.code)?.eps27 ?? '-' }}</template>
      </el-table-column>
    </el-table>

    <!-- 一致预期汇总 -->
    <template v-if="fcSummary">
      <div class="section-title">一致预期加权汇总（前 {{ fcSummary.covered_n }} 只，覆盖 {{ fcSummary.covered_weight }}% 权重）</div>
      <div class="cards">
        <div class="stat-card"><div class="k">篮子 PE-TTM(调和)</div><div class="v">{{ fcSummary.basket_pe_ttm ?? '-' }}</div></div>
        <div class="stat-card"><div class="k">增长 TTM→26E</div><div class="v">{{ fcSummary.g_ttm_to_26e ?? '-' }}%</div></div>
        <div class="stat-card"><div class="k">增长 26E→27E</div><div class="v">{{ fcSummary.g_26e_to_27e ?? '-' }}%</div></div>
        <div class="stat-card"><div class="k">PE 26E / 27E</div><div class="v small">{{ fcSummary.pe_26e ?? '-' }} / {{ fcSummary.pe_27e ?? '-' }}</div></div>
        <div class="stat-card"><div class="k">PEG</div><div class="v">{{ fcSummary.peg ?? '-' }}</div></div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { http, httpLong, errMsg } from '../api/client'
import { pctColor } from '../types'

const presets = ref<{ code: string; name: string }[]>([])
const indexCode = ref('000300')
const custom = ref('')
const summary = ref<any>(null)
const weights = ref<{ snapshot_date: string | null; items: any[] }>({ snapshot_date: null, items: [] })
const forecasting = ref(false)
const forecastItems = ref<any[]>([])
const fcSummary = ref<any>(null)
const peChart = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function fc(code: string) {
  return forecastItems.value.find((x) => x.code === code)
}

function useCustom() {
  const c = custom.value.trim()
  if (!c) return
  indexCode.value = c.replace(/^(sh|sz)/i, '')
  load()
}

async function load() {
  forecastItems.value = []
  fcSummary.value = null
  try {
    const { data } = await http.get('/valuation', { params: { index: indexCode.value } })
    summary.value = data.summary
    await nextTick()
    renderPe(data.pe_history)
    const w = await http.get('/valuation/weights', { params: { index: indexCode.value, top: 20 } })
    weights.value = w.data
  } catch (e) { ElMessage.error(errMsg(e)) }
}

async function forecast() {
  forecasting.value = true
  try {
    const { data } = await httpLong.post('/valuation/forecast', null, { params: { index: indexCode.value } })
    fcSummary.value = data.summary
    forecastItems.value = data.items || []
    ElMessage.success('一致预期计算完成')
  } catch (e) { ElMessage.error(errMsg(e)) } finally { forecasting.value = false }
}

function renderPe(history: { date: string; pe: number | null }[]) {
  if (!chart) return
  const dates = history.map((r) => r.date)
  const pes = history.map((r) => r.pe)
  const last = pes[pes.length - 1]
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    tooltip: { trigger: 'axis', backgroundColor: '#1c1f26', borderColor: '#33363d',
               textStyle: { color: '#e8e8e8', fontSize: 12 } },
    xAxis: { type: 'category', data: dates, axisLabel: { color: '#9aa0a8', fontSize: 11 },
             axisLine: { lineStyle: { color: '#23262d' } }, axisTick: { show: false } },
    yAxis: { type: 'value', scale: true, axisLabel: { color: '#9aa0a8', fontSize: 11 },
             splitLine: { lineStyle: { color: '#1c1f26' } } },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 4,
                 borderColor: '#23262d', textStyle: { color: '#9aa0a8' } }],
    series: [{
      type: 'line', data: pes, showSymbol: false, connectNulls: true,
      lineStyle: { width: 1.4, color: '#5b8ff9' },
      areaStyle: { color: 'rgba(91,143,249,0.10)' },
      markLine: last ? {
        symbol: 'none', silent: true,
        lineStyle: { color: '#e6534e', type: 'dashed', width: 1 },
        label: { color: '#e6534e', formatter: '当前 ' + last },
        data: [{ yAxis: last }],
      } : undefined,
    }],
  }, true)
}

onMounted(async () => {
  if (peChart.value) chart = echarts.init(peChart.value)
  try {
    const { data } = await http.get('/valuation/presets')
    presets.value = data.items
  } catch { /* 预设拉不到也能手输 */ }
  load()
})
onBeforeUnmount(() => { chart?.dispose(); chart = null })
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 8px; }
.cards { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px; }
.cards .stat-card { flex: 1; min-width: 150px; }
.v.small { font-size: 17px; }
.pe-chart { height: 340px; background: #14161a; border: 1px solid #23262d; border-radius: 8px; }
</style>
