<template>
  <el-table :data="items" size="small" style="max-width: 760px">
    <el-table-column type="index" label="#" width="46" />
    <el-table-column prop="name" label="板块" min-width="120" />
    <el-table-column label="涨跌幅" width="90" align="right">
      <template #default="{ row }">
        <span :style="{ color: pctColor(row.pct) }">{{ fmtPct(row.pct) }}</span>
      </template>
    </el-table-column>
    <el-table-column label="主力净流入(亿)" width="140" align="right">
      <template #default="{ row }">
        <span :style="{ color: pctColor(row.main_net_yi) }">{{ fmtSigned(row.main_net_yi) }}</span>
      </template>
    </el-table-column>
    <el-table-column label="净占比" width="90" align="right">
      <template #default="{ row }">
        <span :style="{ color: pctColor(row.main_pct) }">
          {{ row.main_pct != null ? row.main_pct.toFixed(1) + '%' : '-' }}
        </span>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import { fmtPct, pctColor } from '../types'
defineProps<{ items: { name: string; pct: number | null; main_net_yi: number; main_pct: number | null }[] }>()

function fmtSigned(v: number | null | undefined) {
  if (v == null) return '-'
  return (v > 0 ? '+' : '') + v.toFixed(1)
}
</script>
