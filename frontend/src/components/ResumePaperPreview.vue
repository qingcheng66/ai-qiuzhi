<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'

export interface SkillItem {
  type: 'text' | 'group'
  text?: string
  name?: string
  keywords?: string[]
}

export interface Header2DWidget {
  id: string
  type: 'name' | 'label' | 'photo' | 'summary' | 'tag' | 'custom'
  key?: string
  label: string
  value: string
  icon: string
  col: number // 1 to 12
  row: number // 1 to N
  w: number   // 1 to 12
  h: number   // 1 to N
  isCustom?: boolean
}

const PRESET_ICONS: Record<string, string> = {
  phone: '📞',
  email: '✉️',
  wechat: '💬',
  location: '📍',
  birthDate: '🎂',
  github: '🐙',
  blog: '🌐',
  name: '👤',
  label: '🎯',
  photo: '📷',
  summary: '✨',
}

const PRESET_LABELS: Record<string, string> = {
  phone: '电话',
  email: '邮箱',
  wechat: '微信',
  location: '城市',
  birthDate: '生日',
  github: 'GitHub',
  blog: '博客',
  name: '姓名',
  label: '求职意向',
  photo: '证件照',
  summary: '核心优势',
}

const props = withDefaults(
  defineProps<{
    resumeData: any
    scale?: number
    themeColor?: 'classic' | 'indigo' | 'slate' | 'emerald'
    sectionVisibility?: Record<string, boolean>
    editable?: boolean
  }>(),
  {
    scale: 1,
    themeColor: 'classic',
    editable: true,
  }
)

const emit = defineEmits<{
  (e: 'update:resume-data', data: any): void
  (e: 'change', sectionKey?: string): void
  (e: 'select-section', sectionKey: string): void
  (e: 'regenerate-section', sectionKey: string): void
}>()

// 全局拖拽状态侦听（只有在鼠标拖拽组件时，才向用户点亮全量二维方格纸阵列）
const isDraggingActive = ref(false)
const dragOverWidgetId = ref<string | null>(null)
const draggingWidgetId = ref<string | null>(null)
const isHeaderDraggingOver = ref(false)
const headerContainerRef = ref<HTMLElement | null>(null)

const TOTAL_COLS = 12
const BASE_ROW_HEIGHT = 44 // 每个网格行基础高度 44px
const hoverCell = ref<{ col: number; row: number }>({ col: 1, row: 1 })
const draggingDimensions = ref<{ w: number; h: number }>({ w: 4, h: 1 })

function onGlobalDragStart() {
  isDraggingActive.value = true
}

function onGlobalDragEnd() {
  isDraggingActive.value = false
  dragOverWidgetId.value = null
  draggingWidgetId.value = null
  isHeaderDraggingOver.value = false
}

onMounted(() => {
  window.addEventListener('dragstart', onGlobalDragStart)
  window.addEventListener('dragend', onGlobalDragEnd)
  window.addEventListener('drop', onGlobalDragEnd)
})

onUnmounted(() => {
  window.removeEventListener('dragstart', onGlobalDragStart)
  window.removeEventListener('dragend', onGlobalDragEnd)
  window.removeEventListener('drop', onGlobalDragEnd)
})

// 主题色彩方案
const themeStyles = computed(() => {
  const color = props.themeColor || props.resumeData?.theme_color || 'classic'
  switch (color) {
    case 'indigo':
      return {
        primary: '#4f46e5',
        primaryLight: '#eef2ff',
        primaryBorder: '#c7d2fe',
        textPrimary: '#3730a3',
        lineColor: '#4f46e5',
        bullet: '#6366f1',
      }
    case 'emerald':
      return {
        primary: '#059669',
        primaryLight: '#ecfdf5',
        primaryBorder: '#a7f3d0',
        textPrimary: '#065f46',
        lineColor: '#059669',
        bullet: '#10b981',
      }
    case 'slate':
      return {
        primary: '#334155',
        primaryLight: '#f8fafc',
        primaryBorder: '#cbd5e1',
        textPrimary: '#1e293b',
        lineColor: '#334155',
        bullet: '#475569',
      }
    case 'classic':
    default:
      return {
        primary: '#0f172a',
        primaryLight: '#f1f5f9',
        primaryBorder: '#e2e8f0',
        textPrimary: '#0f172a',
        lineColor: '#0f172a',
        bullet: '#334155',
      }
  }
})

function isSectionVisible(secKey: string): boolean {
  if (props.resumeData?.deleted_sections && props.resumeData.deleted_sections.includes(secKey)) return false
  if (props.sectionVisibility && props.sectionVisibility[secKey] === false) return false
  if (props.resumeData?.section_visibility && props.resumeData.section_visibility[secKey] === false) return false
  return true
}

const basics = computed(() => props.resumeData?.basics || {})

