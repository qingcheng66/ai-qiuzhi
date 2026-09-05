<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  sectionName: string
  sectionContent: any
  loading?: boolean
}>()

const emit = defineEmits<{
  save: [content: any]
  regenerate: []
  reset: []
}>()

const editContent = ref<any>(null)

watch(
  () => props.sectionContent,
  (val) => {
    editContent.value = val ? JSON.parse(JSON.stringify(val)) : getDefaultContent(props.sectionName)
  },
  { immediate: true }
)

function getDefaultContent(name: string): any {
  switch (name) {
    case 'basics': return { name: '', label: '', email: '', phone: '', location: '' }
    case 'education': return []
    case 'skills': return []
    case 'projects': return []
    case 'experience': return []
    case 'highlights': return []
    default: return {}
  }
}

function addItem() {
  if (!Array.isArray(editContent.value)) return
  switch (props.sectionName) {
    case 'skills': editContent.value.push({ name: '', keywords: [] }); break
    case 'projects': editContent.value.push({ name: '', description: '', highlights: [] }); break
    case 'experience': editContent.value.push({ company: '', role: '', startDate: '', endDate: '', highlights: [] }); break
    case 'education': editContent.value.push({ institution: '', area: '', studyType: '', startDate: '', endDate: '' }); break
    case 'highlights': editContent.value.push({ title: '', category: '', content: '' }); break
    default: editContent.value.push({})
  }
}

function removeItem(idx: number) {
  if (Array.isArray(editContent.value)) editContent.value.splice(idx, 1)
}

function addKeyword(item: any) {
  if (!item.keywords) item.keywords = []
  const kw = window.prompt('输入技能关键词：')
  if (kw) item.keywords.push(kw)
}

function addHighlight(item: any, promptText = '输入亮点：') {
  if (!item.highlights) item.highlights = []
  const hl = window.prompt(promptText)
  if (hl) item.highlights.push(hl)
}

function removeKeyword(item: any, idx: number) {
  item.keywords.splice(idx, 1)
}

function moveItem(idx: number, dir: -1 | 1) {
  if (!Array.isArray(editContent.value)) return
  const target = idx + dir
  if (target < 0 || target >= editContent.value.length) return
  const arr = editContent.value
  ;[arr[idx], arr[target]] = [arr[target], arr[idx]]
}

function handleSave() {
  emit('save', editContent.value ? JSON.parse(JSON.stringify(editContent.value)) : null)
}

function handleRegenerate() {
  emit('regenerate')
}

function handleReset() {
  editContent.value = props.sectionContent ? JSON.parse(JSON.stringify(props.sectionContent)) : getDefaultContent(props.sectionName)
}
</script>

