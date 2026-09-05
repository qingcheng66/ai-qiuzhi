<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiJd, apiOcr, apiResume, apiTemplates, apiWorkspace, downloadBlob } from '@/api'
import ResumeWorkbenchEditor, { type CustomSection } from '@/components/ResumeWorkbenchEditor.vue'
import ResumePaperPreview from '@/components/ResumePaperPreview.vue'
import ResumeTagPalette from '@/components/ResumeTagPalette.vue'
import CompanyPositionSelector from '@/components/CompanyPositionSelector.vue'
import JdAiCopilotDrawer from '@/components/JdAiCopilotDrawer.vue'

const leftPanelMode = ref<'palette' | 'outline'>('palette')
const paperPreviewRef = ref<any>(null)

function handleAddTagFromPalette(tag: any) {
  if (paperPreviewRef.value?.applyTagToBasics) {
    paperPreviewRef.value.applyTagToBasics(tag)
    triggerAutoSave()
    return
  }

  if (!resume.value) return
  if (!resume.value.basics) resume.value.basics = {}
  const b = resume.value.basics

  const widgetType = tag.type || (tag.category === 'core' ? tag.key : 'tag')
  const w = tag.defaultCols || (widgetType === 'summary' ? 12 : widgetType === 'photo' ? 3 : widgetType === 'name' ? 6 : 4)
  const h = widgetType === 'photo' ? 3 : widgetType === 'summary' ? 2 : 1

  if (!Array.isArray(b.grid_widgets_2d)) {
    b.grid_widgets_2d = []
  }

  const existingIdx2D = b.grid_widgets_2d.findIndex((item: any) =>
    item.id === tag.id || (tag.key && item.key === tag.key && tag.key !== 'custom')
  )

  const new2DWidget = {
    id: tag.id || `widget_${Date.now()}`,
    type: widgetType,
    key: tag.key || 'custom',
    label: tag.label,
    value: tag.value || '',
    icon: tag.icon || '🏷️',
    col: 1,
    row: Math.max(1, b.grid_widgets_2d.length + 1),
    w,
    h,
    isCustom: tag.category === 'custom' || tag.isCustom,
  }

  if (existingIdx2D !== -1) {
    b.grid_widgets_2d[existingIdx2D] = { ...b.grid_widgets_2d[existingIdx2D], ...new2DWidget }
  } else {
    b.grid_widgets_2d.push(new2DWidget)
  }

  // 同步基础字段
  if (tag.id === 'core_name' || widgetType === 'name') {
    b.name = tag.value || b.name || '求职者姓名'
  } else if (tag.id === 'core_label' || widgetType === 'label') {
    b.label = tag.value || b.label || '意向岗位'
  } else if (tag.id === 'core_photo' || widgetType === 'photo') {
    b.photo = tag.value || b.photo || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200'
  } else if (tag.id === 'core_summary' || widgetType === 'summary') {
    b.summary = tag.value || b.summary || '具备扎实的核心专业能力与综合解决问题经验。'
  } else {
    const standardKeys = ['phone', 'email', 'location', 'birthDate', 'github', 'blog', 'wechat']
    if (tag.key && standardKeys.includes(tag.key)) {
      b[tag.key] = tag.value || b[tag.key] || `${tag.label}内容`
    } else {
      if (!Array.isArray(b.custom_fields)) {
        b.custom_fields = []
      }
      const existing = b.custom_fields.find((cf: any) => cf.label === tag.label)
      if (existing) {
        existing.value = tag.value || existing.value
      } else {
        b.custom_fields.push({
          id: tag.id || `cf_${Date.now()}`,
          label: tag.label,
          value: tag.value || '点击编辑内容',
          icon: tag.icon || '🏷️',
          col: 1,
          row: 1,
          w,
          h: 1,
          cols: w,
        })
      }
    }
  }
  triggerAutoSave()
  refreshPreview()
}

function handleRemoveTagFromPalette(tag: any) {
  if (paperPreviewRef.value?.removeTagFromBasics) {
    paperPreviewRef.value.removeTagFromBasics(tag)
    triggerAutoSave()
    return
  }

  if (!resume.value || !resume.value.basics) return
  const b = resume.value.basics

  if (Array.isArray(b.grid_widgets_2d)) {
    b.grid_widgets_2d = b.grid_widgets_2d.filter((w: any) =>
      w.id !== tag.id &&
      (!tag.key || w.key !== tag.key || tag.key === 'custom') &&
      (!tag.type || w.type !== tag.type || tag.type === 'tag') &&
      w.label !== tag.label
    )
  }

  if (tag.id === 'core_name' || tag.type === 'name' || tag.key === 'name') {
    b.name = ''
  } else if (tag.id === 'core_label' || tag.type === 'label' || tag.key === 'label') {
    b.label = ''
  } else if (tag.id === 'core_photo' || tag.type === 'photo' || tag.key === 'photo') {
    b.photo = ''
    delete b.avatar
  } else if (tag.id === 'core_summary' || tag.type === 'summary' || tag.key === 'summary') {
    b.summary = ''
  } else {
    const standardKeys = ['phone', 'email', 'location', 'birthDate', 'github', 'blog', 'wechat']
    if (tag.key && standardKeys.includes(tag.key)) {
      b[tag.key] = ''
    } else if (tag.id && tag.id.startsWith('std_')) {
      const key = tag.id.replace('std_', '')
      b[key] = ''
    } else {
      const cfs = Array.isArray(b.custom_fields) ? b.custom_fields : []
      if (tag.id && tag.id.startsWith('cf_')) {
        const idx = parseInt(tag.id.replace('cf_', ''), 10)
        if (!isNaN(idx) && idx >= 0 && idx < cfs.length) {
          cfs.splice(idx, 1)
        } else {
          b.custom_fields = cfs.filter((cf: any) => cf.label !== tag.label)
        }
      } else {
        b.custom_fields = cfs.filter((cf: any) => cf.label !== tag.label)
      }
    }
  }

  triggerAutoSave()
  refreshPreview()
}

function handleCanvasResumeUpdate(newData: any) {
  resume.value = { ...newData }
  if (newData.section_order) {
    sectionOrder.value = [...newData.section_order]
  }
  triggerAutoSave()
  refreshPreview()
}

const route = useRoute()
const router = useRouter()

// 默认直接进入工作台 (Step 3)
const step = ref(3)
const loading = ref(false)
const error = ref('')
const successMsg = ref('')

// 简历标题与实时重命名
const resumeTitle = ref('未命名简历')

function handleSaveTitle() {
  if (!resumeId.value || !resumeTitle.value.trim()) return
  apiResume.update(resumeId.value, { title: resumeTitle.value.trim() }).catch(console.error)
}

// AI 定向参考助手与模板切换弹窗开关
const showAiCopilotDrawer = ref(false)
const showTemplateModal = ref(false)

async function handleJdBound(data: { raw: string; structured: any } | null) {
  if (data) {
    jdText.value = data.raw
    jdStructured.value = data.structured
    if (resume.value && resumeId.value) {
      resume.value = {
        ...resume.value,
        target_jd: data,
      }
      // 立即持久化到数据库，确保再次打开时 100% 自动恢复
      try {
        await apiResume.update(resumeId.value, {
          content: resume.value,
          template_id: templateId.value,
        })
      } catch (e) {
        console.error('保存绑定 JD 失败', e)
      }
    }
  } else {
    unmountJd()
  }
}

async function handleReferenceGenerated(payload: { referenceResume: any; structuredJd: any; rawJd: string }) {
  if (resume.value && resumeId.value) {
    resume.value = {
      ...resume.value,
      reference_resume: payload.referenceResume,
      target_jd: {
        raw: payload.rawJd,
        structured: payload.structuredJd,
      },
    }
    // 立即持久化到后端数据库
    try {
      await apiResume.update(resumeId.value, {
        content: resume.value,
        template_id: templateId.value,
      })
    } catch (e) {
      console.error('持久化参考简历失败', e)
    }
  }
}

function handleApplySectionItem(payload: { section: string; data: any; mode: 'replace' | 'append' }) {
  if (!resume.value) return
  const { section, data, mode } = payload
  let updated = data
  if (mode === 'append') {
    const existing = Array.isArray(resume.value[section]) ? resume.value[section] : []
    const toAdd = Array.isArray(data) ? data : [data]
    updated = [...existing, ...toAdd]
  }
  resume.value = {
    ...resume.value,
    [section]: updated,
  }
  // 自动切换到对应模块 tab，让用户立刻看到填入的卡片表单
  if (allTabs.value.some(t => t.id === section)) {
    activeTab.value = section
  }
  triggerAutoSave()
  refreshPreview()
}

