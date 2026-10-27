<template>
  <el-container class="layout">
    <el-aside width="172px" class="aside">
      <div class="logo">📈 Finance</div>
      <el-menu :default-active="route.path" router background-color="transparent">
        <el-menu-item index="/market"><el-icon><TrendCharts /></el-icon>盯盘</el-menu-item>
        <el-menu-item index="/us"><el-icon><Money /></el-icon>美股</el-menu-item>
        <el-menu-item index="/review"><el-icon><DataBoard /></el-icon>复盘</el-menu-item>
        <el-menu-item index="/valuation"><el-icon><Histogram /></el-icon>估值</el-menu-item>
        <el-menu-item index="/news"><el-icon><Document /></el-icon>新闻</el-menu-item>
        <el-menu-item index="/profile"><el-icon><Search /></el-icon>详情</el-menu-item>
      </el-menu>
      <div class="clock">{{ clock }}</div>
    </el-aside>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { TrendCharts, DataBoard, Histogram, Document, Search, Money } from '@element-plus/icons-vue'
import { isTradingTimeNow } from './types'

const route = useRoute()
const clock = ref('')
let timer: number | undefined

function tick() {
  const d = new Date()
  clock.value =
    d.toLocaleDateString('zh-CN') + ' ' + d.toLocaleTimeString('zh-CN', { hour12: false }) +
    (isTradingTimeNow() ? '  🟢 盘中' : '  ⚪ 休市')
}

onMounted(() => {
  tick()
  timer = window.setInterval(tick, 1000)
})
onUnmounted(() => window.clearInterval(timer))
</script>

<style>
html, body, #app { height: 100%; margin: 0; }
body {
  background: #101318;
  color: var(--el-text-color-primary);
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
}
.layout { height: 100vh; }
.aside {
  border-right: 1px solid #23262d;
  display: flex; flex-direction: column;
  background: #14161a;
}
.logo { padding: 16px 14px 10px; font-size: 17px; font-weight: 600; }
.clock { margin-top: auto; padding: 12px 14px; font-size: 12px; color: var(--el-text-color-secondary); }
.aside .el-menu { border-right: none; }
.main { padding: 12px 14px; overflow: auto; background: #101318; }

/* 通用小工具 */
.muted { color: var(--el-text-color-secondary); font-size: 12px; }
.up { color: #e6534e; }
.down { color: #2ea36b; }
.stat-card { background: #171a20; border: 1px solid #23262d; border-radius: 8px; padding: 12px 16px; }
.stat-card .k { font-size: 12px; color: var(--el-text-color-secondary); }
.stat-card .v { font-size: 22px; font-weight: 600; margin-top: 4px; }
.section-title { font-size: 14px; font-weight: 600; margin: 18px 0 8px; }
</style>
