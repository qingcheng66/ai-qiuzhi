<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { apiJd, apiKb, apiOcr, apiResume } from '@/api'

const props = defineProps<{
  isOpen: boolean
  resumeId: number | null
  boundJd: { raw: string; structured: any } | null
  currentResume: any
}>()

const emit = defineEmits<{
  (e: 'update:isOpen', val: boolean): void
  (e: 'jd-bound', val: { raw: string; structured: any } | null): void
  (e: 'apply-section', payload: { section: string; data: any; mode: 'replace' | 'append' }): void
  (e: 'replace-all', fullResume: any): void
  (e: 'reference-generated', payload: { referenceResume: any; structuredJd: any; rawJd: string }): void
}>()

// 导航当前标签页: 'jd' (JD OCR) | 'materials' (知识库挑选) | 'reference' (AI生成参考)
const activeTab = ref<'jd' | 'materials' | 'reference'>('jd')

// 1. JD OCR 相关状态
const localJdText = ref('')
const isOcrLoading = ref(false)
const isBinding = ref(false)
const ocrNotice = ref('')
const copySuccessNotice = ref('')

// 2. 知识库素材挑选状态
const loadingKb = ref(false)
const kbProfile = ref<any>(null)
const kbProjects = ref<any[]>([])
const kbExperiences = ref<any[]>([])
const kbSkills = ref<any[]>([])
const kbHighlights = ref<any[]>([])

const selectedProjectIds = ref<number[]>([])
const selectedExperienceIds = ref<number[]>([])
const selectedSkillIds = ref<number[]>([])
const selectedHighlightIds = ref<number[]>([])

// 3. AI 参考简历生成状态
const isGeneratingRef = ref(false)
const referenceResume = ref<any>(null)
const referenceStructuredJd = ref<any>(null)

// 监听已有绑定的 JD 与持久化生成的参考草稿，确保刷新或重新打开直接恢复
watch(
  () => [props.boundJd, props.currentResume],
  ([newJd, curRes]) => {
    if (newJd) {
      localJdText.value = newJd.raw || ''
      referenceStructuredJd.value = newJd.structured || null
    } else {
      localJdText.value = ''
      referenceStructuredJd.value = null
    }
    const savedRef = curRes?.reference_resume || curRes?.target_jd?.reference_resume
    if (savedRef) {
      referenceResume.value = savedRef
    }
    // 智能步进：已生成参考草稿则直达参考结果页；仅绑定了 JD 则进入素材挑选；未绑定则在第一步
    if (newJd && referenceResume.value) {
      activeTab.value = 'reference'
    } else if (newJd) {
      activeTab.value = 'materials'
    } else {
      activeTab.value = 'jd'
    }
  },
  { immediate: true, deep: true }
)

// 加载知识库数据
async function loadKnowledgeBase() {
  if (kbProjects.value.length || kbExperiences.value.length) return
  loadingKb.value = true
  try {
    const bundle = await apiKb.bundle()
    kbProfile.value = bundle.profile || null
    kbProjects.value = bundle.projects || []
    kbExperiences.value = bundle.experiences || []
    kbSkills.value = bundle.skills || []
    kbHighlights.value = bundle.highlights || []

    // 默认全选已有素材，方便用户微调
    selectedProjectIds.value = kbProjects.value.map((p) => p.id)
    selectedExperienceIds.value = kbExperiences.value.map((e) => e.id)
    selectedSkillIds.value = kbSkills.value.map((s) => s.id)
    selectedHighlightIds.value = kbHighlights.value.map((h) => h.id)
  } catch (err: any) {
    console.warn('获取知识库素材失败', err)
  } finally {
    loadingKb.value = false
  }
}

// 智能根据当前 JD 关键词推荐勾选
function smartSelectMaterials() {
  const reqSkills: string[] = referenceStructuredJd.value?.skills_required || []
  if (!reqSkills.length) return

  const lowerSkills = reqSkills.map((s) => s.toLowerCase())
  selectedProjectIds.value = kbProjects.value
    .filter((p) => {
      const txt = (p.name + ' ' + (p.description || '') + ' ' + (p.highlights || []).join(' ')).toLowerCase()
      return lowerSkills.some((s) => txt.includes(s))
    })
    .map((p) => p.id)

  selectedExperienceIds.value = kbExperiences.value
    .filter((e) => {
      const txt = (e.company + ' ' + (e.role || '') + ' ' + (e.highlights || []).join(' ')).toLowerCase()
      return lowerSkills.some((s) => txt.includes(s))
    })
    .map((e) => e.id)
}

// 处理图片文件并调用 OCR
async function handleImageFile(file: File) {
  if (!file || !file.type.startsWith('image/')) return
  isOcrLoading.value = true
  ocrNotice.value = '正在智能识别图片中的职位要求 (OCR)...'
  try {
    const res = await apiOcr.parse(file)
    if (res.text) {
      localJdText.value = (localJdText.value ? localJdText.value + '\n\n' : '') + res.text.trim()
      ocrNotice.value = '✓ 图片文字识别成功！已载入文本框，可继续微调或绑定。'
    } else {
      ocrNotice.value = '未能从图片中识别到清晰文字，请直接粘贴文本。'
    }
  } catch (err: any) {
    ocrNotice.value = 'OCR 识别遇到问题：' + (err.message || err) + '，请直接粘贴 JD 文本。'
  } finally {
    isOcrLoading.value = false
    setTimeout(() => {
      ocrNotice.value = ''
    }, 4000)
  }
}

// 上传图片输入触发
function onImageInputChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) handleImageFile(file)
}

