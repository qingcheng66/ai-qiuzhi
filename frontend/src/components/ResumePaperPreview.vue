<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'

export interface SkillItem {
  type: 'text' | 'group'
  text?: string
  name?: string
  keywords?: string[]
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

// 基础信息已上板的所有标签（包括电话、邮箱、地点等常规字段与自定义字段）
interface ActiveTagChip {
  id: string
  kind: 'standard' | 'custom'
  key: string
  label: string
  value: string
  icon: string
}

const activeHeaderChips = computed<ActiveTagChip[]>(() => {
  const b = basics.value
  const list: ActiveTagChip[] = []

  // 1. 常规预置字段（只要有值就作为药丸展示并可交互）
  if (b.phone) {
    list.push({ id: 'std_phone', kind: 'standard', key: 'phone', label: '电话', value: b.phone, icon: '📞' })
  }
  if (b.email) {
    list.push({ id: 'std_email', kind: 'standard', key: 'email', label: '邮箱', value: b.email, icon: '✉️' })
  }
  if (b.wechat) {
    list.push({ id: 'std_wechat', kind: 'standard', key: 'wechat', label: '微信', value: b.wechat, icon: '💬' })
  }
  if (b.birthDate || b.birth) {
    list.push({ id: 'std_birthDate', kind: 'standard', key: 'birthDate', label: '生日', value: b.birthDate || b.birth, icon: '🎂' })
  }
  if (b.location) {
    list.push({ id: 'std_location', kind: 'standard', key: 'location', label: '城市', value: b.location, icon: '📍' })
  }
  if (b.github) {
    list.push({ id: 'std_github', kind: 'standard', key: 'github', label: 'GitHub', value: b.github, icon: '🐙' })
  }
  if (b.blog) {
    list.push({ id: 'std_blog', kind: 'standard', key: 'blog', label: '博客', value: b.blog, icon: '🌐' })
  }

  // 2. 自定义扩展字段
  const cfs = Array.isArray(b.custom_fields) ? b.custom_fields : []
  cfs.forEach((cf: any, idx: number) => {
    if (cf && (cf.label || cf.value)) {
      list.push({
        id: cf.id || `cf_${idx}`,
        kind: 'custom',
        key: `custom_${idx}`,
        label: cf.label || '自定义项',
        value: cf.value || '',
        icon: cf.icon || '🏷️',
      })
    }
  })

  // 如果有 tag_order，按自定义顺序排序
  const order: string[] = Array.isArray(b.tag_order) ? b.tag_order : []
  if (order.length > 0) {
    list.sort((a, b) => {
      const idxA = order.indexOf(a.id)
      const idxB = order.indexOf(b.id)
      if (idxA === -1 && idxB === -1) return 0
      if (idxA === -1) return 1
      if (idxB === -1) return -1
      return idxA - idxB
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

// =================== 拖放交互状态 ===================
const isHeaderDraggingOver = ref(false)
const draggingTagLabel = ref('')

// 1. Header 接收标签拖入
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
    if (payload.type === 'tag') {
      applyTagToBasics(payload.data)
    }
  } catch (err) {
    console.error('Failed to parse dropped tag data:', err)
  }
}

// 将拖入或点击的标签应用至 basics
function applyTagToBasics(tag: any) {
  if (!props.resumeData) return
  const rd = { ...props.resumeData }
  if (!rd.basics) rd.basics = {}

  const standardKeys = ['phone', 'email', 'location', 'birthDate', 'github', 'blog']
  if (tag.key && standardKeys.includes(tag.key)) {
    // 写入常规标准字段
    rd.basics[tag.key] = tag.value || rd.basics[tag.key] || `${tag.label}内容`
  } else {
    // 写入自定义扩展字段
    if (!Array.isArray(rd.basics.custom_fields)) {
      rd.basics.custom_fields = []
    }
    // 检查是否已有同名标签
    const existing = rd.basics.custom_fields.find((cf: any) => cf.label === tag.label)
    if (existing) {
      existing.value = tag.value || existing.value
    } else {
      rd.basics.custom_fields.push({
        id: tag.id || `cf_${Date.now()}`,
        label: tag.label,
        value: tag.value || '点击编辑内容',
        icon: tag.icon || '🏷️',
      })
    }
  }

  emit('update:resume-data', rd)
  emit('change', 'basics')
}

// 从画板上移除标签
function removeTagFromHeader(chip: ActiveTagChip, e?: MouseEvent) {
  if (e) e.stopPropagation()
  if (!props.resumeData) return
  const rd = { ...props.resumeData }
  if (!rd.basics) return

  if (chip.kind === 'standard') {
    rd.basics[chip.key] = ''
  } else {
    const cfs = Array.isArray(rd.basics.custom_fields) ? rd.basics.custom_fields : []
    const idx = parseInt(chip.id.replace('cf_', ''), 10)
    if (!isNaN(idx) && idx >= 0 && idx < cfs.length) {
      cfs.splice(idx, 1)
      rd.basics.custom_fields = [...cfs]
    } else {
      rd.basics.custom_fields = cfs.filter((cf: any) => cf.label !== chip.label)
    }
  }

  emit('update:resume-data', rd)
  emit('change', 'basics')
}

// 标签原地编辑 (Inline Click-to-Edit)
const editingChipId = ref<string | null>(null)
const editingChipValue = ref('')

function startEditChip(chip: ActiveTagChip) {
  if (!props.editable) return
  editingChipId.value = chip.id
  editingChipValue.value = chip.value
  nextTick(() => {
    const input = document.getElementById(`inline-chip-input-${chip.id}`)
    input?.focus()
  })
}

function finishEditChip(chip: ActiveTagChip) {
  if (!editingChipId.value) return
  const val = editingChipValue.value.trim()
  editingChipId.value = null

  if (!props.resumeData) return
  const rd = { ...props.resumeData }
  if (!rd.basics) rd.basics = {}

  if (chip.kind === 'standard') {
    rd.basics[chip.key] = val
  } else {
    const cfs = Array.isArray(rd.basics.custom_fields) ? rd.basics.custom_fields : []
    const idx = parseInt(chip.id.replace('cf_', ''), 10)
    if (!isNaN(idx) && cfs[idx]) {
      cfs[idx].value = val
      rd.basics.custom_fields = [...cfs]
    }
  }

  emit('update:resume-data', rd)
  emit('change', 'basics')
}

// 姓名/求职头衔/总结 原地点击编辑
const editingField = ref<string | null>(null)
const editingFieldValue = ref('')

function startEditField(fieldName: 'name' | 'label' | 'summary') {
  if (!props.editable) return
  editingField.value = fieldName
  editingFieldValue.value = basics.value[fieldName] || ''
  nextTick(() => {
    const el = document.getElementById(`inline-field-${fieldName}`)
    el?.focus()
  })
}

function finishEditField(fieldName: 'name' | 'label' | 'summary') {
  if (!editingField.value) return
  const val = editingFieldValue.value.trim()
  editingField.value = null

  if (!props.resumeData) return
  const rd = { ...props.resumeData }
  if (!rd.basics) rd.basics = {}
  rd.basics[fieldName] = val

  emit('update:resume-data', rd)
  emit('change', 'basics')
}

function isLongChip(chip: ActiveTagChip): boolean {
  if (['github', 'blog'].includes(chip.key)) return true
  if (chip.value && chip.value.length > 28) return true
  if (chip.value && (chip.value.startsWith('http://') || chip.value.startsWith('https://'))) return true
  return false
}

const draggingChipId = ref<string | null>(null)

function onChipDragStart(e: DragEvent, chip: ActiveTagChip) {
  if (!props.editable) return
  draggingChipId.value = chip.id
  if (e.dataTransfer) {
    e.dataTransfer.setData('application/json', JSON.stringify({ type: 'inner-chip', id: chip.id }))
    e.dataTransfer.effectAllowed = 'move'
  }
}

function onChipDrop(e: DragEvent, targetChip: ActiveTagChip) {
  if (!props.editable) return
  e.preventDefault()
  if (!draggingChipId.value || draggingChipId.value === targetChip.id) return

  const srcId = draggingChipId.value
  draggingChipId.value = null

  if (!props.resumeData) return
  const rd = { ...props.resumeData }
  if (!rd.basics) rd.basics = {}

  let order: string[] = Array.isArray(rd.basics.tag_order) && rd.basics.tag_order.length > 0
    ? [...rd.basics.tag_order]
    : activeHeaderChips.value.map((c) => c.id)

  const srcIdx = order.indexOf(srcId)
  const targetIdx = order.indexOf(targetChip.id)

  if (srcIdx !== -1 && targetIdx !== -1) {
    order.splice(srcIdx, 1)
    order.splice(targetIdx, 0, srcId)
  } else {
    order = activeHeaderChips.value.map((c) => c.id)
    const sI = order.indexOf(srcId)
    const tI = order.indexOf(targetChip.id)
    if (sI !== -1 && tI !== -1) {
      order.splice(sI, 1)
      order.splice(tI, 0, srcId)
    }
  }

  rd.basics.tag_order = order
  emit('update:resume-data', rd)
  emit('change', 'basics')
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
        <!-- ================= 1. Header (严整对齐网格磁吸槽: 左侧姓名/意向/双列网格/总结 + 右侧证件照) ================= -->
        <header
          v-if="isSectionVisible('basics')"
          class="header-section group/header relative pb-4 mb-4 border-b border-slate-200 transition-all rounded-xl p-2.5"
          :class="isHeaderDraggingOver ? 'bg-primary-50/70 ring-2 ring-dashed ring-primary-500 shadow-sm' : 'hover:bg-slate-50/40'"
          @dragover="handleHeaderDragOver"
          @dragleave="handleHeaderDragLeave"
          @drop="handleHeaderDrop"
        >
          <!-- 拖拽悬停吸附指示框 -->
          <div
            v-if="isHeaderDraggingOver"
            class="absolute inset-0 bg-primary-50/90 backdrop-blur-xs rounded-xl flex items-center justify-center z-30 pointer-events-none border-2 border-dashed border-primary-500 animate-pulse"
          >
            <div class="px-5 py-2.5 bg-white rounded-xl shadow-lg border border-primary-200 text-primary-700 font-bold text-xs flex items-center gap-2">
              <span class="text-xl">🎯</span>
              <span>松开鼠标，将标签精准吸附至简历网格</span>
            </div>
          </div>

          <!-- 头部主体：左侧信息区 (姓名+意向+双列对齐网格+总结) + 右侧证件照 -->
          <div class="flex justify-between items-start gap-6">
            <div class="flex-1 min-w-0 space-y-2.5">
              <!-- 1. 姓名与求职意向 (置顶左对齐，层级分明) -->
              <div class="flex items-baseline gap-3.5 flex-wrap">
                <!-- 姓名 (支持原地点击改字) -->
                <div v-if="editingField === 'name'" class="inline-block">
                  <input
                    id="inline-field-name"
                    v-model="editingFieldValue"
                    class="text-3xl font-extrabold tracking-wider text-slate-950 font-sans border-b-2 border-primary-500 outline-none px-1 bg-primary-50/30 rounded"
                    @keydown.enter="finishEditField('name')"
                    @blur="finishEditField('name')"
                  />
                </div>
                <h1
                  v-else
                  class="group/name text-3xl font-extrabold tracking-wider text-slate-950 font-sans cursor-pointer hover:text-primary-600 transition flex items-baseline gap-1"
                  title="点击直接修改姓名"
                  @click="startEditField('name')"
                >
                  <span>{{ basics.name || '您的姓名' }}</span>
                  <span class="text-xs text-slate-300 group-hover/name:text-primary-500 opacity-0 group-hover/name:opacity-100 transition">✎</span>
                </h1>

                <!-- 求职意向 (头衔徽标) -->
                <div class="flex items-center gap-1.5">
                  <span class="text-[11px] text-slate-400 font-medium">求职意向:</span>
                  <div v-if="editingField === 'label'" class="inline-block">
                    <input
                      id="inline-field-label"
                      v-model="editingFieldValue"
                      class="border-b border-primary-500 outline-none text-xs font-bold text-slate-900 px-1 py-0.5 bg-primary-50/30 rounded"
                      @keydown.enter="finishEditField('label')"
                      @blur="finishEditField('label')"
                    />
                  </div>
                  <div
                    v-else
                    class="group/title text-xs font-bold text-slate-800 cursor-pointer hover:text-primary-600 flex items-center gap-1 transition px-2 py-0.5 rounded bg-slate-100/90 border border-slate-200/90"
                    title="点击直接原地修改意向头衔"
                    @click="startEditField('label')"
                  >
                    <span>{{ basics.label || basics.title || '点击设置求职意向 (如：全栈开发工程师)' }}</span>
                    <span class="text-[10px] text-slate-300 group-hover/title:text-primary-500 opacity-0 group-hover/title:opacity-100 transition">✎</span>
                  </div>
                </div>
              </div>

              <!-- 2. 严整的双列网格联系方式与属性 (对齐线笔直，短项占1格，长项跨2格) -->
              <div class="grid grid-cols-2 gap-x-8 gap-y-1 text-xs text-slate-700 font-sans pt-0.5">
                <div
                  v-for="chip in activeHeaderChips"
                  :key="chip.id"
                  class="group/chip relative flex items-center justify-between gap-1.5 py-0.5 px-1.5 rounded transition-all hover:bg-slate-100/70"
                  :class="isLongChip(chip) ? 'col-span-2' : 'col-span-1'"
                  draggable="true"
                  @dragstart="onChipDragStart($event, chip)"
                  @dragover.prevent
                  @drop="onChipDrop($event, chip)"
                >
                  <div class="flex items-center gap-1.5 min-w-0 flex-1">
                    <span class="text-xs shrink-0 select-none opacity-85">{{ chip.icon }}</span>
                    <span class="font-semibold text-slate-500 text-[11px] shrink-0">{{ chip.label }}:</span>

                    <!-- 原地编辑输入框 -->
                    <div v-if="editingChipId === chip.id" class="flex-1 min-w-0">
                      <input
                        :id="`inline-chip-input-${chip.id}`"
                        v-model="editingChipValue"
                        class="border-b border-primary-500 outline-none bg-white text-[11px] font-mono px-1 py-0.5 w-full rounded text-slate-900 shadow-2xs"
                        @keydown.enter="finishEditChip(chip)"
                        @blur="finishEditChip(chip)"
                      />
                    </div>

                    <!-- 原地展示文本 (点击即编辑) -->
                    <span
                      v-else
                      class="font-mono text-slate-800 text-[11px] truncate flex-1 cursor-pointer hover:text-primary-600 hover:underline"
                      title="点击原地编辑内容"
                      @click="startEditChip(chip)"
                    >
                      {{ chip.value }}
                    </span>
                  </div>

                  <!-- 移出标签快捷按钮 (x) & 拖动手柄 -->
                  <div class="flex items-center gap-1 shrink-0 opacity-0 group-hover/chip:opacity-100 transition">
                    <span class="cursor-grab active:cursor-grabbing text-slate-300 hover:text-slate-600 text-xs px-0.5 select-none" title="按住拖拽互换顺序">⠿</span>
                    <button
                      v-if="editable"
                      class="text-slate-400 hover:text-red-600 text-xs font-bold leading-none px-0.5"
                      title="移出此标签"
                      @click="removeTagFromHeader(chip, $event)"
                    >
                      ×
                    </button>
                  </div>
                </div>

                <!-- 空态吸附提示 (当没有任何标签时) -->
                <div
                  v-if="!activeHeaderChips.length"
                  class="col-span-2 px-3 py-2 rounded-lg border border-dashed border-slate-300 text-slate-400 text-xs flex items-center justify-center gap-2 bg-slate-50/60"
                >
                  <span>🏷️</span>
                  <span>从左侧积木池拖入手机、微信、期望薪资等标签，将在此自动形成严整双列对齐网格</span>
                </div>
              </div>

              <!-- 3. 一句话优势 / 自我总结 (通栏对齐) -->
              <div class="pt-1 border-t border-slate-100">
                <div v-if="editingField === 'summary'">
                  <textarea
                    id="inline-field-summary"
                    v-model="editingFieldValue"
                    rows="2"
                    class="w-full text-xs text-slate-700 leading-relaxed border border-primary-300 rounded p-1.5 outline-none bg-primary-50/20"
                    @keydown.enter.ctrl="finishEditField('summary')"
                    @blur="finishEditField('summary')"
                  />
                  <div class="text-[10px] text-slate-400 text-right">按 Ctrl+Enter 或点击空白处完成</div>
                </div>
                <p
                  v-else
                  class="group/summary text-xs text-slate-600 leading-relaxed cursor-pointer hover:text-slate-900 transition flex items-start gap-1"
                  title="点击原地修改个人技术特长与优势总结"
                  @click="startEditField('summary')"
                >
                  <span class="flex-1">{{ basics.summary || '点击输入一句话个人核心技术特长与综合优势总结…' }}</span>
                  <span class="text-[10px] text-slate-300 group-hover/summary:text-primary-500 opacity-0 group-hover/summary:opacity-100 transition shrink-0">✎</span>
                </p>
              </div>
            </div>

            <!-- 右侧免冠证件照 -->
            <div class="shrink-0 flex flex-col items-center justify-start pt-1">
              <div class="w-[82px] h-[108px] border border-slate-300 rounded bg-slate-100 overflow-hidden shadow-2xs flex items-center justify-center shrink-0">
                <img
                  v-if="basics.photo || basics.avatar"
                  :src="basics.photo || basics.avatar"
                  class="w-full h-full object-cover"
                  alt="证件照"
                />
                <div v-else class="text-center text-slate-300 flex flex-col items-center justify-center h-full p-1 select-none">
                  <span class="text-2xl">👤</span>
                  <span class="text-[9px] scale-90">免冠照</span>
                </div>
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