function handleReplaceAll(fullResume: any) {
  if (!resume.value) return
  resume.value = { ...resume.value, ...fullResume }
  triggerAutoSave()
  refreshPreview()
}

async function selectTemplate(id: number) {
  templateId.value = id
  if (resume.value) {
    resume.value.template_id = id
    triggerAutoSave()
  }
  showTemplateModal.value = false
  await refreshPreview()
}

// Step 1 - JD & 非线性 JD 插件抽屉
const jdText = ref('')
const ocrNotice = ref('')
const jdStructured = ref<any>(null)
const jdParsing = ref(false)
let jdParsePromise: Promise<any> | null = null
const matches = ref<any[]>([])
const usedSource = ref('')
const showJdDrawer = ref(false)

// 创建新简历 (mode: 'blank' 纯白板 | 'kb' 知识库预填)
const showNewMenu = ref(false)

async function createResumeDraft(mode: 'blank' | 'kb' = 'blank') {
  showNewMenu.value = false
  showHistory.value = false
  error.value = ''
  loading.value = true
  try {
    const tpls = await apiTemplates.list()
    templates.value = tpls
    const defTpl = tpls[0]?.id || 1
    templateId.value = defTpl

    let initialContent: any = null
    let draftTitle = '通用母简历草稿'

    if (mode === 'blank') {
      draftTitle = '全新空白简历'
      initialContent = {
        is_blank: true,
        basics: {
          name: '',
          label: '',
          email: '',
          phone: '',
          location: '',
          custom_fields: [],
        },
        education: [],
        skills: [],
        projects: [],
        experience: [],
        highlights: [],
        custom_sections: [],
      }
    }

    const draft = await apiResume.createDraft({
      template_id: defTpl,
      title: draftTitle,
      initial_content: initialContent,
    })
    resumeId.value = draft.id
    resume.value = draft.content || {}
    resumeTitle.value = draft.title || draftTitle
    step.value = 3
    updateUrlParams(draft.id, null, 3)
    await refreshPreview()
    successMsg.value = mode === 'blank' ? '✓ 已创建全新空白简历（白板）！' : '✓ 已基于知识库创建简历草稿！'
    setTimeout(() => { successMsg.value = '' }, 2500)
  } catch (err: any) {
    error.value = '创建简历失败：' + err.message
  } finally {
    loading.value = false
  }
}

// 保持兼容旧调用
const startBlankResume = (mode: 'blank' | 'kb' = 'blank') => createResumeDraft(mode)

// 清空当前简历为全新空白白板
function resetCurrentToBlank() {
  if (!confirm('确定要清空当前简历的所有模块内容，重置为一张空白白板吗？（操作后将重新开始）')) return
  if (!resume.value) return
  resume.value = {
    basics: {
      name: '',
      label: '',
      email: '',
      phone: '',
      location: '',
      custom_fields: [],
    },
    education: [],
    skills: [],
    projects: [],
    experience: [],
    highlights: [],
    custom_sections: [],
  }
  handleManualSave()
  successMsg.value = '✓ 当前简历已清空重置为全新白板！'
  setTimeout(() => { successMsg.value = '' }, 2500)
}

// 卸载/解绑已挂载的 JD
async function unmountJd() {
  jdText.value = ''
  jdStructured.value = null
  matches.value = []
  usedSource.value = ''
  linkedPositionId.value = null
  linkedCompanyId.value = null
  if (resume.value) {
    delete resume.value.target_jd
    triggerAutoSave()
  }
  updateUrlParams(resumeId.value, null, step.value)
}

// 在微调台中即时挂载/解析 JD 并持久化到简历数据中
async function mountJdFromDrawer() {
  if (!jdText.value.trim()) return
  jdParsing.value = true
  error.value = ''
  try {
    const res = await apiJd.structurize(jdText.value)
    jdStructured.value = res
    if (resume.value) {
      resume.value.target_jd = {
        raw: jdText.value,
        structured: res,
      }
      triggerAutoSave()
    }
  } catch (err: any) {
    console.warn('JD 结构化失败', err)
  } finally {
    jdParsing.value = false
  }
}



// Step 2 - Template
const templates = ref<any[]>([])
const templateId = ref<number | null>(null)

// Step 3 - Resume state & Magic Workbench
const resumeId = ref<number | null>(null)
const resume = ref<any>(null)
const sectionLoading = ref<string | null>(null)
const activeTab = ref('basics')

// 自动保存状态
const isSaving = ref(false)
const saveStatusText = ref('所有更改已自动保存')
let autoSaveTimer: any = null

// 侧边栏与顶部向导收缩状态 (支持沉浸式最大化工作台)
const isSidePanelCollapsed = ref(false)
const isTopHeaderCollapsed = ref(false)

// 三栏左右自由拖拽调整宽度系统 (对齐 Magic-Resume)
const workbenchContainerRef = ref<HTMLElement | null>(null)
const isDragging = ref(false)
const dragType = ref<'left' | 'center' | null>(null)
const startMouseX = ref(0)
const startLeftPercent = ref(22)
const startCenterPercent = ref(38)
const startCollapsedCenterPercent = ref(50)

const savedLeft = localStorage.getItem('ai_qiuzhi_panel_left_pct')
const savedCenter = localStorage.getItem('ai_qiuzhi_panel_center_pct')
const savedCollapsedCenter = localStorage.getItem('ai_qiuzhi_panel_collapsed_center_pct')

const leftPercent = ref(savedLeft ? parseFloat(savedLeft) : 22)
const centerPercent = ref(savedCenter ? parseFloat(savedCenter) : 38)
const collapsedCenterPercent = ref(savedCollapsedCenter ? parseFloat(savedCollapsedCenter) : 50)

const isDesktop = ref(typeof window !== 'undefined' ? window.innerWidth >= 1024 : true)
function handleWindowResize() {
  isDesktop.value = typeof window !== 'undefined' ? window.innerWidth >= 1024 : true
}

function startDrag(type: 'left' | 'center', e: MouseEvent) {
  isDragging.value = true
  dragType.value = type
  startMouseX.value = e.clientX
  startLeftPercent.value = leftPercent.value
  startCenterPercent.value = centerPercent.value
  startCollapsedCenterPercent.value = collapsedCenterPercent.value

  try {
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'col-resize'
  } catch (e) {
    // ignore
  }

  window.addEventListener('mousemove', onDragging)
  window.addEventListener('mouseup', stopDrag)
}

function onDragging(e: MouseEvent) {
  if (!isDragging.value || !workbenchContainerRef.value) return
  const containerRect = workbenchContainerRef.value.getBoundingClientRect()
  const totalWidth = containerRect.width
  if (totalWidth <= 0) return

  const deltaX = e.clientX - startMouseX.value
  const deltaPercent = (deltaX / totalWidth) * 100

  if (dragType.value === 'left') {
    // 限制左栏宽度在 14% 到 36% 之间
    const newLeft = Math.max(14, Math.min(36, startLeftPercent.value + deltaPercent))
    leftPercent.value = Math.round(newLeft * 10) / 10
  } else if (dragType.value === 'center') {
    if (isSidePanelCollapsed.value) {
      // 侧栏收起时，编辑区与预览区在 25% 到 75% 之间调节
      const newCenter = Math.max(25, Math.min(75, startCollapsedCenterPercent.value + deltaPercent))
      collapsedCenterPercent.value = Math.round(newCenter * 10) / 10
    } else {
      // 侧栏存在时，中栏可调节，且确保右侧预览区至少保留 22% 宽度
      const maxCenter = Math.min(60, 100 - leftPercent.value - 22)
      const newCenter = Math.max(25, Math.min(maxCenter, startCenterPercent.value + deltaPercent))
      centerPercent.value = Math.round(newCenter * 10) / 10
    }
  }
}

function stopDrag() {
  if (!isDragging.value) return
  isDragging.value = false
  dragType.value = null

  try {
    document.body.style.userSelect = ''
    document.body.style.cursor = ''
    localStorage.setItem('ai_qiuzhi_panel_left_pct', String(leftPercent.value))
    localStorage.setItem('ai_qiuzhi_panel_center_pct', String(centerPercent.value))
    localStorage.setItem('ai_qiuzhi_panel_collapsed_center_pct', String(collapsedCenterPercent.value))
  } catch (e) {
    // ignore
  }

  window.removeEventListener('mousemove', onDragging)
  window.removeEventListener('mouseup', stopDrag)
}

