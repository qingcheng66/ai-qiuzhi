<script setup lang="ts">
import { computed, ref, watch } from 'vue'

export interface CustomField {
  label: string
  value: string
}

export interface CustomSectionItem {
  id?: string
  title: string
  subtitle?: string
  date?: string
  description?: string
  highlights?: string[]
  visible?: boolean
}

export interface CustomSection {
  id: string
  title: string
  icon?: string
  items: CustomSectionItem[]
  content?: string
  visible?: boolean
}

const props = defineProps<{
  resumeContent: any
  activeSection: string
  loadingSection?: string | null
}>()

const emit = defineEmits<{
  'update:resumeContent': [content: any]
  'change': [sectionName: string, sectionData: any]
  'regenerate': [sectionName: string]
  'add-section': [section: CustomSection]
  'remove-section': [sectionId: string]
}>()

// 本地草稿镜像
const localResume = ref<any>({})
let isInternalChange = false

// 专业技能自由编辑模式: 'text' (推荐，与 Magic-Resume 对齐) | 'tags' (分类标签卡片)
const skillMode = ref<'text' | 'tags'>('text')
const skillText = ref('')

function syncSkillTextFromResume() {
  const content = localResume.value.skillContent
  const raw = localResume.value.skills
  if (typeof content === 'string' && content.trim()) {
    skillText.value = content
    return
  }
  if (typeof raw === 'string' && raw.trim()) {
    skillText.value = raw
    return
  }
  if (Array.isArray(raw) && raw.length > 0) {
    if (raw.every((item: any) => typeof item === 'string')) {
      skillText.value = raw.join('\n')
    } else {
      skillText.value = raw
        .map((g: any) => {
          if (g && typeof g === 'object') {
            if (Array.isArray(g.keywords) && g.keywords.length > 0) {
              return `${g.name ? g.name + '：' : ''}${g.keywords.join('、')}`
            }
            return g.name || ''
          }
          return String(g || '')
        })
        .filter(Boolean)
        .join('\n')
    }
  } else {
    skillText.value = ''
  }
}

function initLocal(val: any) {
  if (!val) return
  localResume.value = JSON.parse(JSON.stringify(val))
  if (!localResume.value.basics) localResume.value.basics = {}
  if (!localResume.value.basics.custom_fields) localResume.value.basics.custom_fields = []
  if (!Array.isArray(localResume.value.education)) localResume.value.education = []
  if (!Array.isArray(localResume.value.skills) && typeof localResume.value.skills !== 'string') {
    localResume.value.skills = []
  }
  if (!Array.isArray(localResume.value.projects)) localResume.value.projects = []
  if (!Array.isArray(localResume.value.experience)) localResume.value.experience = []
  if (!Array.isArray(localResume.value.highlights)) localResume.value.highlights = []
  if (!Array.isArray(localResume.value.custom_sections)) localResume.value.custom_sections = []

  syncSkillTextFromResume()
}

watch(
  () => props.resumeContent,
  (val) => {
    if (isInternalChange) {
      isInternalChange = false
      return
    }
    initLocal(val)
  },
  { immediate: true, deep: true }
)

// 手风琴折叠状态集合 (默认展开第一项)
const expandedItems = ref<Record<string, boolean>>({
  'projects-0': true,
  'experience-0': true,
  'education-0': true,
})

function isExpanded(key: string): boolean {
  return expandedItems.value[key] !== false
}

function toggleExpand(key: string) {
  expandedItems.value[key] = !isExpanded(key)
}

function triggerChange(secName: string) {
  isInternalChange = true
  emit('update:resumeContent', localResume.value)
  emit('change', secName, localResume.value[secName])
}

// ---------------- 技能即刻 0ms 联动 ----------------
function handleSkillTextInput(e: Event) {
  const target = e.target as HTMLTextAreaElement
  const val = target.value
  skillText.value = val
  localResume.value.skillContent = val
  // 将文本同步拆分为每行数组供后端与模板解析
  const lines = val.split('\n').map((l) => l.trim()).filter(Boolean)
  localResume.value.skills = lines
  triggerChange('skills')
}

// 技能快捷插入格式
function insertSkillPrefix(prefix: string) {
  if (prefix === 'numbered') {
    const lines = skillText.value.split('\n')
    let num = 1
    const newLines = lines.map((l) => {
      const stripped = l.replace(/^\d+[\.、]\s*/, '').trim()
      if (!stripped) return l
      return `${num++}. ${stripped}`
    })
    skillText.value = newLines.join('\n')
  } else if (prefix === 'bullet') {
    const lines = skillText.value.split('\n')
    const newLines = lines.map((l) => {
      const stripped = l.replace(/^[•\-\*]\s*/, '').trim()
      if (!stripped) return l
      return `• ${stripped}`
    })
    skillText.value = newLines.join('\n')
  } else if (prefix === 'bold') {
    skillText.value += '\n【核心领域】: 深入掌握 ...'
  } else if (prefix === 'demo') {
    skillText.value = [
      '1. 双 Agent 工作流: 熟练设计 LangGraph / Multi-Agent 协作架构，擅长复杂任务规划、上下文剪枝与工具路由；',
      '2. 全栈架构研发: 深入掌握 Python (FastAPI, SQLAlchemy) 与 前端工程化 (Vue 3, TypeScript, Vite, Tailwind)；',
      '3. 检索增强 (RAG): 深入掌握向量检索 (Chroma / FAISS) 与 混合重排 (Re-rank) 算法，具备高质量知识库调优经验；',
      '4. 模型微调与部署: 熟悉 LLaMA-Factory / vLLM 高并发推理优化，具备端到端生产部署落地能力。'
    ].join('\n')
  } else if (prefix === 'clear') {
    skillText.value = ''
  }
  localResume.value.skillContent = skillText.value
  localResume.value.skills = skillText.value.split('\n').map((l) => l.trim()).filter(Boolean)
  triggerChange('skills')
}

