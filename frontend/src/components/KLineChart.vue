<template>
  <div ref="el" class="kline"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { init, dispose } from 'klinecharts'
import type { DataLoader } from 'klinecharts'
import { type Bar } from '../types'

const props = defineProps<{ bars: Bar[] }>()
const el = ref<HTMLElement>()
let chart: ReturnType<typeof init> | null = null

const UP = '#e6534e'
const DOWN = '#2ea36b'

function toKLine(b: Bar) {
  return {
    timestamp: new Date(b.date + ' 15:00:00').getTime(),
    open: b.open, high: b.high, low: b.low, close: b.close, volume: b.volume,
  }
}

// klinecharts v10 数据装载：setDataLoader 会触发一次 init 加载，
// 之后 props.bars 变化时重新 setDataLoader 即可整体替换数据。
function makeLoader(): DataLoader {
  return {
    getBars: (params) => {
      params.callback(props.bars.map(toKLine), { backward: false, forward: false })
    },
  }
}

onMounted(() => {
  if (!el.value) return
  chart = init(el.value, {
    styles: {
      grid: { horizontal: { color: '#23262d' }, vertical: { show: false } },
      candle: {
        bar: {
          upColor: UP, downColor: DOWN, noChangeColor: '#888',
          upWickColor: UP, downWickColor: DOWN, noChangeWickColor: '#888',
        },
        priceMark: {
          high: { color: '#9aa0a8' }, low: { color: '#9aa0a8' },
          last: { upColor: UP, downColor: DOWN, noChangeColor: '#888' },
        },
        tooltip: { text: { upColor: UP, downColor: DOWN, noChangeColor: '#888' } },
      },
      indicator: {
        bars: [{ upColor: UP, downColor: DOWN, noChangeColor: '#888' }],
        tooltip: { text: { upColor: UP, downColor: DOWN, noChangeColor: '#888' } },
        lines: [{ colors: ['#5b8ff9', '#f5a623', '#2ea36b', '#b06df1', '#e6534e'] }],
      },
      axis: { tickText: { color: '#9aa0a8' }, line: { color: '#23262d' } },
      separator: { color: '#23262d' },
      crosshair: {
        horizontal: { line: { color: '#555' }, text: { backgroundColor: '#33363d' } },
        vertical: { line: { color: '#555' }, text: { backgroundColor: '#33363d' } },
      },
    },
  })
  if (!chart) return
  // v10 必须先有有效 symbol/period，getBars 才会被触发
  chart.setSymbol({ ticker: 'CUSTOM', pricePrecision: 3, volumePrecision: 0 })
  chart.setPeriod({ type: 'day', span: 1 })
  chart.createIndicator({ name: 'MA', calcParams: [5, 10, 20], paneId: 'candle_pane' }, true)
  chart.createIndicator('VOL')
  chart.setDataLoader(makeLoader())
})

watch(() => props.bars, () => {
  if (chart) chart.setDataLoader(makeLoader())
})

onBeforeUnmount(() => {
  if (el.value) dispose(el.value)
  chart = null
})
</script>

<style scoped>
.kline { width: 100%; height: 100%; min-height: 380px; }
</style>