function resetPanelWidths() {
  leftPercent.value = 22
  centerPercent.value = 38
  collapsedCenterPercent.value = 50
  try {
    localStorage.removeItem('ai_qiuzhi_panel_left_pct')
    localStorage.removeItem('ai_qiuzhi_panel_center_pct')
    localStorage.removeItem('ai_qiuzhi_panel_collapsed_center_pct')
  } catch (e) {
    // ignore
  }
}

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize)
  window.removeEventListener('keydown', handleGlobalKeyDown)
  window.removeEventListener('mousemove', onDragging)
  window.removeEventListener('mouseup', stopDrag)
})

// 自定义模块弹窗
const showAddSectionModal = ref(false)
const newSectionTitle = ref('')
const newSectionIcon = ref('📌')

// 历史草稿列表抽屉
const showHistory = ref(false)
const historyList = ref<any[]>([])
const loadingHistory = ref(false)

// Step 4 - Link to company
const linkedCompanyId = ref<number | null>(null)
const linkedPositionId = ref<number | null>(null)

// 基础模块清单
const CORE_SECTIONS = [
  { id: 'basics', label: '基本资料', icon: '👤' },
  { id: 'education', label: '教育经历', icon: '🎓' },
  { id: 'skills', label: '专业技能', icon: '⚡' },
  { id: 'experience', label: '工作经历', icon: '💼' },
  { id: 'projects', label: '项目经历', icon: '🚀' },
  { id: 'highlights', label: '个人亮点', icon: '🌟' },
]

const sectionOrder = ref<string[]>([
  'basics',
  'education',
  'skills',
  'experience',
  'projects',
  'highlights',
])

const sectionVisibility = ref<Record<string, boolean>>({
  basics: true,
  education: true,
  skills: true,
  experience: true,
  projects: true,
  highlights: true,
})

const resumeThemeColor = ref<'classic' | 'indigo' | 'slate' | 'emerald'>('classic')

// 已删除的基础模块列表 (持久化在 resume.content.deleted_sections)
const deletedSections = ref<string[]>([])

// 动态合并所有模块标签（已剔除删除的基础模块 + 自定义）并按 sectionOrder 排序
const allTabs = computed(() => {
  const availableCore = CORE_SECTIONS.filter((s) => !deletedSections.value.includes(s.id))
  const tabs = [...availableCore]
  if (resume.value?.custom_sections) {
    for (const cs of resume.value.custom_sections) {
      tabs.push({
        id: `custom_${cs.id}`,
        label: cs.title,
        icon: cs.icon || '📌',
      })
    }
  }

  if (sectionOrder.value.length) {
    tabs.sort((a, b) => {
      const ia = sectionOrder.value.indexOf(a.id)
      const ib = sectionOrder.value.indexOf(b.id)
      if (ia === -1 && ib === -1) return 0
      if (ia === -1) return 1
      if (ib === -1) return -1
      return ia - ib
    })
  }

  return tabs
})

// 可恢复/重新添加的基础模块列表
const restorableCoreSections = computed(() => {
  return CORE_SECTIONS.filter((s) => deletedSections.value.includes(s.id))
})

// 删除模块逻辑（支持基础模块与自定义模块）
function deleteSection(id: string) {
  if (id.startsWith('custom_')) {
    const rawId = id.replace('custom_', '')
    handleRemoveCustomSection(rawId)
    return
  }

  // 基础模块删除
  if (!deletedSections.value.includes(id)) {
    deletedSections.value.push(id)
  }
  sectionOrder.value = sectionOrder.value.filter((s) => s !== id)

  if (resume.value) {
    resume.value.deleted_sections = [...deletedSections.value]
    resume.value.section_order = [...sectionOrder.value]
  }

  // 若当前正在查看被删除的模块，自动切换到下一个可用模块
  if (activeTab.value === id) {
    const remaining = allTabs.value.filter((t) => t.id !== id)
    if (remaining.length > 0) {
      activeTab.value = remaining[0].id
    }
  }

  triggerAutoSave()
  refreshPreview()
}

function confirmDeleteSection(id: string, label: string) {
  if (confirm(`确定要从简历中删除【${label}】模块吗？\n删除后该模块将从排版中隐去，后续可随时点击【➕ 添加新模块】一键恢复。`)) {
    deleteSection(id)
  }
}

// 恢复已删除的基础模块
function restoreSection(id: string) {
  deletedSections.value = deletedSections.value.filter((s) => s !== id)
  if (!sectionOrder.value.includes(id)) {
    sectionOrder.value.push(id)
  }
  sectionVisibility.value[id] = true

  if (resume.value) {
    resume.value.deleted_sections = [...deletedSections.value]
    resume.value.section_order = [...sectionOrder.value]
    resume.value.section_visibility = { ...sectionVisibility.value }
  }

  activeTab.value = id
  triggerAutoSave()
  refreshPreview()
}

function toggleSectionVisibility(id: string) {
  sectionVisibility.value[id] = sectionVisibility.value[id] === false ? true : false
  if (resume.value) {
    resume.value.section_visibility = { ...sectionVisibility.value }
  }
  triggerAutoSave()
}

function moveSection(idx: number, dir: -1 | 1) {
  const target = idx + dir
  if (target < 0 || target >= allTabs.value.length) return
  const currentList = [...allTabs.value]
  const [moved] = currentList.splice(idx, 1)
  currentList.splice(target, 0, moved)
  sectionOrder.value = currentList.map((t) => t.id)
  if (resume.value) {
    resume.value.section_order = [...sectionOrder.value]
  }
  triggerAutoSave()
}

function handleThemeChange(color: 'classic' | 'indigo' | 'slate' | 'emerald') {
  resumeThemeColor.value = color
  if (resume.value) {
    resume.value.theme_color = color
  }
  triggerAutoSave()
}

const canNext = computed(() => {
  switch (step.value) {
    case 1: return jdText.value.trim().length > 10
    case 2: return templateId.value != null
    case 3: return resumeId.value != null
    default: return true
  }
})

function updateUrlParams(rid: number | null, posId: number | null, currentStep: number) {
  const query: Record<string, any> = {}
  if (rid) query.resume_id = String(rid)
  if (posId) query.position_id = String(posId)
  if (currentStep > 1) query.step = String(currentStep)
  router.replace({ query })
}

// 实时预览 HTML 与单页缩放控制
const previewMode = ref<'live' | 'template'>('live')
const previewHtml = ref('')
const templatePreview = ref<any>(null)
const previewScale = ref(1.0)
const isFittingPage = ref(false)

function fitToOnePage() {
  isFittingPage.value = true
  // 智能微调比例，使溢出边缘刚好收敛于一页
  previewScale.value = previewScale.value === 0.92 ? 1.0 : 0.92
  setTimeout(() => {
    isFittingPage.value = false
  }, 400)
}

// 刷新右侧实时 A4 预览
async function refreshPreview() {
  if (!resumeId.value || !resume.value) return
  const tid = templateId.value || resume.value?.template_id || (templates.value[0]?.id)
  if (!tid) return
  try {
    const renderResult = await apiTemplates.render(tid, resume.value)
    previewHtml.value = renderResult.html
  } catch (err: any) {
    console.warn('预览渲染失败', err)
  }
}



// 防抖自动保存
function triggerAutoSave() {
  if (!resumeId.value || !resume.value) return
  isSaving.value = true
  saveStatusText.value = '正在自动保存…'

  clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(async () => {
    try {
      await apiResume.update(resumeId.value!, {
        content: resume.value,
        template_id: templateId.value,
      })
      isSaving.value = false
      saveStatusText.value = '所有更改已自动保存'
      refreshPreview()
    } catch (err: any) {
      isSaving.value = false
      saveStatusText.value = '保存失败，请稍候重试'
    }
  }, 1000)
}

const isFinalizing = ref(false)

