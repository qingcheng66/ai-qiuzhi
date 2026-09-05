<script setup lang="ts">
import { ref, computed } from 'vue'

export interface TagItem {
  id: string
  type?: 'name' | 'label' | 'photo' | 'summary' | 'tag' | 'custom'
  key?: string
  label: string
  value: string
  icon: string
  category: 'core' | 'contact' | 'status' | 'profile' | 'social' | 'custom'
  defaultCols: number
  isCustom?: boolean
}

const props = defineProps<{
  resumeData: any
}>()

const emit = defineEmits<{
  (e: 'add-tag', tag: TagItem): void
  (e: 'remove-tag', tag: TagItem): void
}>()

// 预设丰富标签与核心排版组件池 (含推荐 12 栅格默认占据格数)
const PRESET_TAGS: TagItem[] = [
  // 0. 核心排版组件 (可自由拖入网格 / 设尺寸)
  { id: 'core_name', type: 'name', key: 'name', label: '姓名', value: '您的姓名', icon: '👤', category: 'core', defaultCols: 6 },
  { id: 'core_label', type: 'label', key: 'label', label: '求职意向', value: '前端开发工程师', icon: '🎯', category: 'core', defaultCols: 6 },
  { id: 'core_photo', type: 'photo', key: 'photo', label: '免冠证件照', value: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200', icon: '📷', category: 'core', defaultCols: 3 },
  { id: 'core_summary', type: 'summary', key: 'summary', label: '一句话优势总结', value: '5年大厂研发经验，主导核心高并发系统与中后台架构设计。', icon: '✨', category: 'core', defaultCols: 12 },

  // 1. 核心联系
  { id: 'phone', type: 'tag', key: 'phone', label: '联系电话', value: '13800138000', icon: '📞', category: 'contact', defaultCols: 4 },
  { id: 'email', type: 'tag', key: 'email', label: '电子邮箱', value: 'job@example.com', icon: '✉️', category: 'contact', defaultCols: 4 },
  { id: 'wechat', type: 'tag', key: 'wechat', label: '微信号', value: 'wx_hireme', icon: '💬', category: 'contact', defaultCols: 4 },
  { id: 'location', type: 'tag', key: 'location', label: '所在城市', value: '北京 / 上海 / 深圳', icon: '📍', category: 'contact', defaultCols: 4 },

  // 2. 求职状态与预期
  { id: 'status_ready', type: 'tag', key: 'custom', label: '求职状态', value: '离职-随时到岗', icon: '🟢', category: 'status', defaultCols: 4 },
  { id: 'status_look', type: 'tag', key: 'custom', label: '求职状态', value: '在职-月内到岗', icon: '🟡', category: 'status', defaultCols: 4 },
  { id: 'status_grad', type: 'tag', key: 'custom', label: '求职状态', value: '2025届应届毕业生', icon: '🎓', category: 'status', defaultCols: 4 },
  { id: 'exp_years', type: 'tag', key: 'custom', label: '工作年限', value: '5年大厂经验', icon: '💼', category: 'status', defaultCols: 3 },
  { id: 'salary', type: 'tag', key: 'custom', label: '期望薪资', value: '25k-35k · 15薪', icon: '💰', category: 'status', defaultCols: 4 },
  { id: 'target_city', type: 'tag', key: 'custom', label: '期望城市', value: '杭州 / 远程', icon: '🎯', category: 'status', defaultCols: 4 },

  // 3. 个人属性与资历
  { id: 'birthDate', type: 'tag', key: 'birthDate', label: '出生年月', value: '1998/06', icon: '🎂', category: 'profile', defaultCols: 3 },
  { id: 'age', type: 'tag', key: 'custom', label: '年龄', value: '26岁', icon: '📅', category: 'profile', defaultCols: 3 },
  { id: 'education_level', type: 'tag', key: 'custom', label: '最高学历', value: '统招本科 (985/211)', icon: '🏛️', category: 'profile', defaultCols: 4 },
  { id: 'political', type: 'tag', key: 'custom', label: '政治面貌', value: '中共党员', icon: '🚩', category: 'profile', defaultCols: 3 },
  { id: 'english', type: 'tag', key: 'custom', label: '英语等级', value: 'CET-6 (580分) · 流利商务沟通', icon: '🗣️', category: 'profile', defaultCols: 6 },
  { id: 'license', type: 'tag', key: 'custom', label: '资格认证', value: 'PMP 项目管理专业人士', icon: '📜', category: 'profile', defaultCols: 6 },
  { id: 'driver', type: 'tag', key: 'custom', label: '驾照资质', value: 'C1 驾照 (熟练驾驶)', icon: '🚗', category: 'profile', defaultCols: 3 },

  // 4. 主页与作品
  { id: 'github', type: 'tag', key: 'github', label: 'GitHub', value: 'https://github.com/username', icon: '🐙', category: 'social', defaultCols: 6 },
  { id: 'blog', type: 'tag', key: 'blog', label: '技术博客', value: 'https://blog.example.com', icon: '🌐', category: 'social', defaultCols: 6 },
  { id: 'portfolio', type: 'tag', key: 'custom', label: '在线作品集', value: 'https://portfolio.me', icon: '🎨', category: 'social', defaultCols: 6 },
  { id: 'juejin', type: 'tag', key: 'custom', label: '掘金/知乎', value: '掘金 Lv5 优秀作者', icon: '📘', category: 'social', defaultCols: 6 },
]

// 用户自建标签列表 (从 localStorage 恢复)
const LOCAL_CUSTOM_TAGS_KEY = 'ai_qiuzhi_user_created_tags'
const userCustomTags = ref<TagItem[]>([])

try {
  const saved = localStorage.getItem(LOCAL_CUSTOM_TAGS_KEY)
  if (saved) {
    userCustomTags.value = JSON.parse(saved)
  }
} catch (e) {
  // ignore
}

// 标签分类过滤
const activeCategory = ref<'all' | 'core' | 'contact' | 'status' | 'profile' | 'social' | 'custom'>('all')

const allAvailableTags = computed(() => {
  const list = [...PRESET_TAGS, ...userCustomTags.value]
  if (activeCategory.value === 'all') return list
  return list.filter((t) => t.category === activeCategory.value)
})

// 检查某个标签当前是否已经在简历画板上
function isTagOnCanvas(tag: TagItem): boolean {
  const b = props.resumeData?.basics || {}
  const gw: any[] = Array.isArray(b.grid_widgets) ? b.grid_widgets : []
  if (gw.length > 0) {
    return gw.some((w: any) =>
      w.id === tag.id ||
      (tag.key && w.key === tag.key && tag.key !== 'custom') ||
      (tag.type && w.type === tag.type && w.type !== 'tag') ||
      w.label === tag.label
    )
  }

  // 传统兼容性判定
  if (tag.id === 'core_name' || tag.type === 'name') return Boolean(b.name)
  if (tag.id === 'core_label' || tag.type === 'label') return Boolean(b.label || b.title)
  if (tag.id === 'core_photo' || tag.type === 'photo') return Boolean(b.photo || b.avatar)
  if (tag.id === 'core_summary' || tag.type === 'summary') return Boolean(b.summary)
  if (tag.key && ['phone', 'email', 'location', 'birthDate', 'github', 'blog', 'wechat'].includes(tag.key)) {
    return Boolean(b[tag.key])
  }
  const cfs = Array.isArray(b.custom_fields) ? b.custom_fields : []
  return cfs.some((cf: any) => cf.label === tag.label)
}

// 拖拽开始：设置 HTML5 Drag 数据，并携带推荐网格跨度
function onDragStart(e: DragEvent, tag: TagItem) {
  if (!e.dataTransfer) return
  const payload = {
    type: 'grid-widget',
    data: {
      id: tag.id,
      widgetType: tag.type || (tag.category === 'core' ? tag.key : 'tag'),
      key: tag.key || 'custom',
      label: tag.label,
      value: tag.value,
      icon: tag.icon,
      cols: tag.defaultCols || 4,
      category: tag.category,
      isCustom: tag.isCustom,
    },
  }
  e.dataTransfer.setData('application/json', JSON.stringify(payload))
  e.dataTransfer.setData('text/plain', tag.label)
  e.dataTransfer.effectAllowed = 'copy'

  const el = e.target as HTMLElement
  if (el) {
    el.classList.add('opacity-50')
  }
}

function onDragEnd(e: DragEvent) {
  const el = e.target as HTMLElement
  if (el) {
    el.classList.remove('opacity-50')
  }
}

// 点击标签卡片：未上板则上板，已上板则下板
function toggleTag(tag: TagItem) {
  if (isTagOnCanvas(tag)) {
    emit('remove-tag', tag)
  } else {
    emit('add-tag', tag)
  }
}

// 接收从画布拖回素材池下板
const isPaletteDraggingOver = ref(false)

function onPaletteDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
  isPaletteDraggingOver.value = true
}

