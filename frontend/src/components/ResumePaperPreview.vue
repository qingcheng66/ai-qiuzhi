<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'

export interface SkillItem {
  type: 'text' | 'group'
  text?: string
  name?: string
  keywords?: string[]
}

export interface HeaderGridWidget {
  id: string
  type: 'name' | 'label' | 'photo' | 'summary' | 'tag' | 'custom'
  key?: string
  label: string
  value: string
  icon: string
  cols: number // 2, 3, 4, 6, 12 (out of 12)
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

// 全局拖拽状态侦听（只有在鼠标拖拽组件时，才向用户点亮 12 栅格辅助对齐导轨）
const isDraggingActive = ref(false)
const dragOverWidgetId = ref<string | null>(null)
const draggingWidgetId = ref<string | null>(null)
const isHeaderDraggingOver = ref(false)

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

// 计算当前画板上的 12 栅格组件列表（支持持久化或从 basics 自动推导）
const activeGridWidgets = computed<HeaderGridWidget[]>(() => {
  const b = basics.value
  if (Array.isArray(b.grid_widgets) && b.grid_widgets.length > 0) {
    return b.grid_widgets
  }

  // 自动从当前已有 basics 数据推导初态
  const list: HeaderGridWidget[] = []

  if (b.name) {
    list.push({
      id: 'core_name',
      type: 'name',
      key: 'name',
      label: '姓名',
      value: b.name,
      icon: '👤',
      cols: b.label ? 6 : 12,
    })
  }

  if (b.label || b.title) {
    list.push({
      id: 'core_label',
      type: 'label',
      key: 'label',
      label: '求职意向',
      value: b.label || b.title,
      icon: '🎯',
      cols: 6,
    })
  }

  if (b.photo || b.avatar) {
    list.push({
      id: 'core_photo',
      type: 'photo',
      key: 'photo',
      label: '免冠照',
      value: b.photo || b.avatar,
      icon: '📷',
      cols: 3,
    })
  }

  const stdKeys = ['phone', 'email', 'wechat', 'location', 'birthDate', 'github', 'blog']
  for (const k of stdKeys) {
    if (b[k]) {
      const isLong = ['github', 'blog'].includes(k) || (b[k] && b[k].length > 25)
      list.push({
        id: `std_${k}`,
        type: 'tag',
        key: k,
        label: PRESET_LABELS[k] || k,
        value: b[k],
        icon: PRESET_ICONS[k] || '🏷️',
        cols: isLong ? 6 : 4,
      })
    }
  }

  const cfs = Array.isArray(b.custom_fields) ? b.custom_fields : []
  cfs.forEach((cf: any, idx: number) => {
    if (cf && (cf.label || cf.value)) {
      list.push({
        id: cf.id || `cf_${idx}`,
        type: 'custom',
        label: cf.label || '自定义项',
        value: cf.value || '',
        icon: cf.icon || '🏷️',
        cols: cf.cols || 4,
        isCustom: true,
      })
    }
  })

  if (b.summary) {
    list.push({
      id: 'core_summary',
      type: 'summary',
      key: 'summary',
      label: '一句话核心优势',
      value: b.summary,
      icon: '✨',
      cols: 12,
    })
  }

  return list
})

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

// =================== 12 栅格个人信息组件管理与拖拽交互 ===================

// 更新并同步网格数据回 basics，保证导出与后端无缝兼容
function updateGridWidgets(newWidgets: HeaderGridWidget[]) {
  if (!props.resumeData) return
  const rd = { ...props.resumeData }
  if (!rd.basics) rd.basics = {}
  rd.basics.grid_widgets = newWidgets

  // 严格同步基本数据字段
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
    cols: w.cols,
  }))

  emit('update:resume-data', rd)
  emit('change', 'basics')
}

// 自由调整某个组件在 12 栅格中的列跨度 (cols)
function setWidgetCols(widget: HeaderGridWidget, newCols: number) {
  if (!props.editable) return
  const current = [...activeGridWidgets.value]
  const idx = current.findIndex((w) => w.id === widget.id)
  if (idx !== -1) {
    current[idx] = {
      ...current[idx],
      cols: newCols,
    }
    updateGridWidgets(current)
  }
}

// 从画板上移除组件（下板）
function removeWidget(widget: HeaderGridWidget) {
  if (!props.editable) return
  const current = activeGridWidgets.value.filter((w) => w.id !== widget.id)
  updateGridWidgets(current)
}

// 原地编辑组件内容
const editingWidgetId = ref<string | null>(null)
const editingWidgetValue = ref('')