// 手动保存草稿（支持保存按钮与 Cmd+S / Ctrl+S 快捷键）
async function handleManualSave() {
  if (!resumeId.value || !resume.value) return
  isSaving.value = true
  saveStatusText.value = '正在手动保存…'
  clearTimeout(autoSaveTimer)
  try {
    await apiResume.update(resumeId.value, {
      content: resume.value,
      template_id: templateId.value,
      title: resumeTitle.value.trim() || undefined,
    })
    isSaving.value = false
    saveStatusText.value = '所有更改已手动保存 ✓'
    successMsg.value = '✓ 简历草稿已成功保存！'
    setTimeout(() => {
      if (successMsg.value.includes('已成功保存')) successMsg.value = ''
    }, 2500)
    await refreshPreview()
  } catch (err: any) {
    isSaving.value = false
    saveStatusText.value = '保存失败'
    error.value = '保存失败：' + err.message
  }
}

// 全局快捷键监听 (Cmd+S / Ctrl+S)
function handleGlobalKeyDown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    handleManualSave()
  }
}

// 一键完成并前往求职工作台进行后续操作
async function handleFinalizeAndGoWorkspace() {
  if (!resumeId.value) return
  isFinalizing.value = true
  error.value = ''
  try {
    // 1. 立即同步当前最新内容与标题
    if (resume.value) {
      await apiResume.update(resumeId.value, {
        content: resume.value,
        template_id: templateId.value,
        title: resumeTitle.value.trim() || undefined,
      })
    }
    // 2. 调用 finalize 建立快照与求职工作台任务自动绑定
    await apiResume.finalize(resumeId.value, '定稿')
    // 3. 页面直接跳转到求职工作台，后续操作（投递流转、AI 押题、PDF 下载）统一在工作台开展
    await router.push({
      path: '/workspace',
      query: {
        focus_resume_id: String(resumeId.value),
        from_finalized: '1',
      },
    })
  } catch (err: any) {
    error.value = '定稿并前往求职工作台失败：' + err.message
  } finally {
    isFinalizing.value = false
  }
}

function handleSectionChange(secName: string, secData: any) {
  if (resume.value) {
    resume.value[secName] = secData
  }
  triggerAutoSave()
}

// 历史草稿相关
async function loadHistory() {
  loadingHistory.value = true
  try {
    const list = await apiResume.list()
    historyList.value = list
  } catch (err: any) {
    console.error('获取历史简历失败', err)
  } finally {
    loadingHistory.value = false
  }
}

function openHistory() {
  showHistory.value = true
  loadHistory()
}

async function selectHistoryResume(item: any) {
  showHistory.value = false
  await loadResumeById(item.id, item.position_id || null, 3)
}

async function deleteHistoryResume(id: number, e: Event) {
  e.stopPropagation()
  if (!confirm('确定要删除这份简历草稿吗？')) return
  try {
    await apiResume.remove(id)
    historyList.value = historyList.value.filter((x: any) => x.id !== id)
    if (resumeId.value === id) {
      resetToNew()
    }
  } catch (err: any) {
    error.value = '删除失败：' + err.message
  }
}

async function resetToNew() {
  await startBlankResume()
}

async function loadResumeById(rid: number, posId: number | null = null, targetStep = 3) {
  resumeId.value = rid
  if (posId) linkedPositionId.value = posId
  loading.value = true
  error.value = ''
  try {
    const r = await apiResume.get(rid)
    resume.value = r.content || {}
    resumeTitle.value = r.title || '未命名简历'
    templateId.value = r.template_id
    if (r.position_id) {
      linkedPositionId.value = r.position_id
    }
    // 恢复持久化挂载的 target_jd
    if (r.content?.target_jd) {
      jdText.value = r.content.target_jd.raw || ''
      jdStructured.value = r.content.target_jd.structured || null
    }
    if (r.content?.section_visibility) {
      sectionVisibility.value = { ...sectionVisibility.value, ...r.content.section_visibility }
    }
    if (r.content?.section_order && Array.isArray(r.content.section_order)) {
      sectionOrder.value = r.content.section_order
    }
    if (r.content?.deleted_sections && Array.isArray(r.content.deleted_sections)) {
      deletedSections.value = [...r.content.deleted_sections]
    } else {
      deletedSections.value = []
    }
    if (r.content?.theme_color) {
      resumeThemeColor.value = r.content.theme_color
    }
    const tpls = await apiTemplates.list()
    templates.value = tpls

    const activePosId = linkedPositionId.value
    if (activePosId) {
      try {
        const positions = await apiWorkspace.positions.list()
        const pos = positions.find((p: any) => p.id === Number(activePosId))
        if (pos) {
          linkedCompanyId.value = pos.company_id
          // 仅在简历本身未绑定 target_jd 时，才以关联岗位中的 JD 作为备选填充
          if (!r.content?.target_jd && pos.jd_structured?.title) {
            jdStructured.value = pos.jd_structured
            jdText.value = pos.jd_raw || ''
            resume.value.target_jd = {
              raw: pos.jd_raw || '',
              structured: pos.jd_structured,
            }
          }
        }
      } catch (e) {
        console.warn('加载关联岗位信息失败', e)
      }
    }

    step.value = 3
    updateUrlParams(rid, linkedPositionId.value, 3)
    await refreshPreview()
  } catch (err: any) {
    error.value = '加载简历失败：' + err.message
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  window.addEventListener('resize', handleWindowResize)
  window.addEventListener('keydown', handleGlobalKeyDown)
  handleWindowResize()

  const resumeIdParam = route.query.resume_id as string
  const positionIdParam = route.query.position_id as string
  const stepParam = route.query.step as string

  if (positionIdParam) {
    linkedPositionId.value = Number(positionIdParam)
  }

  if (resumeIdParam) {
    const targetStep = stepParam ? parseInt(stepParam, 10) : 3
    await loadResumeById(Number(resumeIdParam), linkedPositionId.value, targetStep)
  } else if (positionIdParam) {
    try {
      loading.value = true
      const r = await apiResume.getByPosition(Number(positionIdParam))
      if (r) {
        await loadResumeById(r.id, Number(positionIdParam), stepParam ? parseInt(stepParam, 10) : 3)
      } else {
        await startBlankResume()
      }
    } catch (err: any) {
      console.warn('获取岗位对应简历失败', err)
      await startBlankResume()
    } finally {
      loading.value = false
    }
  } else {
    // 默认直接进入简历编辑工作台！优先载入已有最新草稿，否则一键创建母简历
    try {
      loading.value = true
      const list = await apiResume.list()
      if (list && list.length > 0) {
        await loadResumeById(list[0].id, list[0].position_id || null, 3)
      } else {
        await startBlankResume()
      }
    } catch (e) {
      await startBlankResume()
    } finally {
      loading.value = false
    }
  }
})

async function handleOcr(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  error.value = ''
  loading.value = true
  try {
    const r = await apiOcr.parse(file)
    jdText.value = (jdText.value + '\n' + r.text).trim()
  } catch (err: any) {
    ocrNotice.value = 'OCR 未配置：' + err.message + '。请直接粘贴 JD 文本。'
  } finally {
    loading.value = false
  }
}

async function step1Next() {
  error.value = ''
  step.value = 2
  updateUrlParams(resumeId.value, linkedPositionId.value, 2)

  if (!templates.value.length) {
    try {
      templates.value = await apiTemplates.list()
    } catch (e) {
      console.warn('加载模板失败', e)
    }
  }

  if (!jdStructured.value && jdText.value.trim()) {
    jdParsing.value = true
    jdParsePromise = apiJd.structurize(jdText.value)
      .then((r) => {
        jdStructured.value = r
        return r
      })
      .catch((err) => {
        console.warn('JD 异步结构化失败，将降级处理', err)
        return null
      })
      .finally(() => {
        jdParsing.value = false
      })
  }
}