function onPaletteDragLeave(e: DragEvent) {
  const target = e.currentTarget as HTMLElement
  if (!target.contains(e.relatedTarget as Node)) {
    isPaletteDraggingOver.value = false
  }
}

function onPaletteDrop(e: DragEvent) {
  e.preventDefault()
  isPaletteDraggingOver.value = false
  const raw = e.dataTransfer?.getData('application/json')
  if (!raw) return
  try {
    const payload = JSON.parse(raw)
    if (payload.type === 'inner-chip' && payload.id) {
      emit('remove-tag', { id: payload.id, label: '' } as any)
    } else if (payload.type === 'grid-widget-move' && payload.id) {
      emit('remove-tag', { id: payload.id, label: '' } as any)
    }
  } catch (err) {
    console.error('Failed to drop chip back to palette:', err)
  }
}

// 新建自定义标签表单
const showCreateModal = ref(false)
const newTagForm = ref({
  icon: '🏷️',
  label: '',
  value: '',
})

const EMOJI_PRESETS = ['🏷️', '🎖️', '⭐', '🚀', '💡', '🏆', '🎯', '🚗', '📜', '📱', '💬', '🌐']

function createCustomTag() {
  const label = newTagForm.value.label.trim()
  const val = newTagForm.value.value.trim()
  if (!label) return

  const newTag: TagItem = {
    id: `custom_${Date.now()}`,
    key: 'custom',
    label,
    value: val || `${label}内容`,
    icon: newTagForm.value.icon || '🏷️',
    category: 'custom',
    defaultCols: 4,
    isCustom: true,
  }

  userCustomTags.value.push(newTag)
  try {
    localStorage.setItem(LOCAL_CUSTOM_TAGS_KEY, JSON.stringify(userCustomTags.value))
  } catch (e) {
    // ignore
  }

  newTagForm.value = { icon: '🏷️', label: '', value: '' }
  showCreateModal.value = false
  emit('add-tag', newTag)
}

