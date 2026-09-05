<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiSettings } from '@/api'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const error = ref('')
const successMsg = ref('')

const providers = ref<any[]>([])
const currentConfig = ref<any>({
  provider: 'deepseek',
  api_key_masked: '',
  has_key: false,
  base_url: '',
  model: '',
})

// 分类与搜索过滤
const activeCategory = ref<'all' | 'domestic' | 'global' | 'aggregator' | 'local_custom'>('all')
const searchQuery = ref('')

const CATEGORIES = [
  { id: 'all', label: '🌟 全部' },
  { id: 'domestic', label: '🇨🇳 国内主流推荐' },
  { id: 'global', label: '🌍 国际顶尖模型' },
  { id: 'aggregator', label: '🚀 算力聚合平台' },
  { id: 'local_custom', label: '💻 本地私有与自建' },
]

// 表单输入
const selectedProviderId = ref('deepseek')
const inputApiKey = ref('')
const inputBaseUrl = ref('')
const inputModel = ref('')
const showApiKey = ref(false)
const showAdvanced = ref(false)

// 测试状态
const testResult = ref<any>(null)

const activeProviderMeta = computed(() => {
  return providers.value.find((p) => p.id === selectedProviderId.value) || null
})

const filteredProviders = computed(() => {
  let list = providers.value
  if (activeCategory.value !== 'all') {
    list = list.filter((p) => p.category === activeCategory.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.id.toLowerCase().includes(q) ||
        (p.default_model && p.default_model.toLowerCase().includes(q)) ||
        (p.description && p.description.toLowerCase().includes(q))
    )
  }
  return list
})

async function loadSettings() {
  loading.value = true
  error.value = ''
  try {
    const res = await apiSettings.getLlm()
    providers.value = res.providers || []
    currentConfig.value = res.current || {}

    selectedProviderId.value = res.current?.provider || 'deepseek'
    inputApiKey.value = res.current?.api_key_masked || ''
    inputBaseUrl.value = res.current?.base_url || ''
    inputModel.value = res.current?.model || ''
  } catch (e: any) {
    error.value = '加载设置失败：' + e.message
  } finally {
    loading.value = false
  }
}

function handleSelectProvider(provider: any) {
  selectedProviderId.value = provider.id
  // 如果切换了提供商，自动填充该提供商的最佳预设，方便用户只需输入 Key
  if (provider.id !== currentConfig.value.provider) {
    inputBaseUrl.value = provider.default_base_url
    inputModel.value = provider.default_model
    inputApiKey.value = ''
  } else {
    inputBaseUrl.value = currentConfig.value.base_url || provider.default_base_url
    inputModel.value = currentConfig.value.model || provider.default_model
    inputApiKey.value = currentConfig.value.api_key_masked || ''
  }
  testResult.value = null
  successMsg.value = ''
}

async function handleTest() {
  // 本地 Ollama 或自定义可无需必须填写 Key
  if (!inputApiKey.value.trim() && selectedProviderId.value !== 'ollama' && selectedProviderId.value !== 'custom') {
    testResult.value = {
      success: false,
      message: '请先输入该提供商的 API Key，再进行连通性测试！',
    }
    return
  }
  testing.value = true
  testResult.value = null
  try {
    const res = await apiSettings.testLlm({
      provider: selectedProviderId.value,
      api_key: inputApiKey.value.trim(),
      base_url: inputBaseUrl.value.trim() || undefined,
      model: inputModel.value.trim() || undefined,
    })
    testResult.value = res
  } catch (e: any) {
    testResult.value = {
      success: false,
      message: '测试请求异常：' + e.message,
    }
  } finally {
    testing.value = false
  }
}