// 拖拽图片放置触发
function onDropImage(e: DragEvent) {
  e.preventDefault()
  const file = e.dataTransfer?.files?.[0]
  if (file) handleImageFile(file)
}

// 全局粘贴监听 (支持用户直接在工作台按 Cmd+V 粘贴截图)
function handleGlobalPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return

  for (let i = 0; i < items.length; i++) {
    if (items[i].type.indexOf('image') !== -1) {
      const file = items[i].getAsFile()
      if (file) {
        e.preventDefault()
        emit('update:isOpen', true)
        activeTab.value = 'jd'
        handleImageFile(file)
        break
      }
    }
  }
}

onMounted(() => {
  window.addEventListener('paste', handleGlobalPaste)
})

onUnmounted(() => {
  window.removeEventListener('paste', handleGlobalPaste)
})

// 绑定当前 JD 到简历并提取技能实体
async function bindJd() {
  if (!localJdText.value.trim()) return
  isBinding.value = true
  try {
    const res = await apiJd.structurize(localJdText.value)
    referenceStructuredJd.value = res
    emit('jd-bound', {
      raw: localJdText.value,
      structured: res,
    })
    copySuccessNotice.value = '✓ 目标 JD 已成功绑定到当前简历！'
    setTimeout(() => {
      copySuccessNotice.value = ''
    }, 3000)
    // 自动切换到挑选素材或生成
    await loadKnowledgeBase()
    activeTab.value = 'materials'
  } catch (err: any) {
    console.warn('绑定 JD 失败', err)
  } finally {
    isBinding.value = false
  }
}

// 解绑当前 JD
function unbindJd() {
  localJdText.value = ''
  referenceStructuredJd.value = null
  referenceResume.value = null
  emit('jd-bound', null)
}

// AI 生成定向参考简历
async function generateReferenceResume() {
  if (!props.resumeId) return
  if (!localJdText.value.trim()) {
    activeTab.value = 'jd'
    return
  }

  isGeneratingRef.value = true
  try {
    // 聚合挑选的素材列表
    const selectedMaterials: any[] = []
    for (const p of kbProjects.value) {
      if (selectedProjectIds.value.includes(p.id)) {
        selectedMaterials.push({ source: 'kb', type: 'project', name: p.name, content: p.description, meta: p })
      }
    }
    for (const exp of kbExperiences.value) {
      if (selectedExperienceIds.value.includes(exp.id)) {
        selectedMaterials.push({ source: 'kb', type: 'experience', name: exp.company, content: (exp.highlights || []).join('\n'), meta: exp })
      }
    }
    for (const sk of kbSkills.value) {
      if (selectedSkillIds.value.includes(sk.id)) {
        selectedMaterials.push({ source: 'kb', type: 'skill', name: sk.name, content: (sk.keywords || []).join(','), meta: sk })
      }
    }

    const res = await apiResume.generateReference(props.resumeId, localJdText.value, selectedMaterials)
    referenceResume.value = res.resume || null
    if (res.jd_structured) {
      referenceStructuredJd.value = res.jd_structured
    }
    emit('reference-generated', {
      referenceResume: referenceResume.value,
      structuredJd: referenceStructuredJd.value,
      rawJd: localJdText.value,
    })
    activeTab.value = 'reference'
  } catch (err: any) {
    console.error('AI 定向生成失败', err)
  } finally {
    isGeneratingRef.value = false
  }
}

// 一键复制文本到剪贴板
async function copyToClipboard(text: string, label = '内容') {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
    }
    copySuccessNotice.value = `已复制「${label}」！直接在中间表单按 Cmd+V 粘贴即可。`
    setTimeout(() => {
      copySuccessNotice.value = ''
    }, 3000)
  } catch (e) {
    // ignore
  }
}

// 一键将单项填入当前编辑表单
function applySectionItem(section: string, data: any, mode: 'replace' | 'append' = 'append') {
  emit('apply-section', { section, data, mode })
  copySuccessNotice.value = `✓ 已成功填入当前简历【${getSectionLabel(section)}】！可在中间表单直接查看。`
  setTimeout(() => {
    copySuccessNotice.value = ''
  }, 3000)
}

// 全量应用 AI 参考草稿
function applyAllReference() {
  if (!referenceResume.value) return
  if (confirm('确认将 AI 定向生成的整套内容作为当前简历草稿？（当前未保存修改会被覆盖）')) {
    emit('replace-all', referenceResume.value)
    copySuccessNotice.value = '✓ 整套 AI 参考简历已全量载入当前工作台！'
    setTimeout(() => {
      copySuccessNotice.value = ''
    }, 3000)
  }
}

function getSectionLabel(key: string) {
  const map: Record<string, string> = {
    basics: '基本资料',
    skills: '专业技能',
    projects: '项目经历',
    experience: '工作经历',
    highlights: '个人亮点',
    education: '教育经历',
  }
  return map[key] || key
}

// ==========================================
// 4. 悬浮窗 & 随意拖拽悬浮球核心逻辑
// ==========================================
const displayMode = ref<'floating' | 'drawer'>('floating')
const isDraggingWin = ref(false)
const isDraggingBall = ref(false)
const isResizing = ref(false)

// 悬浮球位置 (收起态)
const ballPos = ref({
  x: typeof window !== 'undefined' ? window.innerWidth - 170 : 800,
  y: typeof window !== 'undefined' ? window.innerHeight - 130 : 600,
})