// 标签模式相关
const skillInputs = ref<Record<number, string>>({})

function handleAddKeyword(idx: number) {
  const kw = (skillInputs.value[idx] || '').trim()
  if (!kw) return
  if (!Array.isArray(localResume.value.skills)) {
    localResume.value.skills = []
  }
  if (!localResume.value.skills[idx] || typeof localResume.value.skills[idx] !== 'object') {
    localResume.value.skills[idx] = { name: '技能分类', keywords: [] }
  }
  if (!localResume.value.skills[idx].keywords) {
    localResume.value.skills[idx].keywords = []
  }
  localResume.value.skills[idx].keywords.push(kw)
  skillInputs.value[idx] = ''
  syncSkillTextFromResume()
  triggerChange('skills')
}

function removeKeyword(group: any, ki: number) {
  group.keywords.splice(ki, 1)
  syncSkillTextFromResume()
  triggerChange('skills')
}

function addSkillGroup() {
  if (!Array.isArray(localResume.value.skills)) {
    localResume.value.skills = []
  }
  localResume.value.skills.push({ name: '新技能分类', keywords: [] })
  triggerChange('skills')
}

function removeSkillGroup(idx: number) {
  localResume.value.skills.splice(idx, 1)
  syncSkillTextFromResume()
  triggerChange('skills')
}

// ---------------- 个人信息头像上传 ----------------
function handlePhotoUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (event) => {
    if (event.target?.result) {
      localResume.value.basics.photo = event.target.result as string
      triggerChange('basics')
    }
  }
  reader.readAsDataURL(file)
}

// ---------------- 个人信息自定义字段 ----------------
const newFieldLabel = ref('')
const newFieldValue = ref('')
const showAddField = ref(false)

function addCustomField(label?: string) {
  const name = label || newFieldLabel.value.trim()
  if (!name) return
  if (!localResume.value.basics.custom_fields) {
    localResume.value.basics.custom_fields = []
  }
  localResume.value.basics.custom_fields.push({
    label: name,
    value: newFieldValue.value.trim(),
  })
  newFieldLabel.value = ''
  newFieldValue.value = ''
  showAddField.value = false
  triggerChange('basics')
}

function removeCustomField(idx: number) {
  localResume.value.basics.custom_fields.splice(idx, 1)
  triggerChange('basics')
}

// ---------------- 列表项增删 / 排序 / 显隐 ----------------
function addItem(listName: string, defaultObj: any) {
  if (!Array.isArray(localResume.value[listName])) {
    localResume.value[listName] = []
  }
  defaultObj.visible = true
  localResume.value[listName].unshift(defaultObj)
  expandedItems.value[`${listName}-0`] = true
  triggerChange(listName)
}

function removeItem(listName: string, idx: number) {
  localResume.value[listName].splice(idx, 1)
  triggerChange(listName)
}

function moveItem(listName: string, idx: number, dir: -1 | 1) {
  const arr = localResume.value[listName]
  const target = idx + dir
  if (target < 0 || target >= arr.length) return
  ;[arr[idx], arr[target]] = [arr[target], arr[idx]]
  triggerChange(listName)
}

function toggleItemVisible(item: any, listName: string) {
  item.visible = item.visible === false ? true : false
  triggerChange(listName)
}

function setPresent(item: any, fieldName = 'endDate') {
  item[fieldName] = '至今'
  triggerChange(props.activeSection)
}

// ---------------- 亮点项增删 ----------------
function addHighlightToItem(item: any) {
  if (!item.highlights) item.highlights = []
  item.highlights.push('')
  triggerChange(props.activeSection)
}

function removeHighlightFromItem(item: any, hi: number) {
  item.highlights.splice(hi, 1)
  triggerChange(props.activeSection)
}

// ---------------- 自定义模块 ----------------
const currentCustomSection = computed(() => {
  if (!props.activeSection.startsWith('custom_')) return null
  const secId = props.activeSection.replace('custom_', '')
  return localResume.value.custom_sections?.find((s: any) => s.id === secId) || null
})

function addCustomSectionItem(sec: CustomSection) {
  if (!sec.items) sec.items = []
  sec.items.push({
    title: '新条目',
    subtitle: '',
    date: '',
    description: '',
    highlights: [],
    visible: true,
  })
  triggerChange('custom_sections')
}
</script>

