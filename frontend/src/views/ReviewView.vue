<template>
  <div>
    <div class="toolbar">
      <el-select v-model="date" size="small" style="width: 150px" @change="load">
        <el-option v-for="d in dates" :key="d" :value="d" :label="d" />
      </el-select>
      <el-button size="small" type="primary" :loading="refreshing" @click="refresh">
        生成/刷新最新
      </el-button>
      <span class="muted" v-if="snap">生成于 {{ snap.generated_at }}</span>
    </div>

    <el-alert v-if="!snap" type="info" :closable="false"
              :title="`${date} 暂无快照，点上方按钮生成（数据源只支持最近 10 个交易日）`" />

    <template v-if="snap">
      <!-- 大盘近 5 日 -->
      <div class="cards">
        <div v-for="m in snap.market" :key="m.code" class="stat-card">
          <div class="k">{{ m.name }} <span class="muted">{{ m.date }}</span></div>
          <div class="v" :style="{ color: cc(m.chg5d) }">{{ m.close?.toFixed(2) }}</div>
          <div :style="{ color: cc(m.chg5d) }">近5日 {{ fmtPct(m.chg5d) }}</div>
        </div>
      </div>

      <!-- 涨停情绪 -->
      <div class="section-title">涨停情绪</div>
      <el-alert v-if="!snap.sentiment" type="warning" :closable="false" title="情绪数据缺失" />
      <template v-else>
        <div class="cards">
          <div class="stat-card"><div class="k">涨停</div><div class="v up">{{ s.zt }}</div></div>
          <div class="stat-card"><div class="k">炸板</div><div class="v down">{{ s.zb }}</div></div>
          <div class="stat-card"><div class="k">跌停</div><div class="v down">{{ s.dt }}</div></div>
          <div class="stat-card"><div class="k">炸板率</div><div class="v">{{ s.break_rate }}%</div></div>
          <div class="stat-card"><div class="k">最高连板</div><div class="v up">{{ s.max_height }}板</div></div>
        </div>
        <div class="row2">
          <div class="half">
            <div class="muted" style="margin-bottom:6px">连板梯队</div>
            <el-tag v-for="(n, h) in s.ladder" :key="h" class="ladder-tag"
                    :type="Number(h) >= 3 ? 'danger' : Number(h) === 2 ? 'warning' : 'info'">
              {{ h }}板 × {{ n }}
            </el-tag>
          </div>
          <div class="half">
            <div class="muted" style="margin-bottom:6px">涨停行业聚集 TOP8</div>
            <div v-for="(n, hy) in s.zt_industry" :key="hy" class="hy-row">
              <span class="hy-name">{{ hy }}</span>
              <el-progress :percentage="indPct(n)" :show-text="false" :stroke-width="8"
                           color="#e6534e" class="hy-bar" />
              <span class="muted">{{ n }}</span>
            </div>
          </div>
        </div>
        <QuoteTable :items="stockItems(s.zt_stocks)" style="max-width: 720px" />
      </template>

      <!-- 板块资金流 -->
      <div class="section-title">板块主力资金（5 日净额）</div>
      <el-alert v-if="!snap.board_flow" type="warning" :closable="false" title="资金流数据缺失" />
      <el-tabs v-else v-model="flowTab">
        <el-tab-pane label="行业" name="industry">
          <FlowTable :items="snap.board_flow.industry" />
        </el-tab-pane>
        <el-tab-pane label="概念" name="concept">
          <FlowTable :items="snap.board_flow.concept" />
        </el-tab-pane>
      </el-tabs>

      <!-- ETF 份额变动 -->
      <div class="section-title">
        沪市 ETF 份额变动
        <span class="muted" v-if="snap.etf_delta">
          数据日 {{ snap.etf_delta.date }} · 对比 {{ snap.etf_delta.prev_date || '-' }}
          · 共 {{ snap.etf_delta.total }} 只有变动
        </span>
      </div>
      <el-alert v-if="!snap.etf_delta" type="warning" :closable="false"
                title="份额数据缺失（交易所发布有延迟，次日再试）" />
      <el-table v-else :data="snap.etf_delta.items" size="small" style="max-width: 760px">
        <el-table-column prop="code" label="代码" width="90" />
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column label="份额变动(万份)" width="140" align="right">
          <template #default="{ row }">
            <span :style="{ color: cc(row.d_wan) }">{{ fmtSigned(row.d_wan) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="估算流入(亿)" width="130" align="right">
          <template #default="{ row }">
            <span :style="{ color: cc(row.amt_yi) }">{{ fmtSigned(row.amt_yi) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="现价" width="90" align="right">
          <template #default="{ row }">{{ row.price ?? '-' }}</template>
        </el-table-column>
      </el-table>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import QuoteTable from '../components/QuoteTable.vue'
import FlowTable from '../components/FlowTable.vue'
import { http, errMsg } from '../api/client'
import { fmtPct, pctColor } from '../types'

interface Snapshot {
  date: string
  generated_at: string
  market: { code: string; name: string; date: string; close: number; chg5d: number }[]
  sentiment: null | {
    zt: number; zb: number; dt: number; break_rate: number; max_height: number
    ladder: Record<string, number>
    zt_industry: Record<string, number>
    zt_stocks: { code: string; name: string; lbc: number; hybk: string; first_time: string }[]
  }
  board_flow: null | { industry: any[]; concept: any[] }
  etf_delta: null | { date: string; prev_date: string | null; total: number;
                      items: { code: string; name: string; d_wan: number; price: number | null; amt_yi: number }[] }
}

const date = ref('')
const dates = ref<string[]>([])
const snap = ref<Snapshot | null>(null)
const refreshing = ref(false)
const flowTab = ref('industry')

const s = computed(() => snap.value?.sentiment || ({} as any))

function cc(v: number | null | undefined) { return pctColor(v) }
function fmtSigned(v: number | null | undefined) {
  if (v == null) return '-'
  return (v > 0 ? '+' : '') + v.toLocaleString('zh-CN')
}
function indPct(n: number) {
  const max = Math.max(...Object.values(s.value.zt_industry || { 0: 1 }))
  return Math.round((n / (max || 1)) * 100)
}
function stockItems(stocks: any[]) {
  return (stocks || []).map((x) => ({ code: x.code, name: `${x.name}（${x.lbc}板 · ${x.hybk}）` }))
}

async function load() {
  try {
    const { data } = await http.get('/review', { params: date.value ? { date: date.value } : {} })
    snap.value = data.snapshot
    dates.value = data.dates
    date.value = data.date
    if (!data.dates.includes(data.date) && !data.snapshot) {
      // 保持 date 供刷新按钮使用
    }
  } catch (e) { ElMessage.error(errMsg(e)) }
}

async function refresh() {
  refreshing.value = true
  try {
    const { data } = await http.post('/review/refresh', {})
    snap.value = data.snapshot
    dates.value = data.dates
    date.value = data.date
    ElMessage.success('已生成 ' + data.date)
  } catch (e) { ElMessage.error(errMsg(e)) } finally { refreshing.value = false }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 8px; }
.cards { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px; }
.cards .stat-card { flex: 1; min-width: 130px; }
.row2 { display: flex; gap: 20px; margin-top: 12px; }
.half { flex: 1; min-width: 300px; }
.ladder-tag { margin-right: 6px; margin-bottom: 4px; }
.hy-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.hy-name { width: 90px; font-size: 12px; text-align: right; }
.hy-bar { flex: 1; max-width: 260px; }
</style>