// 悬浮窗位置与尺寸 (展开态)
const winPos = ref({
  x: typeof window !== 'undefined' ? Math.max(20, window.innerWidth - 650) : 600,
  y: 64,
})
const winSize = ref({
  width: 620,
  height: typeof window !== 'undefined' ? Math.min(800, window.innerHeight - 90) : 700,
})

function clampBallPos(x: number, y: number) {
  const w = typeof window !== 'undefined' ? window.innerWidth : 1200
  const h = typeof window !== 'undefined' ? window.innerHeight : 800
  return {
    x: Math.max(10, Math.min(w - 150, x)),
    y: Math.max(10, Math.min(h - 60, y)),
  }
}

function clampWinPos(x: number, y: number) {
  const w = typeof window !== 'undefined' ? window.innerWidth : 1200
  const h = typeof window !== 'undefined' ? window.innerHeight : 800
  return {
    x: Math.max(10, Math.min(w - 200, x)),
    y: Math.max(10, Math.min(h - 100, y)),
  }
}

function handleWindowResize() {
  ballPos.value = clampBallPos(ballPos.value.x, ballPos.value.y)
  winPos.value = clampWinPos(winPos.value.x, winPos.value.y)
  if (typeof window !== 'undefined') {
    if (winSize.value.width > window.innerWidth - 20) {
      winSize.value.width = window.innerWidth - 20
    }
    if (winSize.value.height > window.innerHeight - 40) {
      winSize.value.height = window.innerHeight - 40
    }
  }
}

onMounted(() => {
  try {
    const savedMode = localStorage.getItem('ai_copilot_display_mode')
    if (savedMode === 'drawer' || savedMode === 'floating') {
      displayMode.value = savedMode
    }
    const savedBall = localStorage.getItem('ai_copilot_ball_pos')
    if (savedBall) {
      const parsed = JSON.parse(savedBall)
      if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
        ballPos.value = clampBallPos(parsed.x, parsed.y)
      }
    }
    const savedWin = localStorage.getItem('ai_copilot_win_pos')
    if (savedWin) {
      const parsed = JSON.parse(savedWin)
      if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
        winPos.value = clampWinPos(parsed.x, parsed.y)
      }
    }
    const savedSize = localStorage.getItem('ai_copilot_win_size')
    if (savedSize) {
      const parsed = JSON.parse(savedSize)
      if (typeof parsed.width === 'number' && typeof parsed.height === 'number') {
        winSize.value = {
          width: Math.max(420, Math.min(window.innerWidth - 40, parsed.width)),
          height: Math.max(380, Math.min(window.innerHeight - 40, parsed.height)),
        }
      }
    }
  } catch (_) {}

  window.addEventListener('resize', handleWindowResize)
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', handleWindowResize)
  }
})

// 悬浮球拖拽逻辑
let ballDragState: { clientX: number; clientY: number; initX: number; initY: number; moved: boolean } | null = null

function onBallPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  isDraggingBall.value = true
  ballDragState = {
    clientX: e.clientX,
    clientY: e.clientY,
    initX: ballPos.value.x,
    initY: ballPos.value.y,
    moved: false,
  }
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', onBallPointerMove)
  window.addEventListener('pointerup', onBallPointerUp)
}

function onBallPointerMove(e: PointerEvent) {
  if (!ballDragState) return
  const dx = e.clientX - ballDragState.clientX
  const dy = e.clientY - ballDragState.clientY
  if (Math.hypot(dx, dy) > 4) {
    ballDragState.moved = true
  }
  ballPos.value = clampBallPos(ballDragState.initX + dx, ballDragState.initY + dy)
}

function onBallPointerUp(_e: PointerEvent) {
  window.removeEventListener('pointermove', onBallPointerMove)
  window.removeEventListener('pointerup', onBallPointerUp)
  document.body.style.userSelect = ''
  isDraggingBall.value = false
  if (ballDragState) {
    if (!ballDragState.moved) {
      // 单击触发打开悬浮窗
      emit('update:isOpen', true)
    } else {
      try {
        localStorage.setItem('ai_copilot_ball_pos', JSON.stringify(ballPos.value))
      } catch (_) {}
    }
    ballDragState = null
  }
}

// 悬浮窗拖拽 (按住标题栏移动)
let winDragState: { clientX: number; clientY: number; initX: number; initY: number } | null = null

function onWinHeaderPointerDown(e: PointerEvent) {
  if (displayMode.value !== 'floating') return
  if (e.button !== 0) return
  const target = e.target as HTMLElement
  if (target.closest('button') || target.closest('input') || target.closest('a')) return

  isDraggingWin.value = true
  winDragState = {
    clientX: e.clientX,
    clientY: e.clientY,
    initX: winPos.value.x,
    initY: winPos.value.y,
  }
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', onWinHeaderPointerMove)
  window.addEventListener('pointerup', onWinHeaderPointerUp)
}

function onWinHeaderPointerMove(e: PointerEvent) {
  if (!winDragState) return
  const dx = e.clientX - winDragState.clientX
  const dy = e.clientY - winDragState.clientY
  winPos.value = clampWinPos(winDragState.initX + dx, winDragState.initY + dy)
}

function onWinHeaderPointerUp(_e: PointerEvent) {
  window.removeEventListener('pointermove', onWinHeaderPointerMove)
  window.removeEventListener('pointerup', onWinHeaderPointerUp)
  document.body.style.userSelect = ''
  isDraggingWin.value = false
  if (winDragState) {
    try {
      localStorage.setItem('ai_copilot_win_pos', JSON.stringify(winPos.value))
    } catch (_) {}
    winDragState = null
  }
}

// 悬浮窗右下角拉伸调整尺寸
let resizeState: { clientX: number; clientY: number; initW: number; initH: number } | null = null