async function handleSave() {
  saving.value = true
  error.value = ''
  successMsg.value = ''
  try {
    const res = await apiSettings.saveLlm({
      provider: selectedProviderId.value,
      api_key: inputApiKey.value.trim(),
      base_url: inputBaseUrl.value.trim() || undefined,
      model: inputModel.value.trim() || undefined,
    })
    currentConfig.value = res.current || {}
    inputApiKey.value = res.current?.api_key_masked || ''
    successMsg.value = `✓ 大模型配置已成功保存！当前已切换激活「${activeProviderMeta.value?.name || selectedProviderId.value}」，后续所有简历生成、AI 润色与押题即刻生效。`
    setTimeout(() => {
      if (successMsg.value.includes('已成功保存')) successMsg.value = ''
    }, 4000)
  } catch (e: any) {
    error.value = '保存失败：' + e.message
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>

<template>
  <div class="max-w-5xl mx-auto pb-16">
    <!-- 页面标题 -->
    <div class="mb-6">
      <h2 class="text-2xl font-bold text-slate-800 flex items-center gap-2">
        <span>⚙️</span> 大模型引擎与系统设置
      </h2>
      <p class="text-sm text-slate-500 mt-1">
        系统原生支持 <strong>19+ 种主流大模型提供商</strong>（DeepSeek、智谱 GLM、通义千问、Kimi、字节豆包、OpenAI、Gemini、Ollama 等）。只需选定厂商并保存您的 API Key，即可全自动驱动全套 AI 智聘引擎！
      </p>
    </div>

    <!-- 消息横幅 -->
    <div v-if="error" class="mb-4 p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-center justify-between">
      <span>{{ error }}</span>
      <button class="text-xs text-red-500 hover:underline cursor-pointer" @click="error = ''">✕</button>
    </div>

    <div v-if="successMsg" class="mb-4 p-3.5 rounded-xl bg-green-50 border border-green-200 text-green-700 text-sm flex items-center justify-between shadow-xs">
      <span class="font-medium">{{ successMsg }}</span>
      <button class="text-xs text-green-500 hover:underline cursor-pointer" @click="successMsg = ''">✕</button>
    </div>

    <!-- 当前生效模型状态卡片 -->
    <div class="mb-6 p-4.5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-3.5">
        <div class="w-11 h-11 rounded-xl bg-primary-50 flex items-center justify-center text-2xl shadow-2xs">
          {{ activeProviderMeta?.icon || '🤖' }}
        </div>
        <div>
          <div class="flex items-center gap-2">
            <span class="font-bold text-slate-800 text-sm">
              当前生效引擎：{{ providers.find(p => p.id === currentConfig.provider)?.name || currentConfig.provider || '未配置' }}
            </span>
            <span
              class="text-[10px] px-2 py-0.5 rounded-full font-medium"
              :class="currentConfig.has_key ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'"
            >
              {{ currentConfig.has_key ? '● 真实大模型在线' : '○ Mock 兜底演示模式' }}
            </span>
          </div>
          <p class="text-xs text-slate-400 mt-1">
            模型型号：<code class="font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded font-medium">{{ currentConfig.model || '未设定' }}</code> · 
            API Key：<code class="font-mono text-slate-500">{{ currentConfig.api_key_masked || '未设置 (填入 Key 并保存后生效)' }}</code>
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button class="btn-secondary !text-xs !py-1.5 flex items-center gap-1" :disabled="loading" @click="loadSettings">
          <span>🔄</span>
          <span>{{ loading ? '刷新中…' : '刷新状态' }}</span>
        </button>
      </div>
    </div>

    <!-- 主配置面板：选择提供商 & 填入 Key -->
    <div class="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6 mb-6">
      <!-- 步骤 1: 选择模型供应商 -->
      <div>
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
          <label class="font-bold text-sm text-slate-800 flex items-center gap-2">
            <span class="w-5 h-5 rounded-full bg-primary-600 text-white text-xs flex items-center justify-center font-mono">1</span>
            <span>选择您的大模型提供商 (共 {{ providers.length }} 款主流厂商)</span>
          </label>
          <span class="text-xs text-slate-400">点击任意卡片即可一键加载最佳预设</span>
        </div>

        <!-- 分类切换标签与搜索栏 -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3.5 pb-2.5 border-b border-slate-100">
          <div class="flex flex-wrap items-center gap-1 text-xs">
            <button
              v-for="cat in CATEGORIES"
              :key="cat.id"
              class="px-2.5 py-1 rounded-lg transition font-medium cursor-pointer"
              :class="activeCategory === cat.id ? 'bg-primary-600 text-white shadow-2xs font-bold' : 'bg-slate-50 text-slate-600 hover:bg-slate-100'"
              @click="activeCategory = cat.id as any"
            >
              {{ cat.label }}
            </button>
          </div>

          <div class="relative min-w-[180px] sm:max-w-xs">
            <input
              v-model="searchQuery"
              type="text"
              class="w-full pl-7 pr-2.5 py-1 text-xs rounded-lg border border-slate-200 focus:border-primary-500 focus:outline-hidden"
              placeholder="搜索厂商或模型代号…"
            />
            <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-400">🔍</span>
          </div>
        </div>

        <!-- 提供商卡片网格 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[460px] overflow-y-auto pr-1">
          <div
            v-for="p in filteredProviders"
            :key="p.id"
            class="p-3.5 rounded-xl border-2 transition-all cursor-pointer relative flex flex-col justify-between"
            :class="selectedProviderId === p.id
              ? 'border-primary-600 bg-primary-50/20 shadow-xs ring-2 ring-primary-100'
              : 'border-slate-100 bg-slate-50/50 hover:border-slate-300 hover:bg-white'"
            @click="handleSelectProvider(p)"
          >
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-2xl">{{ p.icon }}</span>
                <div class="flex items-center gap-1">
                  <span v-if="p.badge" class="text-[10px] px-1.5 py-0.2 rounded font-medium bg-slate-100 text-slate-600 border border-slate-200">
                    {{ p.badge }}
                  </span>
                  <span v-if="selectedProviderId === p.id" class="text-primary-600 text-xs font-bold">✓ 已选择</span>
                  <span v-else-if="currentConfig.provider === p.id && currentConfig.has_key" class="text-emerald-600 text-[10px] bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200 font-medium">当前在线</span>
                </div>
              </div>
              <h4 class="font-bold text-xs text-slate-900 leading-tight">{{ p.name }}</h4>
              <p class="text-[11px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">{{ p.description }}</p>
            </div>
            
            <div class="mt-2.5 pt-2 border-t border-slate-200/60 text-[10px] text-slate-400 flex items-center justify-between">
              <span>默认模型: <strong class="text-slate-600 font-mono">{{ p.default_model }}</strong></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 步骤 2: 填入 API Key -->
      <div v-if="activeProviderMeta" class="pt-4 border-t border-slate-100">
        <div class="flex items-center justify-between mb-2">
          <label class="font-bold text-sm text-slate-800 flex items-center gap-2">
            <span class="w-5 h-5 rounded-full bg-primary-600 text-white text-xs flex items-center justify-center font-mono">2</span>
            <span>输入 【{{ activeProviderMeta.name }}】 的 API Key</span>
          </label>

          <a
            v-if="activeProviderMeta.docs_url"
            :href="activeProviderMeta.docs_url"
            target="_blank"
            rel="noopener noreferrer"
            class="text-xs text-primary-600 hover:text-primary-700 hover:underline flex items-center gap-1 font-medium"
          >
            <span>👉 访问该平台控制台获取 Key</span>
            <span>↗</span>
          </a>
        </div>

        <div class="relative">
          <input
            v-model="inputApiKey"
            :type="showApiKey ? 'text' : 'password'"
            class="input pr-10 font-mono text-sm"
            :placeholder="activeProviderMeta.key_placeholder || '请粘贴您的 API Key (如 sk-...)'"
          />
          <button
            type="button"
            class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-sm cursor-pointer"
            @click="showApiKey = !showApiKey"
            title="显示/隐藏 Key"
          >
            {{ showApiKey ? '🙈' : '👁️' }}
          </button>
        </div>

        <p class="text-xs text-slate-400 mt-1.5 flex items-center gap-1">
          <span>🔒 安全合规保障：您的 API Key 仅保存在您本地电脑的 SQLite 数据库（<code class="font-mono text-[11px] text-slate-500">ai-qiuzhi.db</code>）中，每次调用均由本机直连模型官方服务器，绝不上报任何外部第三方云端。</span>
        </p>
      </div>

      <!-- 高级自定义参数 (折叠开关) -->
      <div class="pt-3 border-t border-slate-100">
        <button
          class="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1 cursor-pointer select-none"
          @click="showAdvanced = !showAdvanced"
        >
          <span>{{ showAdvanced ? '▾' : '▸' }}</span>
          <span>⚙️ 高级自定义参数 (Base URL 与 Model 标识，通常保持默认即可)</span>
        </button>

        <div v-if="showAdvanced" class="mt-3 p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3.5 animation-fade-in">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">接口 Base URL</label>
              <input
                v-model="inputBaseUrl"
                type="text"
                class="input text-xs font-mono"
                :placeholder="activeProviderMeta?.default_base_url || 'https://api.openai.com/v1'"
              />
              <span class="text-[10px] text-slate-400 mt-1 block">末尾无需写 /chat/completions</span>
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">模型名称代号 (Model)</label>
              <div class="flex gap-2">
                <input
                  v-model="inputModel"
                  type="text"
                  class="input text-xs font-mono flex-1"
                  :placeholder="activeProviderMeta?.default_model || 'deepseek-chat'"
                />
                <select
                  v-if="activeProviderMeta?.available_models?.length"
                  class="select text-xs max-w-[150px]"
                  @change="(e: any) => inputModel = e.target.value"
                >
                  <option value="" disabled selected>选择常见型号</option>
                  <option v-for="m in activeProviderMeta.available_models" :key="m" :value="m">{{ m }}</option>
                </select>
              </div>
              <span class="text-[10px] text-slate-400 mt-1 block">可直接手工输入该平台支持的任意模型代号</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 操作按钮与连通性测试结果 -->
      <div class="pt-4 border-t border-slate-100 space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2.5">
            <!-- 测试按钮 -->
            <button
              class="btn-secondary !text-xs !py-2 flex items-center gap-1.5 font-medium"
              :disabled="testing || saving"
              @click="handleTest"
            >
              <span v-if="testing" class="animate-spin text-primary-500">⏳</span>
              <span v-else>⚡</span>
              <span>{{ testing ? '正在测试连通性…' : '测试连通性' }}</span>
            </button>

            <!-- 保存配置按钮 -->
            <button
              class="btn-primary !text-xs !py-2 px-5 flex items-center gap-1.5 font-bold shadow-xs cursor-pointer"
              :disabled="saving || testing"
              @click="handleSave"
            >
              <span v-if="saving" class="animate-spin">⏳</span>
              <span v-else>💾</span>
              <span>{{ saving ? '正在保存…' : '保存模型配置' }}</span>
            </button>
          </div>

          <span class="text-xs text-slate-400">修改配置后点击保存即可立即热生效，无需重启后端服务。</span>
        </div>

        <!-- 连通性测试结果面板 -->
        <div
          v-if="testResult"
          class="p-4 rounded-xl border text-xs animation-fade-in"
          :class="testResult.success
            ? 'bg-emerald-50/80 border-emerald-300 text-emerald-900'
            : 'bg-red-50/80 border-red-300 text-red-900'"
        >
          <div class="flex items-start gap-2.5">
            <span class="text-base mt-0.5">{{ testResult.success ? '🎉' : '⚠️' }}</span>
            <div class="flex-1 min-w-0">
              <div class="font-bold flex items-center gap-2">
                <span>{{ testResult.success ? '模型接口连接成功！' : '接口连接失败' }}</span>
                <span v-if="testResult.latency_ms" class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-200 text-emerald-800 font-mono">
                  往返延迟: {{ testResult.latency_ms }} ms
                </span>
              </div>
              <p class="mt-1 leading-relaxed">{{ testResult.message }}</p>
              <div v-if="testResult.reply" class="mt-2 p-2 rounded bg-white/70 border border-emerald-200 font-mono text-[11px] text-slate-700">
                模型连通心跳回复片段: "{{ testResult.reply }}"
              </div>
            </div>
            <button class="text-slate-400 hover:text-slate-600 text-sm px-1 cursor-pointer" @click="testResult = null">✕</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 辅助配置说明卡片 (OCR 与 系统运行环境) -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="card p-5">
        <h3 class="font-bold text-sm text-slate-800 mb-2 flex items-center gap-1.5">
          <span>📷</span> 简历与 JD 图片 OCR 配置
        </h3>
        <p class="text-xs text-slate-500 leading-relaxed">
          截图上传 JD 支持通过 PaddleOCR（本地免 Key）或百度/腾讯云 OCR 在线识别。若未配置在线密钥，系统将自动降级为「直接粘贴 JD 文本」，完全不影响核心功能。
        </p>
        <div class="mt-3 pt-2.5 border-t border-slate-100 flex items-center gap-2 text-[11px] text-slate-400">
          <span class="badge bg-slate-100 text-slate-600 font-mono">PaddleOCR 内置就绪</span>
        </div>
      </div>

      <div class="card p-5">
        <h3 class="font-bold text-sm text-slate-800 mb-2 flex items-center gap-1.5">
          <span>ℹ️</span> 关于 ai-qiuzhi 运行环境
        </h3>
        <ul class="text-xs text-slate-500 space-y-1.5">
          <li>• 前端架构：Vue 3 + Tailwind CSS + Vite</li>
          <li>• 后端架构：FastAPI + SQLAlchemy + SQLite</li>
          <li>• 数据文件路径：<code class="bg-slate-100 px-1 py-0.5 rounded font-mono text-[10px]">backend/data/ai-qiuzhi.db</code></li>
          <li>• 离线安全：所有数据与 Key 均在使用者电脑本地保存</li>
        </ul>
      </div>
    </div>
  </div>
</template>
