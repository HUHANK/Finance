<template>
  <div>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="历史定投测试" name="backtest">
        <div class="form-row">
          <el-input v-model="code" size="small" placeholder="代码：600519 / sh000001 / 159994"
                    style="width: 240px" clearable @change="fetchName" />
          <span v-if="name" class="stock-name">{{ name }}</span>
          <el-date-picker v-model="startDate" type="date" value-format="YYYY-MM-DD"
                          placeholder="开始日期" size="small" style="width: 150px" />
          <span class="muted">至</span>
          <el-date-picker v-model="endDate" type="date" value-format="YYYY-MM-DD"
                          placeholder="结束日期" size="small" style="width: 150px" />
          <el-select v-model="period" size="small" style="width: 120px">
            <el-option label="每月定投" value="month" />
            <el-option label="每周定投" value="week" />
            <el-option label="每日定投" value="day" />
          </el-select>
          <el-input-number v-model="amount" :min="1" :step="100" size="small" controls-position="right" />
          <span class="muted">元/次</span>
          <el-button type="primary" size="small" :loading="loading" @click="runBacktest">生成收益曲线</el-button>
        </div>

        <el-alert v-if="error" type="error" :closable="false" :title="error" style="margin: 10px 0" />

        <template v-if="result">
          <div class="cards">
            <div class="stat-card">
              <div class="k">总投入</div>
              <div class="v small">{{ fmtMoney(result.summary.total_invested) }}</div>
              <div class="muted">{{ result.summary.invest_count }} 次买入</div>
            </div>
            <div class="stat-card">
              <div class="k">当前市值</div>
              <div class="v small">{{ fmtMoney(result.summary.final_value) }}</div>
              <div class="muted">期末 {{ result.end }}</div>
            </div>
            <div class="stat-card">
              <div class="k">收益</div>
              <div class="v small" :style="{ color: pctColor(result.summary.profit) }">
                {{ fmtMoney(result.summary.profit) }}</div>
            </div>
            <div class="stat-card">
              <div class="k">收益率</div>
              <div class="v small" :style="{ color: pctColor(result.summary.return_pct) }">
                {{ fmtPct(result.summary.return_pct) }}</div>
              <div class="muted">年化 {{ fmtPct(result.summary.annualized_pct) }}</div>
            </div>
          </div>
          <div class="chart-box">
            <DcaCurveChart :curve="result.curve" />
          </div>
        </template>
      </el-tab-pane>

      <el-tab-pane label="定投计划" name="plan">
        <el-empty description="待开发" />
      </el-tab-pane>
      <el-tab-pane label="定投对比" name="compare">
        <el-empty description="待开发" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import DcaCurveChart from '../components/DcaCurveChart.vue'
import { http, errMsg } from '../api/client'
import { type DcaBacktestResult, pctColor, fmtPct } from '../types'

const code = ref('')
const name = ref('')
const activeTab = ref('backtest')
const startDate = ref(defaultStart())
const endDate = ref(today())
const period = ref('month')
const amount = ref(1000)
const loading = ref(false)
const error = ref('')
const result = ref<DcaBacktestResult | null>(null)

function today(): string {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function pad(n: number): string { return String(n).padStart(2, '0') }
function defaultStart(): string {
  const d = new Date()
  d.setFullYear(d.getFullYear() - 1)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function fmtMoney(v: number): string {
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function fetchName() {
  const c = code.value.trim()
  if (!c) { name.value = ''; return }
  try {
    const { data } = await http.get('/quotes', { params: { codes: c } })
    const quotes = data.quotes || {}
    const first = Object.values(quotes)[0] as { name?: string } | undefined
    name.value = quotes[c]?.name || first?.name || ''
  } catch { name.value = '' }
}

async function runBacktest() {
  const c = code.value.trim()
  if (!c) { ElMessage.warning('请先输入股票代码'); return }
  if (!startDate.value || !endDate.value) { ElMessage.warning('请选择开始和结束日期'); return }
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.get('/dca/backtest', {
      params: { code: c, start: startDate.value, end: endDate.value, amount: amount.value, period: period.value },
    })
    result.value = data
    if (data.name) name.value = data.name
  } catch (e) { error.value = errMsg(e); result.value = null } finally { loading.value = false }
}
</script>

<style scoped>
.form-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.stock-name { color: #67c23a; font-size: 13px; font-weight: 600; }
.cards { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
.stat-card { flex: 1; min-width: 160px; }
.v.small { font-size: 17px; }
.chart-box {
  height: 440px; background: #14161a;
  border: 1px solid #23262d; border-radius: 8px; padding: 6px; margin-top: 12px;
}
</style>