function onResizePointerDown(e: PointerEvent) {
  if (displayMode.value !== 'floating') return
  if (e.button !== 0) return
  e.preventDefault()
  e.stopPropagation()
  isResizing.value = true
  resizeState = {
    clientX: e.clientX,
    clientY: e.clientY,
    initW: winSize.value.width,
    initH: winSize.value.height,
  }
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', onResizePointerMove)
  window.addEventListener('pointerup', onResizePointerUp)
}

function onResizePointerMove(e: PointerEvent) {
  if (!resizeState) return
  const dw = e.clientX - resizeState.clientX
  const dh = e.clientY - resizeState.clientY
  const maxW = typeof window !== 'undefined' ? window.innerWidth - winPos.value.x - 10 : 1200
  const maxH = typeof window !== 'undefined' ? window.innerHeight - winPos.value.y - 10 : 800
  winSize.value = {
    width: Math.max(420, Math.min(maxW, resizeState.initW + dw)),
    height: Math.max(380, Math.min(maxH, resizeState.initH + dh)),
  }
}

function onResizePointerUp(_e: PointerEvent) {
  window.removeEventListener('pointermove', onResizePointerMove)
  window.removeEventListener('pointerup', onResizePointerUp)
  document.body.style.userSelect = ''
  isResizing.value = false
  if (resizeState) {
    try {
      localStorage.setItem('ai_copilot_win_size', JSON.stringify(winSize.value))
    } catch (_) {}
    resizeState = null
  }
}

function toggleDisplayMode() {
  displayMode.value = displayMode.value === 'floating' ? 'drawer' : 'floating'
  try {
    localStorage.setItem('ai_copilot_display_mode', displayMode.value)
  } catch (_) {}
}

function resetWinPos() {
  winPos.value = {
    x: Math.max(20, window.innerWidth - 650),
    y: 64,
  }
  winSize.value = {
    width: 620,
    height: Math.min(800, window.innerHeight - 90),
  }
  try {
    localStorage.setItem('ai_copilot_win_pos', JSON.stringify(winPos.value))
    localStorage.setItem('ai_copilot_win_size', JSON.stringify(winSize.value))
  } catch (_) {}
}
</script>