// 计算当前画板上的 2D 坐标网格组件列表（支持持久化或从 basics 智能推导）
const active2DWidgets = computed<Header2DWidget[]>(() => {
  const b = basics.value
  if (Array.isArray(b.grid_widgets_2d)) {
    return b.grid_widgets_2d
  }

  // 智能推导初始 2D 坐标排版 (横向 12 格坐标纸，向下自由衍生)
  const list: Header2DWidget[] = []
  let currentRow = 1

  // 1. 证件照 (如果有，占据右上角第 10~12 列，第 1~3 行)
  const hasPhoto = Boolean(b.photo || b.avatar)
  if (hasPhoto) {
    list.push({
      id: 'core_photo',
      type: 'photo',
      key: 'photo',
      label: '免冠照',
      value: b.photo || b.avatar,
      icon: '📷',
      col: 10,
      row: 1,
      w: 3,
      h: 3,
    })
  }

  // 2. 姓名 (如果有)
  if (b.name) {
    list.push({
      id: 'core_name',
      type: 'name',
      key: 'name',
      label: '姓名',
      value: b.name,
      icon: '👤',
      col: 1,
      row: currentRow,
      w: b.label ? 5 : (hasPhoto ? 9 : 12),
      h: 1,
    })
  }

  // 3. 求职意向 (如果有)
  if (b.label || b.title) {
    list.push({
      id: 'core_label',
      type: 'label',
      key: 'label',
      label: '求职意向',
      value: b.label || b.title,
      icon: '🎯',
      col: b.name ? 6 : 1,
      row: currentRow,
      w: hasPhoto ? 4 : 6,
      h: 1,
    })
  }

  if (b.name || b.label || b.title) {
    currentRow++
  }

  // 4. 标准联系方式标签 (电话、邮箱、微信、城市等)
  const stdKeys = ['phone', 'email', 'wechat', 'location', 'birthDate', 'github', 'blog']
  let currentCol = 1
  for (const k of stdKeys) {
    if (b[k]) {
      const isLong = ['github', 'blog'].includes(k) || (b[k] && b[k].length > 25)
      const w = isLong ? 6 : 4
      const maxColAvailable = (hasPhoto && currentRow <= 3) ? 9 : 12

      if (currentCol + w - 1 > maxColAvailable) {
        currentRow++
        currentCol = 1
      }

      list.push({
        id: `std_${k}`,
        type: 'tag',
        key: k,
        label: PRESET_LABELS[k] || k,
        value: b[k],
        icon: PRESET_ICONS[k] || '🏷️',
        col: currentCol,
        row: currentRow,
        w,
        h: 1,
      })
      currentCol += w
    }
  }

  if (currentCol > 1) {
    currentRow++
  }

  // 保证超出第 3 行的照片高度
  if (hasPhoto && currentRow < 4) {
    currentRow = 4
  }

  // 5. 自定义标签
  const cfs = Array.isArray(b.custom_fields) ? b.custom_fields : []
  currentCol = 1
  cfs.forEach((cf: any, idx: number) => {
    if (cf && (cf.label || cf.value)) {
      const w = cf.w || cf.cols || 4
      if (currentCol + w - 1 > 12) {
        currentRow++
        currentCol = 1
      }
      list.push({
        id: cf.id || `cf_${idx}`,
        type: 'custom',
        label: cf.label || '自定义项',
        value: cf.value || '',
        icon: cf.icon || '🏷️',
        col: cf.col || currentCol,
        row: cf.row || currentRow,
        w,
        h: cf.h || 1,
        isCustom: true,
      })
      currentCol += w
    }
  })

  if (currentCol > 1) {
    currentRow++
  }

  // 6. 一句话优势总结 (通栏 12 格，高 2 格)
  if (b.summary) {
    list.push({
      id: 'core_summary',
      type: 'summary',
      key: 'summary',
      label: '一句话核心优势',
      value: b.summary,
      icon: '✨',
      col: 1,
      row: currentRow,
      w: 12,
      h: 2,
    })
  }

  return list
})

// 计算当前总行数（支持随组件放置向下无限延伸，并在拖拽时根据鼠标位置实时向下扩展）
const totalGridRows = computed(() => {
  let maxR = 4
  for (const w of active2DWidgets.value) {
    const bottom = (w.row || 1) + (w.h || 1) - 1
    if (bottom > maxR) maxR = bottom
  }
  if (isDraggingActive.value && hoverCell.value.row) {
    const dragBottom = hoverCell.value.row + (draggingDimensions.value.h || 1) - 1
    if (dragBottom > maxR) maxR = dragBottom
  }
  // 向下预留 3 行空白方格，保证用户可以随心所欲往下放置（无限大方格纸体验）
  return maxR + 3
})

function isCellHovered(c: number, r: number): boolean {
  if (!isDraggingActive.value || !isHeaderDraggingOver.value) return false
  const hc = hoverCell.value.col
  const hr = hoverCell.value.row
  const w = draggingDimensions.value.w || 4
  const h = draggingDimensions.value.h || 1
  return c >= hc && c < hc + w && r >= hr && r < hr + h
}

const projects = computed(() => {
  const arr = Array.isArray(props.resumeData?.projects) ? props.resumeData.projects : []
  return arr.filter((p: any) => p.visible !== false)
})
const experience = computed(() => {
  const arr = Array.isArray(props.resumeData?.experience) ? props.resumeData.experience : []
  return arr.filter((e: any) => e.visible !== false)
})
const education = computed(() => {
  const arr = Array.isArray(props.resumeData?.education) ? props.resumeData.education : []
  return arr.filter((e: any) => e.visible !== false)
})
const highlights = computed(() => {
  const arr = Array.isArray(props.resumeData?.highlights) ? props.resumeData.highlights : []
  return arr.filter((h: any) => h.visible !== false)
})
const customSections = computed(() => {
  const arr = Array.isArray(props.resumeData?.custom_sections) ? props.resumeData.custom_sections : []
  return arr.filter((c: any) => c.visible !== false)
})

// 技能智能解析 (支持：纯文本多行、纯文本数组、对象分组数组)
const rawSkills = computed(() => {
  return props.resumeData?.skills ?? props.resumeData?.skillContent ?? ''
})

const parsedSkills = computed<SkillItem[]>(() => {
  const val = rawSkills.value
  if (!val) return []
  if (typeof val === 'string') {
    return val.split('\n').map((s) => s.trim()).filter(Boolean).map((text) => ({
      type: 'text' as const,
      text,
    }))
  }
  if (Array.isArray(val)) {
    return val.map((item): SkillItem => {
      if (typeof item === 'string') {
        return { type: 'text', text: item }
      }
      if (item && typeof item === 'object') {
        if (Array.isArray(item.keywords) && item.keywords.length > 0) {
          return {
            type: 'group',
            name: item.name || '',
            keywords: item.keywords,
          }
        }
        if (item.name) {
          return {
            type: 'text',
            text: item.name,
          }
        }
      }
      return { type: 'text', text: String(item) }
    })
  }
  return []
})

// 模块动态排序列表 (除 basics 抬头外)
const defaultSectionOrder = ['education', 'skills', 'projects', 'experience', 'highlights']

const dynamicSections = computed(() => {
  const order: string[] = props.resumeData?.section_order || defaultSectionOrder
  // 过滤掉 basics (抬头固定) 和隐藏/删除的模块
  const list = order.filter((secId) => {
    if (secId === 'basics') return false
    return isSectionVisible(secId)
  })

  // 确保所有自定义模块也包含在其中
  customSections.value.forEach((cs: any) => {
    const customKey = `custom_${cs.id}`
    if (!list.includes(customKey) && !list.includes(cs.id) && isSectionVisible(cs.id)) {
      list.push(customKey)
    }
  })

  return list
})

