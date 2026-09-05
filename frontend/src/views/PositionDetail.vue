<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiResume, apiTemplates, apiWorkspace, downloadBlob } from '@/api'

const route = useRoute()
const router = useRouter()
const positionId = Number(route.params.id)

const position = ref<any>(null)
const applications = ref<any[]>([])
const loading = ref(false)
const error = ref('')
const activeApp = ref<any>(null)

// 简历
const resume = ref<any>(null)
const resumeVersions = ref<any[]>([])
const exportLoading = ref(false)
const resumeMsg = ref('')

const STAGE_LABELS = ['投递', '测评', '笔试', '简历评估', '一面', '二面', '三面', 'HR面', 'Offer评估', 'Offer']
const stageIdx = computed(() => activeApp.value?.current_stage ?? 0)

async function loadResume() {
  const r = await apiResume.getByPosition(positionId)
  resume.value = r
  if (r) {
    resumeVersions.value = await apiResume.getVersions(r.id)
  } else {
    resumeVersions.value = []
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [ps, apps] = await Promise.all([apiWorkspace.positions.list(), apiWorkspace.applications.list()])
    position.value = ps.find((x: any) => x.id === positionId) || null
    applications.value = apps.filter((a: any) => a.position?.id === positionId)
    if (applications.value.length && !activeApp.value) {
      activeApp.value = applications.value[0]
    }
    await loadResume()
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)

function editResume() {
  if (resume.value) {
    router.push(`/generate?resume_id=${resume.value.id}&position_id=${positionId}`)
  } else {
    router.push(`/generate?position_id=${positionId}`)
  }
}

async function exportResume(format: 'html' | 'pdf' | 'docx') {
  if (!resume.value) return
  exportLoading.value = true
  try {
    const blob = await apiResume.export(resume.value.id, format)
    downloadBlob(blob, `resume-${resume.value.id}.${format}`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    exportLoading.value = false
  }
}

async function finalizeResume() {
  if (!resume.value) return
  try {
    await apiResume.finalize(resume.value.id, '定稿')
    resume.value.status = 'final'
    await loadResume()
    resumeMsg.value = '已标记定稿'
    setTimeout(() => (resumeMsg.value = ''), 3000)
  } catch (e: any) {
    error.value = e.message
  }
}

const showCreateApp = ref(false)
const newApp = ref({ applied_date: new Date().toISOString().slice(0, 10) })

async function createApplication() {
  try {
    const created = await apiWorkspace.applications.create({
      position_id: positionId,
      current_stage: 0,
      notes: '',
      applied_date: newApp.value.applied_date ? newApp.value.applied_date + 'T00:00:00' : null,
    })
    showCreateApp.value = false
    await load()
    activeApp.value = applications.value.find((a: any) => a.id === created.id) || null
  } catch (e: any) {
    error.value = e.message
  }
}

async function advance(target?: number) {
  if (!activeApp.value) return
  try {
    await apiWorkspace.applications.advance(activeApp.value.id, target)
    await load()
    activeApp.value = applications.value.find((a: any) => a.id === activeApp.value!.id) || null
  } catch (e: any) {
    error.value = e.message
  }
}

function stageStatus(idx: number): 'done' | 'active' | 'todo' {
  if (!activeApp.value) return 'todo'
  const stages = activeApp.value.stages || {}
  const key = ['applied', 'assessment', 'written_test', 'resume_review', 'interview_1', 'interview_2', 'interview_3', 'hr_interview', 'offer_eval', 'offer'][idx]
  const st2 = stages[key]
  if (!st2) return 'todo'
  if (st2.status === 'active') return 'active'
  if (st2.status === 'completed') return 'done'
  return 'todo'
}

// interviews
const interviewForm = ref({ stage_index: 4, type: '', date: '', interviewers: '', result: 'pending', feedback: '' })
const showInterviewForm = ref(false)

function openInterview(stageIdx: number) {
  interviewForm.value = { stage_index: stageIdx, type: '', date: new Date().toISOString().slice(0, 16), interviewers: '', result: 'pending', feedback: '' }
  showInterviewForm.value = true
}

async function saveInterview() {
  if (!activeApp.value) return
  try {
    await apiWorkspace.interviews.create({
      application_id: activeApp.value.id,
      stage_index: interviewForm.value.stage_index,
      type: interviewForm.value.type,
      date: interviewForm.value.date,
      interviewers: interviewForm.value.interviewers.split(',').map((s) => s.trim()).filter(Boolean),
      result: interviewForm.value.result,
      feedback: interviewForm.value.feedback,
    })
    showInterviewForm.value = false
    await load()
    activeApp.value = applications.value.find((a: any) => a.id === activeApp.value!.id) || null
  } catch (e: any) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-5">
      <div>
        <button class="text-sm text-primary-600 hover:underline mb-1" @click="router.push(`/companies/${position?.company_id || ''}`)">← 返回公司</button>
        <h2 class="text-2xl font-bold">{{ position?.title || '岗位详情' }}</h2>
        <p class="text-sm text-slate-500">{{ position?.jd_raw ? '含 JD 快照' : '无 JD 快照' }}</p>
      </div>
      <button class="btn-primary text-xs" @click="showCreateApp = !showCreateApp">＋ 新建投递</button>
    </div>

    <div v-if="error" class="mb-3 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">{{ error }}</div>

    <!-- 新建投递 -->
    <div v-if="showCreateApp" class="card mb-4 border-primary-200">
      <label class="label">投递日期</label>
      <input v-model="newApp.applied_date" type="date" class="input max-w-[200px]" />
      <div class="mt-3 flex justify-end gap-2">
        <button class="btn-secondary text-xs" @click="showCreateApp = false">取消</button>
        <button class="btn-primary text-xs" @click="createApplication">创建投递</button>
      </div>
    </div>

    <!-- 投递选择 -->
    <div v-if="applications.length" class="flex gap-2 mb-4 overflow-x-auto">
      <button
        v-for="a in applications"
        :key="a.id"
        class="px-3 py-1.5 rounded-lg text-xs whitespace-nowrap border"
        :class="activeApp?.id === a.id ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-slate-600 border-slate-200 hover:border-primary-300'"
        @click="activeApp = a"
      >
        投递 #{{ a.id }} · {{ STAGE_LABELS[a.current_stage] }}
      </button>
    </div>

    <!-- 针对本岗位的简历 -->
    <div class="card mb-4">
      <div class="flex items-center justify-between mb-2">
        <h3 class="font-medium text-sm">📄 针对本岗位的简历</h3>
        <button class="btn-primary !py-1 !text-xs" @click="editResume">
          {{ resume ? '编辑 / 重新生成' : '＋ 创建简历' }}
        </button>
      </div>

      <div v-if="resumeMsg" class="mb-2 p-2 rounded bg-green-50 border border-green-200 text-green-700 text-xs">{{ resumeMsg }}</div>

      <template v-if="resume">
        <div class="flex flex-wrap items-center gap-2 text-sm">
          <span class="font-medium">{{ resume.title }}</span>
          <span class="badge" :class="resume.status === 'final' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">
            {{ resume.status === 'final' ? '已定稿' : '草稿' }}
          </span>
          <span class="text-xs text-slate-400">更新于 {{ resume.updated_at?.replace('T', ' ').slice(0, 16) }}</span>
        </div>
        <div class="text-xs text-slate-500 mt-1">来源：{{ resume.source }} · AI生成：{{ resume.content?.meta?.ai_generated ? '是' : '否' }} · 目标岗位：{{ resume.content?.meta?.target_job || (position?.title || '') }}</div>
        <div class="flex flex-wrap gap-2 mt-3">
          <button class="btn-secondary !py-1 !text-xs" :disabled="exportLoading" @click="exportResume('pdf')">导出 PDF</button>
          <button class="btn-secondary !py-1 !text-xs" :disabled="exportLoading" @click="exportResume('html')">导出 HTML</button>
          <button class="btn-secondary !py-1 !text-xs" :disabled="exportLoading" @click="exportResume('docx')">导出 DOCX</button>
          <button v-if="resume.status !== 'final'" class="btn-primary !py-1 !text-xs" @click="finalizeResume">标记定稿</button>
        </div>

        <!-- 版本历史 -->
        <div v-if="resumeVersions.length" class="mt-4 border-t border-slate-100 pt-3">
          <div class="text-xs text-slate-400 mb-2">版本历史</div>
          <div class="space-y-1.5">
            <div v-for="v in resumeVersions" :key="v.id" class="flex items-center gap-2 text-xs">
              <span class="font-mono text-primary-600">v{{ v.version }}</span>
              <span class="text-slate-600">{{ v.change_log }}</span>
              <span class="text-slate-400">{{ v.created_at?.replace('T', ' ').slice(0, 16) }}</span>
            </div>
          </div>
        </div>
      </template>
      <p v-else class="text-sm text-slate-400">暂无简历。点击右上角「创建简历」，从生成向导开始，或关联已保存的简历到本岗位。</p>
    </div>

    <template v-if="activeApp">
      <!-- 10 阶段时间线 -->
      <div class="card mb-4">
        <div class="flex items-center justify-between mb-1">
          <h3 class="font-medium text-sm">面试进度</h3>
          <div class="text-xs text-slate-400">当前：第 {{ activeApp.current_stage + 1 }} 阶段 · {{ STAGE_LABELS[activeApp.current_stage] }}</div>
        </div>
        <div class="text-xs text-slate-500 mb-3">投递日期：{{ activeApp.applied_date?.slice(0, 10) }}</div>
        <div class="flex items-center gap-1 overflow-x-auto py-2">
          <template v-for="(label, idx) in STAGE_LABELS" :key="idx">
            <button
              class="shrink-0 text-center rounded-lg border px-3 py-1.5 min-w-[72px] text-xs transition-colors"
              :class="{
                'bg-green-50 border-green-200 text-green-700': stageStatus(idx) === 'done',
                'bg-primary-600 border-primary-600 text-white': stageStatus(idx) === 'active',
                'bg-white border-slate-200 text-slate-400 hover:border-slate-300': stageStatus(idx) === 'todo',
              }"
              @click="advance(idx)"
            >
              {{ label }}
            </button>
            <div v-if="idx < 9" class="w-3 h-px bg-slate-200 shrink-0" />
          </template>
        </div>
        <div class="flex gap-2 mt-2">
          <button class="btn-secondary !py-1 !text-xs" @click="advance(stageIdx + 1)" :disabled="stageIdx >= 9">下一步 →</button>
          <button class="btn-secondary !py-1 !text-xs" @click="showInterviewForm = true; interviewForm.stage_index = stageIdx">＋ 记录本轮面试</button>
        </div>
      </div>

      <!-- 面试记录 -->
      <div class="card mb-4">
        <h3 class="font-medium text-sm mb-3">面试记录</h3>
        <div v-if="activeApp.interviews?.length" class="space-y-2">
          <div v-for="iv in activeApp.interviews" :key="iv.id" class="border border-slate-100 rounded-lg p-3">
            <div class="flex items-center justify-between text-sm">
              <span class="font-medium">{{ STAGE_LABELS[iv.stage_index] }} · {{ iv.type || '面试' }}</span>
              <span class="badge" :class="iv.result === 'pass' ? 'bg-green-50 text-green-700' : iv.result === 'fail' ? 'bg-red-50 text-red-700' : 'bg-slate-100 text-slate-600'">
                {{ iv.result === 'pass' ? '通过' : iv.result === 'fail' ? '未通过' : '待定' }}
              </span>
            </div>
            <div class="text-xs text-slate-400 mt-1">{{ iv.date?.replace('T', ' ').slice(0, 16) }}<span v-if="iv.interviewers?.length"> · {{ iv.interviewers.join(', ') }}</span></div>
            <div v-if="iv.feedback" class="text-sm text-slate-600 mt-1">{{ iv.feedback }}</div>
          </div>
        </div>
        <p v-else class="text-sm text-slate-400">暂无面试记录</p>
      </div>

      <!-- 新增面试表单 -->
      <div v-if="showInterviewForm" class="card mb-4 border-primary-200">
        <h3 class="font-medium text-sm mb-3">记录面试 · {{ STAGE_LABELS[interviewForm.stage_index] }}</h3>
        <div class="grid md:grid-cols-2 gap-3">
          <div><label class="label">阶段</label><select v-model.number="interviewForm.stage_index" class="input"> <option v-for="(l, i) in STAGE_LABELS" :key="i" :value="i">{{ l }}</option></select></div>
          <div><label class="label">类型</label><input v-model="interviewForm.type" class="input" placeholder="技术面 / HR面 / 二面…" /></div>
          <div><label class="label">时间</label><input v-model="interviewForm.date" type="datetime-local" class="input" /></div>
          <div><label class="label">面试官（逗号分隔）</label><input v-model="interviewForm.interviewers" class="input" /></div>
          <div><label class="label">结果</label><select v-model="interviewForm.result" class="input"> <option value="pending">待定</option><option value="pass">通过</option><option value="fail">未通过</option></select></div>
          <div class="md:col-span-2"><label class="label">反馈</label><textarea v-model="interviewForm.feedback" rows="2" class="input" /></div>
        </div>
        <div class="mt-3 flex justify-end gap-2">
          <button class="btn-secondary text-xs" @click="showInterviewForm = false">取消</button>
          <button class="btn-primary text-xs" @click="saveInterview">保存</button>
        </div>
      </div>
    </template>
    <div v-else-if="!loading" class="text-center py-10 text-slate-400">
      <p>暂无投递记录</p>
      <p class="text-sm">点击右上角「新建投递」开始追踪</p>
    </div>
  </div>
</template>