<script setup lang="ts">
import { computed, ref, watch } from 'vue'

export interface SkillItem {
  type: 'text' | 'group'
  text?: string
  name?: string
  keywords?: string[]
}

const props = defineProps<{
  resumeData: any
  scale?: number
  themeColor?: 'classic' | 'indigo' | 'slate' | 'emerald'
  sectionVisibility?: Record<string, boolean>
}>()

const activeTheme = ref<'classic' | 'indigo' | 'slate' | 'emerald'>(
  props.themeColor || props.resumeData?.theme_color || 'classic'
)

watch(
  () => [props.themeColor, props.resumeData?.theme_color],
  ([newColor, resumeColor]) => {
    const target = newColor || resumeColor
    if (target) {
      activeTheme.value = target as any
    }
  }
)

const themeStyles = computed(() => {
  switch (activeTheme.value) {
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
        bullet: '#64748b',
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
    return val.split('\n').map(s => s.trim()).filter(Boolean).map(text => ({
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

// 智能高亮技能前缀 (例如 1. 双 Agent 工作流: 自动加粗冒号前)
function formatSkillText(text: string) {
  if (!text) return ''
  const colonMatch = text.match(/^(\d+[\.、]\s*[^:：]+[:：]|[^:：]{2,15}[:：])([\s\S]*)$/)
  if (colonMatch) {
    return `<strong>${colonMatch[1]}</strong>${colonMatch[2]}`
  }
  return text
}

// 辅助函数：格式化时间区间
function formatDate(start?: string, end?: string) {
  if (!start && !end) return ''
  if (start && end) return `${start} - ${end}`
  return start || end || ''
}

// 辅助函数：格式化学历/专业/GPA
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

const internalZoom = ref(0.68)
const currentScale = computed(() => {
  return (props.scale ?? 1) * internalZoom.value
})
</script>

<template>
  <div class="resume-paper-container flex flex-col items-center w-full overflow-x-auto pb-6">
    <!-- 纸质顶部微型控制工具条 -->
    <div class="w-full flex items-center justify-between pb-2 mb-3 text-xs text-slate-500 border-b border-slate-200/60 shrink-0">
      <div class="flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span class="font-semibold text-slate-700">实时 A4 纸质渲染</span>
      </div>

      <!-- 缩放与配色 -->
      <div class="flex items-center gap-2.5">
        <!-- 比例切换 -->
        <div class="flex items-center gap-0.5 bg-slate-100 p-0.5 rounded text-[10px]">
          <button
            class="px-1.5 py-0.5 rounded transition font-medium"
            :class="internalZoom === 0.68 ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
            @click="internalZoom = 0.68"
          >
            适屏 68%
          </button>
          <button
            class="px-1.5 py-0.5 rounded transition font-medium"
            :class="internalZoom === 0.85 ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
            @click="internalZoom = 0.85"
          >
            85%
          </button>
          <button
            class="px-1.5 py-0.5 rounded transition font-medium"
            :class="internalZoom === 1.0 ? 'bg-white text-primary-700 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'"
            @click="internalZoom = 1.0"
          >
            100%
          </button>
        </div>

        <!-- 配色主题切换 -->
        <div class="flex items-center gap-1">
          <button
            class="px-2 py-0.5 rounded text-[10px] font-medium border transition-all"
            :class="activeTheme === 'classic' ? 'bg-slate-800 text-white border-slate-800' : 'bg-white text-slate-600 hover:bg-slate-50'"
            @click="activeTheme = 'classic'"
          >
            经典黑
          </button>
          <button
            class="px-2 py-0.5 rounded text-[10px] font-medium border transition-all"
            :class="activeTheme === 'indigo' ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 hover:bg-slate-50'"
            @click="activeTheme = 'indigo'"
          >
            科技蓝
          </button>
          <button
            class="px-2 py-0.5 rounded text-[10px] font-medium border transition-all"
            :class="activeTheme === 'emerald' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-slate-600 hover:bg-slate-50'"
            @click="activeTheme = 'emerald'"
          >
            雅绿
          </button>
          <button
            class="px-2 py-0.5 rounded text-[10px] font-medium border transition-all"
            :class="activeTheme === 'slate' ? 'bg-slate-600 text-white border-slate-600' : 'bg-white text-slate-600 hover:bg-slate-50'"
            @click="activeTheme = 'slate'"
          >
            雅灰
          </button>
        </div>
      </div>
    </div>

    <!-- 标准 A4 纸张主体容器 (物理固定 794px 宽，按比例缩放，确保 100% 格式无畸变) -->
    <div
      class="a4-scalable-wrapper mx-auto transition-all"
      :style="{
        width: `${Math.round(794 * currentScale)}px`,
        height: `${Math.round(1123 * currentScale)}px`,
        position: 'relative',
        flexShrink: 0
      }"
    >
      <div
        class="a4-sheet bg-white text-slate-900 shadow-2xl border border-slate-300 rounded-xs select-text shrink-0"
        :style="{
          width: '794px',
          minHeight: '1123px',
          transform: `scale(${currentScale})`,
          transformOrigin: 'top left',
          position: 'absolute',
          top: 0,
          left: 0,
          padding: '38px 46px',
          boxSizing: 'border-box'
        }"
      >
        <!-- ================= 1. Header (左联系方式、中姓名、右头像) ================= -->
        <header v-if="isSectionVisible('basics')" class="header-section pb-4 mb-4 flex justify-between items-start gap-4">
          <!-- 左侧求职意向与联系方式 -->
          <div class="header-left text-xs text-slate-700 space-y-1.5 pt-1 flex-1 min-w-[360px]">
            <div v-if="basics.label || basics.title" class="flex items-center gap-2">
              <span class="text-slate-500">👤 求职意向</span>
              <span class="font-bold text-slate-900">{{ basics.label || basics.title }}</span>
            </div>

          <div class="grid grid-cols-2 gap-x-6 gap-y-1 text-slate-600 font-sans pt-0.5">
            <div v-if="basics.email" class="flex items-center gap-1.5">
              <span>✉</span>
              <span class="font-mono">{{ basics.email }}</span>
            </div>
            <div v-if="basics.phone" class="flex items-center gap-1.5">
              <span>📞</span>
              <span class="font-mono">{{ basics.phone }}</span>
            </div>
            <div v-if="basics.birthDate || basics.birth" class="flex items-center gap-1.5">
              <span>📅</span>
              <span class="font-mono">{{ basics.birthDate || basics.birth }}</span>
            </div>
            <div v-if="basics.location" class="flex items-center gap-1.5">
              <span>📍</span>
              <span>{{ basics.location }}</span>
            </div>
            <div v-if="basics.github" class="col-span-2 flex items-center gap-1.5">
              <span>🔗</span>
              <span class="font-mono truncate max-w-[280px]">{{ basics.github }}</span>
            </div>
            <div v-if="basics.blog" class="col-span-2 flex items-center gap-1.5">
              <span>🌐</span>
              <span class="font-mono truncate max-w-[280px]">{{ basics.blog }}</span>
            </div>
          </div>

          <!-- 自定义字段 -->
          <div v-if="basics.custom_fields?.length" class="flex flex-wrap gap-x-4 gap-y-0.5 pt-1 text-[11px] text-slate-600">
            <span v-for="(cf, i) in basics.custom_fields" :key="i">
              <strong>{{ cf.label }}:</strong> {{ cf.value }}
            </span>
          </div>

          <!-- 一句话总结 -->
          <p v-if="basics.summary" class="text-xs text-slate-600 mt-1 leading-relaxed max-w-[420px]">
            {{ basics.summary }}
          </p>
        </div>

        <!-- 中部大姓名 + 右侧证件照 -->
        <div class="header-right flex items-center gap-5 shrink-0">
          <h1 class="text-3xl font-extrabold tracking-wider text-slate-950 font-sans">
            {{ basics.name || '您的姓名' }}
          </h1>

          <!-- 头像照片 -->
          <div class="w-[78px] h-[104px] border border-slate-300 rounded bg-slate-100 overflow-hidden shadow-2xs flex items-center justify-center shrink-0">
            <img
              v-if="basics.photo || basics.avatar"
              :src="basics.photo || basics.avatar"
              class="w-full h-full object-cover"
              alt="证件照"
            />
            <div v-else class="text-center text-slate-300 flex flex-col items-center justify-center h-full p-1">
              <span class="text-2xl">👤</span>
              <span class="text-[9px] scale-90">免冠照</span>
            </div>
          </div>
        </div>
      </header>

      <!-- ================= 2. 教育经历 ================= -->
      <section v-if="education.length && isSectionVisible('education')" class="section mb-4">
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

            <!-- 课程与学业成就 -->
            <ul v-if="edu.highlights?.length || edu.courses?.length" class="mt-1 space-y-0.5 text-xs text-slate-700 list-none pl-0">
              <li v-for="(hl, hli) in (edu.highlights || edu.courses || [])" :key="hli" class="flex items-start gap-1.5 leading-relaxed">
                <span class="text-slate-400 font-bold">•</span>
                <span>{{ hl }}</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- ================= 3. 专业技能 (0ms 实时响应：支持多行长句/编号技能与标签) ================= -->
      <section v-if="parsedSkills.length && isSectionVisible('skills')" class="section mb-4">
        <h2
          class="sec-title text-sm font-extrabold text-slate-900 uppercase tracking-wider mb-2 pb-1 border-b"
          :style="{ borderColor: themeStyles.lineColor }"
        >
          <span>专业技能</span>
        </h2>

        <div class="space-y-1.5 pt-1 text-xs text-slate-800 font-sans leading-relaxed">
          <div v-for="(sk, idx) in parsedSkills" :key="idx" class="skill-row">
            <!-- 纯文本行 -->
            <div v-if="sk.type === 'text'" class="flex items-start gap-1.5">
              <span v-if="!/^(\d+[\.、]|[•\-\*])/.test((sk.text || '').trim())" class="text-slate-400 font-bold">•</span>
              <span class="flex-1" v-html="formatSkillText(sk.text || '')"></span>
            </div>

            <!-- 分组标签行 -->
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

      <!-- ================= 4. 项目经历 ================= -->
      <section v-if="projects.length && isSectionVisible('projects')" class="section mb-4">
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

      <!-- ================= 5. 工作经历 ================= -->
      <section v-if="experience.length && isSectionVisible('experience')" class="section mb-4">
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

      <!-- ================= 6. 个人亮点 ================= -->
      <section v-if="highlights.length && isSectionVisible('highlights')" class="section mb-4">
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

      <!-- ================= 7. 自定义板块 ================= -->
      <section
        v-for="cs in customSections.filter((c: any) => isSectionVisible(c.id) && isSectionVisible('custom_' + c.id))"
        :key="cs.id"
        class="section mb-4"
      >
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
              <span v-if="it.subtitle" class="text-slate-600">{{ it.subtitle }}</span>
              <span v-if="it.date" class="text-slate-500 font-mono text-[11px]">{{ it.date }}</span>
            </div>
            <p v-if="it.description" class="text-slate-600 mt-0.5 leading-relaxed">{{ it.description }}</p>
            <ul v-if="it.highlights?.length" class="mt-1 space-y-0.5 text-slate-700 list-none pl-0">
              <li v-for="(hl, hli) in it.highlights" :key="hli" class="flex items-start gap-1.5">
                <span class="text-slate-400 font-bold">•</span>
                <span>{{ hl }}</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- 空白引导占位 -->
      <div
        v-if="!basics.name && !parsedSkills.length && !projects.length && !experience.length && !education.length"
        class="text-center py-24 text-slate-300 text-xs border border-dashed border-slate-200 rounded my-8"
      >
        左侧编辑表单输入内容，右侧将 0ms 实时以标准 A4 排版呈现
      </div>
    </div>
  </div>
</div>
</template>

<style scoped>
.a4-sheet {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  line-height: 1.5;
}
</style>