// 智能高亮技能前缀
function formatSkillText(text: string) {
  if (!text) return ''
  const colonMatch = text.match(/^(\d+[\.、]\s*[^:：]+[:：]|[^:：]{2,15}[:：])([\s\S]*)$/)
  if (colonMatch) {
    return `<strong>${colonMatch[1]}</strong>${colonMatch[2]}`
  }
  return text
}

function formatDate(start?: string, end?: string) {
  if (!start && !end) return ''
  if (start && end) return `${start} - ${end}`
  return start || end || ''
}

function formatEduSub(edu: any) {
  const parts = []
  const major = edu.area || edu.major
  const degree = edu.studyType || edu.degree
  const gpa = edu.gpa
  if (major) parts.push(major)
  if (degree) parts.push(degree)
  if (gpa) parts.push(`GPA ${gpa}`)
  return parts.join(' · ')
}

// 缩放
const internalZoom = ref(0.68)
const currentScale = computed(() => {
  return (props.scale ?? 1) * internalZoom.value
})

// =================== 2D 方格坐标纸组件管理与自由拖放交互 ===================

// 更新并同步 2D 网格数据回 basics，保证导出与后端无缝兼容
function update2DWidgets(newWidgets: Header2DWidget[]) {
  if (!props.resumeData) return
  const rd = { ...props.resumeData }
  if (!rd.basics) rd.basics = {}
  rd.basics.grid_widgets_2d = newWidgets

  // 严格同步基本数据字段，保证导出和后端 100% 兼容
  const nameWidget = newWidgets.find((w) => w.type === 'name' || w.id === 'core_name')
  rd.basics.name = nameWidget ? nameWidget.value : ''

  const labelWidget = newWidgets.find((w) => w.type === 'label' || w.id === 'core_label')
  rd.basics.label = labelWidget ? labelWidget.value : ''

  const photoWidget = newWidgets.find((w) => w.type === 'photo' || w.id === 'core_photo')
  rd.basics.photo = photoWidget ? photoWidget.value : ''

  const summaryWidget = newWidgets.find((w) => w.type === 'summary' || w.id === 'core_summary')
  rd.basics.summary = summaryWidget ? summaryWidget.value : ''

  const stdKeys = ['phone', 'email', 'wechat', 'location', 'birthDate', 'github', 'blog']
  for (const k of stdKeys) {
    const found = newWidgets.find((w) => w.key === k)
    rd.basics[k] = found ? found.value : ''
  }

  const customWidgets = newWidgets.filter(
    (w) => w.type === 'custom' || (!w.key && !['name', 'label', 'photo', 'summary'].includes(w.type))
  )
  rd.basics.custom_fields = customWidgets.map((w) => ({
    id: w.id,
    label: w.label,
    value: w.value,
    icon: w.icon,
    col: w.col,
    row: w.row,
    w: w.w,
    h: w.h,
    cols: w.w,
  }))

  emit('update:resume-data', rd)
  emit('change', 'basics')
}

// 自由调节宽度和高度
function changeWidgetSpan(widget: Header2DWidget, dw: number, dh: number) {
  if (!props.editable) return
  const current = [...active2DWidgets.value]
  const idx = current.findIndex((w) => w.id === widget.id)
  if (idx !== -1) {
    const targetW = Math.min(12, Math.max(1, (current[idx].w || 4) + dw))
    const targetH = Math.max(1, (current[idx].h || 1) + dh)
    const targetCol = Math.min(13 - targetW, current[idx].col || 1)
    current[idx] = {
      ...current[idx],
      col: targetCol,
      w: targetW,
      h: targetH,
    }
    update2DWidgets(current)
  }
}

function setWidgetSize(widget: Header2DWidget, w: number, h: number) {
  if (!props.editable) return
  const current = [...active2DWidgets.value]
  const idx = current.findIndex((item) => item.id === widget.id)
  if (idx !== -1) {
    const targetCol = Math.min(13 - w, current[idx].col || 1)
    current[idx] = {
      ...current[idx],
      col: targetCol,
      w,
      h,
    }
    update2DWidgets(current)
  }
}

// 从画板上移除组件（下板）
function removeWidget(widget: Header2DWidget) {
  if (!props.editable) return
  const current = active2DWidgets.value.filter((w) => w.id !== widget.id)
  update2DWidgets(current)
}

// 原地编辑组件内容
const editingWidgetId = ref<string | null>(null)
const editingWidgetValue = ref('')

function startEditWidget(widget: Header2DWidget) {
  if (!props.editable) return
  editingWidgetId.value = widget.id
  editingWidgetValue.value = widget.value
  nextTick(() => {
    const el = document.getElementById(`inline-input-${widget.id}`)
    el?.focus()
  })
}

function finishEditWidget(widget: Header2DWidget) {
  if (!editingWidgetId.value) return
  const val = editingWidgetValue.value.trim()
  editingWidgetId.value = null

  const current = [...active2DWidgets.value]
  const idx = current.findIndex((w) => w.id === widget.id)
  if (idx !== -1) {
    current[idx] = {
      ...current[idx],
      value: val,
    }
    update2DWidgets(current)
  }
}

// 照片快捷设置 / 提示修改 URL
function promptEditPhoto(widget: Header2DWidget) {
  if (!props.editable) return
  const current = widget.value || ''
  const newUrl = window.prompt('请输入免冠证件照图片链接 (URL) 或清空：', current)
  if (newUrl !== null) {
    const list = [...active2DWidgets.value]
    const idx = list.findIndex((w) => w.id === widget.id)
    if (idx !== -1) {
      list[idx] = { ...list[idx], value: newUrl.trim() }
      update2DWidgets(list)
    }
  }
}

// 2D 网格拖拽开始
// 2D 网格拖拽开始
function onWidgetDragStart(e: DragEvent, widget: Header2DWidget) {
  if (!props.editable) return
  draggingWidgetId.value = widget.id
  draggingDimensions.value = { w: widget.w, h: widget.h }
  hoverCell.value = { col: widget.col, row: widget.row }

  try {
    ;(window as any).__AGY_DRAGGING_TAG__ = {
      id: widget.id,
      w: widget.w,
      h: widget.h,
    }
  } catch {}

  if (e.dataTransfer) {
    e.dataTransfer.setData('application/json', JSON.stringify({
      type: '2d-widget-move',
      id: widget.id,
      w: widget.w,
      h: widget.h,
    }))
    e.dataTransfer.effectAllowed = 'all'
  }
}

