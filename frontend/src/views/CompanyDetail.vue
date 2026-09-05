<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiWorkspace } from '@/api'

const route = useRoute()
const router = useRouter()
const companyId = Number(route.params.id)
const company = ref<any>(null)
const positions = ref<any[]>([])
const applications = ref<any[]>([])
const loading = ref(false)
const error = ref('')
const showCreate = ref(false)
const newPosition = ref({ title: '', jd_raw: '' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [c, ps, apps] = await Promise.all([apiWorkspace.companies.list(), apiWorkspace.positions.list(companyId), apiWorkspace.applications.list()])
    company.value = c.find((x: any) => x.id === companyId) || null
    positions.value = ps
    applications.value = apps.filter((a: any) => a.company?.id === companyId)
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => route.params.id, () => {
  // 简单刷新
  load()
})

async function createPosition() {
  if (!newPosition.value.title.trim()) return
  try {
    await apiWorkspace.positions.create({ company_id: companyId, title: newPosition.value.title, jd_raw: newPosition.value.jd_raw, jd_structured: {} })
    showCreate.value = false
    newPosition.value = { title: '', jd_raw: '' }
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

function stageLabel(idx: number) {
  const labels = ['投递', '测评', '笔试', '简历评估', '一面', '二面', '三面', 'HR面', 'Offer评估', 'Offer']
  return labels[idx] || String(idx)
}
</script>

<template>
  <div class="max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-5">
      <div>
        <button class="text-sm text-primary-600 hover:underline mb-1" @click="router.push('/workspace')">← 返回工作台</button>
        <h2 class="text-2xl font-bold">{{ company?.name || '公司详情' }}</h2>
        <p class="text-sm text-slate-500">{{ company?.industry }} <span v-if="company?.website">· {{ company.website }}</span></p>
      </div>
      <button class="btn-primary text-xs" @click="showCreate = !showCreate">＋ 新增岗位</button>
    </div>

    <div v-if="error" class="mb-3 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">{{ error }}</div>

    <!-- 新增岗位 -->
    <div v-if="showCreate" class="card mb-4 border-primary-200">
      <div class="space-y-3">
        <input v-model="newPosition.title" class="input" placeholder="岗位名称 *" />
        <textarea v-model="newPosition.jd_raw" rows="4" class="input font-mono text-xs" placeholder="JD 快照（可选，粘贴原始 JD）" />
      </div>
      <div class="mt-3 flex justify-end gap-2">
        <button class="btn-secondary text-xs" @click="showCreate = false">取消</button>
        <button class="btn-primary text-xs" @click="createPosition" :disabled="!newPosition.title.trim()">创建</button>
      </div>
    </div>

    <!-- 岗位列表 -->
    <div class="space-y-3" v-if="!loading">
      <div v-for="p in positions" :key="p.id" class="card cursor-pointer hover:border-primary-300 transition-colors" @click="router.push(`/positions/${p.id}`)">
        <div class="flex items-center justify-between">
          <div class="font-semibold">{{ p.title }}</div>
          <div class="flex items-center gap-2 text-xs">
            <span v-if="p.jd_raw" class="text-slate-400" title="含 JD 快照">📋</span>
            <span class="text-primary-600">查看投递 →</span>
          </div>
        </div>
        <div v-if="applications.filter(a => a.position?.id === p.id).length" class="mt-2">
          <span v-for="ap in applications.filter(a => a.position?.id === p.id)" :key="ap.id" class="badge mr-1 bg-primary-50 text-primary-700">
            第 {{ ap.current_stage + 1 }} 阶段：{{ stageLabel(ap.current_stage) }}
          </span>
        </div>
      </div>
      <p v-if="!positions.length" class="text-center text-slate-400 py-8">暂无岗位，点击右上角「新增岗位」</p>
    </div>
    <div v-else class="text-center py-10 text-slate-400">加载中…</div>
  </div>
</template>