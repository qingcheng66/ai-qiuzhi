<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiSettings } from '@/api'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const switching = ref(false)
const error = ref('')
const successMsg = ref('')

const providers = ref<any[]>([])
const savedConfigs = ref<any[]>([])
const currentConfig = ref<any>({
  provider: 'deepseek',
  api_key_masked: '',
  has_key: false,
  base_url: '',
  model: '',
})

// 表单输入 (直接选择厂商 -> 填 Key -> 选择模型)
const selectedProviderId = ref('deepseek')
const inputApiKey = ref('')
const inputBaseUrl = ref('')
const inputModel = ref('deepseek-chat')
const selectedModelPreset = ref('deepseek-chat')
const showApiKey = ref(false)
const showAdvanced = ref(false)

// 测试状态
const testResult = ref<any>(null)

const activeProviderMeta = computed(() => {
  return providers.value.find((p) => p.id === selectedProviderId.value) || null
})

async function loadSettings() {
  loading.value = true
  error.value = ''
  try {
    const res = await apiSettings.getLlm()
    providers.value = res.providers || []
    savedConfigs.value = res.saved_configs || []
    currentConfig.value = res.current || {}

    selectedProviderId.value = res.current?.provider || 'deepseek'
    inputApiKey.value = res.current?.api_key_masked || ''
    inputBaseUrl.value = res.current?.base_url || ''
    inputModel.value = res.current?.model || 'deepseek-chat'
    syncModelPresetWithInput(inputModel.value)
  } catch (e: any) {
    error.value = '加载设置失败：' + e.message
  } finally {
    loading.value = false
  }
}

function syncModelPresetWithInput(modelVal: string) {
  const meta = activeProviderMeta.value
  if (meta && meta.available_models && Array.isArray(meta.available_models)) {
    const match = meta.available_models.find((m: any) => m.id === modelVal)
    if (match) {
      selectedModelPreset.value = match.id
    } else {
      selectedModelPreset.value = '__custom__'
    }
  } else {
    selectedModelPreset.value = '__custom__'
  }
}

function onProviderChange() {
  const meta = activeProviderMeta.value
  if (!meta) return

  // 检查已保存列表里是否有该厂商的配置
  const saved = savedConfigs.value.find((c) => c.provider === meta.id)
  if (saved) {
    inputApiKey.value = saved.api_key_masked || ''
    inputModel.value = saved.model || meta.default_model
    inputBaseUrl.value = meta.default_base_url
  } else if (meta.id === currentConfig.value.provider) {
    inputApiKey.value = currentConfig.value.api_key_masked || ''
    inputModel.value = currentConfig.value.model || meta.default_model
    inputBaseUrl.value = currentConfig.value.base_url || meta.default_base_url
  } else {
    inputApiKey.value = ''
    inputModel.value = meta.default_model
    inputBaseUrl.value = meta.default_base_url
  }

  syncModelPresetWithInput(inputModel.value)
  testResult.value = null
  successMsg.value = ''
}

function selectQuickProvider(providerId: string) {
  selectedProviderId.value = providerId
  onProviderChange()
}

function onModelPresetChange() {
  if (selectedModelPreset.value !== '__custom__') {
    inputModel.value = selectedModelPreset.value
  }
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
    savedConfigs.value = res.saved_configs || []
    inputApiKey.value = res.current?.api_key_masked || ''
    successMsg.value = `✓ 大模型已成功激活！当前已启用「${activeProviderMeta.value?.name || selectedProviderId.value} (${inputModel.value})」，后续所有简历生成、AI 润色与押题即刻生效。`
    setTimeout(() => {
      if (successMsg.value.includes('已成功激活')) successMsg.value = ''
    }, 4000)
  } catch (e: any) {
    error.value = '保存失败：' + e.message
  } finally {
    saving.value = false
  }
}