<template>
  <!-- 协同面板容器 (支持随意拖拽悬浮窗模式 与 贴边抽屉模式) -->
  <div
    v-show="isOpen"
    class="fixed z-50 bg-white shadow-2xl flex flex-col transition-all duration-150"
    :class="displayMode === 'drawer'
      ? 'inset-y-0 right-0 w-full max-w-xl border-l border-slate-200'
      : 'rounded-2xl border border-slate-300 shadow-2xl overflow-hidden ring-1 ring-black/10'
    "
    :style="displayMode === 'floating' ? {
      left: `${winPos.x}px`,
      top: `${winPos.y}px`,
      width: `${winSize.width}px`,
      height: `${winSize.height}px`,
    } : {}"
  >
    <!-- 1. 顶部 Header (浮窗模式下支持按住随意拖拽位置) -->
    <div
      class="px-4 py-3 bg-slate-900 text-white flex items-center justify-between shrink-0 shadow-sm"
      :class="displayMode === 'floating' ? 'cursor-move select-none active:cursor-grabbing' : ''"
      :title="displayMode === 'floating' ? '按住此处可自由拖拽悬浮窗位置' : ''"
      @pointerdown="onWinHeaderPointerDown"
    >
      <div class="flex items-center gap-2.5 min-w-0 pointer-events-none">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-500 flex items-center justify-center font-bold text-sm text-white shadow-md shrink-0">
          🎯
        </div>
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <h3 class="font-bold text-sm text-white tracking-wide truncate">目标岗位与 AI 定向参考助手</h3>
            <span v-if="boundJd" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shrink-0">
              已绑定 JD
            </span>
            <span v-else class="px-2 py-0.5 rounded-full text-[10px] text-slate-400 bg-slate-800 shrink-0">未绑定</span>
          </div>
          <p class="text-[11px] text-slate-400 truncate">
            {{ displayMode === 'floating' ? '按住标题栏可自由拖拽 · 右下角可拉伸大小' : '截屏识别 OCR · 挑选素材 · AI 针对性参考草稿' }}
          </p>
        </div>
      </div>

      <!-- 顶栏操作区 (切换模式/复位/收为悬浮球/关闭) -->
      <div class="flex items-center gap-1 shrink-0 ml-2">
        <!-- 复位居中 (仅浮窗模式) -->
        <button
          v-if="displayMode === 'floating'"
          class="text-slate-400 hover:text-white px-2 py-1 rounded-md hover:bg-slate-800 text-xs transition"
          title="重置浮窗默认位置与大小"
          @click.stop="resetWinPos"
        >
          <span>↺ 复位</span>
        </button>

        <!-- 切换 贴边抽屉 / 自由浮窗 -->
        <button
          class="text-slate-400 hover:text-white px-2 py-1 rounded-md hover:bg-slate-800 text-xs transition flex items-center gap-1"
          :title="displayMode === 'floating' ? '切换为右侧贴边固定抽屉' : '脱离为随意拖拽悬浮窗'"
          @click.stop="toggleDisplayMode"
        >
          <span>{{ displayMode === 'floating' ? '⤢ 贴边抽屉' : '◫ 自由浮窗' }}</span>
        </button>

        <!-- 最小化收起成悬浮球 -->
        <button
          class="text-slate-300 hover:text-white px-2 py-1 rounded-md hover:bg-indigo-900/60 border border-indigo-700/50 text-xs transition flex items-center gap-1"
          title="收起为随意拖拽的悬浮球"
          @click.stop="emit('update:isOpen', false)"
        >
          <span>🗕</span>
          <span class="text-xs">收为悬浮球</span>
        </button>

        <!-- 关闭 -->
        <button
          class="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800 text-base transition ml-1"
          title="关闭"
          @click.stop="emit('update:isOpen', false)"
        >
          ✕
        </button>
      </div>
    </div>

    <!-- 成功提示条 -->
    <div v-if="copySuccessNotice" class="bg-emerald-50 text-emerald-800 border-b border-emerald-200 px-4 py-2 text-xs font-semibold flex items-center justify-between shrink-0">
      <span>{{ copySuccessNotice }}</span>
      <button class="text-emerald-500 hover:text-emerald-700 font-bold" @click="copySuccessNotice = ''">✕</button>
    </div>

    <!-- 2. 标签页切换栏 (流程步骤) -->
    <div class="flex items-center border-b border-slate-200 bg-slate-50 shrink-0 px-4 pt-2">
      <button
        class="flex-1 py-2 text-xs font-bold text-center border-b-2 transition"
        :class="activeTab === 'jd' ? 'border-indigo-600 text-indigo-600 bg-white rounded-t-lg' : 'border-transparent text-slate-500 hover:text-slate-800'"
        @click="activeTab = 'jd'"
      >
        ① 岗位 JD / 截屏 OCR
      </button>
      <button
        class="flex-1 py-2 text-xs font-bold text-center border-b-2 transition"
        :class="activeTab === 'materials' ? 'border-indigo-600 text-indigo-600 bg-white rounded-t-lg' : 'border-transparent text-slate-500 hover:text-slate-800'"
        @click="activeTab = 'materials'; loadKnowledgeBase()"
      >
        ② 挑选素材
      </button>
      <button
        class="flex-1 py-2 text-xs font-bold text-center border-b-2 transition"
        :class="activeTab === 'reference' ? 'border-indigo-600 text-indigo-600 bg-white rounded-t-lg' : 'border-transparent text-slate-500 hover:text-slate-800'"
        @click="activeTab = 'reference'"
      >
        ③ AI 生成参考简历
        <span v-if="referenceResume" class="w-2 h-2 rounded-full bg-emerald-500 inline-block ml-0.5"></span>
      </button>
    </div>

    <!-- 3. 内容滚动区 -->
    <div class="flex-1 overflow-y-auto p-4 space-y-4">

      <!-- ======================================================== -->
      <!-- TAB 1: 岗位 JD (截屏 OCR / 粘贴 / 绑定) -->
      <!-- ======================================================== -->
      <div v-show="activeTab === 'jd'" class="space-y-4">
        <!-- 已绑定展示卡片 -->
        <div v-if="boundJd && referenceStructuredJd" class="p-3 bg-emerald-50/70 border border-emerald-200 rounded-xl space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-emerald-800 flex items-center gap-1.5">
              <span>✅</span> 当前已成功绑定到本简历
            </span>
            <button class="text-xs text-rose-500 hover:text-rose-700 hover:underline" @click="unbindJd">
              解绑 JD
            </button>
          </div>
          <div class="text-sm font-bold text-slate-800">
            {{ referenceStructuredJd.title || '目标职位' }}
            <span v-if="referenceStructuredJd.company" class="text-xs text-slate-500 font-normal"> · {{ referenceStructuredJd.company }}</span>
          </div>
          <!-- 技能标签 -->
          <div v-if="referenceStructuredJd.skills_required?.length" class="flex flex-wrap gap-1 mt-1">
            <span
              v-for="sk in referenceStructuredJd.skills_required"
              :key="sk"
              class="px-2 py-0.5 bg-white border border-emerald-200 text-emerald-700 rounded text-[11px] font-medium"
            >
              {{ sk }}
            </span>
          </div>
        </div>

        <!-- 截屏图片上传 & 拖拽识别区 -->
        <div
          class="border-2 border-dashed border-indigo-200 hover:border-indigo-400 bg-indigo-50/40 rounded-xl p-4 text-center transition cursor-pointer relative"
          @dragover.prevent
          @drop="onDropImage"
        >
          <input
            type="file"
            accept="image/*"
            class="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
            @change="onImageInputChange"
          />
          <div class="flex flex-col items-center justify-center gap-1">
            <span class="text-2xl">📷</span>
            <p class="text-xs font-bold text-indigo-900">
              点击上传招聘截图，或将图片拖拽至此
            </p>
            <p class="text-[11px] text-indigo-600/80">
              快捷操作：直接在任意窗口截图后，回到本页面按 <kbd class="px-1.5 py-0.5 bg-white border border-indigo-200 rounded shadow-2xs font-mono font-bold text-indigo-700">Cmd+V</kbd> 即可自动触发 OCR 提取！
            </p>
          </div>
        </div>

        <!-- OCR 状态提示 -->
        <div v-if="isOcrLoading" class="p-3 bg-indigo-50 border border-indigo-200 rounded-lg flex items-center gap-2 text-xs text-indigo-700 font-medium animate-pulse">
          <span class="animate-spin">🔄</span>
          <span>正在调用 OCR 识别提取职位描述... 请稍候</span>
        </div>
        <div v-else-if="ocrNotice" class="p-2.5 bg-slate-100 border border-slate-200 rounded-lg text-xs text-slate-700">
          {{ ocrNotice }}
        </div>

        <!-- JD 文本框 (支持手动微调) -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <label class="text-xs font-bold text-slate-700">职位描述 (JD 文本)</label>
            <span class="text-[11px] text-slate-400">支持自由编辑修正</span>
          </div>
          <textarea
            v-model="localJdText"
            rows="9"
            class="w-full text-xs font-mono p-3 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none leading-relaxed text-slate-700"
            placeholder="粘贴目标岗位描述，或通过上方截屏 OCR 自动载入...&#10;包含岗位职责、技术栈、硬性要求等，AI 将据此进行智能对齐。"
          />
        </div>

        <!-- 绑定与下一步操作栏 -->
        <div class="flex items-center justify-between pt-2 border-t border-slate-100">
          <span class="text-[11px] text-slate-400">
            绑定后将作为此份简历的定向上下文
          </span>
          <div class="flex items-center gap-2">
            <button
              class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold shadow-xs transition flex items-center gap-1.5 disabled:opacity-50"
              :disabled="!localJdText.trim() || isBinding"
              @click="bindJd"
            >
              <span>{{ isBinding ? '正在智能提取技能…' : '🔗 绑定并去挑选素材 →' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- ======================================================== -->
      <!-- TAB 2: 知识库素材挑选 (多选素材池) -->
      <!-- ======================================================== -->
      <div v-show="activeTab === 'materials'" class="space-y-4">
        <div class="flex items-center justify-between bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-xs">
          <div>
            <span class="font-bold text-slate-800">挑选用于针对该岗位的经历素材</span>
            <p class="text-[11px] text-slate-500">AI 将只选用勾选的真实素材进行重构与润色，杜绝编造</p>
          </div>
          <button
            class="px-2.5 py-1 text-xs bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 rounded font-bold transition"
            @click="smartSelectMaterials"
          >
            ✨ 按 JD 自动智能勾选
          </button>
        </div>

        <div v-if="loadingKb" class="py-8 text-center text-xs text-slate-400">
          正在从知识库加载您的个人素材...
        </div>

        <div v-else class="space-y-4">
          <!-- 1. 项目经历勾选池 -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-slate-800 flex items-center gap-1">
                <span>🚀</span> 项目库 ({{ selectedProjectIds.length }}/{{ kbProjects.length }})
              </span>
              <div class="flex items-center gap-1.5 text-[11px]">
                <button class="text-indigo-600 hover:underline" @click="selectedProjectIds = kbProjects.map(p => p.id)">全选</button>
                <span class="text-slate-300">|</span>
                <button class="text-slate-500 hover:underline" @click="selectedProjectIds = []">清空</button>
              </div>
            </div>
            <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              <label
                v-for="p in kbProjects"
                :key="p.id"
                class="flex items-start gap-2 p-2 rounded-lg border text-xs cursor-pointer transition"
                :class="selectedProjectIds.includes(p.id) ? 'bg-indigo-50/60 border-indigo-300' : 'bg-white border-slate-200 hover:bg-slate-50'"
              >
                <input
                  v-model="selectedProjectIds"
                  type="checkbox"
                  :value="p.id"
                  class="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                />
                <div class="min-w-0 flex-1">
                  <div class="font-bold text-slate-800 truncate">{{ p.name }}</div>
                  <div class="text-[11px] text-slate-500 line-clamp-2 mt-0.5">{{ p.description }}</div>
                </div>
              </label>
            </div>
          </div>

          <!-- 2. 工作经历勾选池 -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-slate-800 flex items-center gap-1">
                <span>💼</span> 工作经历 ({{ selectedExperienceIds.length }}/{{ kbExperiences.length }})
              </span>
              <div class="flex items-center gap-1.5 text-[11px]">
                <button class="text-indigo-600 hover:underline" @click="selectedExperienceIds = kbExperiences.map(e => e.id)">全选</button>
                <span class="text-slate-300">|</span>
                <button class="text-slate-500 hover:underline" @click="selectedExperienceIds = []">清空</button>
              </div>
            </div>
            <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              <label
                v-for="exp in kbExperiences"
                :key="exp.id"
                class="flex items-start gap-2 p-2 rounded-lg border text-xs cursor-pointer transition"
                :class="selectedExperienceIds.includes(exp.id) ? 'bg-indigo-50/60 border-indigo-300' : 'bg-white border-slate-200 hover:bg-slate-50'"
              >
                <input
                  v-model="selectedExperienceIds"
                  type="checkbox"
                  :value="exp.id"
                  class="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                />
                <div class="min-w-0 flex-1">
                  <div class="font-bold text-slate-800">{{ exp.company }} · <span class="font-normal text-slate-500">{{ exp.role }}</span></div>
                  <div class="text-[11px] text-slate-500 line-clamp-2 mt-0.5">
                    {{ (exp.highlights || []).join('；') }}
                  </div>
                </div>
              </label>
            </div>
          </div>
        </div>

        <!-- 底部生成按钮 -->
        <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
          <button class="text-xs text-slate-500 hover:text-slate-700" @click="activeTab = 'jd'">
            ← 返回修改 JD
          </button>
          <button
            class="px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white rounded-lg text-xs font-bold shadow-md transition flex items-center gap-1.5 disabled:opacity-50"
            :disabled="isGeneratingRef"
            @click="generateReferenceResume"
          >
            <span>{{ isGeneratingRef ? 'AI 正在针对 JD 定向润色…' : '✨ 开始生成定向参考简历 →' }}</span>
          </button>
        </div>
      </div>

      <!-- ======================================================== -->
      <!-- TAB 3: AI 生成的定向参考简历与复制面板 -->
      <!-- ======================================================== -->
      <div v-show="activeTab === 'reference'" class="space-y-4">
        <!-- 未生成时的引导 -->
        <div v-if="!referenceResume" class="text-center py-12 px-4 space-y-3 bg-slate-50 rounded-xl border border-dashed border-slate-200">
          <span class="text-3xl block">🤖</span>
          <h4 class="font-bold text-sm text-slate-800">尚未生成针对本岗位的参考简历</h4>
          <p class="text-xs text-slate-500 max-w-sm mx-auto">
            绑定目标 JD 并挑选知识库经历素材后，AI 将为您生成量身定制的高分参考草稿。
          </p>
          <button
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-bold shadow-xs hover:bg-indigo-700 transition"
            :disabled="isGeneratingRef"
            @click="generateReferenceResume"
          >
            {{ isGeneratingRef ? 'AI 正在全力撰写中…' : '✨ 立即生成专属参考简历' }}
          </button>
        </div>

        <!-- 已生成时的内容展示与一键采纳/复制 -->
        <div v-else class="space-y-4">
          <!-- 顶部总览与一键全量替换 -->
          <div class="bg-indigo-50/70 border border-indigo-200 p-3 rounded-xl flex items-center justify-between">
            <div>
              <span class="text-xs font-bold text-indigo-900 block">✨ AI 定向参考版本已就绪</span>
              <p class="text-[11px] text-indigo-700/80">可挑拣满意的句子复制粘贴，也可一键填入对应模块</p>
            </div>
            <div class="flex items-center gap-1.5">
              <button
                class="px-2.5 py-1 bg-white hover:bg-indigo-100 text-indigo-700 border border-indigo-300 rounded text-xs font-bold transition shadow-2xs"
                title="重新由 AI 再次定向生成"
                :disabled="isGeneratingRef"
                @click="generateReferenceResume"
              >
                🔄 重新生成
              </button>
              <button
                class="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-bold shadow-xs transition"
                title="整份替换当前简历"
                @click="applyAllReference"
              >
                🚀 全量应用
              </button>
            </div>
          </div>

          <!-- 1. 专业技能模块参考 -->
          <div v-if="referenceResume.skills?.length" class="bg-white rounded-xl border border-slate-200 p-3 shadow-2xs space-y-2">
            <div class="flex items-center justify-between pb-1.5 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-800 flex items-center gap-1">
                <span>⚡</span> 针对该 JD 匹配的【专业技能】
              </span>
              <div class="flex items-center gap-1">
                <button
                  class="text-[11px] text-slate-500 hover:text-indigo-600 px-1.5 py-0.5 rounded border border-slate-200 hover:border-indigo-200 bg-slate-50"
                  @click="copyToClipboard(JSON.stringify(referenceResume.skills, null, 2), '专业技能')"
                >
                  📋 复制
                </button>
                <button
                  class="text-[11px] text-indigo-600 hover:text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200 bg-indigo-50 font-bold"
                  @click="applySectionItem('skills', referenceResume.skills, 'replace')"
                >
                  ↳ 填入简历技能栏
                </button>
              </div>
            </div>
            <div class="space-y-1.5">
              <div
                v-for="(grp, idx) in referenceResume.skills"
                :key="idx"
                class="text-xs bg-slate-50 p-2 rounded-lg border border-slate-100"
              >
                <span class="font-bold text-slate-700">{{ grp.name || '技术栈' }}：</span>
                <span class="text-slate-600">{{ (grp.keywords || []).join('、') }}</span>
              </div>
            </div>
          </div>

          <!-- 2. 项目经历模块参考 -->
          <div v-if="referenceResume.projects?.length" class="bg-white rounded-xl border border-slate-200 p-3 shadow-2xs space-y-3">
            <div class="flex items-center justify-between pb-1.5 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-800 flex items-center gap-1">
                <span>🚀</span> 针对该 JD 优化的【项目经历】
              </span>
              <button
                class="text-[11px] text-indigo-600 hover:text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200 bg-indigo-50 font-bold"
                @click="applySectionItem('projects', referenceResume.projects, 'replace')"
              >
                ↳ 全量替换项目经历
              </button>
            </div>
            <div
              v-for="(proj, pIdx) in referenceResume.projects"
              :key="pIdx"
              class="p-2.5 rounded-lg border border-slate-100 bg-slate-50/70 space-y-1.5 text-xs"
            >
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-800">{{ proj.name }}</span>
                <div class="flex items-center gap-1">
                  <button
                    class="text-[10px] text-slate-500 hover:text-indigo-600 px-1.5 py-0.5 rounded border border-slate-200 bg-white"
                    @click="copyToClipboard(`${proj.name}\n${proj.description}\n` + (proj.highlights || []).join('\n'), proj.name)"
                  >
                    📋 复制
                  </button>
                  <button
                    class="text-[10px] text-indigo-600 hover:text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200 bg-indigo-50 font-bold"
                    @click="applySectionItem('projects', [proj], 'append')"
                  >
                    ↳ 追加进简历
                  </button>
                </div>
              </div>
              <p class="text-slate-600 text-[11px] leading-relaxed">{{ proj.description }}</p>
              <ul v-if="proj.highlights?.length" class="list-disc list-inside space-y-0.5 text-slate-600 text-[11px]">
                <li v-for="(h, hIdx) in proj.highlights" :key="hIdx">{{ h }}</li>
              </ul>
            </div>
          </div>

          <!-- 3. 工作经历模块参考 -->
          <div v-if="referenceResume.experience?.length" class="bg-white rounded-xl border border-slate-200 p-3 shadow-2xs space-y-3">
            <div class="flex items-center justify-between pb-1.5 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-800 flex items-center gap-1">
                <span>💼</span> 针对该 JD 改写的【工作经历】
              </span>
              <button
                class="text-[11px] text-indigo-600 hover:text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200 bg-indigo-50 font-bold"
                @click="applySectionItem('experience', referenceResume.experience, 'replace')"
              >
                ↳ 全量替换工作经历
              </button>
            </div>
            <div
              v-for="(exp, eIdx) in referenceResume.experience"
              :key="eIdx"
              class="p-2.5 rounded-lg border border-slate-100 bg-slate-50/70 space-y-1.5 text-xs"
            >
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-800">{{ exp.company }} · <span class="font-normal text-slate-600">{{ exp.role }}</span></span>
                <div class="flex items-center gap-1">
                  <button
                    class="text-[10px] text-slate-500 hover:text-indigo-600 px-1.5 py-0.5 rounded border border-slate-200 bg-white"
                    @click="copyToClipboard(`${exp.company} ${exp.role}\n` + (exp.highlights || []).join('\n'), exp.company)"
                  >
                    📋 复制
                  </button>
                  <button
                    class="text-[10px] text-indigo-600 hover:text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200 bg-indigo-50 font-bold"
                    @click="applySectionItem('experience', [exp], 'append')"
                  >
                    ↳ 追加进简历
                  </button>
                </div>
              </div>
              <ul v-if="exp.highlights?.length" class="list-disc list-inside space-y-0.5 text-slate-600 text-[11px]">
                <li v-for="(h, hIdx) in exp.highlights" :key="hIdx">{{ h }}</li>
              </ul>
            </div>
          </div>

          <!-- 4. 个人亮点 / 优势总结参考 -->
          <div v-if="referenceResume.highlights?.length || referenceResume.basics?.summary" class="bg-white rounded-xl border border-slate-200 p-3 shadow-2xs space-y-2">
            <div class="flex items-center justify-between pb-1.5 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-800 flex items-center gap-1">
                <span>🌟</span> 定向提炼的【个人亮点与自我总结】
              </span>
              <button
                class="text-[11px] text-slate-500 hover:text-indigo-600 px-1.5 py-0.5 rounded border border-slate-200 bg-slate-50"
                @click="copyToClipboard(referenceResume.basics?.summary || JSON.stringify(referenceResume.highlights, null, 2), '个人亮点')"
              >
                📋 复制
              </button>
            </div>
            <p v-if="referenceResume.basics?.summary" class="text-xs text-slate-600 leading-relaxed bg-slate-50 p-2 rounded-lg border border-slate-100">
              {{ referenceResume.basics.summary }}
            </p>
          </div>
        </div>
      </div>

    </div>

    <!-- 浮窗右下角拉伸缩放手柄 (仅浮窗模式) -->
    <div
      v-if="displayMode === 'floating'"
      class="absolute bottom-1 right-1 w-4 h-4 cursor-se-resize text-slate-400 hover:text-slate-700 flex items-center justify-center select-none z-20"
      title="按住拖拽调节浮窗大小"
      @pointerdown="onResizePointerDown"
    >
      <svg class="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
        <path d="M14 14H12V12H14V14ZM14 10H12V8H14V10ZM10 14H8V12H10V14ZM14 6H12V4H14V6ZM6 14H4V12H6V14ZM10 10H8V8H10V10Z" opacity="0.6"/>
      </svg>
    </div>
  </div>

  <!-- 4. 收起态: 随意拖拽的悬浮球 (Floating Action Ball) - 仅在进入简历编辑且 resume 数据存在时出现 -->
  <div
    v-if="resumeId && currentResume"
    v-show="!isOpen"
    class="fixed z-50 cursor-grab active:cursor-grabbing select-none group touch-none"
    :style="{ left: `${ballPos.x}px`, top: `${ballPos.y}px` }"
    @pointerdown="onBallPointerDown"
  >
    <div
      class="relative flex items-center gap-2 px-3.5 py-2.5 rounded-full bg-gradient-to-r from-indigo-600 via-indigo-700 to-violet-700 text-white shadow-xl hover:shadow-2xl hover:scale-105 active:scale-95 transition-all border border-indigo-300/40 backdrop-blur-md"
    >
      <!-- 动态呼吸光晕 (已绑定则显示绿色，未绑定显示紫色) -->
      <span class="absolute -top-1 -right-1 flex h-3.5 w-3.5">
        <span
          class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
          :class="boundJd ? 'bg-emerald-400' : 'bg-indigo-300'"
        ></span>
        <span
          class="relative inline-flex rounded-full h-3.5 w-3.5 border-2 border-white"
          :class="boundJd ? 'bg-emerald-500' : 'bg-indigo-400'"
        ></span>
      </span>

      <span class="text-base select-none">🎯</span>
      <span class="text-xs font-bold tracking-wide whitespace-nowrap select-none">AI 参考助手</span>
      <span
        class="text-[10px] px-1.5 py-0.2 rounded-full font-mono select-none"
        :class="boundJd ? 'bg-emerald-400/20 text-emerald-200 border border-emerald-400/30' : 'bg-white/20 text-white/90'"
      >
        {{ boundJd ? '已绑' : '待绑' }}
      </span>

      <!-- 拖拽与快捷提示浮层 -->
      <div class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-slate-900/95 text-white text-[11px] px-2.5 py-1 rounded-md shadow-lg whitespace-nowrap z-50">
        点击展开助手 · 按住任意拖动位置
      </div>
    </div>
  </div>
</template>
