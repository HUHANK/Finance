<template>
  <div ref="el" class="timeline"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { type TimelineData, fmtPct } from '../types'

const props = defineProps<{ data: TimelineData | null }>()
const el = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let ro: ResizeObserver | null = null

const UP = '#e6534e'
const DOWN = '#2ea36b'

function render() {
  if (!chart) return
  const d = props.data
  if (!d || !d.points.length) {
    chart.clear()
    return
  }
  const times = d.points.map((p) => p.time.slice(0, 2) + ':' + p.time.slice(2))
  const prices = d.points.map((p) => p.price)
  const base = d.last_close ?? prices[0]
  const rising = prices[prices.length - 1] >= base
  const color = rising ? UP : DOWN
  const chgPct = base ? (prices[prices.length - 1] / base - 1) * 100 : 0

  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 58, right: 58, top: 16, bottom: 26 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1c1f26', borderColor: '#33363d',
      textStyle: { color: '#e8e8e8', fontSize: 12 },
      formatter: (params: any) => {
        const p = params[0]
        const v = p.value as number
        const pct = base ? ((v / base - 1) * 100) : 0
        const c = v >= base ? UP : DOWN
        return `${p.name}<br/>价 <b style="color:${c}">${v.toFixed(2)}</b> ` +
               `<span style="color:${c}">${fmtPct(pct)}</span>`
      },
    },
    xAxis: {
      type: 'category', data: times, boundaryGap: false,
      axisLabel: { color: '#9aa0a8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#23262d' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value', scale: true, position: 'right',
      axisLabel: {
        color: '#9aa0a8', fontSize: 11,
        formatter: (v: number) => v.toFixed(2),
      },
      splitLine: { lineStyle: { color: '#1c1f26' } },
    },
    series: [
      {
        type: 'line', data: prices, showSymbol: false, connectNulls: true,
        lineStyle: { width: 1.4, color },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: color + '33' }, { offset: 1, color: color + '05' },
          ]),
        },
        markLine: {
          symbol: 'none', silent: true,
          lineStyle: { color: '#888', type: 'dashed', width: 1 },
          label: { color: '#9aa0a8', formatter: () => '昨收 ' + base.toFixed(2) },
          data: [{ yAxis: base }],
        },
      },
    ],
  }, true)
}

onMounted(() => {
  if (!el.value) return
  chart = echarts.init(el.value)
  render()
  // 容器尺寸变化（如弹窗打开动画）时自适应，否则 ECharts 会定格在初始 0 尺寸
  ro = new ResizeObserver(() => { chart?.resize() })
  ro.observe(el.value)
})
watch(() => props.data, render)
onBeforeUnmount(() => {
  ro?.disconnect()
  ro = null
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.timeline { width: 100%; height: 100%; min-height: 380px; }
</style>