async function step2Next() {
  error.value = ''
  loading.value = true
  try {
    if (jdParsing.value && jdParsePromise) {
      await jdParsePromise
    }

    const draftTitle = `${jdStructured.value?.title || '未命名'} 简历草稿`
    const draft = await apiResume.createDraft({ template_id: templateId.value, title: draftTitle })
    resumeId.value = draft.id
    resume.value = draft.content || {}
    step.value = 3
    updateUrlParams(draft.id, linkedPositionId.value, 3)
    await refreshPreview()
  } catch (err: any) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function aiGenerate() {
  if (!resumeId.value) return
  error.value = ''
  loading.value = true
  try {
    const result = await apiResume.aiGenerate(resumeId.value, jdText.value)
    matches.value = result.matches || []
    usedSource.value = result.used_source || ''
    resume.value = result.resume
    await refreshPreview()
  } catch (err: any) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function handleRegenerateSection(section: string) {
  if (!resumeId.value) return
  sectionLoading.value = section
  error.value = ''
  try {
    const result = await apiResume.regenerateSection(resumeId.value, section, jdText.value, {
      jd_structured: jdStructured.value,
      matches: matches.value,
    })
    if (resume.value) {
      resume.value[section] = result.content
    }
    await refreshPreview()
  } catch (err: any) {
    error.value = 'AI 建议失败：' + err.message
  } finally {
    sectionLoading.value = null
  }
}

function handleAddCustomSection() {
  if (!newSectionTitle.value.trim() || !resume.value) return
  if (!resume.value.custom_sections) resume.value.custom_sections = []
  const id = 'sec_' + Date.now()
  resume.value.custom_sections.push({
    id,
    title: newSectionTitle.value.trim(),
    icon: newSectionIcon.value || '📌',
    items: [],
  })
  activeTab.value = `custom_${id}`
  showAddSectionModal.value = false
  newSectionTitle.value = ''
  triggerAutoSave()
}

function handleRemoveCustomSection(secId: string) {
  if (!confirm('确认删除该自定义板块？') || !resume.value?.custom_sections) return
  resume.value.custom_sections = resume.value.custom_sections.filter((s: any) => s.id !== secId)
  activeTab.value = 'basics'
  triggerAutoSave()
}

async function step3Next() {
  if (!resumeId.value) return
  step.value = 4
  updateUrlParams(resumeId.value, linkedPositionId.value, 4)
}

function handleLinkSelect(companyId: number, positionId: number) {
  linkedCompanyId.value = companyId
  linkedPositionId.value = positionId
}

async function linkToPosition() {
  if (!resumeId.value || !linkedPositionId.value) return
  try {
    await apiResume.linkPosition(resumeId.value, linkedPositionId.value)
  } catch (err: any) {
    error.value = err.message
  }
}

async function step4Next() {
  error.value = ''
  loading.value = true
  try {
    if (linkedPositionId.value) {
      await linkToPosition()
    }
    await refreshPreview()
    step.value = 5
    updateUrlParams(resumeId.value, linkedPositionId.value, 5)
  } catch (err: any) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function doExport(format: 'html' | 'pdf' | 'docx') {
  if (!resumeId.value) return
  loading.value = true
  try {
    const blob = await apiResume.export(resumeId.value, format, templateId.value ?? undefined)
    downloadBlob(blob, `resume-${resumeId.value}.${format}`)
  } catch (err: any) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function doFinalize() {
  if (!resumeId.value) return
  try {
    await apiResume.finalize(resumeId.value, '定稿')
    successMsg.value = '已保存到工作台！'
    setTimeout(() => (successMsg.value = ''), 3000)
  } catch (err: any) {
    error.value = err.message
  }
}
</script>

<template>
  <div class="w-full max-w-[1720px] mx-auto h-full flex-1 min-h-0 flex flex-col transition-all duration-300">
    <!-- 历史草稿抽屉 -->
    <div v-if="showHistory" class="fixed inset-0 z-50 bg-black/40 flex justify-end">
      <div class="bg-white w-full max-w-md h-full shadow-2xl flex flex-col">
        <div class="p-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 class="font-bold text-base">简历草稿箱与历史记录</h3>
            <p class="text-xs text-slate-400">点击任意一份可立即恢复微调</p>
          </div>
          <button class="text-slate-400 hover:text-slate-700 text-lg px-2" @click="showHistory = false">✕</button>
        </div>

        <!-- 历史抽屉内快捷新建操作条 -->
        <div class="p-3 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
          <button
            class="flex-1 py-1.5 px-2 bg-white hover:bg-primary-50 border border-slate-200 hover:border-primary-300 rounded-lg text-xs text-slate-700 hover:text-primary-700 font-medium flex items-center justify-center gap-1 transition shadow-2xs"
            @click="createResumeDraft('blank')"
          >
            <span>📄 新建空白白板</span>
          </button>
          <button
            class="flex-1 py-1.5 px-2 bg-white hover:bg-indigo-50 border border-slate-200 hover:border-indigo-300 rounded-lg text-xs text-slate-700 hover:text-indigo-700 font-medium flex items-center justify-center gap-1 transition shadow-2xs"
            @click="createResumeDraft('kb')"
          >
            <span>👤 从知识库预填</span>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-4 space-y-3">
          <div v-if="loadingHistory" class="text-center py-8 text-slate-400 text-sm">加载中…</div>
          <div v-else-if="!historyList.length" class="text-center py-8 text-slate-400 text-sm">
            暂无已保存的简历草稿
          </div>
          <div
            v-for="item in historyList"
            :key="item.id"
            class="card border border-slate-200 hover:border-primary-400 cursor-pointer transition-colors p-3.5"
            :class="resumeId === item.id ? 'ring-2 ring-primary-500 bg-primary-50/20' : ''"
            @click="selectHistoryResume(item)"
          >
            <div class="flex items-center justify-between">
              <span class="font-medium text-sm text-slate-800 line-clamp-1">{{ item.title || '未命名简历' }}</span>
              <span class="badge ml-2 shrink-0" :class="item.status === 'final' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">
                {{ item.status === 'final' ? '已定稿' : '草稿' }}
              </span>
            </div>
            <div class="text-xs text-slate-400 mt-2 flex items-center justify-between">
              <span>{{ item.updated_at ? item.updated_at.replace('T', ' ').slice(0, 16) : '' }}</span>
              <button
                class="text-red-500 hover:text-red-700 text-xs px-1 hover:underline"
                @click="deleteHistoryResume(item.id, $event)"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="error" class="shrink-0 mb-2 p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">{{ error }}</div>
    <div v-if="successMsg" class="shrink-0 mb-2 p-2.5 rounded-lg bg-green-50 border border-green-200 text-green-700 text-xs">{{ successMsg }}</div>

    <!-- 简历沉浸式微调工作台 (直接进入，无冗余向导流程) -->
    <div class="flex-1 min-h-0 flex flex-col space-y-2.5">
      
      <!-- 顶部主操作条 -->
      <div class="shrink-0 flex items-center justify-between bg-white px-3.5 py-2 rounded-xl border border-slate-200 shadow-2xs">
        <div class="flex items-center gap-2 sm:gap-3">
          <!-- 侧边栏展开/收起切换按钮 -->
          <button
            class="px-2.5 py-1 rounded-lg text-xs font-medium border transition flex items-center gap-1.5 select-none"
            :class="isSidePanelCollapsed ? 'bg-primary-50 border-primary-300 text-primary-700 hover:bg-primary-100' : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'"
            :title="isSidePanelCollapsed ? '展开左侧模块编排栏' : '收起左侧模块栏，编辑与预览扩展占满'"
            @click="isSidePanelCollapsed = !isSidePanelCollapsed"
          >
            <span>{{ isSidePanelCollapsed ? '📐' : '«' }}</span>
            <span>{{ isSidePanelCollapsed ? '展开左栏' : '收起左栏' }}</span>
          </button>

          <span class="w-px h-3.5 bg-slate-200 hidden sm:inline"></span>

          <!-- 简历标题实时编辑 -->
          <div class="flex items-center gap-1.5">
            <span class="text-sm">📄</span>
            <input
              v-model="resumeTitle"
              class="font-bold text-sm text-slate-800 hover:bg-slate-50 focus:bg-white px-2 py-0.5 rounded border border-transparent focus:border-slate-300 outline-hidden max-w-[150px] sm:max-w-[200px] truncate"
              placeholder="简历标题"
              title="点击可直接修改简历标题"
              @blur="handleSaveTitle"
              @keyup.enter="handleSaveTitle"
            />
          </div>

          <!-- 自动保存指示灯 -->
          <div class="flex items-center gap-1.5 text-xs text-slate-400">
            <span class="w-2 h-2 rounded-full shrink-0" :class="isSaving ? 'bg-amber-400 animate-pulse' : 'bg-emerald-500'"></span>
            <span class="truncate max-w-[130px] hidden md:inline">{{ saveStatusText }}</span>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <!-- 目标岗位与 AI 定向参考助手 唤起按钮 -->
          <button
            class="px-3 py-1 text-xs rounded-lg border font-bold transition flex items-center gap-1.5 shadow-2xs"
            :class="(resume?.target_jd || jdStructured || jdText.trim())
              ? 'bg-gradient-to-r from-indigo-50 to-purple-50 border-indigo-300 text-indigo-800 hover:border-indigo-400'
              : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'"
            title="展开/收起【目标岗位 JD OCR、知识库素材挑选与 AI 定向参考】助手"
            @click="showAiCopilotDrawer = !showAiCopilotDrawer"
          >
            <span>🎯</span>
            <span>{{ (resume?.target_jd?.structured?.title || jdStructured?.title) ? `已绑定: ${(resume?.target_jd?.structured?.title || jdStructured?.title)}` : '目标岗位与 AI 参考' }}</span>
            <span v-if="(resume?.target_jd?.structured?.skills_required?.length || jdStructured?.skills_required?.length)" class="bg-indigo-600 text-white text-[10px] px-1.5 py-0.2 rounded-full font-mono">
              {{ (resume?.target_jd?.structured?.skills_required?.length || jdStructured?.skills_required?.length) }}
            </span>
          </button>

          <!-- 更换模板弹窗按钮 -->
          <button
            class="btn-secondary !text-xs !py-1"
            title="快速切换简历排版模板"
            @click="showTemplateModal = true"
          >
            🎨 更换模板
          </button>

          <!-- 显式【💾 保存草稿】按钮 (支持快捷键 Cmd+S) -->
          <button
            class="btn-secondary !text-xs !py-1 flex items-center gap-1 font-medium text-slate-700 hover:text-primary-700 hover:border-primary-300 transition"
            :disabled="isSaving"
            title="快捷键 Cmd+S / Ctrl+S 立即保存当前草稿"
            @click="handleManualSave"
          >
            <span v-if="isSaving" class="animate-spin text-primary-500">⏳</span>
            <span v-else>💾</span>
            <span>保存草稿</span>
            <kbd class="hidden sm:inline-block ml-0.5 px-1 py-0.2 text-[9px] bg-slate-100 text-slate-500 rounded border border-slate-200 font-mono">⌘S</kbd>
          </button>

          <!-- 导出 PDF -->
          <button
            class="btn-secondary !text-xs !py-1 flex items-center gap-1"
            title="导出为 A4 PDF 或打印"
            @click="doExport('pdf')"
          >
            <span>📥 PDF</span>
          </button>

          <span class="w-px h-3.5 bg-slate-200 hidden sm:inline"></span>

          <!-- 📁 草稿与历史记录 -->
          <button class="btn-secondary !text-xs !py-1 flex items-center gap-1" @click="openHistory" title="管理所有简历草稿与历史记录">
            <span>📁 草稿箱</span>
          </button>

          <!-- ＋ 新建简历 / 白板 下拉菜单 -->
          <div class="relative">
            <button
              class="btn-secondary !text-xs !py-1 text-primary-600 border-primary-200 hover:bg-primary-50 flex items-center gap-1 font-medium"
              title="新建简历草稿或更换全新空白简历"
              @click="showNewMenu = !showNewMenu"
            >
              <span>＋ 新建</span>
              <span class="text-[9px]">▾</span>
            </button>

            <!-- 点击外部关闭透明遮罩 -->
            <div v-if="showNewMenu" class="fixed inset-0 z-40" @click="showNewMenu = false"></div>

            <div
              v-if="showNewMenu"
              class="absolute right-0 top-full mt-1.5 w-56 bg-white rounded-xl shadow-xl border border-slate-200 py-1 z-50 text-xs animation-fade-in"
              @click="showNewMenu = false"
            >
              <button
                class="w-full text-left px-3 py-2 hover:bg-slate-50 flex items-start gap-2.5 text-slate-700 transition"
                @click="createResumeDraft('blank')"
              >
                <span class="text-base mt-0.5">📄</span>
                <div>
                  <div class="font-bold text-slate-800">新建空白简历 (全新白板)</div>
                  <div class="text-[10px] text-slate-400 leading-tight">不预填数据，干干净净从零编写</div>
                </div>
              </button>
              <button
                class="w-full text-left px-3 py-2 hover:bg-slate-50 flex items-start gap-2.5 text-slate-700 transition"
                @click="createResumeDraft('kb')"
              >
                <span class="text-base mt-0.5">👤</span>
                <div>
                  <div class="font-bold text-slate-800">从知识库预填新建</div>
                  <div class="text-[10px] text-slate-400 leading-tight">自动带入个人资产库技能与经历</div>
                </div>
              </button>
              <div class="border-t border-slate-100 my-1"></div>
              <button
                class="w-full text-left px-3 py-2 hover:bg-red-50 text-red-600 flex items-start gap-2.5 transition"
                @click="resetCurrentToBlank"
              >
                <span class="text-base mt-0.5">🧹</span>
                <div>
                  <div class="font-bold text-red-700">清空当前简历为白板</div>
                  <div class="text-[10px] text-red-400 leading-tight">抹平当前所有模块重新开始</div>
                </div>
              </button>
            </div>
          </div>

          <span class="w-px h-3.5 bg-slate-200 hidden sm:inline"></span>

          <!-- 🚀【完成并前往求职工作台】核心主按钮 -->
          <button
            class="!text-xs !py-1.5 px-3.5 bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-700 hover:to-indigo-700 text-white rounded-lg font-semibold shadow-xs flex items-center gap-1.5 transition-all active:scale-98"
            :disabled="isFinalizing"
            title="保存定稿并直接进入求职工作台，在工作台统一跟踪投递链路、AI 押题演练与 PDF 归档"
            @click="handleFinalizeAndGoWorkspace"
          >
            <span v-if="isFinalizing" class="animate-spin">⏳</span>
            <span v-else>🚀</span>
            <span>{{ isFinalizing ? '定稿中…' : '完成并前往求职工作台' }}</span>
          </button>
        </div>
      </div>

      <!-- 目标岗位与 AI 定向参考助手组件 (悬浮窗 / 悬浮球 / 抽屉模式) -->
      <JdAiCopilotDrawer
        v-model:is-open="showAiCopilotDrawer"
        :resume-id="resumeId"
        :bound-jd="resume?.target_jd || (jdText ? { raw: jdText, structured: jdStructured } : null)"
        :current-resume="resume"
        @jd-bound="handleJdBound"
        @apply-section="handleApplySectionItem"
        @replace-all="handleReplaceAll"
        @reference-generated="handleReferenceGenerated"
      />

      <!-- 更换模板快速弹窗 -->
      <div v-if="showTemplateModal" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
        <div class="bg-white rounded-xl shadow-xl w-full max-w-lg p-5 space-y-4">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <h4 class="font-bold text-sm text-slate-800">切换简历排版模板</h4>
            <button class="text-slate-400 hover:text-slate-600 text-base" @click="showTemplateModal = false">✕</button>
          </div>
          <div class="grid grid-cols-2 gap-3 max-h-80 overflow-y-auto">
            <div
              v-for="t in templates"
              :key="t.id"
              class="p-3 rounded-lg border-2 cursor-pointer transition text-xs"
              :class="templateId === t.id ? 'border-primary-600 bg-primary-50/30 font-bold' : 'border-slate-200 hover:border-slate-300'"
              @click="selectTemplate(t.id)"
            >
              <div class="text-sm font-bold text-slate-800">{{ t.name }}</div>
              <div class="text-[11px] text-slate-400 mt-0.5">{{ t.description || '点击应用此排版' }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Magic-Resume 三栏工作台主体 (支持左右自由拖拽调整宽度，全视口高度拉满) -->
      <div
        ref="workbenchContainerRef"
        class="relative flex-1 min-h-0 h-[calc(100vh-84px)] min-h-[580px] flex flex-col lg:flex-row items-stretch w-full overflow-hidden transition-all duration-300"
        :class="[
          isDragging ? 'select-none cursor-col-resize' : ''
        ]"
      >
        
        <!-- 左栏: 模块导航与排版外观 (SidePanel) -->
        <div
          v-show="!isSidePanelCollapsed"
          class="w-full flex flex-col gap-2.5 overflow-hidden shrink-0 h-full"
          :class="isDragging ? 'transition-none' : 'transition-[width] duration-150'"
          :style="isDesktop ? { width: `${leftPercent}%`, minWidth: '200px', maxWidth: '420px' } : {}"
        >
          
          <!-- 模块编排与标签积木池卡片 -->
          <div class="bg-white rounded-xl border border-slate-200 shadow-2xs flex-1 min-h-0 flex flex-col overflow-hidden">
            <!-- 顶部双 Tab 切换：🏷️ 标签与积木池 vs 📐 模块大纲 -->
            <div class="p-2 border-b border-slate-100 shrink-0 flex items-center justify-between bg-slate-50/50">
              <div class="flex items-center gap-1 bg-slate-200/70 p-0.5 rounded-lg text-xs font-semibold w-full">
                <button
                  class="flex-1 py-1 rounded-md transition text-center"
                  :class="leftPanelMode === 'palette' ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'"
                  @click="leftPanelMode = 'palette'"
                >
                  🏷️ 标签积木池
                </button>
                <button
                  class="flex-1 py-1 rounded-md transition text-center"
                  :class="leftPanelMode === 'outline' ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'"
                  @click="leftPanelMode = 'outline'"
                >
                  📐 模块大纲
                </button>
              </div>
            </div>

            <!-- Tab 1: 标签与积木池 (可拖拽上板) -->
            <div v-if="leftPanelMode === 'palette'" class="flex-1 min-h-0 overflow-hidden">
              <ResumeTagPalette
                :resume-data="resume"
                @add-tag="handleAddTagFromPalette"
                @remove-tag="handleRemoveTagFromPalette"
              />
            </div>

            <!-- Tab 2: 模块编排列表 -->
            <div v-else class="flex-1 min-h-0 flex flex-col p-3 overflow-hidden">
              <div class="flex items-center justify-between pb-1.5 mb-1.5 border-b border-slate-100 text-[11px] text-slate-400 shrink-0">
                <span>模块显隐与排序</span>
                <span>共 {{ allTabs.length }} 个模块</span>
              </div>
              <div class="flex-1 overflow-y-auto space-y-1.5 pr-0.5">
                <div
                  v-for="(t, idx) in allTabs"
                  :key="t.id"
                  class="group flex items-center justify-between px-2.5 py-2 rounded-lg border text-xs font-medium cursor-pointer transition select-none"
                  :class="activeTab === t.id
                    ? 'bg-primary-600 text-white border-primary-600 shadow-xs'
                    : (sectionVisibility[t.id] === false ? 'bg-slate-50 text-slate-400 border-slate-200 opacity-60' : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50')"
                  @click="activeTab = t.id"
                >
                  <div class="flex items-center gap-2 min-w-0 flex-1">
                    <span class="text-sm shrink-0">{{ t.icon }}</span>
                    <span class="truncate font-medium">{{ t.label }}</span>
                  </div>

                  <div class="flex items-center gap-0.5 shrink-0" @click.stop>
                    <button
                      class="p-1 rounded transition hover:scale-110"
                      :class="activeTab === t.id ? 'text-white/80 hover:text-white' : 'text-slate-400 hover:text-slate-600'"
                      :title="sectionVisibility[t.id] === false ? '在纸质画布中隐藏中，点击恢复显示' : '在纸质画布中显示中，点击隐藏'"
                      @click="toggleSectionVisibility(t.id)"
                    >
                      <span v-if="sectionVisibility[t.id] === false" class="text-xs">👁️‍🗨️</span>
                      <span v-else class="text-xs">👁️</span>
                    </button>

                    <!-- 上下移动与删除：悬停时才优雅浮现，大幅降低视觉噪点 -->
                    <div class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        class="p-0.5 text-xs disabled:opacity-20 transition"
                        :class="activeTab === t.id ? 'text-white/70 hover:text-white' : 'text-slate-400 hover:text-slate-700'"
                        :disabled="idx === 0"
                        @click="moveSection(idx, -1)"
                        title="上移"
                      >
                        ↑
                      </button>
                      <button
                        class="p-0.5 text-xs disabled:opacity-20 transition"
                        :class="activeTab === t.id ? 'text-white/70 hover:text-white' : 'text-slate-400 hover:text-slate-700'"
                        :disabled="idx === allTabs.length - 1"
                        @click="moveSection(idx, 1)"
                        title="下移"
                      >
                        ↓
                      </button>

                      <button
                        class="p-1 text-xs rounded hover:scale-110 transition ml-0.5"
                        :class="activeTab === t.id ? 'text-white/70 hover:text-red-200' : 'text-slate-400 hover:text-red-500'"
                        :title="`删除【${t.label}】模块`"
                        @click="confirmDeleteSection(t.id, t.label)"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- ＋ 添加模块按钮 -->
              <button
                class="w-full mt-2 py-1.5 px-2 rounded-lg text-xs font-medium text-primary-600 bg-primary-50/60 border border-dashed border-primary-300 hover:bg-primary-100/60 transition flex items-center justify-center gap-1 shrink-0"
                @click="showAddSectionModal = true"
              >
                <span>➕</span> 添加 / 恢复模块
              </button>
            </div>
          </div>

          <!-- 全局配色与排版设置卡片 -->
          <div class="bg-white rounded-xl border border-slate-200 p-3 shadow-2xs shrink-0 space-y-2">
            <div class="flex items-center justify-between pb-1.5 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                <span>🎨</span> 主题配色
              </span>
              <span class="text-[10px] text-slate-400">实时渲染</span>
            </div>

            <!-- 配色圆点选择器 -->
            <div class="grid grid-cols-4 gap-1.5">
              <button
                v-for="c in [
                  { id: 'classic', label: '墨黑', bg: '#0f172a' },
                  { id: 'indigo', label: '科技蓝', bg: '#4f46e5' },
                  { id: 'emerald', label: '雅绿', bg: '#059669' },
                  { id: 'slate', label: '雅灰', bg: '#334155' },
                ]"
                :key="c.id"
                class="flex flex-col items-center gap-1 p-1 rounded-lg border transition text-[10px]"
                :class="resumeThemeColor === c.id ? 'border-primary-500 bg-primary-50 font-bold text-primary-700 shadow-2xs' : 'border-slate-100 hover:border-slate-300 text-slate-600'"
                @click="handleThemeChange(c.id as any)"
              >
                <span class="w-3.5 h-3.5 rounded-full shadow-2xs" :style="{ backgroundColor: c.bg }"></span>
                <span class="scale-90">{{ c.label }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 分割拖拽条 1: 左栏与中栏之间 -->
        <div
          v-if="!isSidePanelCollapsed"
          class="hidden lg:flex group relative items-center justify-center w-2.5 shrink-0 cursor-col-resize hover:bg-primary-50/80 transition-colors z-20 select-none py-2"
          title="按住左右拖动调节宽度（双击复原默认比例）"
          @mousedown.prevent="startDrag('left', $event)"
          @dblclick="resetPanelWidths"
        >
          <div class="w-px h-full bg-slate-200 group-hover:bg-primary-400 group-active:bg-primary-600 transition-colors"></div>
          <div class="absolute top-1/2 -translate-y-1/2 w-1.5 h-7 rounded-full bg-slate-300 group-hover:bg-primary-500 group-active:bg-primary-600 group-hover:scale-110 shadow-2xs transition-all flex flex-col items-center justify-center gap-0.5">
            <span class="w-0.5 h-0.5 rounded-full bg-white"></span>
            <span class="w-0.5 h-0.5 rounded-full bg-white"></span>
            <span class="w-0.5 h-0.5 rounded-full bg-white"></span>
          </div>
        </div>

        <!-- 中栏: 模块编辑表单 (EditPanel) -->
        <div
          class="w-full bg-white rounded-xl border border-slate-200 flex flex-col overflow-hidden shadow-2xs shrink-0 h-full"
          :class="isDragging ? 'transition-none' : 'transition-[width] duration-150'"
          :style="isDesktop ? {
            width: isSidePanelCollapsed ? `${collapsedCenterPercent}%` : `${centerPercent}%`,
            minWidth: '320px'
          } : {}"
        >
          <!-- 模块当前顶部 Title 栏目 (带修改铅笔 & 展开左栏按钮 & 删除按钮) -->
          <div class="px-4 py-2.5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between shrink-0">
            <div class="flex items-center gap-2">
              <button
                v-if="isSidePanelCollapsed"
                class="text-xs text-primary-600 bg-primary-50 border border-primary-200 hover:bg-primary-100 px-2 py-0.5 rounded-md transition flex items-center gap-1 mr-1"
                title="展开左侧模块编排"
                @click="isSidePanelCollapsed = false"
              >
                <span>📐 展开模块栏</span>
              </button>
              <span class="text-lg">
                {{ allTabs.find(t => t.id === activeTab)?.icon }}
              </span>
              <span class="font-bold text-sm text-slate-900">
                {{ allTabs.find(t => t.id === activeTab)?.label }}
              </span>
              <span class="text-[10px] text-slate-400">（输入即刻渲染）</span>
            </div>
            <div class="flex items-center gap-2">
              <button
                class="text-xs text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1"
                :disabled="sectionLoading === activeTab"
                @click="handleRegenerateSection(activeTab)"
              >
                <span>✨</span> {{ sectionLoading === activeTab ? 'AI 润色中…' : 'AI 优化本模块' }}
              </button>
            </div>
          </div>

          <!-- 编辑表单滚动容器 -->
          <div class="flex-1 overflow-y-auto p-4 space-y-4">
            <ResumeWorkbenchEditor
              v-if="resume"
              v-model:resume-content="resume"
              :active-section="activeTab"
              :loading-section="sectionLoading"
              @change="handleSectionChange"
              @regenerate="handleRegenerateSection"
              @remove-section="handleRemoveCustomSection"
            />
          </div>
        </div>

        <!-- 分割拖拽条 2: 中栏与右栏之间 -->
        <div
          class="hidden lg:flex group relative items-center justify-center w-2.5 shrink-0 cursor-col-resize hover:bg-primary-50/80 transition-colors z-20 select-none py-2"
          title="按住左右拖动调节宽度（双击复原默认比例）"
          @mousedown.prevent="startDrag('center', $event)"
          @dblclick="resetPanelWidths"
        >
          <div class="w-px h-full bg-slate-200 group-hover:bg-primary-400 group-active:bg-primary-600 transition-colors"></div>
          <div class="absolute top-1/2 -translate-y-1/2 w-1.5 h-7 rounded-full bg-slate-300 group-hover:bg-primary-500 group-active:bg-primary-600 group-hover:scale-110 shadow-2xs transition-all flex flex-col items-center justify-center gap-0.5">
            <span class="w-0.5 h-0.5 rounded-full bg-white"></span>
            <span class="w-0.5 h-0.5 rounded-full bg-white"></span>
            <span class="w-0.5 h-0.5 rounded-full bg-white"></span>
          </div>
        </div>

        <!-- 右栏: 实时 A4 纸张画布预览 (PreviewPanel) -->
        <div
          class="w-full bg-slate-100 rounded-xl border border-slate-200 flex flex-col overflow-hidden shadow-inner flex-1 min-w-[320px] h-full"
          :class="isDragging ? 'pointer-events-none select-none' : ''"
        >
          <div class="px-3 py-2 border-b border-slate-200 bg-white/90 flex items-center justify-between text-xs text-slate-500 shrink-0">
            <!-- 模式切换：实时纸质 vs 模板原件 -->
            <div class="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg text-[11px]">
              <button
                class="px-2.5 py-1 rounded-md transition font-medium"
                :class="previewMode === 'live' ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
                @click="previewMode = 'live'"
              >
                ⚡ 实时纸质 (0ms)
              </button>
              <button
                class="px-2.5 py-1 rounded-md transition font-medium"
                :class="previewMode === 'template' ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
                @click="previewMode = 'template'; refreshPreview()"
              >
                📑 模板原件
              </button>
            </div>

            <div class="flex items-center gap-2">
              <button
                class="px-2.5 py-1 rounded-md text-[11px] font-medium border transition flex items-center gap-1"
                :class="previewScale < 1 ? 'bg-primary-50 text-primary-700 border-primary-300 font-bold' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'"
                :title="previewScale < 1 ? '已启用单页微调压缩' : '点击将超出一页的内容自动智能压缩为一页'"
                @click="fitToOnePage"
              >
                <span>📄 一页自适应</span>
                <span v-if="previewScale < 1" class="text-[10px] text-primary-600 font-bold">({{ Math.round(previewScale * 100) }}%)</span>
              </button>
              <button v-if="previewMode === 'template'" class="text-primary-600 hover:underline text-xs" @click="refreshPreview">刷新 ⟳</button>
            </div>
          </div>

          <!-- A4 预览容器 -->
          <div class="flex-1 overflow-y-auto p-3 flex justify-center bg-slate-200/60">
            <!-- 0ms 纯响应式实时纸张画布 -->
            <ResumePaperPreview
              v-if="previewMode === 'live' && resume"
              ref="paperPreviewRef"
              :resume-data="resume"
              :scale="previewScale"
              :theme-color="resumeThemeColor"
              :section-visibility="sectionVisibility"
              @update:resume-data="handleCanvasResumeUpdate"
              @change="() => triggerAutoSave()"
              @regenerate-section="handleRegenerateSection"
            />

            <!-- 后端模板渲染 HTML iframe -->
            <div
              v-else
              class="w-full bg-white shadow-md rounded border border-slate-300/80 overflow-hidden min-h-[700px] transition-transform duration-300 origin-top"
              :style="{ transform: `scale(${previewScale})` }"
            >
              <iframe
                v-if="previewHtml"
                :srcdoc="previewHtml"
                class="w-full h-[780px] border-none"
                :class="isDragging ? 'pointer-events-none' : ''"
                sandbox="allow-same-origin"
              />
              <div v-else class="flex items-center justify-center h-64 text-slate-400 text-xs">
                正在渲染模板预览…
              </div>
            </div>
          </div>
        </div>

      </div>



      <!-- 添加 / 恢复模块弹窗 (支持恢复已删除的基础模块 + 新增自定义模块) -->
      <div v-if="showAddSectionModal" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
        <div class="bg-white rounded-xl shadow-xl w-full max-w-md p-5 space-y-4">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <div>
              <h4 class="font-bold text-sm text-slate-800">添加 / 恢复简历模块</h4>
              <p class="text-xs text-slate-500">可恢复已删除的基础模块，或创建全新自定义模块</p>
            </div>
            <button class="text-slate-400 hover:text-slate-600 text-base" @click="showAddSectionModal = false">✕</button>
          </div>

          <!-- 1. 恢复已删除的基础模块 -->
          <div v-if="restorableCoreSections.length" class="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <label class="label !text-xs font-bold text-slate-700 mb-2 flex items-center gap-1">
              <span>♻️</span> 可重新添加的基础模块 (原数据完好保留)
            </label>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="sec in restorableCoreSections"
                :key="sec.id"
                class="px-2.5 py-1.5 bg-white hover:bg-primary-50 hover:border-primary-300 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 hover:text-primary-700 transition flex items-center gap-1.5 shadow-2xs group"
                @click="restoreSection(sec.id); showAddSectionModal = false"
              >
                <span class="text-sm">{{ sec.icon }}</span>
                <span>{{ sec.label }}</span>
                <span class="text-primary-600 font-bold ml-1 text-xs group-hover:scale-110 transition">＋ 恢复</span>
              </button>
            </div>
          </div>
          <div v-else class="text-xs text-slate-400 bg-slate-50 p-2.5 rounded-lg border border-dashed border-slate-200 text-center">
            ✓ 所有基础模块（基本资料、教育、技能、工作、项目、亮点）目前均已在简历中
          </div>

          <!-- 2. 新增自定义模块 -->
          <div class="space-y-3 pt-1 border-t border-slate-100">
            <label class="label !text-xs font-bold text-slate-700">📌 创建自定义模块</label>
            <div>
              <label class="label !text-xs text-slate-500">模块图标</label>
              <div class="flex gap-2 text-base mb-2">
                <button
                  v-for="icon in ['🏆', '📜', '🌐', '💬', '💡', '📌', '🎯', '📖']"
                  :key="icon"
                  type="button"
                  class="w-8 h-8 rounded border flex items-center justify-center transition"
                  :class="newSectionIcon === icon ? 'border-primary-500 bg-primary-50' : 'border-slate-200 hover:bg-slate-50'"
                  @click="newSectionIcon = icon"
                >
                  {{ icon }}
                </button>
              </div>
              <label class="label !text-xs text-slate-500">模块名称</label>
              <input v-model="newSectionTitle" class="input !text-xs" placeholder="如：荣誉奖项、资格证书、自我评价" @keydown.enter="handleAddCustomSection" />
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button class="btn-secondary !text-xs" @click="showAddSectionModal = false">取消</button>
            <button class="btn-primary !text-xs" :disabled="!newSectionTitle.trim()" @click="handleAddCustomSection">＋ 创建自定义模块</button>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>