<template>
  <div class="space-y-4">

    <!-- ===================== 1. 基本信息 ===================== -->
    <div v-if="activeSection === 'basics'" class="space-y-4">
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <div>
          <h4 class="font-bold text-base text-slate-800 flex items-center gap-2">
            <span>👤</span> 基本资料
          </h4>
          <p class="text-xs text-slate-400 mt-0.5">联系方式、求职意向与个人形象展示</p>
        </div>
        <button
          class="btn-secondary !text-xs !py-1.5 flex items-center gap-1.5 text-primary-600 bg-primary-50/50 hover:bg-primary-100/60 border-primary-200"
          :disabled="loadingSection === 'basics'"
          @click="emit('regenerate', 'basics')"
        >
          <span>✨</span> {{ loadingSection === 'basics' ? 'AI 润色中…' : 'AI 优化抬头' }}
        </button>
      </div>

      <!-- 头像照片快捷上传与 URL -->
      <div class="p-3 bg-slate-50 border border-slate-200/80 rounded-xl flex items-center gap-4">
        <div class="w-16 h-20 bg-white border border-slate-300 rounded overflow-hidden shadow-2xs flex items-center justify-center shrink-0">
          <img
            v-if="localResume.basics?.photo"
            :src="localResume.basics.photo"
            alt="头像"
            class="w-full h-full object-cover"
          />
          <span v-else class="text-2xl text-slate-300">👤</span>
        </div>
        <div class="flex-1 space-y-1.5">
          <div class="flex items-center gap-2">
            <label class="btn-secondary !text-xs !py-1 cursor-pointer">
              📷 本地上传免冠照
              <input type="file" accept="image/*" class="hidden" @change="handlePhotoUpload" />
            </label>
            <button
              v-if="localResume.basics?.photo"
              class="text-xs text-slate-400 hover:text-red-500"
              @click="localResume.basics.photo = ''; triggerChange('basics')"
            >
              清除照片
            </button>
          </div>
          <input
            v-model="localResume.basics.photo"
            @input="triggerChange('basics')"
            class="input !text-xs"
            placeholder="或粘贴网络图片 URL / Base64 地址"
          />
        </div>
      </div>

      <!-- 核心常规字段 -->
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label !text-xs font-semibold text-slate-700">姓名 <span class="text-red-500">*</span></label>
          <input v-model="localResume.basics.name" @input="triggerChange('basics')" class="input !text-sm font-medium" placeholder="如：刘先生" />
        </div>
        <div>
          <label class="label !text-xs font-semibold text-slate-700">求职意向 / 职位头衔</label>
          <input v-model="localResume.basics.label" @input="triggerChange('basics')" class="input !text-sm font-medium" placeholder="如：AI 算法工程师 / 全栈架构师" />
        </div>
        <div>
          <label class="label !text-xs text-slate-600">电子邮箱</label>
          <input v-model="localResume.basics.email" @input="triggerChange('basics')" class="input !text-sm font-mono" placeholder="user@example.com" />
        </div>
        <div>
          <label class="label !text-xs text-slate-600">联系电话</label>
          <input v-model="localResume.basics.phone" @input="triggerChange('basics')" class="input !text-sm font-mono" placeholder="如：13800000000" />
        </div>
        <div>
          <label class="label !text-xs text-slate-600">出生年月</label>
          <input v-model="localResume.basics.birthDate" @input="triggerChange('basics')" class="input !text-sm font-mono" placeholder="如：2001/05" />
        </div>
        <div>
          <label class="label !text-xs text-slate-600">所在城市 / 地点</label>
          <input v-model="localResume.basics.location" @input="triggerChange('basics')" class="input !text-sm" placeholder="如：北京 / 上海 / 深圳" />
        </div>
        <div>
          <label class="label !text-xs text-slate-600">GitHub 主页</label>
          <input v-model="localResume.basics.github" @input="triggerChange('basics')" class="input !text-sm font-mono" placeholder="https://github.com/..." />
        </div>
        <div>
          <label class="label !text-xs text-slate-600">个人博客 / 作品集</label>
          <input v-model="localResume.basics.blog" @input="triggerChange('basics')" class="input !text-sm font-mono" placeholder="https://blog.example.com" />
        </div>
        <div class="col-span-2">
          <label class="label !text-xs text-slate-600">一句话技术优势 / 自我总结</label>
          <textarea
            v-model="localResume.basics.summary"
            @input="triggerChange('basics')"
            rows="2"
            class="input !text-xs leading-relaxed"
            placeholder="总结您的核心技术特长与个人综合优势，将直接呈现于简历抬头…"
          />
        </div>
      </div>

      <!-- 自定义扩展字段 -->
      <div class="pt-3 border-t border-slate-100 space-y-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-xs font-semibold text-slate-700">自定义信息项</span>
            <span class="text-[11px] text-slate-400">(快捷添加：微信、期望薪资、政治面貌等)</span>
          </div>
          <button v-if="!showAddField" class="text-xs text-primary-600 hover:underline font-medium" @click="showAddField = true">
            ＋ 新增字段
          </button>
        </div>

        <!-- 常用快捷预设 -->
        <div class="flex items-center gap-1.5 flex-wrap">
          <span class="text-[11px] text-slate-400">快捷建议:</span>
          <button
            v-for="kw in ['微信号', '期望薪资', '期望城市', '政治面貌', '工作经验年限']"
            :key="kw"
            class="text-[10px] px-2 py-0.5 rounded-full border border-slate-200 bg-slate-50 text-slate-600 hover:border-primary-300 hover:text-primary-600 transition"
            @click="addCustomField(kw)"
          >
            + {{ kw }}
          </button>
        </div>

        <div v-if="localResume.basics.custom_fields?.length" class="grid grid-cols-2 gap-2 mt-2">
          <div
            v-for="(cf, cfi) in localResume.basics.custom_fields"
            :key="cfi"
            class="flex items-center gap-2 p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
          >
            <span class="font-medium text-slate-600 shrink-0">{{ cf.label }}:</span>
            <input
              v-model="cf.value"
              @input="triggerChange('basics')"
              class="flex-1 bg-transparent border-b border-transparent focus:border-primary-500 focus:outline-none text-slate-800"
              placeholder="填入内容"
            />
            <button class="text-slate-400 hover:text-red-500 px-1" @click="removeCustomField(cfi)">✕</button>
          </div>
        </div>

        <!-- 手动增加字段表单 -->
        <div v-if="showAddField" class="p-3 bg-primary-50/40 border border-primary-200 rounded-lg flex items-center gap-2 text-xs">
          <input v-model="newFieldLabel" placeholder="字段名(如: 微信)" class="input !text-xs !w-36" />
          <input v-model="newFieldValue" placeholder="字段内容" class="input !text-xs flex-1" @keydown.enter="addCustomField()" />
          <button class="btn-primary !text-xs !py-1.5" @click="addCustomField()">确定</button>
          <button class="btn-secondary !text-xs !py-1.5" @click="showAddField = false">取消</button>
        </div>
      </div>
    </div>


    <!-- ===================== 2. 专业技能 (0ms 即刻打字同步 + Magic-Resume 模式) ===================== -->
    <div v-else-if="activeSection === 'skills'" class="space-y-4">
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <div>
          <h4 class="font-bold text-base text-slate-800 flex items-center gap-2">
            <span>⚡</span> 专业技能
          </h4>
          <p class="text-xs text-slate-400 mt-0.5">即刻打字实时渲染在右侧 A4 纸质区域，支持 1. 2. 3. 编号加粗</p>
        </div>
        <div class="flex items-center gap-2">
          <!-- 模式切换 -->
          <div class="flex p-0.5 bg-slate-100 rounded-lg text-xs">
            <button
              class="px-2.5 py-1 rounded-md transition font-medium"
              :class="skillMode === 'text' ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
              @click="skillMode = 'text'"
            >
              📝 自由多行文本 (推荐)
            </button>
            <button
              class="px-2.5 py-1 rounded-md transition font-medium"
              :class="skillMode === 'tags' ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
              @click="skillMode = 'tags'"
            >
              🏷️ 分类标签卡片
            </button>
          </div>

          <button
            class="btn-secondary !text-xs !py-1.5 flex items-center gap-1 text-primary-600 border-primary-200 bg-primary-50/50"
            :disabled="loadingSection === 'skills'"
            @click="emit('regenerate', 'skills')"
          >
            <span>✨</span> {{ loadingSection === 'skills' ? '对齐中…' : 'AI 针对 JD 优化技能' }}
          </button>
        </div>
      </div>

      <!-- 模式 1: 自由多行文本编辑器 (Magic-Resume 核心标准，0ms 响应) -->
      <div v-if="skillMode === 'text'" class="space-y-2.5">
        <!-- 快速格式化工具栏 -->
        <div class="flex items-center justify-between p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs">
          <div class="flex items-center gap-1.5 flex-wrap">
            <span class="text-slate-400 text-[11px] mr-1">快捷排版:</span>
            <button
              class="px-2 py-0.5 bg-white border border-slate-200 rounded hover:border-primary-400 hover:text-primary-700 transition"
              @click="insertSkillPrefix('numbered')"
            >
              🔢 序号列表 (1. 2.)
            </button>
            <button
              class="px-2 py-0.5 bg-white border border-slate-200 rounded hover:border-primary-400 hover:text-primary-700 transition"
              @click="insertSkillPrefix('bullet')"
            >
              • 圆点列表
            </button>
            <button
              class="px-2 py-0.5 bg-white border border-slate-200 rounded hover:border-primary-400 hover:text-primary-700 transition"
              @click="insertSkillPrefix('bold')"
            >
              【加粗前缀】
            </button>
            <button
              class="px-2 py-0.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded hover:bg-emerald-100 transition"
              @click="insertSkillPrefix('demo')"
            >
              💡 载入高质范例
            </button>
          </div>
          <button class="text-slate-400 hover:text-red-500 text-[11px]" @click="insertSkillPrefix('clear')">
            清空内容
          </button>
        </div>

        <!-- 文本输入核心区域：每一次打字立刻触发 0ms 实时预览 -->
        <div class="relative">
          <textarea
            :value="skillText"
            @input="handleSkillTextInput"
            rows="8"
            class="input font-mono text-xs leading-relaxed p-3.5 w-full bg-white border border-slate-300 focus:border-primary-500 rounded-xl shadow-inner transition"
            placeholder="在此输入您的专业技能（支持每行一条，以 1. 2. 3. 开头或【领域】: 冒号前会自动加粗渲染）..."
          />
        </div>
        <p class="text-[11px] text-slate-400">
          💡 提示：在右侧纸张中，类似 <span class="font-mono text-slate-600 font-bold">1. 核心技术:</span> 的冒号前半句会自动加粗呈现，完美匹配高保真简历排版规范。
        </p>
      </div>

      <!-- 模式 2: 分类标签卡片模式 -->
      <div v-else class="space-y-3">
        <div class="flex justify-end">
          <button class="btn-primary !text-xs !py-1" @click="addSkillGroup">＋ 新增分类</button>
        </div>

        <div
          v-for="(item, idx) in localResume.skills"
          :key="idx"
          class="p-3.5 border border-slate-200 rounded-xl bg-white space-y-2.5 shadow-2xs hover:border-slate-300 transition"
        >
          <div class="flex items-center justify-between">
            <input
              v-model="item.name"
              @input="syncSkillTextFromResume(); triggerChange('skills')"
              class="font-bold text-xs bg-transparent text-slate-800 border-b border-transparent hover:border-slate-300 focus:border-primary-500 focus:outline-none px-1"
              placeholder="分类名称（如：AI 算法、架构设计）"
            />
            <button class="text-xs text-slate-400 hover:text-red-500" @click="removeSkillGroup(idx)">删除分类</button>
          </div>

          <!-- 标签展示与行内输入框 -->
          <div class="flex flex-wrap items-center gap-1.5">
            <span
              v-for="(kw, ki) in item.keywords"
              :key="ki"
              class="px-2.5 py-1 bg-primary-50/60 border border-primary-200/80 rounded-md text-xs text-primary-800 flex items-center gap-1 font-medium"
            >
              {{ kw }}
              <span class="cursor-pointer text-primary-400 hover:text-red-500 text-[10px]" @click="removeKeyword(item, ki)">✕</span>
            </span>
            <input
              v-model="skillInputs[idx]"
              @keydown.enter.prevent="handleAddKeyword(idx)"
              @blur="handleAddKeyword(idx)"
              placeholder="+ 输入技能回车"
              class="text-xs px-2.5 py-1 bg-slate-50 border border-dashed border-slate-300 rounded-md w-28 focus:bg-white focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition"
            />
          </div>
        </div>
      </div>
    </div>


    <!-- ===================== 3. 工作/实习经历 (Magic-Resume 手风琴卡片) ===================== -->
    <div v-else-if="activeSection === 'experience'" class="space-y-4">
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <div>
          <h4 class="font-bold text-base text-slate-800 flex items-center gap-2">
            <span>💼</span> 工作与实习经历
          </h4>
          <p class="text-xs text-slate-400 mt-0.5">任职企业、职责角色与业务产出</p>
        </div>
        <div class="flex gap-2">
          <button
            class="btn-secondary !text-xs !py-1.5 flex items-center gap-1 text-primary-600 bg-primary-50/50 border-primary-200"
            :disabled="loadingSection === 'experience'"
            @click="emit('regenerate', 'experience')"
          >
            <span>✨</span> {{ loadingSection === 'experience' ? '优化中…' : 'AI 润色经历' }}
          </button>
          <button
            class="btn-primary !text-xs !py-1.5 flex items-center gap-1"
            @click="addItem('experience', { company: '新公司/机构名称', role: '岗位头衔', startDate: '2024/01', endDate: '至今', description: '', highlights: ['负责核心模块研发，实现业务增长与性能优化'] })"
          >
            ＋ 添加工作经历
          </button>
        </div>
      </div>

      <div class="space-y-3">
        <div
          v-for="(item, idx) in localResume.experience"
          :key="idx"
          class="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-2xs hover:border-slate-300 transition"
          :class="item.visible === false ? 'opacity-60 bg-slate-50/50' : ''"
        >
          <!-- 卡片头部 (折叠/显隐/排序/删除) -->
          <div
            class="px-4 py-3 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between cursor-pointer select-none"
            @click="toggleExpand(`experience-${idx}`)"
          >
            <div class="flex items-center gap-2.5 min-w-0">
              <span class="text-slate-400 text-xs font-mono select-none">⋮⋮</span>
              <span class="font-bold text-xs text-slate-900 truncate">{{ item.company || '未填写公司' }}</span>
              <span v-if="item.role || item.position" class="text-xs text-slate-500 font-medium truncate">· {{ item.role || item.position }}</span>
              <span v-if="item.startDate || item.endDate" class="text-[11px] text-slate-400 font-mono hidden sm:inline">
                ({{ item.startDate || '' }} - {{ item.endDate || '' }})
              </span>
            </div>

            <div class="flex items-center gap-1.5 shrink-0" @click.stop>
              <!-- 显隐开关 (Eye) -->
              <button
                class="p-1 rounded text-slate-400 hover:text-primary-600 transition"
                :title="item.visible === false ? '当前在纸张中已隐藏，点击显示' : '点击在纸张中隐藏此项'"
                @click="toggleItemVisible(item, 'experience')"
              >
                <span v-if="item.visible === false" class="text-xs">👁️‍🗨️</span>
                <span v-else class="text-xs">👁️</span>
              </button>

              <!-- 上下调整顺序 -->
              <button
                class="p-1 rounded text-slate-400 hover:text-slate-700 text-xs disabled:opacity-30"
                :disabled="idx === 0"
                @click="moveItem('experience', idx, -1)"
                title="上移"
              >
                ↑
              </button>
              <button
                class="p-1 rounded text-slate-400 hover:text-slate-700 text-xs disabled:opacity-30"
                :disabled="idx === localResume.experience.length - 1"
                @click="moveItem('experience', idx, 1)"
                title="下移"
              >
                ↓
              </button>

              <!-- 删除按钮 -->
              <button
                class="p-1 rounded text-slate-400 hover:text-red-500 text-xs ml-1"
                @click="removeItem('experience', idx)"
                title="删除本条"
              >
                🗑️
              </button>

              <!-- 手风琴展开指示 -->
              <span class="text-slate-400 text-xs ml-1.5 transition-transform duration-200">
                {{ isExpanded(`experience-${idx}`) ? '▲' : '▼' }}
              </span>
            </div>
          </div>

          <!-- 展开后的完整表单 -->
          <div v-show="isExpanded(`experience-${idx}`)" class="p-4 space-y-3.5">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="label !text-xs font-semibold text-slate-700">公司 / 机构名称</label>
                <input v-model="item.company" @input="triggerChange('experience')" class="input !text-xs font-medium" placeholder="如：阿里巴巴 / 字节跳动" />
              </div>
              <div>
                <label class="label !text-xs font-semibold text-slate-700">担任职位 / 角色</label>
                <input v-model="item.role" @input="triggerChange('experience')" class="input !text-xs font-medium" placeholder="如：高级全栈开发工程师" />
              </div>
              <div>
                <label class="label !text-xs text-slate-600">起始时间</label>
                <input v-model="item.startDate" @input="triggerChange('experience')" class="input !text-xs font-mono" placeholder="如：2023/06" />
              </div>
              <div>
                <div class="flex items-center justify-between mb-1">
                  <label class="label !text-xs !mb-0 text-slate-600">截止时间</label>
                  <button class="text-[10px] text-primary-600 hover:underline" @click="setPresent(item, 'endDate')">
                    设为至今
                  </button>
                </div>
                <input v-model="item.endDate" @input="triggerChange('experience')" class="input !text-xs font-mono" placeholder="如：至今 或 2025/12" />
              </div>
              <div class="col-span-2">
                <label class="label !text-xs text-slate-600">职责概括描述 (可选)</label>
                <input v-model="item.description" @input="triggerChange('experience')" class="input !text-xs" placeholder="一句话概括负责业务板块与团队定位…" />
              </div>
            </div>

            <!-- 经历成果要点 (亮点列表) -->
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <label class="label !text-xs !mb-0 font-semibold text-slate-700">核心成果亮点 (按 STAR 法则呈现)</label>
                <button class="text-[11px] text-primary-600 hover:underline font-medium" @click="addHighlightToItem(item)">
                  ＋ 增加亮点要点
                </button>
              </div>
              <div class="space-y-1.5">
                <div v-for="(hl, hi) in item.highlights" :key="hi" class="flex items-center gap-2">
                  <span class="text-slate-300 text-xs shrink-0">•</span>
                  <input
                    v-model="item.highlights[hi]"
                    @input="triggerChange('experience')"
                    class="input !text-xs flex-1 leading-relaxed"
                    placeholder="动词 + 业务情境 + 技术方案 + 量化产出数据（如：主导架构重构，使接口 QPS 提升 120%）…"
                  />
                  <button class="text-slate-300 hover:text-red-500 text-xs px-1" @click="removeHighlightFromItem(item, hi)">✕</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>


    <!-- ===================== 4. 项目经验 (Magic-Resume 手风琴卡片) ===================== -->
    <div v-else-if="activeSection === 'projects'" class="space-y-4">
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <div>
          <h4 class="font-bold text-base text-slate-800 flex items-center gap-2">
            <span>🚀</span> 重点项目经历
          </h4>
          <p class="text-xs text-slate-400 mt-0.5">支持关联项目网址/GitHub、担任角色与关键技术成果</p>
        </div>
        <div class="flex gap-2">
          <button
            class="btn-secondary !text-xs !py-1.5 flex items-center gap-1 text-primary-600 bg-primary-50/50 border-primary-200"
            :disabled="loadingSection === 'projects'"
            @click="emit('regenerate', 'projects')"
          >
            <span>✨</span> {{ loadingSection === 'projects' ? '润色中…' : 'AI 优化项目' }}
          </button>
          <button
            class="btn-primary !text-xs !py-1.5 flex items-center gap-1"
            @click="addItem('projects', { name: '新项目名称', role: '个人主导 / 核心开发', startDate: '2024/03', endDate: '至今', link: '', description: '基于现代全栈技术栈开发的高性能应用系统', highlights: ['设计核心架构并落地自动化流水线，系统稳定性达 99.9%'] })"
          >
            ＋ 添加项目
          </button>
        </div>
      </div>

      <div class="space-y-3">
        <div
          v-for="(item, idx) in localResume.projects"
          :key="idx"
          class="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-2xs hover:border-slate-300 transition"
          :class="item.visible === false ? 'opacity-60 bg-slate-50/50' : ''"
        >
          <!-- 卡片头部 (折叠/显隐/排序/删除) -->
          <div
            class="px-4 py-3 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between cursor-pointer select-none"
            @click="toggleExpand(`projects-${idx}`)"
          >
            <div class="flex items-center gap-2.5 min-w-0">
              <span class="text-slate-400 text-xs font-mono select-none">⋮⋮</span>
              <span class="font-bold text-xs text-slate-900 truncate">{{ item.name || '未命名项目' }}</span>
              <span v-if="item.role" class="text-xs text-slate-500 font-medium truncate">· {{ item.role }}</span>
              <span v-if="item.startDate || item.endDate" class="text-[11px] text-slate-400 font-mono hidden sm:inline">
                ({{ item.startDate || '' }} - {{ item.endDate || '' }})
              </span>
            </div>

            <div class="flex items-center gap-1.5 shrink-0" @click.stop>
              <!-- 显隐开关 -->
              <button
                class="p-1 rounded text-slate-400 hover:text-primary-600 transition"
                :title="item.visible === false ? '当前在纸张中已隐藏，点击显示' : '点击在纸张中隐藏此项'"
                @click="toggleItemVisible(item, 'projects')"
              >
                <span v-if="item.visible === false" class="text-xs">👁️‍🗨️</span>
                <span v-else class="text-xs">👁️</span>
              </button>

              <!-- 上下排序 -->
              <button
                class="p-1 rounded text-slate-400 hover:text-slate-700 text-xs disabled:opacity-30"
                :disabled="idx === 0"
                @click="moveItem('projects', idx, -1)"
                title="上移"
              >
                ↑
              </button>
              <button
                class="p-1 rounded text-slate-400 hover:text-slate-700 text-xs disabled:opacity-30"
                :disabled="idx === localResume.projects.length - 1"
                @click="moveItem('projects', idx, 1)"
                title="下移"
              >
                ↓
              </button>

              <!-- 删除 -->
              <button
                class="p-1 rounded text-slate-400 hover:text-red-500 text-xs ml-1"
                @click="removeItem('projects', idx)"
                title="删除本条"
              >
                🗑️
              </button>

              <span class="text-slate-400 text-xs ml-1.5 transition-transform duration-200">
                {{ isExpanded(`projects-${idx}`) ? '▲' : '▼' }}
              </span>
            </div>
          </div>

          <!-- 展开表单 -->
          <div v-show="isExpanded(`projects-${idx}`)" class="p-4 space-y-3.5">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="label !text-xs font-semibold text-slate-700">项目名称</label>
                <input v-model="item.name" @input="triggerChange('projects')" class="input !text-xs font-medium" placeholder="如：企业级多模态 Agent 工作台" />
              </div>
              <div>
                <label class="label !text-xs font-semibold text-slate-700">担任角色 / 职责</label>
                <input v-model="item.role" @input="triggerChange('projects')" class="input !text-xs font-medium" placeholder="如：核心开发者 / 独立全栈" />
              </div>
              <div>
                <label class="label !text-xs text-slate-600">起始时间</label>
                <input v-model="item.startDate" @input="triggerChange('projects')" class="input !text-xs font-mono" placeholder="如：2024/01" />
              </div>
              <div>
                <div class="flex items-center justify-between mb-1">
                  <label class="label !text-xs !mb-0 text-slate-600">截止时间</label>
                  <button class="text-[10px] text-primary-600 hover:underline" @click="setPresent(item, 'endDate')">设为至今</button>
                </div>
                <input v-model="item.endDate" @input="triggerChange('projects')" class="input !text-xs font-mono" placeholder="如：至今 或 2024/08" />
              </div>
              <div class="col-span-2">
                <label class="label !text-xs text-slate-600">项目链接 / 演示网址 (可选，支持带链接跳转)</label>
                <input v-model="item.link" @input="triggerChange('projects')" class="input !text-xs font-mono" placeholder="如：https://github.com/JOYCEQL/magic-resume" />
              </div>
              <div class="col-span-2">
                <label class="label !text-xs text-slate-600">项目简介与主要技术栈</label>
                <input v-model="item.description" @input="triggerChange('projects')" class="input !text-xs" placeholder="如：基于 Vue 3 + FastAPI 研发的高拟真 AI 简历排版引擎" />
              </div>
            </div>

            <!-- 项目技术亮点 -->
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <label class="label !text-xs !mb-0 font-semibold text-slate-700">核心亮点与难点突破 (亮点列表)</label>
                <button class="text-[11px] text-primary-600 hover:underline font-medium" @click="addHighlightToItem(item)">
                  ＋ 增加亮点要点
                </button>
              </div>
              <div class="space-y-1.5">
                <div v-for="(hl, hi) in item.highlights" :key="hi" class="flex items-center gap-2">
                  <span class="text-slate-300 text-xs shrink-0">•</span>
                  <input
                    v-model="item.highlights[hi]"
                    @input="triggerChange('projects')"
                    class="input !text-xs flex-1 leading-relaxed"
                    placeholder="按 STAR 法则描述动作、技术难点及最终收益成果…"
                  />
                  <button class="text-slate-300 hover:text-red-500 text-xs px-1" @click="removeHighlightFromItem(item, hi)">✕</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>


    <!-- ===================== 5. 教育背景 (Magic-Resume 手风琴卡片) ===================== -->
    <div v-else-if="activeSection === 'education'" class="space-y-4">
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <div>
          <h4 class="font-bold text-base text-slate-800 flex items-center gap-2">
            <span>🎓</span> 教育经历
          </h4>
          <p class="text-xs text-slate-400 mt-0.5">毕业院校、专业层次与主修成就</p>
        </div>
        <button
          class="btn-primary !text-xs !py-1.5 flex items-center gap-1"
          @click="addItem('education', { institution: '院校名称', area: '软件工程 / 计算机', studyType: '本科', gpa: '3.8/4.0', startDate: '2020/09', endDate: '2024/06', highlights: ['获得国家奖学金，专业排名前 5%'] })"
        >
          ＋ 添加教育经历
        </button>
      </div>

      <div class="space-y-3">
        <div
          v-for="(item, idx) in localResume.education"
          :key="idx"
          class="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-2xs hover:border-slate-300 transition"
          :class="item.visible === false ? 'opacity-60 bg-slate-50/50' : ''"
        >
          <!-- 头部条 -->
          <div
            class="px-4 py-3 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between cursor-pointer select-none"
            @click="toggleExpand(`education-${idx}`)"
          >
            <div class="flex items-center gap-2.5 min-w-0">
              <span class="text-slate-400 text-xs font-mono select-none">⋮⋮</span>
              <span class="font-bold text-xs text-slate-900 truncate">{{ item.institution || item.school || '未填写院校' }}</span>
              <span v-if="item.area || item.major" class="text-xs text-slate-500 font-medium truncate">· {{ item.area || item.major }}</span>
              <span v-if="item.studyType || item.degree" class="text-xs text-slate-400">({{ item.studyType || item.degree }})</span>
            </div>

            <div class="flex items-center gap-1.5 shrink-0" @click.stop>
              <!-- 显隐开关 -->
              <button
                class="p-1 rounded text-slate-400 hover:text-primary-600 transition"
                :title="item.visible === false ? '当前在纸张中已隐藏，点击显示' : '点击在纸张中隐藏此项'"
                @click="toggleItemVisible(item, 'education')"
              >
                <span v-if="item.visible === false" class="text-xs">👁️‍🗨️</span>
                <span v-else class="text-xs">👁️</span>
              </button>

              <button
                class="p-1 rounded text-slate-400 hover:text-slate-700 text-xs disabled:opacity-30"
                :disabled="idx === 0"
                @click="moveItem('education', idx, -1)"
                title="上移"
              >
                ↑
              </button>
              <button
                class="p-1 rounded text-slate-400 hover:text-slate-700 text-xs disabled:opacity-30"
                :disabled="idx === localResume.education.length - 1"
                @click="moveItem('education', idx, 1)"
                title="下移"
              >
                ↓
              </button>
              <button
                class="p-1 rounded text-slate-400 hover:text-red-500 text-xs ml-1"
                @click="removeItem('education', idx)"
                title="删除"
              >
                🗑️
              </button>
              <span class="text-slate-400 text-xs ml-1.5 transition-transform duration-200">
                {{ isExpanded(`education-${idx}`) ? '▲' : '▼' }}
              </span>
            </div>
          </div>

          <!-- 展开表单 -->
          <div v-show="isExpanded(`education-${idx}`)" class="p-4 space-y-3.5">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="label !text-xs font-semibold text-slate-700">学校 / 院校名称</label>
                <input v-model="item.institution" @input="triggerChange('education')" class="input !text-xs font-medium" placeholder="如：北京大学 / 清华大学" />
              </div>
              <div>
                <label class="label !text-xs font-semibold text-slate-700">主修专业</label>
                <input v-model="item.area" @input="triggerChange('education')" class="input !text-xs font-medium" placeholder="如：计算机科学与技术" />
              </div>
              <div>
                <label class="label !text-xs text-slate-600">学历层次</label>
                <select v-model="item.studyType" @change="triggerChange('education')" class="input !text-xs">
                  <option value="本科">本科</option>
                  <option value="硕士研究生">硕士研究生</option>
                  <option value="博士研究生">博士研究生</option>
                  <option value="大专">大专</option>
                  <option value="其他">其他</option>
                </select>
              </div>
              <div>
                <label class="label !text-xs text-slate-600">GPA / 成绩排名 (可选)</label>
                <input v-model="item.gpa" @input="triggerChange('education')" class="input !text-xs font-mono" placeholder="如：3.85 / 前 5%" />
              </div>
              <div>
                <label class="label !text-xs text-slate-600">入学时间</label>
                <input v-model="item.startDate" @input="triggerChange('education')" class="input !text-xs font-mono" placeholder="如：2020/09" />
              </div>
              <div>
                <div class="flex items-center justify-between mb-1">
                  <label class="label !text-xs !mb-0 text-slate-600">毕业时间</label>
                  <button class="text-[10px] text-primary-600 hover:underline" @click="setPresent(item, 'endDate')">设为至今</button>
                </div>
                <input v-model="item.endDate" @input="triggerChange('education')" class="input !text-xs font-mono" placeholder="如：2024/06 或 至今" />
              </div>
            </div>

            <!-- 主修课程与学业荣誉 -->
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <label class="label !text-xs !mb-0 font-semibold text-slate-700">主修课程与学业荣誉 (如奖学金、竞赛等)</label>
                <button class="text-[11px] text-primary-600 hover:underline font-medium" @click="addHighlightToItem(item)">
                  ＋ 增加荣誉要点
                </button>
              </div>
              <div class="space-y-1.5">
                <div v-for="(hl, hi) in item.highlights" :key="hi" class="flex items-center gap-2">
                  <span class="text-slate-300 text-xs shrink-0">•</span>
                  <input
                    v-model="item.highlights[hi]"
                    @input="triggerChange('education')"
                    class="input !text-xs flex-1"
                    placeholder="主修核心课程、国家奖学金、数学建模国奖等…"
                  />
                  <button class="text-slate-300 hover:text-red-500 text-xs px-1" @click="removeHighlightFromItem(item, hi)">✕</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>


    <!-- ===================== 6. 个人亮点 ===================== -->
    <div v-else-if="activeSection === 'highlights'" class="space-y-4">
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <div>
          <h4 class="font-bold text-base text-slate-800 flex items-center gap-2">
            <span>🌟</span> 个人技术亮点
          </h4>
          <p class="text-xs text-slate-400 mt-0.5">针对目标岗位重点要求的专项技术积累</p>
        </div>
        <button class="btn-primary !text-xs !py-1.5" @click="addItem('highlights', { title: '亮点标题', category: '技术', content: '针对关键瓶颈设计创新架构方案…' })">
          ＋ 添加亮点
        </button>
      </div>

      <div class="space-y-3">
        <div
          v-for="(item, idx) in localResume.highlights"
          :key="idx"
          class="border border-slate-200 rounded-xl p-4 bg-white space-y-2.5 shadow-2xs"
        >
          <div class="flex items-center justify-between">
            <input v-model="item.title" @input="triggerChange('highlights')" class="font-bold text-xs input !w-56" placeholder="亮点标题" />
            <div class="flex items-center gap-2">
              <select v-model="item.category" @change="triggerChange('highlights')" class="input !text-xs !w-24">
                <option value="技术">技术</option>
                <option value="架构">架构</option>
                <option value="管理">管理</option>
                <option value="荣誉">荣誉</option>
              </select>
              <button class="text-slate-400 hover:text-red-500 text-xs px-1" @click="removeItem('highlights', idx)">✕</button>
            </div>
          </div>
          <textarea v-model="item.content" @input="triggerChange('highlights')" rows="2" class="input !text-xs leading-relaxed" placeholder="亮点详述…" />
        </div>
      </div>
    </div>


    <!-- ===================== 7. 自定义板块 (Magic-Resume CustomPanel) ===================== -->
    <div v-else-if="currentCustomSection" class="space-y-4">
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <div class="flex items-center gap-2">
          <span class="text-xl">{{ currentCustomSection.icon || '📌' }}</span>
          <input
            v-model="currentCustomSection.title"
            @input="triggerChange('custom_sections')"
            class="text-base font-bold text-slate-800 bg-transparent border-b border-dashed border-slate-300 focus:border-primary-500 focus:outline-none px-1"
            placeholder="板块名称（点击直接改名）"
          />
        </div>
        <div class="flex gap-2">
          <button class="btn-primary !text-xs !py-1.5" @click="addCustomSectionItem(currentCustomSection)">
            ＋ 添加条目
          </button>
          <button class="btn-secondary !text-xs !py-1.5 text-red-500 hover:bg-red-50" @click="emit('remove-section', currentCustomSection.id)">
            删除此板块
          </button>
        </div>
      </div>

      <div class="space-y-3">
        <div
          v-for="(item, idx) in currentCustomSection.items"
          :key="idx"
          class="border border-slate-200 rounded-xl p-4 bg-white space-y-2.5 shadow-2xs"
        >
          <div class="flex items-center justify-between">
            <input
              v-model="item.title"
              @input="triggerChange('custom_sections')"
              class="input !text-xs font-bold flex-1 mr-2"
              placeholder="条目标题（如开源库名/专业资质）"
            />
            <button class="text-slate-400 hover:text-red-500 text-xs" @click="currentCustomSection.items.splice(idx, 1); triggerChange('custom_sections')">✕</button>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <input v-model="item.subtitle" @input="triggerChange('custom_sections')" class="input !text-xs" placeholder="副标题 / 机构" />
            <input v-model="item.date" @input="triggerChange('custom_sections')" class="input !text-xs font-mono" placeholder="时间（如 2024/05）" />
          </div>
          <textarea v-model="item.description" @input="triggerChange('custom_sections')" rows="2" class="input !text-xs leading-relaxed" placeholder="详述或主要贡献点…" />
        </div>
      </div>
    </div>

  </div>
</template>

