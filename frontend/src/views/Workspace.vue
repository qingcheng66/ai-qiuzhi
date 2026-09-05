<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiResume, apiWorkspace } from '@/api'

const router = useRouter()
const activeWorkspaceView = ref<'resumes' | 'companies'>('resumes')
const resumes = ref<any[]>([])
const selectedResume = ref<any>(null)
const mockInterviewData = ref<any>(null)
const isGeneratingMock = ref(false)

const companies = ref<any[]>([])
const stats = ref<any>(null)
const loading = ref(false)
const error = ref('')
const showCreate = ref(false)
const newCompany = ref({ name: '', website: '', industry: '' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [cs, st, rList] = await Promise.all([
      apiWorkspace.companies.list(),
      apiWorkspace.stats(),
      apiResume.list(),
    ])
    companies.value = cs
    stats.value = st
    resumes.value = rList
    if (rList.length && !selectedResume.value) {
      selectedResume.value = rList[0]
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function create() {
  if (!newCompany.value.name.trim()) return
  try {
    await apiWorkspace.companies.create(newCompany.value)
    showCreate.value = false
    newCompany.value = { name: '', website: '', industry: '' }
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

function stageLabel(stage: string | number) {
  return String(stage).includes(':') ? String(stage).split(':')[1] : String(stage)
}
function stageIndex(k: string) {
  return parseInt(String(k).split(':')[0] || '0', 10)
}

async function handleGenerateMock(rId: number) {
  isGeneratingMock.value = true
  error.value = ''
  try {
    mockInterviewData.value = await apiResume.mockInterview(rId)
  } catch (e: any) {
    error.value = '生成押题失败：' + e.message
  } finally {
    isGeneratingMock.value = false
  }
}

const isUpdatingStage = ref(false)
const STAGES = ['投递', '测评', '笔试', '初筛', '一面', '二面', '三面', 'HR面', '评估', 'Offer']

const currentResumeStage = computed(() => {
  return selectedResume.value?.content?.current_stage ?? 0
})

async function handleSetStage(stageIdx: number) {
  if (!selectedResume.value) return
  if (stageIdx < 0 || stageIdx >= STAGES.length) return
  isUpdatingStage.value = true
  try {
    await apiResume.setStage(selectedResume.value.id, stageIdx)
    if (!selectedResume.value.content) selectedResume.value.content = {}
    selectedResume.value.content.current_stage = stageIdx
  } catch (e: any) {
    error.value = '更新阶段失败：' + e.message
  } finally {
    isUpdatingStage.value = false
  }
}

function selectResume(r: any) {
  selectedResume.value = r
  mockInterviewData.value = null
}
</script>

<template>
  <div class="max-w-6xl mx-auto">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-2xl font-bold text-slate-800">求职专属作战室</h2>
        <p class="text-sm text-slate-500">以每份定制简历为核心的作战看板、投递推进与专属 AI 押题</p>
      </div>

      <!-- 视图切换：简历专属作战室 vs 公司维度看板 -->
      <div class="flex items-center gap-2">
        <div class="bg-slate-100 p-0.5 rounded-lg flex text-xs font-medium">
          <button
            class="px-3 py-1.5 rounded-md transition"
            :class="activeWorkspaceView === 'resumes' ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
            @click="activeWorkspaceView = 'resumes'"
          >
            📋 简历专属作战室
          </button>
          <button
            class="px-3 py-1.5 rounded-md transition"
            :class="activeWorkspaceView === 'companies' ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
            @click="activeWorkspaceView = 'companies'"
          >
            🏢 公司与岗位维度
          </button>
        </div>
        <button class="btn-secondary text-xs !py-1.5" @click="load()">刷新</button>
      </div>
    </div>

    <div v-if="error" class="mb-3 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">{{ error }}</div>

    <!-- ================= 视图 A: 简历专属作战室 (Resume-Centric War Room) ================= -->
    <div v-if="activeWorkspaceView === 'resumes'" class="space-y-4">
      <div v-if="!resumes.length" class="text-center py-16 bg-white rounded-2xl border border-slate-200">
        <div class="text-3xl mb-2">📑</div>
        <div class="font-bold text-slate-700">暂无任何已保存的简历</div>
        <div class="text-xs text-slate-400 mt-1 mb-4">前往简历制作台生成或微调一份简历后，将在这里建立专属作战舱</div>
        <button class="btn-primary text-xs" @click="router.push('/generate')">立刻制作简历 →</button>
      </div>

      <div v-else class="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <!-- 左侧 4 列：简历列表卡片 -->
        <div class="lg:col-span-4 space-y-3">
          <div class="flex items-center justify-between px-1">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">简历档案 ({{ resumes.length }})</span>
            <button class="text-xs text-primary-600 hover:underline" @click="router.push('/generate')">+ 制作新简历</button>
          </div>

          <div
            v-for="r in resumes"
            :key="r.id"
            class="p-4 rounded-xl border transition-all cursor-pointer bg-white"
            :class="selectedResume?.id === r.id
              ? 'border-primary-500 ring-2 ring-primary-100 shadow-sm'
              : 'border-slate-200 hover:border-slate-300 hover:shadow-2xs'"
            @click="selectResume(r)"
          >
            <div class="flex items-start justify-between gap-2">
              <h4 class="font-bold text-sm text-slate-800 line-clamp-1">{{ r.title || '未命名简历' }}</h4>
              <span class="text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0"
                :class="r.status === 'final' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-amber-50 text-amber-700 border border-amber-200'">
                {{ r.status === 'final' ? '已定稿' : '草稿' }}
              </span>
            </div>

            <div class="mt-2 text-xs text-slate-500 flex items-center justify-between">
              <span>{{ r.content?.basics?.label || '通用候选人' }}</span>
              <span class="text-slate-400">{{ r.updated_at ? r.updated_at.replace('T', ' ').slice(0, 10) : '' }}</span>
            </div>

            <div v-if="r.position_id" class="mt-2.5 pt-2 border-t border-slate-100 flex items-center gap-1.5 text-[11px] text-emerald-700">
              <span>🎯 关联岗位 ID: {{ r.position_id }}</span>
            </div>
          </div>
        </div>

        <!-- 右侧 8 列：当前选中简历的专属作战舱 -->
        <div v-if="selectedResume" class="lg:col-span-8 space-y-4">
          <!-- 舱体 Header -->
          <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-2xs">
            <div class="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h3 class="font-bold text-lg text-slate-800">{{ selectedResume.title }}</h3>
                <p class="text-xs text-slate-400 mt-0.5">
                  候选人：{{ selectedResume.content?.basics?.name || '未命名' }} · {{ selectedResume.content?.basics?.label || '' }}
                </p>
              </div>
              <div class="flex items-center gap-2">
                <button
                  class="btn-secondary !text-xs !py-1.5"
                  @click="router.push(`/generate?resume_id=${selectedResume.id}&step=3`)"
                >
                  ✏️ 进入微调编辑
                </button>
                <button
                  class="btn-primary !text-xs !py-1.5"
                  :disabled="isGeneratingMock"
                  @click="handleGenerateMock(selectedResume.id)"
                >
                  {{ isGeneratingMock ? '生成中…' : '🎯 针对该简历 AI 押题' }}
                </button>
              </div>
            </div>

            <!-- 10 阶段求职推进流转 (交互式实时同步) -->
            <div class="mt-4">
              <div class="text-xs font-bold text-slate-700 mb-2.5 flex items-center justify-between">
                <span class="flex items-center gap-1.5">
                  <span>求职推进链路 (点击任意节点直接流转)</span>
                  <span v-if="isUpdatingStage" class="text-primary-600 font-normal">正在保存…</span>
                </span>
                <div class="flex items-center gap-2">
                  <span class="text-[11px] text-primary-600 font-medium">
                    当前阶段：{{ STAGES[currentResumeStage] }} ({{ currentResumeStage + 1 }}/10)
                  </span>
                  <button
                    class="px-2 py-0.5 text-[11px] rounded border border-slate-200 hover:bg-slate-50 text-slate-600 disabled:opacity-40"
                    :disabled="currentResumeStage === 0 || isUpdatingStage"
                    @click="handleSetStage(currentResumeStage - 1)"
                  >
                    ← 上一阶
                  </button>
                  <button
                    class="px-2 py-0.5 text-[11px] rounded bg-primary-50 border border-primary-200 text-primary-700 hover:bg-primary-100 font-medium disabled:opacity-40"
                    :disabled="currentResumeStage >= STAGES.length - 1 || isUpdatingStage"
                    @click="handleSetStage(currentResumeStage + 1)"
                  >
                    推进下一阶 →
                  </button>
                </div>
              </div>

              <div class="grid grid-cols-5 sm:grid-cols-10 gap-1.5 text-center">
                <button
                  v-for="(stName, idx) in STAGES"
                  :key="idx"
                  class="p-2 rounded-xl border text-[11px] transition-all relative flex flex-col items-center justify-center cursor-pointer"
                  :class="idx < currentResumeStage
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200 font-medium hover:bg-emerald-100'
                    : (idx === currentResumeStage
                      ? 'bg-primary-600 text-white font-bold border-primary-600 shadow-md ring-2 ring-primary-200 scale-102 z-10'
                      : 'bg-slate-50 text-slate-400 border-slate-100 hover:bg-slate-100 hover:text-slate-600')"
                  @click="handleSetStage(idx)"
                >
                  <div class="text-[9px] opacity-70 mb-0.5 flex items-center gap-0.5">
                    <span v-if="idx < currentResumeStage">✓</span>
                    <span v-else-if="idx === currentResumeStage" class="w-1.5 h-1.5 rounded-full bg-amber-300 animate-ping inline-block mr-0.5"></span>
                    <span>{{ idx + 1 }}</span>
                  </div>
                  <div class="truncate font-medium">{{ stName }}</div>
                </button>
              </div>
            </div>
          </div>

          <!-- AI 针对该简历版本专属押题结果面板 -->
          <div v-if="mockInterviewData" class="bg-white rounded-2xl border border-indigo-100 shadow-sm p-5 space-y-3">
            <div class="flex items-center justify-between pb-3 border-b border-indigo-50">
              <div class="flex items-center gap-2">
                <span class="text-lg">🤖</span>
                <h4 class="font-bold text-sm text-slate-800">
                  基于本简历定制的面试高频挖掘题 (针对 {{ mockInterviewData.position_title }})
                </h4>
              </div>
              <span class="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full font-bold">
                {{ mockInterviewData.questions?.length }} 道精选挖掘题
              </span>
            </div>

            <div class="space-y-3 pt-1">
              <div
                v-for="(q, i) in mockInterviewData.questions"
                :key="i"
                class="p-3.5 rounded-xl bg-slate-50/80 border border-slate-200/80 space-y-1.5"
              >
                <div class="flex items-center gap-2">
                  <span class="text-[10px] bg-primary-100 text-primary-800 px-1.5 py-0.5 rounded font-semibold">{{ q.category }}</span>
                  <div class="font-bold text-xs text-slate-800 leading-snug">Q{{ i + 1 }}: {{ q.question }}</div>
                </div>
                <div class="text-xs text-slate-600 bg-white p-2 rounded-lg border border-slate-100 leading-relaxed font-sans mt-1">
                  <strong class="text-indigo-600">💡 回答破题锦囊 (STAR)：</strong> {{ q.star_hint }}
                </div>
              </div>
            </div>
          </div>

          <!-- 简历基本档案详情 -->
          <div class="bg-white rounded-2xl border border-slate-200 p-5 space-y-3">
            <h4 class="font-bold text-xs text-slate-500 uppercase tracking-wider">经历快照</h4>
            <div class="space-y-2">
              <div v-for="proj in (selectedResume.content?.projects || []).slice(0, 3)" :key="proj.name" class="p-3 bg-slate-50 rounded-xl">
                <div class="font-semibold text-xs text-slate-800">{{ proj.name }}</div>
                <div class="text-xs text-slate-500 mt-1 line-clamp-2">{{ proj.description }}</div>
              </div>
              <div v-if="!selectedResume.content?.projects?.length" class="text-xs text-slate-400 py-2">
                该简历暂无项目记录，点击上方「进入微调编辑」完善。
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ================= 视图 B: 公司与岗位维度 (Company Board) ================= -->
    <div v-else class="space-y-4">
      <!-- 统计面板 -->
      <div v-if="stats" class="grid grid-cols-4 gap-3 mb-4">
        <div class="card">
          <div class="text-xs text-slate-400">总投递</div>
          <div class="text-2xl font-bold text-slate-800">{{ stats.total_applications }}</div>
        </div>
        <div class="card">
          <div class="text-xs text-slate-400">进行中</div>
          <div class="text-2xl font-bold text-primary-600">{{ stats.active_applications }}</div>
        </div>
        <div class="card">
          <div class="text-xs text-slate-400">Offer</div>
          <div class="text-2xl font-bold text-green-600">{{ stats.offers }}</div>
        </div>
        <div class="card">
          <div class="text-xs text-slate-400">Offer 转化率</div>
          <div class="text-2xl font-bold text-amber-600">{{ (stats.offer_rate * 100).toFixed(0) }}%</div>
        </div>
      </div>


    <!-- 阶段分布 -->
    <div v-if="stats" class="card mb-6">
      <h3 class="font-medium text-sm mb-3">各阶段分布</h3>
      <div class="flex flex-wrap gap-x-4 gap-y-2">
        <div v-for="(count, stageKey) in stats.by_stage" :key="stageKey" class="text-xs flex items-center gap-1">
          <span class="w-2 h-2 rounded-full" :class="count > 0 ? 'bg-primary-500' : 'bg-slate-200'" />
          <span class="text-slate-500">{{ stageLabel(stageKey) }}</span>
          <span class="font-medium" :class="count > 0 ? 'text-slate-800' : 'text-slate-300'">{{ count }}</span>
        </div>
      </div>
    </div>

    <!-- 新增公司 -->
    <div v-if="showCreate" class="card mb-4 border-primary-200">
      <div class="grid md:grid-cols-3 gap-3">
        <input v-model="newCompany.name" class="input" placeholder="公司名 *" />
        <input v-model="newCompany.website" class="input" placeholder="网站" />
        <input v-model="newCompany.industry" class="input" placeholder="行业" />
      </div>
      <div class="mt-3 flex justify-end gap-2">
        <button class="btn-secondary text-xs" @click="showCreate = false">取消</button>
        <button class="btn-primary text-xs" @click="create" :disabled="!newCompany.name.trim()">创建</button>
      </div>
    </div>

    <!-- 公司列表 -->
    <div class="space-y-3" v-if="!loading">
      <div v-for="c in companies" :key="c.id" class="card cursor-pointer hover:border-primary-300 transition-colors" @click="router.push(`/companies/${c.id}`)">
        <div class="flex items-center justify-between">
          <div>
            <div class="font-semibold text-lg">{{ c.name }}</div>
            <div class="text-xs text-slate-400">{{ c.industry }} <span v-if="c.website">· {{ c.website }}</span></div>
          </div>
          <div class="text-primary-600 text-sm">查看岗位 →</div>
        </div>
      </div>
      <p v-if="!companies.length" class="text-center text-slate-400 py-10">暂无公司，点击右上角「新增公司」开始</p>
    </div>
    <div v-else class="text-center py-10 text-slate-400">加载中…</div>
    </div>
  </div>
</template>