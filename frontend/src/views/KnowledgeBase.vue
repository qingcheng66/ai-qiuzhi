<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiKb } from '@/api'
import MdEditor from '@/components/MdEditor.vue'

const tab = ref('v2_chunks')
const loading = ref(false)
const error = ref('')

interface Chunk {
  id: number
  category_id: number
  title: string
  content: string
  tags: string[]
  enabled: boolean
  sort_order: number
}

interface Category {
  id: number
  name: string
  icon: string
  color: string
  sort_order: number
  chunks: Chunk[]
}

interface Bundle {
  profile: any | null
  projects: any[]
  skills: any[]
  highlights: any[]
  experiences: any[]
  categories: Category[]
}
const bundle = ref<Bundle>({ profile: null, projects: [], skills: [], highlights: [], experiences: [], categories: [] })

// v2 栏目与卡片操作状态
const showNewCategoryModal = ref(false)
const newCategoryName = ref('')
const newCategoryColor = ref('blue')
const selectedCategoryId = ref<number | null>(null)

const selectedCategory = computed(() => {
  if (!bundle.value.categories?.length) return null
  return bundle.value.categories.find(c => c.id === selectedCategoryId.value) || bundle.value.categories[0]
})

const copySuccessMsg = ref('')

async function copyChunkContent(c: Chunk) {
  try {
    const textToCopy = `### ${c.title}\n\n${c.content}`
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(textToCopy)
    }
    copySuccessMsg.value = `已复制「${c.title}」内容到剪贴板！可直接在简历制作微调中粘贴。`
    setTimeout(() => {
      copySuccessMsg.value = ''
    }, 3500)
  } catch (err: any) {
    copySuccessMsg.value = `已选中内容，可直接复制。`
  }
}

const showChunkModal = ref(false)
const editingChunk = ref<{
  id?: number
  category_id?: number
  title: string
  content: string
  tags: string[]
  enabled: boolean
  sort_order?: number
}>({
  title: '',
  content: '',
  tags: [],
  enabled: true,
})
const chunkTagsInput = ref('')

function openCreateChunk(categoryId: number) {
  editingChunk.value = {
    category_id: categoryId,
    title: '',
    content: '',
    tags: [],
    enabled: true,
  }
  chunkTagsInput.value = ''
  showChunkModal.value = true
}

function openEditChunk(c: Chunk) {
  editingChunk.value = { ...c }
  chunkTagsInput.value = (c.tags || []).join(', ')
  showChunkModal.value = true
}

