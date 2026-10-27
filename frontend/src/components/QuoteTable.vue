<template>
  <el-table
    :data="rows"
    size="small"
    highlight-current-row
    style="width: 100%"
    @row-click="(row: Row) => emit('select', row.code)"
    @row-dblclick="(row: Row) => emit('dblclick', row.code)"
  >
    <el-table-column label="名称" min-width="86">
      <template #default="{ row }">
        <div class="nm" :title="`${row.name || row.code}（${row.code}）`">
          <span class="name">{{ row.name || row.code }}</span>
          <span class="muted code">{{ row.code }}</span>
        </div>
      </template>
    </el-table-column>
    <el-table-column label="现价" width="66" align="right">
      <template #default="{ row }"><span :style="{ color: c(row) }">{{ n(row.price) }}</span></template>
    </el-table-column>
    <el-table-column label="涨跌幅" width="80" align="right">
      <template #default="{ row }"><span :style="{ color: c(row) }">{{ pct(row.pct) }}</span></template>
    </el-table-column>
    <el-table-column v-if="deletable" width="34" align="center">
      <template #default="{ row }">
        <el-button link type="danger" size="small" @click.stop="emit('remove', row.code)">✕</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { type Quote, pctColor, fmtPct, fmtNum } from '../types'

interface Row extends Partial<Quote> { code: string; name?: string; price?: number }

const props = defineProps<{ items: { code: string; name?: string; quote?: Quote | null }[]; deletable?: boolean }>()
const emit = defineEmits<{ select: [code: string]; remove: [code: string]; dblclick: [code: string] }>()

const rows = computed<Row[]>(() =>
  props.items.map((it) => ({ ...(it.quote || {}), code: it.code, name: it.name || it.quote?.name }) as Row))

function c(row: Row): string { return pctColor(row.pct) }
function n(v?: number | null): string { return fmtNum(v) }
function pct(v?: number | null): string { return fmtPct(v) }
</script>

<style scoped>
.name {
  display: block; font-weight: 500;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.code { display: block; font-size: 10px; white-space: nowrap; }
.nm { line-height: 1.25; }
:deep(.el-table__row) { cursor: pointer; }
</style>