// 头部整张方格纸接收拖拽悬停：实时基于鼠标坐标高精度计算目标 (col, row)
function onHeaderDragOver(e: DragEvent) {
  if (!props.editable) return
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'copy'
  }
  isHeaderDraggingOver.value = true

  // 读取全局拖拽的组件尺寸（如果有）
  try {
    const globalTag = (window as any).__AGY_DRAGGING_TAG__
    if (globalTag && globalTag.w && globalTag.h) {
      draggingDimensions.value = { w: globalTag.w, h: globalTag.h }
    }
  } catch {}

  const container = headerContainerRef.value
  if (!container) return

  const rect = container.getBoundingClientRect()
  // 核心：必须考虑 A4 缩放比例 currentScale，反求真实的 100% 原始像素
  const scale = currentScale.value || 1
  const paddingX = 12
  const paddingTop = 12
  const gap = 8

  const mouseX = Math.max(0, (e.clientX - rect.left) / scale - paddingX)
  const mouseY = Math.max(0, (e.clientY - rect.top) / scale - paddingTop)

  const unscaledContainerWidth = rect.width / scale
  const availableWidth = Math.max(100, unscaledContainerWidth - paddingX * 2)
  const colWidth = (availableWidth - (TOTAL_COLS - 1) * gap) / TOTAL_COLS
  const rowHeightWithGap = BASE_ROW_HEIGHT + gap

  const targetCol = Math.min(TOTAL_COLS, Math.max(1, Math.floor(mouseX / (colWidth + gap)) + 1))
  const targetRow = Math.max(1, Math.floor(mouseY / rowHeightWithGap) + 1)

  const w = draggingDimensions.value.w || 4
  const clampedCol = Math.min(TOTAL_COLS - w + 1, targetCol)

  hoverCell.value = { col: Math.max(1, clampedCol), row: targetRow }
}

function onHeaderDragLeave(e: DragEvent) {
  const target = e.currentTarget as HTMLElement
  if (!target.contains(e.relatedTarget as Node)) {
    isHeaderDraggingOver.value = false
  }
}

function onHeaderDrop(e: DragEvent) {
  if (!props.editable) return
  e.preventDefault()
  isHeaderDraggingOver.value = false
  const raw = e.dataTransfer?.getData('application/json')
  if (!raw) return

  const targetCol = hoverCell.value.col
  const targetRow = hoverCell.value.row

  try {
    const payload = JSON.parse(raw)
    // 1. 移动已有组件
    if (payload.type === '2d-widget-move' && payload.id) {
      moveWidgetTo(payload.id, targetCol, targetRow)
      return
    }

    // 2. 从左侧素材池拖入新组件落位
    if (payload.type === 'grid-widget' && payload.data) {
      placeNewWidget(payload.data, targetCol, targetRow)
      return
    }
  } catch (err) {
    console.error('2D Grid drop error:', err)
  }
}

function moveWidgetTo(id: string, col: number, row: number) {
  const current = [...active2DWidgets.value]
  const idx = current.findIndex((w) => w.id === id)
  if (idx !== -1) {
    const w = current[idx].w || 4
    const clampedCol = Math.min(TOTAL_COLS - w + 1, Math.max(1, col))
    const clampedRow = Math.max(1, row)
    current[idx] = {
      ...current[idx],
      col: clampedCol,
      row: clampedRow,
    }
    update2DWidgets(current)
  }
}

function placeNewWidget(data: any, col: number, row: number) {
  const current = [...active2DWidgets.value]
  const existingIdx = current.findIndex(
    (w) => w.id === data.id || (data.key && w.key === data.key && data.key !== 'custom')
  )

  const widgetType = data.widgetType || data.type || (data.category === 'core' ? data.key : 'tag')
  const w = data.w || (widgetType === 'summary' ? 12 : widgetType === 'photo' ? 3 : widgetType === 'name' ? 6 : 4)
  const h = data.h || (widgetType === 'photo' ? 3 : widgetType === 'summary' ? 2 : 1)
  const clampedCol = Math.min(TOTAL_COLS - w + 1, Math.max(1, col))
  const clampedRow = Math.max(1, row)

  if (existingIdx !== -1) {
    current[existingIdx] = {
      ...current[existingIdx],
      col: clampedCol,
      row: clampedRow,
      w,
      h,
      value: data.value || current[existingIdx].value,
    }
    update2DWidgets(current)
    return
  }

  const newWidget: Header2DWidget = {
    id: data.id || `widget_${Date.now()}`,
    type: widgetType,
    key: data.key,
    label: data.label || '组件',
    value: data.value || '',
    icon: data.icon || '🏷️',
    col: clampedCol,
    row: clampedRow,
    w,
    h,
    isCustom: data.category === 'custom' || data.isCustom,
  }

  current.push(newWidget)
  update2DWidgets(current)
}

// 供父组件直接调用
function applyTagToBasics(tag: any) {
  // 找一个靠下的空行放置
  const nextRow = Math.max(1, totalGridRows.value - 2)
  const widgetType = tag.type || (tag.category === 'core' ? tag.key : 'tag')
  placeNewWidget(
    {
      id: tag.id,
      widgetType,
      key: tag.key || 'custom',
      label: tag.label,
      value: tag.value,
      icon: tag.icon,
      w: tag.defaultCols || (widgetType === 'summary' ? 12 : widgetType === 'photo' ? 3 : widgetType === 'name' ? 6 : 4),
      h: tag.type === 'photo' ? 3 : tag.type === 'summary' ? 2 : 1,
      category: tag.category,
      isCustom: tag.isCustom,
    },
    1,
    nextRow
  )
}

function removeTagFromBasics(tag: any) {
  const current = active2DWidgets.value.filter(
    (w) => w.id !== tag.id && (!tag.key || w.key !== tag.key || tag.key === 'custom') && w.label !== tag.label
  )
  update2DWidgets(current)
}

defineExpose({
  applyTagToBasics,
  removeTagFromBasics,
})
</script>

