<template>
  <div>
    <div class="toolbar">
      <el-button size="small" type="primary" :loading="loading" @click="loadLatest">加载最新一期</el-button>
      <el-select v-model="date" size="small" style="width: 150px" @change="loadDate" clearable
                 placeholder="按日期回看">
        <el-option v-for="d in dates" :key="d" :value="d" :label="d" />
      </el-select>
      <span class="muted" v-if="date && items.length">{{ date }} 共 {{ items.length }} 条</span>
      <span class="muted" v-if="date && !items.length">该日未发布或暂未入库</span>
    </div>

    <el-row :gutter="12" class="news-body">
      <el-col :span="10">
        <div class="title-list">
          <div v-for="it in items" :key="it.idx" class="title-item"
               :class="{ active: it.idx === currentIdx }" @click="currentIdx = it.idx">
            <span class="no">{{ String(it.idx).padStart(2, '0') }}</span>{{ it.title }}
          </div>
        </div>
      </el-col>
      <el-col :span="14">
        <div class="content">
          <template v-if="current">
            <div class="ct">{{ current.title }}</div>
            <pre class="body">{{ current.content || '（正文缺失或已下架）' }}</pre>
            <el-link v-if="current.url" :href="current.url" target="_blank" type="primary" class="muted">
              视频原文 ↗
            </el-link>
          </template>
          <div v-else class="muted" style="padding: 40px; text-align: center">← 选择左侧条目阅读</div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http, errMsg } from '../api/client'

interface Item { idx: number; title: string; url: string; content: string | null }

const date = ref('')
const dates = ref<string[]>([])
const items = ref<Item[]>([])
const loading = ref(false)
const currentIdx = ref(0)
const current = computed(() => items.value.find((x) => x.idx === currentIdx.value))

async function loadDates() {
  try {
    const { data } = await http.get('/news/cctv/dates')
    dates.value = data.dates
  } catch { /* 首次为空正常 */ }
}

async function loadLatest() {
  loading.value = true
  try {
    const { data } = await http.get('/news/cctv/latest', { timeout: 120000 })
    items.value = data.items
    date.value = data.date || ''
    currentIdx.value = items.value.length ? items.value[0].idx : 0
    loadDates()
    if (!data.date) ElMessage.warning('近 4 天均未取到联播')
  } catch (e) { ElMessage.error(errMsg(e)) } finally { loading.value = false }
}

async function loadDate() {
  if (!date.value) return
  try {
    const { data } = await http.get('/news/cctv', { params: { date: date.value }, timeout: 120000 })
    items.value = data.items
    currentIdx.value = items.value.length ? items.value[0].idx : 0
  } catch (e) { ElMessage.error(errMsg(e)) }
}

onMounted(loadLatest)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 8px; }
.news-body { margin-top: 10px; }
.title-list {
  background: #14161a; border: 1px solid #23262d; border-radius: 8px;
  max-height: calc(100vh - 140px); overflow: auto;
}
.title-item {
  padding: 8px 12px; cursor: pointer; font-size: 13px; line-height: 1.5;
  border-bottom: 1px solid #1c1f26;
}
.title-item:hover { background: #1c1f26; }
.title-item.active { background: #1f2630; color: #5b8ff9; }
.title-item .no { color: var(--el-text-color-secondary); margin-right: 8px; }
.content {
  background: #14161a; border: 1px solid #23262d; border-radius: 8px;
  padding: 16px 18px; max-height: calc(100vh - 140px); overflow: auto;
}
.ct { font-size: 16px; font-weight: 600; margin-bottom: 12px; }
.body {
  white-space: pre-wrap; font-family: inherit; font-size: 14px; line-height: 1.9;
  margin: 0 0 12px; color: var(--el-text-color-regular);
}
</style>