async function saveChunk() {
  if (!editingChunk.value.title?.trim() || !editingChunk.value.category_id) return
  const tags = chunkTagsInput.value.split(/[,，]/).map(t => t.trim()).filter(Boolean)
  const payload = {
    title: editingChunk.value.title,
    content: editingChunk.value.content || '',
    tags,
    enabled: editingChunk.value.enabled ?? true,
    sort_order: editingChunk.value.sort_order ?? 0,
  }
  try {
    if (editingChunk.value.id) {
      await apiKb.chunks.update(editingChunk.value.id, payload)
    } else {
      await apiKb.chunks.create(editingChunk.value.category_id, payload)
    }
    showChunkModal.value = false
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function removeChunk(chunkId: number) {
  if (!confirm('确定删除该段落卡片？')) return
  try {
    await apiKb.chunks.remove(chunkId)
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function toggleChunk(c: Chunk) {
  try {
    c.enabled = !c.enabled
    await apiKb.chunks.toggle(c.id, c.enabled)
  } catch (e: any) {
    c.enabled = !c.enabled
    error.value = e.message
  }
}

async function createCategory() {
  if (!newCategoryName.value.trim()) return
  try {
    await apiKb.categories.create({
      name: newCategoryName.value.trim(),
      color: newCategoryColor.value,
      icon: 'folder',
      sort_order: (bundle.value.categories || []).length,
    })
    newCategoryName.value = ''
    showNewCategoryModal.value = false
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function removeCategory(catId: number) {
  if (!confirm('确定删除该栏目及其所有段落卡片？')) return
  try {
    await apiKb.categories.remove(catId)
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}


const autosaveMsg = ref('')
let saveTimer: any = null
const queue: { fn: () => Promise<void>; label: string }[] = []
let saving = false

function scheduleSave(fn: () => Promise<void>, label: string) {
  queue.push({ fn, label })
  if (saving) return
  saving = true
  const drain = async () => {
    while (queue.length) {
      const job = queue.shift()!
      try {
        await job.fn()
        autosaveMsg.value = `已保存：${job.label}`
      } catch (e: any) {
        error.value = e.message
      }
    }
    saving = false
  }
  drain()
}

async function load() {
  loading.value = true
  try {
    bundle.value = await apiKb.bundle()
    const p = bundle.value.profile
    if (p) {
      profileForm.value = {
        name: p.name || '', label: p.label || '', email: p.email || '', phone: p.phone || '',
        location: p.location || '', birth: p.birth || '', github: p.github || '', blog: p.blog || '', summary: p.summary || '',
      }
      profileEdu.value = (p.education || []).filter((e: any) => e && typeof e === 'object')
        .map((e: any) => ({
          institution: e.institution || '', area: e.area || '', studyType: e.studyType || '',
          startDate: e.startDate || '', endDate: e.endDate || '', gpa: e.gpa || '',
        }))
    }
    if (bundle.value.categories?.length && (!selectedCategoryId.value || !bundle.value.categories.some(c => c.id === selectedCategoryId.value))) {
      selectedCategoryId.value = bundle.value.categories[0].id
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)

// profile
const profileForm = ref({ name: '', label: '', email: '', phone: '', location: '', birth: '', github: '', blog: '', summary: '' })
const profileEdu = ref<any[]>([])

function saveProfile() {
  const edu = profileEdu.value
  scheduleSave(
    () => apiKb.profile.upsert({ ...profileForm.value, education: edu }),
    '个人信息',
  )
}

// generic list item helpers
interface ListItem {
  id?: number
  isNew?: boolean
  enabled?: boolean
}

const projectForm = ref<any>({ name: '', description: '', role: '', url: '', start_date: '', end_date: '', keywords: '', highlights: '' })
const skillForm = ref<any>({ name: '', keywords: '', level: '' })
const highlightForm = ref<any>({ title: '', category: '', content: '', metrics: '' })
const experienceForm = ref<any>({ company: '', role: '', start_date: '', end_date: '', highlights: '', enabled: true })
const editingId = ref<number | null>(null)

function resetProject() {
  projectForm.value = { name: '', description: '', role: '', url: '', start_date: '', end_date: '', keywords: '', highlights: '' }
}
function resetSkill() {
  skillForm.value = { name: '', keywords: '', level: '' }
}
function resetHighlight() {
  highlightForm.value = { title: '', category: '', content: '', metrics: '' }
}
function resetExperience() {
  experienceForm.value = { company: '', role: '', start_date: '', end_date: '', highlights: '', enabled: true }
}

function saveProject() {
  const d = {
    name: projectForm.value.name,
    description: projectForm.value.description,
    role: projectForm.value.role,
    url: projectForm.value.url,
    start_date: projectForm.value.start_date,
    end_date: projectForm.value.end_date,
    keywords: (projectForm.value.keywords as unknown as string).split(',').map((s) => s.trim()).filter(Boolean),
    highlights: (projectForm.value.highlights as unknown as string).split('\n').map((s) => s.trim()).filter(Boolean),
  }
  if (editingId.value) {
    scheduleSave(async () => {
      await apiKb.projects.update(editingId.value!, d)
      await load()
    }, '项目更新')
  } else {
    scheduleSave(async () => {
      await apiKb.projects.create(d)
      await load()
    }, '项目新增')
  }
  resetProject()
  editingId.value = null
}

function editProject(p: any) {
  editingId.value = p.id
  projectForm.value = {
    name: p.name,
    description: p.description,
    role: p.role,
    url: p.url,
    start_date: p.start_date,
    end_date: p.end_date,
    keywords: (p.keywords || []).join(','),
    highlights: (p.highlights || []).join('\n'),
  }
  tab.value = 'projects'
}

function delProject(id: number) {
  scheduleSave(async () => {
    await apiKb.projects.remove(id)
    await load()
  }, '项目删除')
}

function saveSkill() {
  const d = {
    name: skillForm.value.name,
    level: skillForm.value.level,
    keywords: (skillForm.value.keywords as unknown as string).split(',').map((s) => s.trim()).filter(Boolean),
  }
  if (editingId.value) {
    scheduleSave(async () => {
      await apiKb.skills.update(editingId.value!, d)
      await load()
    }, '技能更新')
  } else {
    scheduleSave(async () => {
      await apiKb.skills.create(d)
      await load()
    }, '技能新增')
  }
  resetSkill()
  editingId.value = null
}

function editSkill(s: any) {
  editingId.value = s.id
  skillForm.value = { name: s.name, level: s.level, keywords: (s.keywords || []).join(',') }
  tab.value = 'skills'
}

function delSkill(id: number) {
  scheduleSave(async () => {
    await apiKb.skills.remove(id)
    await load()
  }, '技能删除')
}

function saveHighlight() {
  const d = {
    title: highlightForm.value.title,
    category: highlightForm.value.category,
    content: highlightForm.value.content,
    metrics: highlightForm.value.metrics ? JSON.parse(highlightForm.value.metrics) : {},
  }
  if (editingId.value) {
    scheduleSave(async () => {
      await apiKb.highlights.update(editingId.value!, d)
      await load()
    }, '亮点更新')
  } else {
    scheduleSave(async () => {
      await apiKb.highlights.create(d)
      await load()
    }, '亮点新增')
  }
  resetHighlight()
  editingId.value = null
}

function editHighlight(h: any) {
  editingId.value = h.id
  highlightForm.value = {
    title: h.title,
    category: h.category,
    content: h.content,
    metrics: h.metrics ? JSON.stringify(h.metrics) : '',
  }
  tab.value = 'highlights'
}

function delHighlight(id: number) {
  scheduleSave(async () => {
    await apiKb.highlights.remove(id)
    await load()
  }, '亮点删除')
}

function saveExperience() {
  const d = {
    company: experienceForm.value.company,
    role: experienceForm.value.role,
    start_date: experienceForm.value.start_date,
    end_date: experienceForm.value.end_date,
    enabled: experienceForm.value.enabled,
    highlights: (experienceForm.value.highlights as unknown as string).split('\n').map((s) => s.trim()).filter(Boolean),
  }
  if (editingId.value) {
    scheduleSave(async () => {
      await apiKb.experiences.update(editingId.value!, d)
      await load()
    }, '经历更新')
  } else {
    scheduleSave(async () => {
      await apiKb.experiences.create(d)
      await load()
    }, '经历新增')
  }
  resetExperience()
  editingId.value = null
}

function editExperience(e: any) {
  editingId.value = e.id
  experienceForm.value = {
    company: e.company,
    role: e.role,
    start_date: e.start_date,
    end_date: e.end_date,
    enabled: e.enabled,
    highlights: (e.highlights || []).join('\n'),
  }
  tab.value = 'experiences'
}

function delExperience(id: number) {
  scheduleSave(async () => {
    await apiKb.experiences.remove(id)
    await load()
  }, '经历删除')
}

function startProject() {
  resetProject(); editingId.value = null; tab.value = 'projects'
  setTimeout(() => document.getElementById('new-item')?.scrollIntoView({ behavior: 'smooth' }), 50)
}

// import
const importText = ref('')
const importMsg = ref('')
async function doImport() {
  error.value = ''
  try {
    const r = await apiKb.import(importText.value)
    importMsg.value = '导入完成：' + JSON.stringify(r.counts)
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-2xl font-bold">个人知识库</h2>
        <p class="text-sm text-slate-500">在这里维护你的真实经历，AI 生成简历时会优先使用</p>
      </div>
      <button class="btn-secondary text-xs" @click="load()">刷新</button>
    </div>

    <div v-if="error" class="mb-3 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">{{ error }}</div>
    <div v-if="autosaveMsg" class="mb-3 p-2 rounded-lg bg-green-50 border border-green-200 text-green-700 text-xs">{{ autosaveMsg }}</div>
    <div v-if="copySuccessMsg" class="mb-3 p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2 shadow-2xs">
      <span>✅</span>
      <span>{{ copySuccessMsg }}</span>
    </div>

    <!-- tabs -->
    <div class="flex items-center justify-between border-b border-slate-200 mb-4 overflow-x-auto">
      <div class="flex gap-1">
        <button
          class="px-4 py-2 text-sm font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5"
          :class="tab === 'v2_chunks' ? 'text-primary-600 border-b-2 border-primary-600' : 'text-slate-500 hover:text-slate-700'"
          @click="tab = 'v2_chunks'"
        >
          <span class="w-2 h-2 rounded-full bg-primary-500"></span>
          Markdown 分段知识库 (v2)
          <span class="text-xs bg-primary-50 text-primary-600 px-1.5 py-0.5 rounded-full font-bold ml-1">
            {{ (bundle.categories || []).reduce((acc, c) => acc + (c.chunks || []).length, 0) }} 段
          </span>
        </button>
        <button
          v-for="(t, key) in { profile: '个人信息', projects: '项目经历', skills: '技能', highlights: '技术亮点', experiences: '工作经历' }"
          :key="key"
          class="px-3.5 py-2 text-sm font-medium whitespace-nowrap transition-colors"
          :class="tab === key ? 'text-primary-700 border-b-2 border-primary-600' : 'text-slate-400 hover:text-slate-600'"
          @click="tab = key"
        >
          {{ t }}
          <span v-if="key === 'projects'" class="text-xs text-slate-400 ml-0.5">{{ bundle.projects.length }}</span>
          <span v-if="key === 'skills'" class="text-xs text-slate-400 ml-0.5">{{ bundle.skills.length }}</span>
          <span v-if="key === 'highlights'" class="text-xs text-slate-400 ml-0.5">{{ bundle.highlights.length }}</span>
          <span v-if="key === 'experiences'" class="text-xs text-slate-400 ml-0.5">{{ bundle.experiences.length }}</span>
        </button>
      </div>

      <button
        v-if="tab === 'v2_chunks'"
        class="btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5 shrink-0 ml-2"
        @click="showNewCategoryModal = true"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
        添加自定义栏目
      </button>
    </div>


    <div v-if="loading" class="text-center py-10 text-slate-400">加载中…</div>

    <!-- v2: Markdown 分段知识库视图 (对标 Magic-Resume: 左分类树 + 右卡片流) -->
    <div v-else-if="tab === 'v2_chunks'" class="space-y-4">
      <div class="bg-primary-50/60 border border-primary-100 rounded-xl p-3.5 flex items-center justify-between text-xs text-primary-900">
        <div class="flex items-center gap-2">
          <span class="text-base">💡</span>
          <span>
            <strong>知识分段沉淀原则：</strong> 每个栏目相当于一个独立的 Markdown 主题。建议将个人亮点、架构难点、开源贡献按<strong>段落（Chunk）</strong>原子化拆分，大模型在匹配不同岗位时将自动检索并组装最贴切的段落。
          </span>
        </div>
        <button class="text-primary-600 font-semibold hover:underline shrink-0 ml-4" @click="showNewCategoryModal = true">+ 新建自定义栏目</button>
      </div>

      <!-- 双栏主体容器 -->
      <div class="flex flex-col md:flex-row gap-5 items-start">
        
        <!-- 左列：知识分类资料树 (Magic-Resume 风格) -->
        <div class="w-full md:w-64 bg-white rounded-2xl border border-slate-200/90 flex flex-col shrink-0 shadow-2xs overflow-hidden">
          <div class="p-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <span class="font-bold text-xs text-slate-700 uppercase tracking-wider">知识分类树</span>
            <button
              class="text-xs text-primary-600 font-semibold hover:underline flex items-center gap-0.5"
              @click="showNewCategoryModal = true"
            >
              ＋ 新建分类
            </button>
          </div>
          <div class="p-2 space-y-1 overflow-y-auto max-h-[600px]">
            <div
              v-for="cat in bundle.categories"
              :key="cat.id"
              class="w-full text-left px-3 py-2.5 rounded-xl text-xs font-medium flex items-center justify-between group transition cursor-pointer"
              :class="selectedCategory?.id === cat.id
                ? 'bg-primary-50 text-primary-800 font-bold border border-primary-200/80 shadow-2xs'
                : 'text-slate-600 hover:bg-slate-50 border border-transparent'"
              @click="selectedCategoryId = cat.id"
            >
              <div class="flex items-center gap-2 truncate">
                <span class="w-2.5 h-2.5 rounded-full shrink-0" :class="{
                  'bg-blue-500': cat.color === 'blue',
                  'bg-emerald-500': cat.color === 'emerald',
                  'bg-indigo-500': cat.color === 'indigo',
                  'bg-amber-500': cat.color === 'amber',
                  'bg-purple-500': cat.color === 'purple',
                  'bg-rose-500': cat.color === 'rose'
                }"></span>
                <span class="truncate">{{ cat.name }}</span>
              </div>
              <div class="flex items-center gap-1.5 shrink-0">
                <span class="text-[10px] px-1.5 py-0.2 rounded-full font-mono"
                  :class="selectedCategory?.id === cat.id ? 'bg-primary-200/70 text-primary-800' : 'bg-slate-100 text-slate-500'">
                  {{ (cat.chunks || []).length }}
                </span>
                <button
                  class="text-slate-300 hover:text-red-500 p-0.5 opacity-0 group-hover:opacity-100 transition"
                  title="删除分类"
                  @click.stop="removeCategory(cat.id)"
                >
                  ✕
                </button>
              </div>
            </div>

            <div v-if="!bundle.categories || bundle.categories.length === 0" class="p-4 text-center text-xs text-slate-400">
              暂无分类，点击上方「+ 新建分类」
            </div>
          </div>
        </div>

        <!-- 右列：选中分类的段落卡片流 -->
        <div class="flex-1 w-full bg-white rounded-2xl border border-slate-200/90 p-5 shadow-2xs space-y-4">
          <div v-if="selectedCategory" class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <div class="flex items-center gap-2">
                <span class="w-3 h-3 rounded-full" :class="{
                  'bg-blue-500': selectedCategory.color === 'blue',
                  'bg-emerald-500': selectedCategory.color === 'emerald',
                  'bg-indigo-500': selectedCategory.color === 'indigo',
                  'bg-amber-500': selectedCategory.color === 'amber',
                  'bg-purple-500': selectedCategory.color === 'purple',
                  'bg-rose-500': selectedCategory.color === 'rose'
                }"></span>
                <h3 class="font-bold text-base text-slate-800">{{ selectedCategory.name }}</h3>
                <span class="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-mono">
                  共 {{ (selectedCategory.chunks || []).length }} 个段落卡片
                </span>
              </div>
              <p class="text-xs text-slate-400 mt-1">像搭积木一样沉淀经历，写简历时可一键插入到当前草稿或一键复制</p>
            </div>

            <button
              class="btn-primary text-xs px-3 py-1.5 flex items-center gap-1 shadow-xs"
              @click="openCreateChunk(selectedCategory.id)"
            >
              ＋ 添加段落卡片
            </button>
          </div>

          <!-- 卡片列表 -->
          <div v-if="selectedCategory && selectedCategory.chunks && selectedCategory.chunks.length" class="space-y-3">
            <div
              v-for="c in selectedCategory.chunks"
              :key="c.id"
              class="bg-white rounded-xl p-4 border border-slate-200/90 shadow-2xs hover:border-primary-300 hover:shadow-xs transition group space-y-2.5"
              :class="{ 'opacity-60 bg-slate-50': !c.enabled }"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="flex items-start gap-2.5">
                  <button
                    class="w-4 h-4 rounded border mt-0.5 transition flex items-center justify-center text-[10px] shrink-0"
                    :class="c.enabled ? 'bg-primary-600 border-primary-600 text-white' : 'border-slate-300 bg-white text-transparent'"
                    title="切换启用/停用"
                    @click="toggleChunk(c)"
                  >
                    ✓
                  </button>
                  <div>
                    <h4 class="font-bold text-sm text-slate-800 group-hover:text-primary-700 transition leading-snug">
                      {{ c.title }}
                    </h4>
                    <!-- 标签流 -->
                    <div v-if="c.tags?.length" class="flex flex-wrap gap-1.5 mt-1.5">
                      <span
                        v-for="t in c.tags"
                        :key="t"
                        class="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded border border-slate-200/60 font-mono"
                      >
                        #{{ t }}
                      </span>
                    </div>
                  </div>
                </div>

                <div class="flex items-center gap-2 shrink-0">
                  <button
                    class="text-xs text-primary-600 bg-primary-50 hover:bg-primary-100 px-2.5 py-1 rounded-lg font-medium border border-primary-200 transition flex items-center gap-1 shadow-2xs"
                    title="复制为 Markdown 片段并可直接贴入简历"
                    @click="copyChunkContent(c)"
                  >
                    <span>📥</span>
                    <span>引用到简历</span>
                  </button>
                  <button class="text-xs text-slate-400 hover:text-slate-700 px-1" @click="openEditChunk(c)">编辑</button>
                  <button class="text-xs text-slate-400 hover:text-red-500 px-1" @click="removeChunk(c.id)">删除</button>
                </div>
              </div>

              <!-- Markdown 核心内容展示 -->
              <div class="text-xs text-slate-700 bg-slate-50/80 p-3 rounded-lg border border-slate-100 font-mono whitespace-pre-wrap leading-relaxed">
                {{ c.content }}
              </div>
            </div>
          </div>

          <div v-else-if="selectedCategory" class="text-center py-16 text-xs text-slate-400 border border-dashed border-slate-200 rounded-xl bg-slate-50/30">
            <div class="text-2xl mb-2">📑</div>
            <div class="font-semibold text-slate-600">该栏目下暂无知识段落</div>
            <div class="text-slate-400 mt-1 mb-3">将经历原子化拆分成卡片，大模型可极速精准读取</div>
            <button class="btn-primary !text-xs !py-1" @click="openCreateChunk(selectedCategory.id)">＋ 立即添加段落</button>
          </div>
        </div>

      </div>
    </div>

    <!-- 个人信息 -->
    <div v-else-if="tab === 'profile'" class="card">
      <div class="grid md:grid-cols-2 gap-3">
        <div><label class="label">姓名</label><input v-model="profileForm.name" class="input" /></div>
        <div><label class="label">职位标签</label><input v-model="profileForm.label" class="input" /></div>
        <div><label class="label">邮箱</label><input v-model="profileForm.email" class="input" /></div>
        <div><label class="label">电话</label><input v-model="profileForm.phone" class="input" /></div>
        <div><label class="label">所在地</label><input v-model="profileForm.location" class="input" /></div>
        <div><label class="label">出生年月</label><input v-model="profileForm.birth" class="input" placeholder="2005/03" /></div>
        <div><label class="label">GitHub</label><input v-model="profileForm.github" class="input" /></div>
        <div><label class="label">Blog</label><input v-model="profileForm.blog" class="input" /></div>
      </div>
      <div class="mt-3">
        <label class="label">个人简介（Markdown）</label>
        <MdEditor v-model="profileForm.summary" :rows="3" />
      </div>
      <div class="mt-4">
        <label class="label">教育经历</label>
        <div v-for="(edu, i) in profileEdu" :key="i" class="grid md:grid-cols-6 gap-2 mb-2 items-end">
          <input v-model="edu.institution" class="input" placeholder="学校" />
          <input v-model="edu.area" class="input" placeholder="专业" />
          <input v-model="edu.studyType" class="input" placeholder="学历" />
          <input v-model="edu.gpa" class="input" placeholder="GPA" />
          <input v-model="edu.startDate" class="input" placeholder="2023/09" />
          <input v-model="edu.endDate" class="input" placeholder="2027/06" />
        </div>
        <div class="flex gap-2">
          <button class="btn-secondary !py-1 !text-xs" @click="profileEdu.push({ institution: '', area: '', studyType: '', gpa: '', startDate: '', endDate: '' })">＋ 添加教育经历</button>
          <button v-if="profileEdu.length" class="btn-secondary !py-1 !text-xs text-red-500" @click="profileEdu.pop()">移除最后一条</button>
        </div>
      </div>
      <div class="mt-4 flex justify-end"><button class="btn-primary" @click="saveProfile()">保存个人信息</button></div>
    </div>

    <!-- 项目经历 -->
    <div v-else-if="tab === 'projects'" class="space-y-3">
      <div id="new-item" v-if="true" class="card border-dashed">
        <h3 class="font-medium text-sm mb-3">{{ editingId ? '编辑项目' : '新增项目' }}</h3>
        <div class="grid md:grid-cols-2 gap-3">
          <div><label class="label">项目名称 *</label><input v-model="projectForm.name" class="input" /></div>
          <div><label class="label">角色</label><input v-model="projectForm.role" class="input" /></div>
          <div class="md:col-span-2"><label class="label">描述</label><input v-model="projectForm.description" class="input" /></div>
          <div><label class="label">开始时间</label><input v-model="projectForm.start_date" class="input" placeholder="2026/05" /></div>
          <div><label class="label">结束时间</label><input v-model="projectForm.end_date" class="input" placeholder="至今" /></div>
          <div><label class="label">URL</label><input v-model="projectForm.url" class="input" /></div>
          <div><label class="label">关键词（逗号分隔）</label><input v-model="projectForm.keywords" class="input" /></div>
          <div class="md:col-span-2"><label class="label">亮点（每行一条，支持 Markdown）</label><MdEditor v-model="projectForm.highlights" :rows="4" /></div>
        </div>
        <div class="mt-3 flex justify-end gap-2">
          <button v-if="editingId" class="btn-secondary" @click="resetProject(); editingId = null">取消</button>
          <button class="btn-primary" @click="saveProject()" :disabled="!projectForm.name">{{ editingId ? '保存修改' : '添加项目' }}</button>
        </div>
      </div>
      <div v-for="p in bundle.projects" :key="p.id" class="card">
        <div class="flex items-start justify-between">
          <div>
            <div class="font-medium">{{ p.name }} <span v-if="p.role" class="text-xs text-slate-500">· {{ p.role }}</span></div>
            <div class="text-xs text-slate-400">{{ p.start_date }} - {{ p.end_date }}</div>
          </div>
          <div class="flex gap-1">
            <span class="badge" :class="p.enabled ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-400'">{{ p.enabled ? '启用' : '停用' }}</span>
            <button class="text-xs text-primary-600 hover:underline" @click="editProject(p)">编辑</button>
            <button class="text-xs text-red-500 hover:underline" @click="delProject(p.id)">删除</button>
          </div>
        </div>
        <div class="text-sm text-slate-600 mt-1 line-clamp-2">{{ p.description }}</div>
      </div>
    </div>

    <!-- 技能 -->
    <div v-else-if="tab === 'skills'" class="space-y-3">
      <div class="card border-dashed">
        <h3 class="font-medium text-sm mb-3">{{ editingId ? '编辑技能' : '新增技能' }}</h3>
        <div class="grid md:grid-cols-3 gap-3">
          <div><label class="label">技能名 *</label><input v-model="skillForm.name" class="input" /></div>
          <div><label class="label">熟练度</label><input v-model="skillForm.level" class="input" /></div>
          <div><label class="label">关键词（逗号分隔）</label><input v-model="skillForm.keywords" class="input" /></div>
        </div>
        <div class="mt-3 flex justify-end gap-2">
          <button v-if="editingId" class="btn-secondary" @click="resetSkill(); editingId = null">取消</button>
          <button class="btn-primary" @click="saveSkill()" :disabled="!skillForm.name">{{ editingId ? '保存' : '添加技能' }}</button>
        </div>
      </div>
      <div class="grid md:grid-cols-2 gap-2">
        <div v-for="s in bundle.skills" :key="s.id" class="card !py-2">
          <div class="flex items-center justify-between">
            <div class="text-sm font-medium">{{ s.name }} <span v-if="s.level" class="text-xs text-slate-400">[{{ s.level }}]</span></div>
            <div class="flex gap-1.5">
              <button class="text-xs text-primary-600" @click="editSkill(s)">编辑</button>
              <button class="text-xs text-red-500" @click="delSkill(s.id)">删除</button>
            </div>
          </div>
          <div v-if="s.keywords?.length" class="text-xs text-slate-500 mt-0.5">{{ s.keywords.join(', ') }}</div>
        </div>
      </div>
    </div>

    <!-- 技术亮点 -->
    <div v-else-if="tab === 'highlights'" class="space-y-3">
      <div class="card border-dashed">
        <h3 class="font-medium text-sm mb-3">{{ editingId ? '编辑亮点' : '新增亮点' }}</h3>
        <div class="grid md:grid-cols-2 gap-3">
          <div><label class="label">标题 *</label><input v-model="highlightForm.title" class="input" /></div>
          <div><label class="label">分类</label><input v-model="highlightForm.category" class="input" placeholder="后端架构 / AI & IoT / 支付" /></div>
          <div class="md:col-span-2"><label class="label">内容（支持 Markdown）</label><MdEditor v-model="highlightForm.content" :rows="3" /></div>
          <div class="md:col-span-2"><label class="label">量化指标（JSON，可选）</label><input v-model="highlightForm.metrics" class="input font-mono text-xs" placeholder='{"users": 2400, "orders": 1305}' /></div>
        </div>
        <div class="mt-3 flex justify-end gap-2">
          <button v-if="editingId" class="btn-secondary" @click="resetHighlight(); editingId = null">取消</button>
          <button class="btn-primary" @click="saveHighlight()" :disabled="!highlightForm.title">{{ editingId ? '保存' : '添加亮点' }}</button>
        </div>
      </div>
      <div v-for="h in bundle.highlights" :key="h.id" class="card">
        <div class="flex items-start justify-between">
          <div>
            <div class="font-medium">{{ h.title }} <span v-if="h.category" class="badge bg-slate-100 text-slate-500 ml-1">{{ h.category }}</span></div>
            <div class="text-sm text-slate-600 mt-0.5 line-clamp-2">{{ h.content }}</div>
          </div>
          <div class="flex gap-1.5">
            <button class="text-xs text-primary-600" @click="editHighlight(h)">编辑</button>
            <button class="text-xs text-red-500" @click="delHighlight(h.id)">删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 工作经历 -->
    <div v-else-if="tab === 'experiences'" class="space-y-3">
      <div class="card border-dashed">
        <h3 class="font-medium text-sm mb-3">{{ editingId ? '编辑经历' : '新增经历' }}</h3>
        <div class="grid md:grid-cols-2 gap-3">
          <div><label class="label">公司 *</label><input v-model="experienceForm.company" class="input" /></div>
          <div><label class="label">职位</label><input v-model="experienceForm.role" class="input" /></div>
          <div><label class="label">开始时间</label><input v-model="experienceForm.start_date" class="input" placeholder="2026/06" /></div>
          <div><label class="label">结束时间</label><input v-model="experienceForm.end_date" class="input" placeholder="2026/09" /></div>
          <div class="md:col-span-2"><label class="label">工作亮点（每行一条，支持 Markdown）</label><MdEditor v-model="experienceForm.highlights" :rows="4" /></div>
        </div>
        <div class="mt-3 flex justify-end gap-2">
          <button v-if="editingId" class="btn-secondary" @click="resetExperience(); editingId = null">取消</button>
          <button class="btn-primary" @click="saveExperience()" :disabled="!experienceForm.company">{{ editingId ? '保存' : '添加经历' }}</button>
        </div>
      </div>
      <div v-for="e in bundle.experiences" :key="e.id" class="card">
        <div class="flex items-start justify-between">
          <div>
            <div class="font-medium">{{ e.company }} <span v-if="e.role" class="text-xs text-slate-500">· {{ e.role }}</span></div>
            <div class="text-xs text-slate-400">{{ e.start_date }} - {{ e.end_date }}</div>
          </div>
          <div class="flex gap-1.5">
            <button class="text-xs text-primary-600" @click="editExperience(e)">编辑</button>
            <button class="text-xs text-red-500" @click="delExperience(e.id)">删除</button>
          </div>
        </div>
        <div class="text-sm text-slate-600 mt-1"><span v-for="h in e.highlights" :key="h" class="block line-clamp-1">• {{ h }}</span></div>
      </div>
    </div>

    <!-- 导入区 -->
    <div class="card mt-6">
      <h3 class="font-medium mb-2">一键导入 JSON 简历</h3>
      <p class="text-xs text-slate-500 mb-2">粘贴标准 JSON Resume 格式（含 basics/projects/skills/work）或拖入 resume.json 文件内容，自动拆分到各分类。</p>
      <div class="mt-2 flex items-center gap-3">
        <button class="btn-secondary text-xs" @click="doImport" :disabled="!importText.trim()">导入</button>
        <span v-if="importMsg" class="text-xs text-green-600">{{ importMsg }}</span>
      </div>
    </div>

    <!-- 弹窗：新增自定义栏目 -->
    <div v-if="showNewCategoryModal" class="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-100">
        <h3 class="text-base font-bold text-slate-800 mb-4">新建自定义知识栏目</h3>
        <div class="space-y-4">
          <div>
            <label class="label">栏目名称</label>
            <input v-model="newCategoryName" class="input" placeholder="例如：架构沉淀 / 开源贡献 / 避坑日记" autofocus />
          </div>
          <div>
            <label class="label">标识颜色</label>
            <div class="flex items-center gap-3 mt-1.5">
              <button
                v-for="color in ['blue', 'emerald', 'indigo', 'amber', 'purple', 'rose']"
                :key="color"
                class="w-7 h-7 rounded-full transition flex items-center justify-center border-2"
                :class="[
                  color === 'blue' ? 'bg-blue-500' :
                  color === 'emerald' ? 'bg-emerald-500' :
                  color === 'indigo' ? 'bg-indigo-500' :
                  color === 'amber' ? 'bg-amber-500' :
                  color === 'purple' ? 'bg-purple-500' : 'bg-rose-500',
                  newCategoryColor === color ? 'border-slate-800 scale-110 shadow-sm' : 'border-transparent opacity-80 hover:opacity-100'
                ]"
                @click="newCategoryColor = color"
              >
                <span v-if="newCategoryColor === color" class="text-white text-xs">✓</span>
              </button>
            </div>
          </div>
        </div>
        <div class="mt-6 flex justify-end gap-2.5">
          <button class="btn-secondary text-xs" @click="showNewCategoryModal = false">取消</button>
          <button class="btn-primary text-xs" :disabled="!newCategoryName.trim()" @click="createCategory">确定创建</button>
        </div>
      </div>
    </div>

    <!-- 弹窗：添加/编辑段落卡片 -->
    <div v-if="showChunkModal" class="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl border border-slate-100 max-h-[90vh] flex flex-col">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
          <h3 class="text-base font-bold text-slate-800">
            {{ editingChunk.id ? '编辑 Markdown 段落卡片' : '添加 Markdown 段落卡片' }}
          </h3>
          <button class="text-slate-400 hover:text-slate-600" @click="showChunkModal = false">✕</button>
        </div>

        <div class="space-y-4 overflow-y-auto flex-1 pr-1">
          <div>
            <label class="label">段落标题 *</label>
            <input v-model="editingChunk.title" class="input" placeholder="例如：高并发抢购秒杀限流架构 / 复杂表单联动架构设计" />
          </div>

          <div>
            <label class="label">标签 (逗号分隔，便于智能检索)</label>
            <input v-model="chunkTagsInput" class="input" placeholder="例如：Redis, 分布式锁, 架构优化, Kafka" />
          </div>

          <div>
            <label class="label">Markdown 内容 (支持 STAR 法则详细展开) *</label>
            <MdEditor v-model="editingChunk.content" :rows="8" placeholder="使用 Markdown 记录背景、难点、思考与量化成果..." />
          </div>

          <div class="flex items-center gap-2 pt-1">
            <input type="checkbox" id="chunk-enabled" v-model="editingChunk.enabled" class="rounded border-slate-300 text-primary-600 focus:ring-primary-500" />
            <label for="chunk-enabled" class="text-xs text-slate-600 cursor-pointer">在生成简历和 AI 匹配时启用此段落</label>
          </div>
        </div>

        <div class="mt-5 pt-3 border-t border-slate-100 flex justify-end gap-2.5">
          <button class="btn-secondary text-xs" @click="showChunkModal = false">取消</button>
          <button class="btn-primary text-xs" :disabled="!editingChunk.title?.trim()" @click="saveChunk">
            {{ editingChunk.id ? '保存更新' : '保存段落' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>