function startEditWidget(widget: HeaderGridWidget) {
  if (!props.editable) return
  editingWidgetId.value = widget.id
  editingWidgetValue.value = widget.value
  nextTick(() => {
    const el = document.getElementById(`inline-input-${widget.id}`)
    el?.focus()
  })
}

function finishEditWidget(widget: HeaderGridWidget) {
  if (!editingWidgetId.value) return
  const val = editingWidgetValue.value.trim()
  editingWidgetId.value = null

  const current = [...activeGridWidgets.value]
  const idx = current.findIndex((w) => w.id === widget.id)
  if (idx !== -1) {
    current[idx] = {
      ...current[idx],
      value: val,
    }
    updateGridWidgets(current)
  }
}

// 照片快捷设置 / 提示修改 URL
function promptEditPhoto(widget: HeaderGridWidget) {
  if (!props.editable) return
  const current = widget.value || ''
  const newUrl = window.prompt('请输入免冠证件照图片链接 (URL) 或清空：', current)
  if (newUrl !== null) {
    const list = [...activeGridWidgets.value]
    const idx = list.findIndex((w) => w.id === widget.id)
    if (idx !== -1) {
      list[idx] = { ...list[idx], value: newUrl.trim() }
      updateGridWidgets(list)
    }
  }
}

// 网格内部拖拽排序与从素材池拖入
function onWidgetDragStart(e: DragEvent, widget: HeaderGridWidget) {
  if (!props.editable) return
  draggingWidgetId.value = widget.id
  if (e.dataTransfer) {
    e.dataTransfer.setData('application/json', JSON.stringify({
      type: 'grid-widget-move',
      id: widget.id,
    }))
    e.dataTransfer.effectAllowed = 'move'
  }
}

function onWidgetDragOver(e: DragEvent, targetWidget: HeaderGridWidget) {
  if (!props.editable) return
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
  dragOverWidgetId.value = targetWidget.id
}

function onWidgetDrop(e: DragEvent, targetWidget: HeaderGridWidget) {
  if (!props.editable) return
  e.preventDefault()
  dragOverWidgetId.value = null
  const raw = e.dataTransfer?.getData('application/json')
  if (!raw) return

  try {
    const payload = JSON.parse(raw)
    // 1. 内部拖拽互换顺序
    if (payload.type === 'grid-widget-move' && payload.id) {
      if (payload.id === targetWidget.id) return
      const current = [...activeGridWidgets.value]
      const srcIdx = current.findIndex((w) => w.id === payload.id)
      const targetIdx = current.findIndex((w) => w.id === targetWidget.id)
      if (srcIdx !== -1 && targetIdx !== -1) {
        const [moved] = current.splice(srcIdx, 1)
        current.splice(targetIdx, 0, moved)
        updateGridWidgets(current)
      }
      return
    }

    // 2. 从左侧素材池拖入插在 targetWidget 之前
    if (payload.type === 'grid-widget' && payload.data) {
      insertWidgetAt(payload.data, targetWidget.id)
    }
  } catch (err) {
    console.error('Widget drop error:', err)
  }
}

function insertWidgetAt(data: any, targetId: string) {
  const current = [...activeGridWidgets.value]
  const existingIdx = current.findIndex(
    (w) => w.id === data.id || (data.key && w.key === data.key && data.key !== 'custom')
  )
  if (existingIdx !== -1) {
    // 已在板上，调整位置
    const [moved] = current.splice(existingIdx, 1)
    const targetIdx = current.findIndex((w) => w.id === targetId)
    if (targetIdx !== -1) {
      current.splice(targetIdx, 0, moved)
    } else {
      current.push(moved)
    }
    updateGridWidgets(current)
    return
  }

  const widgetType = data.widgetType || data.type || (data.category === 'core' ? data.key : 'tag')
  const newWidget: HeaderGridWidget = {
    id: data.id || `widget_${Date.now()}`,
    type: widgetType,
    key: data.key,
    label: data.label || '组件',
    value: data.value || '',
    icon: data.icon || '🏷️',
    cols: data.cols || (widgetType === 'summary' ? 12 : widgetType === 'photo' ? 3 : widgetType === 'name' ? 6 : 4),
    isCustom: data.category === 'custom' || data.isCustom,
  }

  const targetIdx = current.findIndex((w) => w.id === targetId)
  if (targetIdx !== -1) {
    current.splice(targetIdx, 0, newWidget)
  } else {
    current.push(newWidget)
  }
  updateGridWidgets(current)
}