function deleteUserTag(tagId: string, e: MouseEvent) {
  e.stopPropagation()
  userCustomTags.value = userCustomTags.value.filter((t) => t.id !== tagId)
  try {
    localStorage.setItem(LOCAL_CUSTOM_TAGS_KEY, JSON.stringify(userCustomTags.value))
  } catch (err) {
    // ignore
  }
}
</script>

<template>
  <div
    class="resume-tag-palette relative flex flex-col h-full bg-slate-50 border-r border-slate-200 select-none transition-colors"
    :class="isPaletteDraggingOver ? 'bg-red-50/80 ring-2 ring-dashed ring-red-400' : ''"
    @dragover="onPaletteDragOver"
    @dragleave="onPaletteDragLeave"
    @drop="onPaletteDrop"
  >
    <!-- 拖回下板悬停遮罩提示 -->
    <div
      v-if="isPaletteDraggingOver"
      class="absolute inset-0 bg-red-50/90 backdrop-blur-xs rounded-xl flex items-center justify-center z-30 pointer-events-none border-2 border-dashed border-red-500 animate-pulse"
    >
      <div class="px-4 py-2 bg-white rounded-xl shadow-md border border-red-200 text-red-600 font-bold text-xs flex items-center gap-2">
        <span class="text-base">🗑️</span>
        <span>松开鼠标，将此标签下板移出简历</span>
      </div>
    </div>

    <!-- 头部说明与自建标签入口 -->
    <div class="p-3 border-b border-slate-200 bg-white shrink-0">
      <div class="flex items-center justify-between mb-1.5">
        <span class="text-xs font-bold text-slate-800 flex items-center gap-1.5">
          <span>🏷️</span> 个人信息标签池
        </span>
        <button
          class="text-[11px] font-semibold text-primary-600 bg-primary-50 hover:bg-primary-100 px-2 py-0.5 rounded border border-primary-200 flex items-center gap-1 transition"
          @click="showCreateModal = true"
        >
          <span>➕</span> 自建标签
        </button>
      </div>
      <p class="text-[11px] text-slate-500 leading-tight">
        点击 <span class="text-primary-600 font-semibold">[上板 +]</span> 或直接按住拖入画布；已上板点击 <span class="text-red-500 font-semibold">[下板 ×]</span> 即可移出！
      </p>

      <!-- 分类过滤栏 -->
      <div class="flex items-center gap-1 mt-2.5 overflow-x-auto pb-0.5 no-scrollbar text-[11px]">
        <button
          v-for="cat in [
            { id: 'all', label: '全部' },
            { id: 'core', label: '核心' },
            { id: 'contact', label: '联系' },
            { id: 'status', label: '求职' },
            { id: 'profile', label: '属性' },
            { id: 'social', label: '主页' },
            { id: 'custom', label: '自建' },
          ]"
          :key="cat.id"
          class="px-2 py-0.5 rounded-full border transition whitespace-nowrap shrink-0"
          :class="activeCategory === cat.id ? 'bg-primary-600 text-white border-primary-600 font-bold shadow-2xs' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'"
          @click="activeCategory = cat.id as any"
        >
          {{ cat.label }}
        </button>
      </div>
    </div>

    <!-- 标签卡片列表滚动区 -->
    <div class="flex-1 overflow-y-auto p-2.5 space-y-2">
      <div
        v-for="tag in allAvailableTags"
        :key="tag.id"
        draggable="true"
        class="group relative flex items-center justify-between p-2 rounded-lg border text-xs cursor-grab active:cursor-grabbing transition-all transform hover:-translate-y-0.5 hover:shadow-sm"
        :class="isTagOnCanvas(tag)
          ? 'bg-primary-50/80 border-primary-300 text-primary-950 ring-1 ring-primary-300'
          : 'bg-white border-slate-200 text-slate-700 hover:border-primary-400 hover:bg-slate-50/80'"
        @dragstart="onDragStart($event, tag)"
        @dragend="onDragEnd"
        @click="toggleTag(tag)"
      >
        <div class="flex items-center gap-2 min-w-0 flex-1">
          <span class="text-base shrink-0 select-none">{{ tag.icon }}</span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="font-bold text-slate-800 text-[11px] truncate">{{ tag.label }}</span>
              <!-- 推荐格数标识 -->
              <span class="text-[9px] px-1 py-0.2 rounded font-mono border"
                :class="tag.defaultCols === 12 ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-slate-100 text-slate-500 border-slate-200'"
                title="默认占据 12 栅格中的格数"
              >
                {{ tag.defaultCols === 12 ? '全宽12格' : `${tag.defaultCols}格` }}
              </span>
              <span
                v-if="isTagOnCanvas(tag)"
                class="text-[9px] px-1 py-0.2 rounded bg-primary-100 text-primary-700 font-medium"
              >
                已在板上 ✓
              </span>
            </div>
            <p class="text-[10px] text-slate-400 truncate mt-0.5">{{ tag.value }}</p>
          </div>
        </div>

        <!-- 显式上板 / 下板按钮与拖动手柄 -->
        <div class="flex items-center gap-1.5 shrink-0 ml-1.5" @click.stop>
          <button
            class="text-[11px] px-2 py-0.5 rounded font-semibold transition shadow-2xs"
            :class="isTagOnCanvas(tag)
              ? 'bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 hover:border-red-300'
              : 'bg-primary-50 hover:bg-primary-100 text-primary-700 border border-primary-200 hover:border-primary-300'"
            :title="isTagOnCanvas(tag) ? '点击将此标签下板移出简历' : '点击将此标签上板加入简历'"
            @click="toggleTag(tag)"
          >
            {{ isTagOnCanvas(tag) ? '下板 ×' : '上板 +' }}
          </button>
          <span class="cursor-grab active:cursor-grabbing text-slate-300 group-hover:text-primary-500 text-xs px-0.5 transition" title="按住拖入画布">⠿</span>
          <button
            v-if="tag.isCustom"
            class="text-slate-300 hover:text-red-500 text-xs px-0.5 transition"
            title="删除此自建标签"
            @click="deleteUserTag(tag.id, $event)"
          >
            🗑️
          </button>
        </div>
      </div>
    </div>

    <!-- 新建自定义标签 Modal -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4"
      @click.self="showCreateModal = false"
    >
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-4 space-y-3 border border-slate-100">
        <div class="flex items-center justify-between pb-2 border-b border-slate-100">
          <h4 class="font-bold text-sm text-slate-800 flex items-center gap-1.5">
            <span>✨</span> 创建自定义积木标签
          </h4>
          <button class="text-slate-400 hover:text-slate-600 text-lg leading-none" @click="showCreateModal = false">×</button>
        </div>

        <!-- 图标选择 -->
        <div>
          <label class="text-xs font-semibold text-slate-700 block mb-1">选择图标</label>
          <div class="flex items-center gap-1.5 flex-wrap">
            <button
              v-for="em in EMOJI_PRESETS"
              :key="em"
              class="w-7 h-7 rounded-lg border text-sm flex items-center justify-center transition"
              :class="newTagForm.icon === em ? 'border-primary-500 bg-primary-50 ring-1 ring-primary-300' : 'border-slate-200 hover:bg-slate-50'"
              @click="newTagForm.icon = em"
            >
              {{ em }}
            </button>
          </div>
        </div>

        <!-- 标签名称 -->
        <div>
          <label class="text-xs font-semibold text-slate-700 block mb-1">标签名称 (如: 英语能力、驾照资质、开源成果)</label>
          <input
            v-model="newTagForm.label"
            class="input !text-xs"
            placeholder="如：退伍军人、CET-6、全栈软考"
            autofocus
            @keydown.enter="createCustomTag"
          />
        </div>

        <!-- 标签初始值 -->
        <div>
          <label class="text-xs font-semibold text-slate-700 block mb-1">初始内容 (可拖入画布后在纸上随时修改)</label>
          <input
            v-model="newTagForm.value"
            class="input !text-xs"
            placeholder="如：良好商务英语交流能力"
            @keydown.enter="createCustomTag"
          />
        </div>

        <div class="flex items-center justify-end gap-2 pt-2">
          <button class="btn-secondary !text-xs !py-1" @click="showCreateModal = false">取消</button>
          <button
            class="btn-primary !text-xs !py-1"
            :disabled="!newTagForm.label.trim()"
            @click="createCustomTag"
          >
            创建并上板 ➔
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