<template>
  <div class="card border border-slate-200">
    <div class="flex items-center justify-between mb-3">
      <h3 class="font-semibold text-sm flex items-center gap-2">
        <span class="w-2 h-2 rounded-full"
          :class="sectionName === 'basics' ? 'bg-blue-500' : sectionName === 'skills' ? 'bg-green-500' : sectionName === 'projects' ? 'bg-purple-500' : sectionName === 'experience' ? 'bg-orange-500' : sectionName === 'education' ? 'bg-cyan-500' : 'bg-pink-500'"
        />
        {{ { basics: '基本信息', education: '教育背景', skills: '技能清单', projects: '项目经验', experience: '工作经历', highlights: '个人亮点' }[sectionName] || sectionName }}
      </h3>
      <div class="flex gap-1.5">
        <button class="btn-secondary !py-1 !text-xs" :disabled="loading" @click="handleRegenerate">
          {{ loading ? '生成中…' : 'AI 建议' }}
        </button>
        <button class="btn-secondary !py-1 !text-xs" @click="handleReset">还原</button>
        <button class="btn-primary !py-1 !text-xs" @click="handleSave">保存此段</button>
      </div>
    </div>

    <!-- basics -->
    <div v-if="sectionName === 'basics'" class="grid grid-cols-2 gap-3">
      <div><label class="label">姓名</label><input v-model="editContent.name" class="input" placeholder="姓名" /></div>
      <div><label class="label">职称</label><input v-model="editContent.label" class="input" placeholder="职称" /></div>
      <div><label class="label">邮箱</label><input v-model="editContent.email" class="input" placeholder="email@example.com" /></div>
      <div><label class="label">电话</label><input v-model="editContent.phone" class="input" placeholder="手机号" /></div>
      <div class="col-span-2"><label class="label">地址</label><input v-model="editContent.location" class="input" placeholder="城市 / 地址" /></div>
      <div class="col-span-2"><label class="label">个人链接</label><input v-model="editContent.url" class="input" placeholder="GitHub / 博客 / 作品集 URL" /></div>
    </div>

    <!-- skills -->
    <div v-else-if="sectionName === 'skills'" class="space-y-3">
      <div v-for="(item, idx) in editContent" :key="idx" class="border border-slate-100 rounded-lg p-3">
        <div class="flex items-center justify-between mb-2">
          <input v-model="item.name" class="input !w-48 !text-sm" placeholder="分类名（如：前端）" />
          <div class="flex gap-1">
            <button class="btn-secondary !py-0.5 !px-1.5 !text-xs" @click="moveItem(idx, -1)" :disabled="idx === 0">↑</button>
            <button class="btn-secondary !py-0.5 !px-1.5 !text-xs" @click="moveItem(idx, 1)" :disabled="idx === editContent.length - 1">↓</button>
            <button class="btn-secondary !py-0.5 !px-1.5 !text-xs text-red-500" @click="removeItem(idx)">×</button>
          </div>
        </div>
        <div class="flex flex-wrap gap-1.5">
          <span v-for="(kw, ki) in item.keywords" :key="ki" class="badge bg-primary-50 text-primary-700 flex items-center gap-1">
            {{ kw }}
            <span class="cursor-pointer hover:text-red-500" @click="removeKeyword(item, ki)">×</span>
          </span>
          <button class="badge border border-dashed border-slate-300 text-slate-400 cursor-pointer hover:border-primary-300" @click="addKeyword(item)">＋</button>
        </div>
      </div>
      <button class="btn-secondary !text-xs" @click="addItem">＋ 添加分类</button>
    </div>

    <!-- array sections -->
    <div v-else-if="['projects', 'experience', 'education', 'highlights'].includes(sectionName)" class="space-y-3">
      <div v-for="(item, idx) in editContent" :key="idx" class="border border-slate-100 rounded-lg p-3">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-medium text-slate-400">#{{ idx + 1 }}</span>
          <div class="flex gap-1">
            <button class="btn-secondary !py-0.5 !px-1.5 !text-xs" @click="moveItem(idx, -1)" :disabled="idx === 0">↑</button>
            <button class="btn-secondary !py-0.5 !px-1.5 !text-xs" @click="moveItem(idx, 1)" :disabled="idx === editContent.length - 1">↓</button>
            <button class="btn-secondary !py-0.5 !px-1.5 !text-xs text-red-500" @click="removeItem(idx)">×</button>
          </div>
        </div>

        <!-- projects -->
        <template v-if="sectionName === 'projects'">
          <div class="grid grid-cols-2 gap-2">
            <input v-model="item.name" class="input !text-sm" placeholder="项目名称" />
            <input v-model="item.url" class="input !text-sm" placeholder="项目链接（可选）" />
          </div>
          <textarea v-model="item.description" rows="2" class="input !text-sm mt-2" placeholder="项目描述" />
          <div class="mt-2">
            <div class="text-xs text-slate-400 mb-1">亮点：</div>
            <div class="flex flex-wrap gap-1">
              <span v-for="(hl, hi) in item.highlights" :key="hi" class="badge bg-slate-100 text-slate-600 flex items-center gap-1">
                {{ hl }}
                <span class="cursor-pointer hover:text-red-500" @click="item.highlights.splice(hi, 1)">×</span>
              </span>
              <button class="badge border border-dashed border-slate-300 text-slate-400 cursor-pointer text-xs" @click="addHighlight(item, '输入亮点：')">＋</button>
            </div>
          </div>
        </template>

        <!-- experience -->
        <template v-else-if="sectionName === 'experience'">
          <div class="grid grid-cols-2 gap-2">
            <input v-model="item.company" class="input !text-sm" placeholder="公司名称" />
            <input v-model="item.role" class="input !text-sm" placeholder="职位" />
            <input v-model="item.startDate" class="input !text-sm" placeholder="开始时间" />
            <input v-model="item.endDate" class="input !text-sm" placeholder="结束时间" />
          </div>
          <div class="mt-2">
            <div class="text-xs text-slate-400 mb-1">职责亮点：</div>
            <div class="flex flex-wrap gap-1">
              <span v-for="(hl, hi) in item.highlights" :key="hi" class="badge bg-slate-100 text-slate-600 flex items-center gap-1">
                {{ hl }}
                <span class="cursor-pointer hover:text-red-500" @click="item.highlights.splice(hi, 1)">×</span>
              </span>
              <button class="badge border border-dashed border-slate-300 text-slate-400 cursor-pointer text-xs" @click="addHighlight(item, '输入职责亮点：')">＋</button>
            </div>
          </div>
        </template>

        <!-- education -->
        <template v-else-if="sectionName === 'education'">
          <div class="grid grid-cols-2 gap-2">
            <input v-model="item.institution" class="input !text-sm" placeholder="学校名称" />
            <input v-model="item.area" class="input !text-sm" placeholder="专业" />
            <input v-model="item.studyType" class="input !text-sm" placeholder="学历（本科/硕士）" />
            <input v-model="item.gpa" class="input !text-sm" placeholder="GPA（可选）" />
            <input v-model="item.startDate" class="input !text-sm" placeholder="开始时间" />
            <input v-model="item.endDate" class="input !text-sm" placeholder="结束时间" />
          </div>
        </template>

        <!-- highlights -->
        <template v-else-if="sectionName === 'highlights'">
          <div class="grid grid-cols-2 gap-2">
            <input v-model="item.title" class="input !text-sm" placeholder="标题" />
            <select v-model="item.category" class="input !text-sm">
              <option value="">选择分类</option>
              <option value="技术">技术</option>
              <option value="管理">管理</option>
              <option value="荣誉">荣誉</option>
              <option value="其他">其他</option>
            </select>
          </div>
          <textarea v-model="item.content" rows="2" class="input !text-sm mt-2" placeholder="内容描述" />
        </template>
      </div>
      <button class="btn-secondary !text-xs" @click="addItem">
        ＋ 添加{{
          { projects: '项目', experience: '经历', education: '教育', highlights: '亮点' }[sectionName]
        }}
      </button>
    </div>

    <div v-else class="text-sm text-slate-400 py-4 text-center">
      暂不支持编辑此段
    </div>
  </div>
</template>