function appendWidget(data: any) {
  const current = [...activeGridWidgets.value]
  const existingIdx = current.findIndex(
    (w) => w.id === data.id || (data.key && w.key === data.key && data.key !== 'custom')
  )
  if (existingIdx !== -1) {
    if (data.value) current[existingIdx].value = data.value
    updateGridWidgets(current)
    return
  }

  const widgetType = data.widgetType || data.type || (data.category === 'core' ? data.key : 'tag')
  const newWidget: HeaderGridWidget = {
    id: data.id || `widget_${Date.now()}`,
    type: widgetType,
    key: data.key,
    label: data.label || '组件',
    value: data.value || '',
    icon: data.icon || '🏷️',
    cols: data.cols || (widgetType === 'summary' ? 12 : widgetType === 'photo' ? 3 : widgetType === 'name' ? 6 : 4),
    isCustom: data.category === 'custom' || data.isCustom,
  }

  current.push(newWidget)
  updateGridWidgets(current)
}

// 头部区域拖拽事件
function handleHeaderDragOver(e: DragEvent) {
  if (!props.editable) return
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'copy'
  }
  isHeaderDraggingOver.value = true
}

function handleHeaderDragLeave(e: DragEvent) {
  const target = e.currentTarget as HTMLElement
  if (!target.contains(e.relatedTarget as Node)) {
    isHeaderDraggingOver.value = false
  }
}

function handleHeaderDrop(e: DragEvent) {
  if (!props.editable) return
  e.preventDefault()
  isHeaderDraggingOver.value = false
  const raw = e.dataTransfer?.getData('application/json')
  if (!raw) return

  try {
    const payload = JSON.parse(raw)
    if (payload.type === 'grid-widget' && payload.data) {
      appendWidget(payload.data)
    } else if (payload.type === 'tag' && payload.data) {
      appendWidget(payload.data)
    }
  } catch (err) {
    console.error('Header drop error:', err)
  }
}

// 供父组件直接调用
function applyTagToBasics(tag: any) {
  appendWidget({
    id: tag.id,
    widgetType: tag.type || (tag.category === 'core' ? tag.key : 'tag'),
    key: tag.key || 'custom',
    label: tag.label,
    value: tag.value,
    icon: tag.icon,
    cols: tag.defaultCols || 4,
    category: tag.category,
    isCustom: tag.isCustom,
  })
}

