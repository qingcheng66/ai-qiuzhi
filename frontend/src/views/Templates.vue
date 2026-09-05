<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiTemplates } from '@/api'

const templates = ref<any[]>([])
const loading = ref(false)
const error = ref('')
const msg = ref('')
const showCreate = ref(false)
const editor = ref({ name: '', description: '', content: '' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    templates.value = await apiTemplates.list()
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function create() {
  if (!editor.value.name.trim() || !editor.value.content.trim()) return
  try {
    await apiTemplates.create({ ...editor.value, variables: [] })
    showCreate.value = false
    editor.value = { name: '', description: '', content: '' }
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function remove(id: number) {
  if (!confirm('确认删除该模板？')) return
  try {
    await apiTemplates.remove(id)
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function handleImport(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  error.value = ''
  try {
    await apiTemplates.importFile(file, file.name.replace(/\.(pdf|docx)$/i, ''))
    msg.value = `已导入模板：${file.name}`
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

// 模板编辑预览
const previewId = ref<number | null>(null)
const previewHtml = ref('')
const previewData = ref<any>({
  name: '张三', label: '软件工程师', email: 'zhang@example.com', phone: '13800000000', location: '北京',
  skills: [{ name: '后端', keywords: ['Java', 'Spring Boot'] }],
  experience: [{ company: '示例公司', role: '工程师', startDate: '2024/01', endDate: '至今', highlights: ['负责核心模块'] }],
})
async function preview(id: number) {
  previewId.value = id
  try {
    const r = await apiTemplates.render(id, { basics: {}, education: [], skills: previewData.value.skills, experience: previewData.value.experience, projects: [], highlights: [] })
    previewHtml.value = r.html
  } catch (e: any) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-5">
      <div>
        <h2 class="text-2xl font-bold">模板管理</h2>
        <p class="text-sm text-slate-500">内置 3 套模板 + 上传 PDF/Word 自动生成可复用模板</p>
      </div>
      <div class="flex gap-2">
        <label class="btn-secondary text-xs cursor-pointer">
          ⬆ 导入 PDF/Word
          <input type="file" accept=".pdf,.docx" class="hidden" @change="handleImport" />
        </label>
        <button class="btn-primary text-xs" @click="showCreate = !showCreate">＋ 新建模板</button>
      </div>
    </div>

    <div v-if="error" class="mb-3 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">{{ error }}</div>
    <div v-if="msg" class="mb-3 p-2 rounded-lg bg-green-50 border border-green-200 text-green-700 text-xs">{{ msg }}</div>

    <!-- 新建模板 -->
    <div v-if="showCreate" class="card mb-4 border-primary-200">
      <div class="grid md:grid-cols-2 gap-3 mb-3">
        <input v-model="editor.name" class="input" placeholder="模板名 *" />
        <input v-model="editor.description" class="input" placeholder="描述" />
      </div>
      <textarea v-model="editor.content" rows="10" class="input font-mono text-xs" placeholder="Jinja2 HTML 模板，可使用 {{ name }} {{ email }} {{ skills }} {{ experience }} 等变量与 for 循环" />
      <div class="mt-3 flex justify-end gap-2">
        <button class="btn-secondary text-xs" @click="showCreate = false">取消</button>
        <button class="btn-primary text-xs" @click="create" :disabled="!editor.name || !editor.content">创建模板</button>
      </div>
    </div>

    <!-- 模板列表 -->
    <div class="grid md:grid-cols-3 gap-3" v-if="!loading">
      <div v-for="t in templates" :key="t.id" class="card flex flex-col">
        <div class="flex items-start justify-between">
          <div class="font-medium">{{ t.name }}</div>
          <span class="badge" :class="t.is_builtin ? 'bg-primary-50 text-primary-600' : 'bg-slate-100 text-slate-600'">
            {{ t.is_builtin ? '内置' : '自定义' }}
          </span>
        </div>
        <div class="text-xs text-slate-400 mt-0.5">{{ t.source }} · {{ (t.content?.length || 0) }} 字符</div>
        <div class="text-xs text-slate-500 mt-1 flex-1 line-clamp-2">{{ t.description || '' }}</div>
        <div class="flex gap-2 mt-3">
          <button class="btn-secondary !py-1 !text-xs flex-1" @click="preview(t.id)">预览</button>
          <button v-if="!t.is_builtin" class="btn-danger !py-1 !text-xs" @click="remove(t.id)">删除</button>
        </div>
      </div>
      <p v-if="!templates.length" class="col-span-3 text-center text-slate-400 py-8">暂无模板</p>
    </div>
    <div v-else class="text-center py-10 text-slate-400">加载中…</div>

    <!-- 预览 -->
    <div v-if="previewHtml" class="card mt-6">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-medium">模板预览</h3>
        <button class="btn-secondary !text-xs" @click="previewHtml = ''">关闭</button>
      </div>
      <div class="border border-slate-200 rounded-lg overflow-auto max-h-[650px] bg-white">
        <iframe :srcdoc="previewHtml" class="w-full h-[600px]" sandbox="" />
      </div>
    </div>
  </div>
</template>