<template>
  <div class="resume-paper-container flex flex-col items-center w-full overflow-x-auto pb-8 select-text">
    <!-- 纸质顶部微型控制工具条 -->
    <div class="w-full flex items-center justify-between pb-2 mb-3 text-xs text-slate-500 border-b border-slate-200/60 shrink-0">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span class="font-bold text-slate-800">A4 交互式简历画布</span>
        <span class="text-[10px] text-slate-400 font-normal">（支持基本信息标签拖入吸附、抬头原地改字）</span>
      </div>

      <!-- 缩放与配色快捷按钮 -->
      <div class="flex items-center gap-2">
        <div class="flex items-center gap-0.5 bg-slate-100 p-0.5 rounded text-[10px]">
          <button
            class="px-2 py-0.5 rounded transition font-medium"
            :class="internalZoom === 0.68 ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
            @click="internalZoom = 0.68"
          >
            适屏 68%
          </button>
          <button
            class="px-2 py-0.5 rounded transition font-medium"
            :class="internalZoom === 0.85 ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
            @click="internalZoom = 0.85"
          >
            85%
          </button>
          <button
            class="px-2 py-0.5 rounded transition font-medium"
            :class="internalZoom === 1.0 ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
            @click="internalZoom = 1.0"
          >
            100%
          </button>
        </div>
      </div>
    </div>

    <!-- 真实 210mm x 297mm 标准 A4 纸张画布 -->
    <div
      class="a4-paper-wrapper transition-all duration-150 origin-top"
      :style="{ transform: `scale(${currentScale})` }"
    >
      <div
        class="a4-paper relative bg-white text-slate-800 shadow-xl border border-slate-200/80 mx-auto"
        :style="{
          width: '794px',
          minHeight: '1123px',
          padding: '40px 48px',
          boxSizing: 'border-box',
          fontFamily: `-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif`,
        }"
      >
        <!-- ================= 1. Header (二维坐标无限方格纸：全部格子矩阵呈现，支持任意落位与行列调节) ================= -->
        <header
          v-if="isSectionVisible('basics')"
          ref="headerContainerRef"
          class="header-section relative pb-4 mb-4 border-b border-slate-200 transition-all rounded-xl p-3 select-text"
          :style="{
            minHeight: isDraggingActive ? `${totalGridRows * (BASE_ROW_HEIGHT + 8) + 24}px` : '150px',
          }"
          :class="{
            'ring-2 ring-primary-500 ring-dashed bg-primary-50/20 shadow-sm': isDraggingActive,
            'hover:bg-slate-50/30': !isDraggingActive,
          }"
          @dragover="onHeaderDragOver"
          @dragleave="onHeaderDragLeave"
          @drop="onHeaderDrop"
        >
          <!-- 只有在拖拽时才点亮的无限二维方格纸阵列 (平时 100% 彻底隐形，拖动时显示全量矩阵方格) -->
          <div
            v-if="isDraggingActive"
            class="pointer-events-none absolute inset-x-3 top-3 z-10 grid grid-cols-12 gap-2 transition-all duration-200"
            :style="{
              gridAutoRows: `${BASE_ROW_HEIGHT}px`,
              height: `${totalGridRows * (BASE_ROW_HEIGHT + 8) - 8}px`,
            }"
          >
            <div v-for="r in totalGridRows" :key="`r-${r}`" style="display: contents">
              <div
                v-for="c in TOTAL_COLS"
                :key="`cell-${r}-${c}`"
                class="border border-dashed rounded-md flex flex-col items-center justify-center p-0.5 select-none transition-all duration-150"
                :class="
                  isCellHovered(c, r)
                    ? 'border-primary-500 bg-primary-500/25 text-primary-700 font-bold shadow-inner ring-1 ring-primary-400'
                    : 'border-slate-300/80 bg-slate-50/40 text-slate-300'
                "
              >
                <span class="text-[8px] font-mono select-none opacity-60" :class="isCellHovered(c, r) ? 'opacity-100 font-bold text-primary-700' : ''">
                  {{ c }},{{ r }}
                </span>
              </div>
            </div>
          </div>

          <!-- 拖拽悬停至头部时的落位坐标指示条 -->
          <div
            v-if="isHeaderDraggingOver"
            class="absolute top-1 left-1/2 -translate-x-1/2 z-30 pointer-events-none px-3.5 py-1 bg-primary-600 text-white rounded-full shadow-lg text-[11px] font-bold flex items-center gap-1.5 animate-bounce"
          >
            <span>🎯</span>
            <span>吸附落位至 [第 {{ hoverCell.col }} 列, 第 {{ hoverCell.row }} 行]</span>
          </div>

          <!-- 二维坐标网格核心组件排版 (真实自由坐标渲染) -->
          <div
            class="relative z-20 grid grid-cols-12 gap-2 items-stretch"
            :style="{
              gridAutoRows: `${BASE_ROW_HEIGHT}px`,
              minHeight: isDraggingActive ? `${totalGridRows * (BASE_ROW_HEIGHT + 8) - 8}px` : undefined,
            }"
          >
            <div
              v-for="widget in active2DWidgets"
              :key="widget.id"
              class="widget-2d-item group/widget relative rounded-lg transition-all flex flex-col justify-center"
              :style="{
                gridColumn: `${widget.col} / span ${widget.w}`,
                gridRow: `${widget.row} / span ${widget.h}`,
              }"
              :class="[
                draggingWidgetId === widget.id ? 'opacity-40 ring-2 ring-primary-400' : '',
                editable ? 'hover:ring-1 hover:ring-primary-300/80 hover:bg-slate-50/70 p-1.5' : 'p-0.5'
              ]"
              :draggable="editable"
              @dragstart="onWidgetDragStart($event, widget)"
            >
              <!-- 悬停控制条: 宽度 (2/3/4/6/12列) + 高度 (1/2/3行) + 拖拽手柄 + 下板 (×) -->
              <div
                v-if="editable"
                class="widget-ctrl-bar absolute -top-3.5 right-1 flex items-center gap-1 bg-white/95 backdrop-blur-xs shadow-md border border-slate-200/90 rounded-md px-1.5 py-0.5 z-30 opacity-0 group-hover/widget:opacity-100 transition-opacity"
              >
                <!-- 宽度选择 -->
                <div class="flex items-center gap-0.5 text-[9px] font-mono text-slate-500">
                  <span class="text-slate-400 mr-0.5 scale-90 select-none">宽:</span>
                  <button
                    v-for="col in [2, 3, 4, 6, 12]"
                    :key="`w-${col}`"
                    class="px-1 py-0.2 rounded transition font-medium"
                    :class="widget.w === col ? 'bg-primary-600 text-white font-bold' : 'hover:bg-slate-100 text-slate-600'"
                    :title="`设定占 ${col} 列宽`"
                    @click.stop="setWidgetSize(widget, col, widget.h)"
                  >
                    {{ col === 12 ? '全宽' : `${col}列` }}
                  </button>
                </div>

                <span class="w-[1px] h-2.5 bg-slate-200"></span>

                <!-- 高度选择 -->
                <div class="flex items-center gap-0.5 text-[9px] font-mono text-slate-500">
                  <span class="text-slate-400 mr-0.5 scale-90 select-none">高:</span>
                  <button
                    v-for="row in [1, 2, 3]"
                    :key="`h-${row}`"
                    class="px-1 py-0.2 rounded transition font-medium"
                    :class="widget.h === row ? 'bg-primary-600 text-white font-bold' : 'hover:bg-slate-100 text-slate-600'"
                    :title="`设定占 ${row} 行高`"
                    @click.stop="setWidgetSize(widget, widget.w, row)"
                  >
                    {{ `${row}行` }}
                  </button>
                </div>

                <span class="w-[1px] h-2.5 bg-slate-200"></span>

                <!-- 拖动换高手柄 -->
                <span
                  class="cursor-grab active:cursor-grabbing text-slate-400 hover:text-slate-700 text-xs px-0.5 select-none"
                  title="按住拖拽自由吸附至网格坐标"
                >
                  ⠿
                </span>

                <!-- 下板按钮 -->
                <button
                  class="text-slate-400 hover:text-red-600 hover:bg-red-50 rounded px-1 text-xs font-bold leading-none transition"
                  title="下板移出画板"
                  @click.stop="removeWidget(widget)"
                >
                  ×
                </button>
              </div>

              <!-- ================= 各组件内容具体分支渲染 ================= -->

              <!-- 1. 姓名组件 -->
              <div v-if="widget.type === 'name' || widget.id === 'core_name'" class="flex items-baseline gap-2 h-full justify-center flex-col">
                <div v-if="editingWidgetId === widget.id" class="w-full">
                  <input
                    :id="`inline-input-${widget.id}`"
                    v-model="editingWidgetValue"
                    placeholder="输入姓名"
                    class="text-2xl font-extrabold tracking-wider text-slate-950 font-sans border-b-2 border-primary-500 outline-none w-full bg-primary-50/30 px-1 rounded"
                    @keydown.enter="finishEditWidget(widget)"
                    @blur="finishEditWidget(widget)"
                  />
                </div>
                <h1
                  v-else
                  class="font-extrabold tracking-wider font-sans cursor-pointer transition flex items-baseline gap-1.5"
                  :class="[
                    widget.w >= 6 ? 'text-3xl' : 'text-2xl',
                    widget.value ? 'text-slate-950 hover:text-primary-600' : 'text-slate-300 hover:text-primary-500 italic font-normal'
                  ]"
                  title="点击原地编辑姓名"
                  @click="startEditWidget(widget)"
                >
                  <span>{{ widget.value || '（点击输入姓名）' }}</span>
                  <span v-if="editable" class="text-xs text-slate-300 group-hover/widget:text-primary-500 opacity-0 group-hover/widget:opacity-100 transition not-italic">✎</span>
                </h1>
              </div>

              <!-- 2. 求职意向组件 -->
              <div v-else-if="widget.type === 'label' || widget.id === 'core_label'" class="flex items-center gap-1.5 h-full">
                <span class="text-[11px] text-slate-400 font-medium shrink-0">求职意向:</span>
                <div v-if="editingWidgetId === widget.id" class="flex-1 min-w-0">
                  <input
                    :id="`inline-input-${widget.id}`"
                    v-model="editingWidgetValue"
                    placeholder="如：全栈开发工程师"
                    class="border-b border-primary-500 outline-none text-xs font-bold text-slate-900 px-1 py-0.5 w-full bg-primary-50/30 rounded"
                    @keydown.enter="finishEditWidget(widget)"
                    @blur="finishEditWidget(widget)"
                  />
                </div>
                <div
                  v-else
                  class="cursor-pointer hover:text-primary-600 flex items-center gap-1 transition px-2 py-0.5 rounded border text-xs"
                  :class="widget.value ? 'text-slate-800 bg-slate-100/90 border-slate-200/90 font-bold' : 'text-slate-400 bg-slate-50 border-dashed border-slate-200 italic font-normal'"
                  title="点击原地编辑求职意向"
                  @click="startEditWidget(widget)"
                >
                  <span class="truncate">{{ widget.value || '+ 设置意向岗位' }}</span>
                  <span v-if="editable" class="text-[10px] text-slate-300 group-hover/widget:text-primary-500 opacity-0 group-hover/widget:opacity-100 transition not-italic">✎</span>
                </div>
              </div>

              <!-- 3. 免冠证件照组件 -->
              <div v-else-if="widget.type === 'photo' || widget.id === 'core_photo'" class="flex items-center justify-center h-full">
                <div
                  class="relative group/photo border border-slate-300 rounded bg-slate-100 overflow-hidden shadow-2xs cursor-pointer hover:ring-2 hover:ring-primary-400 transition w-full h-full max-h-[140px] flex items-center justify-center"
                  title="点击设置免冠照链接"
                  @click="promptEditPhoto(widget)"
                >
                  <img
                    v-if="widget.value"
                    :src="widget.value"
                    class="w-full h-full object-cover"
                    alt="证件照"
                  />
                  <div v-else class="text-center text-slate-300 flex flex-col items-center justify-center h-full p-1 select-none">
                    <span class="text-2xl">👤</span>
                    <span class="text-[9px] scale-90">上传照</span>
                  </div>
                  <div v-if="editable" class="absolute inset-0 bg-black/40 text-white text-[10px] flex items-center justify-center opacity-0 group-hover/photo:opacity-100 transition font-medium">
                    更换
                  </div>
                </div>
              </div>

              <!-- 4. 核心优势总结组件 -->
              <div v-else-if="widget.type === 'summary' || widget.id === 'core_summary'" class="w-full h-full flex flex-col justify-center">
                <div v-if="editingWidgetId === widget.id">
                  <textarea
                    :id="`inline-input-${widget.id}`"
                    v-model="editingWidgetValue"
                    placeholder="输入个人核心技术特长与综合优势总结…"
                    rows="2"
                    class="w-full text-xs text-slate-700 leading-relaxed border border-primary-300 rounded p-1.5 outline-none bg-primary-50/20 font-sans"
                    @keydown.enter.ctrl="finishEditWidget(widget)"
                    @blur="finishEditWidget(widget)"
                  />
                  <div class="text-[10px] text-slate-400 text-right">按 Ctrl+Enter 或点击空白处完成</div>
                </div>
                <div
                  v-else
                  class="cursor-pointer hover:bg-slate-50 p-1 rounded transition group/sum flex items-start gap-1.5 h-full"
                  @click="startEditWidget(widget)"
                >
                  <span class="text-xs font-bold text-primary-600 shrink-0 select-none">💡 优势:</span>
                  <p
                    class="text-xs text-slate-600 leading-relaxed flex-1 font-sans line-clamp-3"
                    :class="{ 'text-slate-300 italic': !widget.value }"
                  >
                    {{ widget.value || '+ 添加一句话核心优势总结 (可选)' }}
                  </p>
                  <span v-if="editable" class="text-[10px] text-slate-300 group-hover/widget:text-primary-500 opacity-0 group-hover/widget:opacity-100 transition shrink-0">✎</span>
                </div>
              </div>

              <!-- 5. 常规联系方式与个性化属性标签组件 -->
              <div v-else class="flex items-center gap-1.5 text-xs min-w-0 h-full">
                <span class="text-xs shrink-0 select-none opacity-85">{{ widget.icon || '🏷️' }}</span>
                <span class="font-semibold text-slate-500 text-[11px] shrink-0">{{ widget.label }}:</span>

                <!-- 原地编辑输入框 -->
                <div v-if="editingWidgetId === widget.id" class="flex-1 min-w-0">
                  <input
                    :id="`inline-input-${widget.id}`"
                    v-model="editingWidgetValue"
                    class="border-b border-primary-500 outline-none bg-white text-[11px] font-mono px-1 py-0.5 w-full rounded text-slate-900 shadow-2xs"
                    @keydown.enter="finishEditWidget(widget)"
                    @blur="finishEditWidget(widget)"
                  />
                </div>

                <!-- 原地展示文本 (点击即编辑) -->
                <span
                  v-else
                  class="font-mono text-slate-800 text-[11px] truncate flex-1 cursor-pointer hover:text-primary-600 hover:underline"
                  title="点击原地编辑内容"
                  @click="startEditWidget(widget)"
                >
                  {{ widget.value || '点击输入' }}
                </span>
              </div>
            </div>

            <!-- 空态吸附提示 (当没有任何组件时) -->
            <div
              v-if="!active2DWidgets.length && editable"
              class="col-span-12 py-6 px-4 rounded-xl border-2 border-dashed border-slate-200 text-slate-400 text-xs flex flex-col items-center justify-center gap-2 bg-slate-50/40 select-none"
            >
              <div class="text-2xl">📐</div>
              <div class="font-medium text-slate-600">个人信息二维坐标画布已就绪（暂无组件）</div>
              <div class="text-[11px] text-slate-400">
                从左侧积木池自由拖入【姓名、求职意向、联系电话、照片、核心优势】至任意网格坐标
              </div>
            </div>
          </div>
        </header>

        <!-- ================= 2~N 动态大模块流 (按 section_order 呈现，纯净优雅排版) ================= -->
        <div class="resume-sections-flow space-y-4">
          <div
            v-for="secId in dynamicSections"
            :key="secId"
            class="section-wrapper"
          >
            <!-- ---------------- 具体模块分支渲染 ---------------- -->

            <!-- 1. 教育背景 -->
            <section v-if="secId === 'education' && education.length" class="section">
              <h2
                class="sec-title text-sm font-extrabold text-slate-900 uppercase tracking-wider mb-2 pb-1 border-b"
                :style="{ borderColor: themeStyles.lineColor }"
              >
                <span>教育经历</span>
              </h2>
              <div class="space-y-2.5 pt-1">
                <div v-for="(edu, idx) in education" :key="idx" class="edu-item">
                  <div class="flex items-baseline justify-between text-xs font-sans">
                    <span class="font-bold text-slate-900 text-[13px] min-w-[120px]">{{ edu.institution || edu.school || '院校名称' }}</span>
                    <span class="text-slate-600 font-medium text-center flex-1 px-2">
                      {{ formatEduSub(edu) }}
                    </span>
                    <span class="text-slate-500 font-mono text-[11px] text-right shrink-0">
                      {{ formatDate(edu.startDate || edu.start_date, edu.endDate || edu.end_date) }}
                    </span>
                  </div>
                  <ul v-if="edu.highlights?.length || edu.courses?.length" class="mt-1 space-y-0.5 text-xs text-slate-700 list-none pl-0">
                    <li v-for="(hl, hli) in (edu.highlights || edu.courses || [])" :key="hli" class="flex items-start gap-1.5 leading-relaxed">
                      <span class="text-slate-400 font-bold">•</span>
                      <span>{{ hl }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </section>

            <!-- 2. 专业技能 -->
            <section v-else-if="secId === 'skills' && parsedSkills.length" class="section">
              <h2
                class="sec-title text-sm font-extrabold text-slate-900 uppercase tracking-wider mb-2 pb-1 border-b"
                :style="{ borderColor: themeStyles.lineColor }"
              >
                <span>专业技能</span>
              </h2>
              <div class="space-y-1.5 pt-1 text-xs text-slate-800 font-sans leading-relaxed">
                <div v-for="(sk, idx) in parsedSkills" :key="idx" class="skill-row">
                  <div v-if="sk.type === 'text'" class="flex items-start gap-1.5">
                    <span v-if="!/^(\d+[\.、]|[•\-\*])/.test((sk.text || '').trim())" class="text-slate-400 font-bold">•</span>
                    <span class="flex-1" v-html="formatSkillText(sk.text || '')"></span>
                  </div>
                  <div v-else-if="sk.type === 'group'" class="flex items-baseline gap-2">
                    <span v-if="sk.name" class="font-bold text-slate-900 shrink-0">{{ sk.name }}:</span>
                    <div v-if="sk.keywords?.length" class="flex flex-wrap gap-1.5 flex-1">
                      <span
                        v-for="(kw, kwi) in sk.keywords"
                        :key="kwi"
                        class="px-2 py-0.5 rounded text-[11px] font-mono border"
                        :style="{
                          backgroundColor: themeStyles.primaryLight,
                          borderColor: themeStyles.primaryBorder,
                          color: themeStyles.textPrimary
                        }"
                      >
                        {{ kw }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <!-- 3. 工作经历 -->
            <section v-else-if="secId === 'experience' && experience.length" class="section">
              <h2
                class="sec-title text-sm font-extrabold text-slate-900 uppercase tracking-wider mb-2 pb-1 border-b"
                :style="{ borderColor: themeStyles.lineColor }"
              >
                <span>工作经历</span>
              </h2>
              <div class="space-y-3 pt-1">
                <div v-for="(exp, idx) in experience" :key="idx" class="exp-item">
                  <div class="flex items-baseline justify-between text-xs">
                    <span class="font-bold text-slate-950 text-[13px]">{{ exp.company || '公司名称' }}</span>
                    <span v-if="exp.role || exp.position" class="text-slate-600 font-medium text-center flex-1 px-2">
                      {{ exp.role || exp.position }}
                    </span>
                    <span class="text-slate-500 font-mono text-[11px] text-right shrink-0">
                      {{ formatDate(exp.startDate || exp.start_date, exp.endDate || exp.end_date) }}
                    </span>
                  </div>
                  <p v-if="exp.description" class="text-xs text-slate-600 mt-0.5 leading-relaxed">
                    {{ exp.description }}
                  </p>
                  <ul v-if="exp.highlights?.length" class="mt-1 space-y-1 text-xs text-slate-700 list-none pl-0">
                    <li v-for="(hl, hli) in exp.highlights" :key="hli" class="flex items-start gap-1.5 leading-relaxed">
                      <span class="text-slate-400 font-bold">•</span>
                      <span>{{ hl }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </section>

            <!-- 4. 项目经历 -->
            <section v-else-if="secId === 'projects' && projects.length" class="section">
              <h2
                class="sec-title text-sm font-extrabold text-slate-900 uppercase tracking-wider mb-2 pb-1 border-b"
                :style="{ borderColor: themeStyles.lineColor }"
              >
                <span>项目经历</span>
              </h2>
              <div class="space-y-3 pt-1">
                <div v-for="(proj, idx) in projects" :key="idx" class="proj-item">
                  <div class="flex items-baseline justify-between text-xs">
                    <div class="flex items-baseline gap-2">
                      <span class="font-bold text-slate-950 text-[13px]">{{ proj.name || '项目名称' }}</span>
                      <span v-if="proj.link || proj.url" class="text-[11px] text-blue-600 font-mono underline truncate max-w-[200px]">
                        {{ proj.link || proj.url }}
                      </span>
                    </div>
                    <span v-if="proj.role" class="text-slate-600 font-medium text-center flex-1 px-2">
                      {{ proj.role }}
                    </span>
                    <span class="text-slate-500 font-mono text-[11px] text-right shrink-0">
                      {{ formatDate(proj.startDate || proj.start_date, proj.endDate || proj.end_date) }}
                    </span>
                  </div>
                  <div v-if="proj.description" class="text-xs text-slate-600 mt-1 leading-relaxed">
                    {{ proj.description }}
                  </div>
                  <ul v-if="proj.highlights?.length" class="mt-1 space-y-1 text-xs text-slate-700 list-none pl-0">
                    <li v-for="(hl, hli) in proj.highlights" :key="hli" class="flex items-start gap-1.5 leading-relaxed">
                      <span class="text-slate-400 font-bold">•</span>
                      <span>{{ hl }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </section>

            <!-- 5. 个人亮点 -->
            <section v-else-if="secId === 'highlights' && highlights.length" class="section">
              <h2
                class="sec-title text-sm font-extrabold text-slate-900 uppercase tracking-wider mb-2 pb-1 border-b"
                :style="{ borderColor: themeStyles.lineColor }"
              >
                <span>个人亮点</span>
              </h2>
              <ul class="space-y-1 pt-1 text-xs text-slate-700 list-none pl-0">
                <li v-for="(hl, idx) in highlights" :key="idx" class="flex items-start gap-1.5 leading-relaxed">
                  <span class="text-slate-400 font-bold">•</span>
                  <span>{{ hl }}</span>
                </li>
              </ul>
            </section>

            <!-- 6. 自定义模块 (custom_xxx) -->
            <section
              v-else-if="secId.startsWith('custom_') && customSections.find((c: any) => `custom_${c.id}` === secId || c.id === secId)"
              class="section"
            >
              <template v-for="cs in [customSections.find((c: any) => `custom_${c.id}` === secId || c.id === secId)]" :key="cs.id">
                <h2
                  class="sec-title text-sm font-extrabold text-slate-900 uppercase tracking-wider mb-2 pb-1 border-b"
                  :style="{ borderColor: themeStyles.lineColor }"
                >
                  <span>{{ cs.title }}</span>
                </h2>
                <div class="space-y-2 pt-1">
                  <div v-for="(it, iti) in cs.items || []" :key="iti" class="text-xs">
                    <div class="flex items-baseline justify-between">
                      <span class="font-bold text-slate-900">{{ it.title }}</span>
                      <span v-if="it.subtitle" class="text-slate-500 font-medium">{{ it.subtitle }}</span>
                      <span v-if="it.date" class="text-slate-400 font-mono text-[11px]">{{ it.date }}</span>
                    </div>
                    <p v-if="it.description" class="text-slate-600 mt-0.5 leading-relaxed">{{ it.description }}</p>
                  </div>
                </div>
              </template>
            </section>
          </div>
        </div>

        <!-- 纸张底脚空白占位 -->
        <div class="h-6"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.a4-paper-wrapper {
  transform-origin: top center;
}
.a4-paper {
  page-break-after: always;
}
</style>