defineExpose({
  applyTagToBasics,
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
        <!-- ================= 1. Header (12 栅格自适应个人信息板：所有组件支持自由拖拽、设定列宽，拖动时浮现网格) ================= -->
        <header
          v-if="isSectionVisible('basics')"
          class="header-section relative pb-4 mb-4 border-b border-slate-200 transition-all rounded-xl p-3 select-text"
          :class="{
            'ring-2 ring-primary-500 ring-dashed bg-primary-50/20 shadow-sm': isDraggingActive,
            'hover:bg-slate-50/40': !isDraggingActive,
          }"
          @dragover="handleHeaderDragOver"
          @dragleave="handleHeaderDragLeave"
          @drop="handleHeaderDrop"
        >
          <!-- 只有在拖拽时才点亮的 12 栅格蓝图辅助对齐导轨 (平时 100% 彻底隐形) -->
          <div
            v-if="isDraggingActive"
            class="pointer-events-none absolute inset-0 z-10 grid grid-cols-12 gap-3 p-3 rounded-xl transition-all duration-200"
          >
            <div
              v-for="col in 12"
              :key="col"
              class="h-full rounded-md border border-dashed border-primary-300/80 bg-primary-500/5 flex flex-col items-center justify-between py-1 transition-all"
            >
              <span class="text-[9px] font-mono text-primary-500 font-bold select-none opacity-80">{{ col }}</span>
              <div class="h-full w-px border-r border-dashed border-primary-200/50 my-1"></div>
              <span class="text-[8px] font-mono text-primary-400 select-none opacity-50">C{{ col }}</span>
            </div>
          </div>

          <!-- 拖拽悬停至整个头部时的吸附高亮条 -->
          <div
            v-if="isHeaderDraggingOver"
            class="absolute top-1 left-1/2 -translate-x-1/2 z-30 pointer-events-none px-4 py-1.5 bg-primary-600 text-white rounded-full shadow-lg text-[11px] font-bold flex items-center gap-1.5 animate-bounce"
          >
            <span>🎯</span>
            <span>松开鼠标，将组件吸附至 12 栅格画板</span>
          </div>

          <!-- 12 栅格核心组件流排版 -->
          <div class="relative z-20 grid grid-cols-12 gap-x-4 gap-y-2.5 items-center">
            <div
              v-for="(widget, idx) in activeGridWidgets"
              :key="widget.id"
              class="grid-widget-item group/widget relative rounded-lg transition-all"
              :style="{ gridColumn: `span ${Math.min(12, Math.max(1, widget.cols || 4))}` }"
              :class="[
                dragOverWidgetId === widget.id ? 'ring-2 ring-primary-500 scale-[1.01] bg-primary-50/50 shadow-xs' : '',
                editable ? 'hover:ring-1 hover:ring-primary-300/80 hover:bg-slate-50/80 p-1.5' : 'p-0.5'
              ]"
              :draggable="editable"
              @dragstart="onWidgetDragStart($event, widget)"
              @dragover="onWidgetDragOver($event, widget)"
              @drop="onWidgetDrop($event, widget)"
            >
              <!-- 悬停微型控制条: 尺寸调节 (2格/3格/4格/6格/12格) + 拖动手柄 + 下板 (×) -->
              <div
                v-if="editable"
                class="widget-ctrl-bar absolute -top-3.5 right-1 flex items-center gap-1 bg-white/95 backdrop-blur-xs shadow-md border border-slate-200/90 rounded-md px-1.5 py-0.5 z-30 opacity-0 group-hover/widget:opacity-100 transition-opacity"
              >
                <!-- 尺寸快速切换按钮组 -->
                <div class="flex items-center gap-0.5 text-[9px] font-mono text-slate-500">
                  <span class="text-slate-400 mr-0.5 scale-90 select-none">格数:</span>
                  <button
                    v-for="col in [2, 3, 4, 6, 12]"
                    :key="col"
                    class="px-1 py-0.2 rounded transition font-medium"
                    :class="widget.cols === col ? 'bg-primary-600 text-white font-bold' : 'hover:bg-slate-100 text-slate-600'"
                    :title="`设定占 ${col} 格 (${Math.round((col / 12) * 100)}% 宽度)`"
                    @click.stop="setWidgetCols(widget, col)"
                  >
                    {{ col === 12 ? '全宽' : `${col}格` }}
                  </button>
                </div>

                <span class="w-[1px] h-2.5 bg-slate-200"></span>

                <!-- 拖动换高手柄 -->
                <span
                  class="cursor-grab active:cursor-grabbing text-slate-400 hover:text-slate-700 text-xs px-0.5 select-none"
                  title="按住拖拽互换网格顺序"
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
              <div v-if="widget.type === 'name' || widget.id === 'core_name'" class="flex items-baseline gap-2">
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
                    widget.cols >= 6 ? 'text-3xl' : 'text-2xl',
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
              <div v-else-if="widget.type === 'label' || widget.id === 'core_label'" class="flex items-center gap-1.5">
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
              <div v-else-if="widget.type === 'photo' || widget.id === 'core_photo'" class="flex items-center justify-center">
                <div
                  class="relative group/photo border border-slate-300 rounded bg-slate-100 overflow-hidden shadow-2xs cursor-pointer hover:ring-2 hover:ring-primary-400 transition"
                  :style="{
                    width: widget.cols >= 4 ? '92px' : '72px',
                    height: widget.cols >= 4 ? '122px' : '96px',
                  }"
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
              <div v-else-if="widget.type === 'summary' || widget.id === 'core_summary'" class="w-full pt-0.5">
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
                  class="cursor-pointer hover:bg-slate-50 p-1 rounded transition group/sum flex items-start gap-1.5"
                  @click="startEditWidget(widget)"
                >
                  <span class="text-xs font-bold text-primary-600 shrink-0 select-none">💡 优势:</span>
                  <p
                    class="text-xs text-slate-600 leading-relaxed flex-1 font-sans"
                    :class="{ 'text-slate-300 italic': !widget.value }"
                  >
                    {{ widget.value || '+ 添加一句话核心优势总结 (可选)' }}
                  </p>
                  <span v-if="editable" class="text-[10px] text-slate-300 group-hover/widget:text-primary-500 opacity-0 group-hover/widget:opacity-100 transition shrink-0">✎</span>
                </div>
              </div>

              <!-- 5. 常规联系方式与个性化属性标签组件 -->
              <div v-else class="flex items-center gap-1.5 text-xs min-w-0">
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
              v-if="!activeGridWidgets.length && editable"
              class="col-span-12 py-6 px-4 rounded-xl border-2 border-dashed border-slate-200 text-slate-400 text-xs flex flex-col items-center justify-center gap-2 bg-slate-50/40 select-none"
            >
              <div class="text-2xl">🧱</div>
              <div class="font-medium text-slate-600">个人信息 12 栅格已就绪（暂无组件）</div>
              <div class="text-[11px] text-slate-400">
                从左侧积木池点击或拖入【姓名、求职意向、联系电话、照片、核心优势】等任意积木自由拼配
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
