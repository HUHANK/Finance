<template>
  <div ref="el" class="dca-curve"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { type DcaCurvePoint, fmtPct, pctColor } from '../types'

const props = defineProps<{ curve: DcaCurvePoint[] }>()
const el = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let ro: ResizeObserver | null = null

const COST_COLOR = '#5b8ff9'
const VALUE_COLOR = '#e6534e'
const PRICE_COLOR = '#f2c03c'

function render() {
  if (!chart) return
  const curve = props.curve
  if (!curve || !curve.length) {
    chart.clear()
    return
  }
  const dates = curve.map((p) => p.date)
  const costs = curve.map((p) => p.cost)
  const values = curve.map((p) => p.value)
  const prices = curve.map((p) => p.price)
  const last = curve[curve.length - 1]
  const pct = last.cost ? (last.value / last.cost - 1) * 100 : 0

  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 70, right: 70, top: 40, bottom: 28 },
    legend: { textStyle: { color: '#9aa0a8' }, top: 8 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1c1f26', borderColor: '#33363d',
      textStyle: { color: '#e8e8e8', fontSize: 12 },
      formatter: (params: any) => {
        const idx = params?.[0]?.dataIndex ?? 0
        const p = curve[idx]
        if (!p) return ''
        const ret = p.cost ? (p.value / p.cost - 1) * 100 : 0
        const rows = params.map((item: any) =>
          `${item.marker}${item.seriesName}: ${Number(item.value).toFixed(2)}`)
        rows.push(`<span style="color:${pctColor(ret)}">收益率: ${fmtPct(ret)}</span>`)
        return `<div style="margin-bottom:2px">${p.date}</div>${rows.join('<br/>')}`
      },
    },
    xAxis: {
      type: 'category', data: dates, boundaryGap: false,
      axisLabel: { color: '#9aa0a8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#23262d' } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value', scale: true,
        axisLabel: { color: '#9aa0a8', fontSize: 11 },
        splitLine: { lineStyle: { color: '#1c1f26' } },
      },
      {
        type: 'value', scale: true, position: 'right',
        axisLabel: { color: PRICE_COLOR, fontSize: 11 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '累计投入', type: 'line', data: costs, showSymbol: false,
        lineStyle: { width: 1.4, color: COST_COLOR },
        itemStyle: { color: COST_COLOR },
      },
      {
        name: '持仓市值', type: 'line', data: values, showSymbol: false,
        lineStyle: { width: 1.6, color: VALUE_COLOR },
        itemStyle: { color: VALUE_COLOR },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: VALUE_COLOR + '33' }, { offset: 1, color: VALUE_COLOR + '05' },
          ]),
        },
      },
      {
        name: '价格(前复权)', type: 'line', data: prices, showSymbol: false, yAxisIndex: 1,
        lineStyle: { width: 1, color: PRICE_COLOR, type: 'dashed' },
        itemStyle: { color: PRICE_COLOR },
      },
    ],
    graphic: [
      {
        type: 'text', left: 8, top: 12,
        style: {
          text: '区间收益率 ' + fmtPct(pct),
          fill: pctColor(pct), fontSize: 13, fontWeight: 'bold',
        },
      },
    ],
  }, true)
}

onMounted(() => {
  if (!el.value) return
  chart = echarts.init(el.value)
  render()
  ro = new ResizeObserver(() => { chart?.resize() })
  ro.observe(el.value)
})
watch(() => props.curve, render)
onBeforeUnmount(() => {
  ro?.disconnect()
  ro = null
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.dca-curve { width: 100%; height: 420px; }
</style>
