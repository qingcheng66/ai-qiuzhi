<script setup lang="ts">
import { ref } from 'vue'

const showTips = ref(true)
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <h2 class="text-2xl font-bold mb-5">设置</h2>

    <div class="card mb-4">
      <h3 class="font-medium mb-3">AI 提供商配置</h3>
      <p class="text-sm text-slate-500 mb-3">
        在 <code class="bg-slate-100 px-1 rounded">backend/.env</code> 中配置 API Key，当前自动加载并缓存客户端，改后需重启后端生效。
      </p>
      <ul class="text-sm space-y-2">
        <li class="flex items-center gap-2">
          <span class="badge bg-slate-100 text-slate-600">DeepSeek</span>
          <code class="text-xs">LLM_PROVIDER=deepseek</code>
          <code class="text-xs text-slate-400">DEEPSEEK_API_KEY=sk-…</code>
        </li>
        <li class="flex items-center gap-2">
          <span class="badge bg-slate-100 text-slate-600">OpenRouter</span>
          <code class="text-xs">LLM_PROVIDER=openrouter</code>
          <code class="text-xs text-slate-400">OPENROUTER_API_KEY=sk-or-…</code>
        </li>
        <li class="flex items-center gap-2">
          <span class="badge bg-amber-50 text-amber-600">Mock 兜底</span>
          <span class="text-xs text-slate-400">未配置任何 key 时，自动使用内置 Mock 生成，全链路可调试</span>
        </li>
      </ul>
    </div>

    <div class="card mb-4">
      <h3 class="font-medium mb-3">OCR 配置</h3>
      <p class="text-sm text-slate-500">
        上传图片解析 JD 需配置百度 OCR 或腾讯 OCR。未配置时自动降级为「粘贴文本」。
        配置项：<code class="bg-slate-100 px-1 rounded">BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY</code> 或
        <code class="bg-slate-100 px-1 rounded">TENCENT_OCR_SECRET_ID / TENCENT_OCR_SECRET_KEY</code>
      </p>
    </div>

    <div class="card">
      <h3 class="font-medium mb-3">关于</h3>
      <ul class="text-sm text-slate-500 space-y-1">
        <li class="badge bg-primary-50 text-primary-600">ai-qiuzhi v1.0</li>
        <li>FastAPI + Vue 3 + SQLite（可切 PostgreSQL）</li>
        <li>内置 10 阶段求职状态机（投递→Offer）</li>
        <li>应用内知识库 + 只读 wiki 缓存双源匹配</li>
        <li>数据存储：<code class="bg-slate-100 px-1 rounded">backend/data/ai-qiuzhi.db</code></li>
      </ul>
    </div>
  </div>
</template>