async function handleQuickSwitch(providerId: string) {
  if (providerId === currentConfig.value.provider) return
  switching.value = true
  error.value = ''
  successMsg.value = ''
  try {
    const res = await apiSettings.switchLlm(providerId)
    currentConfig.value = res.current || {}
    savedConfigs.value = res.saved_configs || []
    selectedProviderId.value = res.current?.provider || providerId
    inputApiKey.value = res.current?.api_key_masked || ''
    inputBaseUrl.value = res.current?.base_url || ''
    inputModel.value = res.current?.model || ''
    syncModelPresetWithInput(inputModel.value)
    successMsg.value = `✓ 已快速热切换至「${providers.value.find(p => p.id === providerId)?.name || providerId}」！`
    setTimeout(() => {
      if (successMsg.value.includes('已快速热切换')) successMsg.value = ''
    }, 3000)
  } catch (e: any) {
    error.value = '切换失败：' + e.message
  } finally {
    switching.value = false
  }
}

onMounted(loadSettings)
</script>

<template>
  <div class="max-w-3xl mx-auto pb-16">
    <!-- 顶部标题 -->
    <div class="mb-6">
      <h2 class="text-2xl font-bold text-slate-800 flex items-center gap-2">
        <span>⚙️</span> 大模型服务配置
      </h2>
      <p class="text-sm text-slate-500 mt-1">
        支持直接切换各主流大模型厂商（DeepSeek、Kimi、通义千问、OpenAI 等）。仅需三步：<strong>选择厂商 ➔ 填写 Key ➔ 选择模型</strong>，即可开始使用！
      </p>
    </div>

    <!-- 消息提示条 -->
    <div v-if="error" class="mb-4 p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-center justify-between">
      <span>{{ error }}</span>
      <button class="text-xs text-red-500 hover:underline cursor-pointer" @click="error = ''">✕</button>
    </div>

    <div v-if="successMsg" class="mb-4 p-3.5 rounded-xl bg-green-50 border border-green-200 text-green-700 text-sm flex items-center justify-between shadow-xs">
      <span class="font-medium">{{ successMsg }}</span>
      <button class="text-xs text-green-500 hover:underline cursor-pointer" @click="successMsg = ''">✕</button>
    </div>

    <!-- 核心模型配置主卡片 (直观一体化 3 步设置) -->
    <div class="bg-white rounded-2xl border border-slate-200 p-6 sm:p-7 shadow-xs space-y-6">
      <!-- 头部：当前状态与切换 -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-primary-50 text-primary-600 flex items-center justify-center text-2xl shadow-2xs">
            {{ activeProviderMeta?.icon || '🤖' }}
          </div>
          <div>
            <h3 class="font-bold text-base text-slate-900">
              配置 AI 引擎
            </h3>
            <p class="text-xs text-slate-400 mt-0.5">选择任意厂商并提供一个 Key，系统将自动桥接全站 AI 简历功能</p>
          </div>
        </div>

        <span
          class="text-xs px-2.5 py-1 rounded-full font-medium shrink-0"
          :class="currentConfig.has_key ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'"
        >
          {{ currentConfig.has_key ? `● 当前生效: ${providers.find(p => p.id === currentConfig.provider)?.name?.split(' ')[0] || currentConfig.provider}` : '○ Mock 模式 (未填 Key)' }}
        </span>
      </div>

      <!-- 步骤 1: 直接选择厂商 -->
      <div>
        <label class="block text-sm font-bold text-slate-800 mb-2 flex items-center justify-between">
          <span class="flex items-center gap-2">
            <span class="w-5 h-5 rounded-full bg-primary-600 text-white text-xs flex items-center justify-center font-mono">1</span>
            <span>选择模型厂商 (Provider)</span>
          </span>
          <span class="text-xs font-normal text-slate-400">已预置 19 款国内外主流厂商</span>
        </label>

        <!-- 厂商下拉选择 -->
        <select
          v-model="selectedProviderId"
          class="select text-sm font-medium w-full py-2.5 bg-slate-50 hover:bg-white focus:bg-white border-slate-200 cursor-pointer"
          @change="onProviderChange"
        >
          <optgroup label="🇨🇳 国内主流大厂">
            <option value="deepseek">🐳 DeepSeek (深度求索) - 高性价比首选</option>
            <option value="moonshot">🌙 月之暗面 Kimi (Moonshot) - 长文本精准解析</option>
            <option value="qwen">☁️ 通义千问 Qwen (阿里云百炼) - 阿里全能大模型</option>
            <option value="zhipu">🔮 智谱清言 GLM (Zhipu AI) - 含免费 glm-4-flash</option>
            <option value="doubao">🥟 字节跳动 豆包 (火山引擎 Ark) - 字节自研高并发</option>
            <option value="qianfan">🐻 百度千帆文心 (Baidu Qianfan) - ERNIE 系列</option>
            <option value="minimax">🐚 MiniMax (海螺 AI) - 自研 MoE 架构</option>
            <option value="lingyi">💡 零一万物 01.AI (李开复 Yi) - 闪电极速推理</option>
            <option value="baichuan">🌊 百川智能 Baichuan - 知识密集增强</option>
            <option value="stepfun">🪐 阶跃星辰 StepFun (跃问) - 万亿参数基座</option>
          </optgroup>
          <optgroup label="🌍 国际主流顶尖">
            <option value="openai">⚡ OpenAI (ChatGPT) - GPT-4o / GPT-4o-mini</option>
            <option value="gemini">✨ Google Gemini - Gemini 2.0 Flash 极速</option>
            <option value="groq">⚡ Groq (LPU 极速推理) - 硬件级高吞吐</option>
            <option value="mistral">🌪️ Mistral AI - 欧洲开源商用旗舰</option>
            <option value="perplexity">🔍 Perplexity AI - 搜索增强模型</option>
          </optgroup>
          <optgroup label="🚀 算力聚合平台">
            <option value="siliconflow">🚀 硅基流动 SiliconFlow - 满血 DeepSeek 直连</option>
            <option value="openrouter">🌐 OpenRouter - 一站式全球网关</option>
          </optgroup>
          <optgroup label="💻 本地与自建">
            <option value="ollama">🦙 Ollama (本地私有化部署) - 免 Key 离线</option>
            <option value="custom">🛠️ 自定义 OpenAI 兼容代理 - OneAPI / vLLM 等</option>
          </optgroup>
        </select>

        <!-- 常用快捷直达胶囊按钮 -->
        <div class="flex flex-wrap items-center gap-1.5 mt-2.5">
          <span class="text-slate-400 text-[11px] mr-1">快捷切换:</span>
          <button
            v-for="quick in ['deepseek', 'moonshot', 'qwen', 'zhipu', 'doubao', 'openai', 'siliconflow', 'ollama']"
            :key="quick"
            type="button"
            class="px-2.5 py-0.5 rounded-lg border text-xs transition cursor-pointer flex items-center gap-1"
            :class="selectedProviderId === quick ? 'bg-primary-50 border-primary-400 text-primary-700 font-bold shadow-2xs' : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'"
            @click="selectQuickProvider(quick)"
          >
            <span>{{ providers.find(p => p.id === quick)?.icon }}</span>
            <span>{{ providers.find(p => p.id === quick)?.name?.split(' ')[0] }}</span>
          </button>
        </div>
      </div>

      <!-- 步骤 2: 填写 API Key -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <label class="block text-sm font-bold text-slate-800 flex items-center gap-2">
            <span class="w-5 h-5 rounded-full bg-primary-600 text-white text-xs flex items-center justify-center font-mono">2</span>
            <span>填写 【{{ activeProviderMeta?.name?.split(' ')[0] || '该厂商' }}】 的 API Key</span>
          </label>

          <a
            v-if="activeProviderMeta?.docs_url"
            :href="activeProviderMeta.docs_url"
            target="_blank"
            rel="noopener noreferrer"
            class="text-xs text-primary-600 hover:text-primary-700 hover:underline flex items-center gap-1 font-medium"
          >
            <span>👉 获取 Key</span>
            <span>↗</span>
          </a>
        </div>

        <div class="relative">
          <input
            v-model="inputApiKey"
            :type="showApiKey ? 'text' : 'password'"
            class="input font-mono text-sm pr-10 py-2.5 bg-slate-50 hover:bg-white focus:bg-white"
            :placeholder="activeProviderMeta?.key_placeholder || '请粘贴您的 API Key (如 sk-...)'"
          />
          <button
            type="button"
            class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-sm cursor-pointer select-none"
            @click="showApiKey = !showApiKey"
            title="查看或隐藏 Key"
          >
            {{ showApiKey ? '🙈' : '👁️' }}
          </button>
        </div>
        <p class="text-[11px] text-slate-400 mt-1.5 flex items-center gap-1">
          <span>🔒 隐私保障：Key 仅保存在本机 SQLite 数据库中，绝不上报任何外部服务器。</span>
        </p>
      </div>

      <!-- 步骤 3: 直接选择具体模型 (Model) -->
      <div>
        <label class="block text-sm font-bold text-slate-800 mb-2 flex items-center gap-2">
          <span class="w-5 h-5 rounded-full bg-primary-600 text-white text-xs flex items-center justify-center font-mono">3</span>
          <span>选择模型型号 (Model)</span>
        </label>

        <div class="space-y-2">
          <!-- 预设常用模型下拉 -->
          <div v-if="activeProviderMeta?.available_models?.length">
            <select
              v-model="selectedModelPreset"
              class="select text-sm font-medium w-full py-2.5 bg-slate-50 hover:bg-white focus:bg-white border-slate-200 cursor-pointer"
              @change="onModelPresetChange"
            >
              <option
                v-for="m in activeProviderMeta.available_models"
                :key="m.id"
                :value="m.id"
              >
                {{ m.label }}
              </option>
              <option value="__custom__">✎ 自定义手动输入模型名称…</option>
            </select>
          </div>

          <!-- 自定义模型名称输入框 -->
          <div v-if="!activeProviderMeta?.available_models?.length || selectedModelPreset === '__custom__'">
            <input
              v-model="inputModel"
              type="text"
              class="input text-sm font-mono py-2 bg-slate-50 hover:bg-white focus:bg-white"
              placeholder="请输入您在该平台想要调用的具体模型代号（如 deepseek-chat）"
            />
          </div>

          <div class="text-[11px] text-slate-400 flex items-center justify-between">
            <span>当前选定调用模型：<strong class="font-mono text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">{{ inputModel || '未设定' }}</strong></span>
            <span class="text-slate-400">{{ activeProviderMeta?.description }}</span>
          </div>
        </div>
      </div>

      <!-- 高级接口 Base URL (折叠) -->
      <div class="pt-2 border-t border-slate-100">
        <button
          type="button"
          class="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 cursor-pointer select-none"
          @click="showAdvanced = !showAdvanced"
        >
          <span>{{ showAdvanced ? '▾' : '▸' }}</span>
          <span>高级设置 (自定义 Base URL: <code class="font-mono text-[10px] text-slate-400">{{ inputBaseUrl || activeProviderMeta?.default_base_url }}</code>)</span>
        </button>

        <div v-if="showAdvanced" class="mt-2.5 p-3.5 rounded-xl bg-slate-50 border border-slate-200 animation-fade-in">
          <label class="block text-xs font-bold text-slate-700 mb-1">接口 Base URL (常规使用官方服务无需修改)</label>
          <input
            v-model="inputBaseUrl"
            type="text"
            class="input text-xs font-mono py-1.5"
            :placeholder="activeProviderMeta?.default_base_url"
          />
          <span class="text-[10px] text-slate-400 mt-1 block">自建内网转发或通过 OneAPI 中转时在此填写。</span>
        </div>
      </div>

      <!-- 底部核心按钮栏 -->
      <div class="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <!-- 测试连通性 -->
          <button
            type="button"
            class="btn-secondary !text-xs !py-2.5 px-4 flex items-center gap-1.5 font-medium"
            :disabled="testing || saving"
            @click="handleTest"
          >
            <span v-if="testing" class="animate-spin text-primary-500">⏳</span>
            <span v-else>⚡</span>
            <span>{{ testing ? '正在测试连通性…' : '测试连通性' }}</span>
          </button>

          <!-- 保存并立即启用 -->
          <button
            type="button"
            class="btn-primary !text-xs !py-2.5 px-6 flex items-center gap-1.5 font-bold shadow-xs cursor-pointer"
            :disabled="saving || testing"
            @click="handleSave"
          >
            <span v-if="saving" class="animate-spin">⏳</span>
            <span v-else>💾</span>
            <span>{{ saving ? '正在保存…' : '保存并开始使用' }}</span>
          </button>
        </div>

        <span class="text-xs text-slate-400">点击保存后即刻热更新生效，无需重启服务。</span>
      </div>

      <!-- 连通性测试结果面板 -->
      <div
        v-if="testResult"
        class="p-4 rounded-xl border text-xs animation-fade-in"
        :class="testResult.success
          ? 'bg-emerald-50/90 border-emerald-300 text-emerald-900'
          : 'bg-red-50/90 border-red-300 text-red-900'"
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
              模型连通心跳回复: "{{ testResult.reply }}"
            </div>
          </div>
          <button class="text-slate-400 hover:text-slate-600 text-sm px-1 cursor-pointer" @click="testResult = null">✕</button>
        </div>
      </div>
    </div>

    <!-- CC-Switch 风格：已配置模型一键热切换栏目 (仅当已配置多个厂商时展示) -->
    <div v-if="savedConfigs.length > 0" class="mt-6 p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
      <div class="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
        <h4 class="font-bold text-sm text-slate-800 flex items-center gap-1.5">
          <span>🔄</span> 快捷切换已配置的模型 (CC-Switch 风格)
        </h4>
        <span class="text-xs text-slate-400">已保存 {{ savedConfigs.length }} 款模型配置，无需重填 Key 即可一键热切换</span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
        <div
          v-for="item in savedConfigs"
          :key="item.provider"
          class="p-3 rounded-xl border flex items-center justify-between transition cursor-pointer"
          :class="item.is_active ? 'bg-primary-50/50 border-primary-500 ring-2 ring-primary-100 shadow-2xs' : 'bg-slate-50/50 border-slate-200 hover:border-slate-300 hover:bg-white'"
          @click="handleQuickSwitch(item.provider)"
        >
          <div class="flex items-center gap-2.5 min-w-0">
            <span class="text-2xl shrink-0">{{ item.icon }}</span>
            <div class="min-w-0">
              <div class="font-bold text-xs text-slate-800 truncate">{{ item.name }}</div>
              <div class="text-[11px] text-slate-400 font-mono truncate">{{ item.model }}</div>
            </div>
          </div>

          <button
            class="text-xs px-2.5 py-1 rounded-lg font-medium shrink-0 ml-2 transition"
            :class="item.is_active ? 'bg-primary-600 text-white font-bold' : 'bg-white border border-slate-200 text-slate-700 hover:bg-primary-50 hover:text-primary-700 hover:border-primary-300'"
          >
            {{ item.is_active ? '使用中 ✓' : '切到此模型' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 辅助运行环境与 OCR 说明 -->
    <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="card p-5">
        <h3 class="font-bold text-sm text-slate-800 mb-2 flex items-center gap-1.5">
          <span>📷</span> 简历与 JD 图片 OCR 说明
        </h3>
        <p class="text-xs text-slate-500 leading-relaxed">
          截图上传 JD 支持通过 PaddleOCR 本地免 Key 离线识别，或配置百度/腾讯 OCR 在线识别。若未配置任何 OCR 密钥，系统将自动降级为「直接粘贴 JD 文本」，核心功能不受任何影响。
        </p>
      </div>

      <div class="card p-5">
        <h3 class="font-bold text-sm text-slate-800 mb-2 flex items-center gap-1.5">
          <span>ℹ️</span> 运行环境与存储说明
        </h3>
        <ul class="text-xs text-slate-500 space-y-1.5">
          <li>• 前后端状态：FastAPI + Vue 3 + SQLite</li>
          <li>• 数据文件：<code class="bg-slate-100 px-1 py-0.5 rounded font-mono text-[10px]">backend/data/ai-qiuzhi.db</code></li>
          <li>• 离线保障：所有模型 API Key 均存储于本机，绝不上报外部云端</li>
        </ul>
      </div>
    </div>
  </div>
</template>
