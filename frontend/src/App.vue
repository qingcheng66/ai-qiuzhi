<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from './stores/app'

const route = useRoute()
const store = useAppStore()

// 全局侧边导航收缩状态
const isSidebarCollapsed = ref(false)

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

onMounted(() => {
  store.loadStages()
})
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-slate-50">
    <!-- 全局左侧导航栏 (支持收起为图标栏) -->
    <aside
      class="bg-white border-r border-slate-200 flex flex-col shrink-0 transition-all duration-300 relative select-none"
      :class="isSidebarCollapsed ? 'w-16' : 'w-56'"
    >
      <!-- Logo 区域 -->
      <div class="p-3.5 border-b border-slate-200 flex items-center gap-3 overflow-hidden">
        <img src="/logo.png" alt="ai-qiuzhi logo" class="w-9 h-9 rounded-xl shadow-xs object-cover shrink-0" />
        <div v-show="!isSidebarCollapsed" class="min-w-0 transition-opacity duration-200">
          <h1 class="text-base font-bold text-slate-900 leading-tight truncate">ai-qiuzhi</h1>
          <p class="text-[11px] text-primary-600 font-medium truncate">AI 智聘求职助手</p>
        </div>
      </div>

      <!-- 导航链接 -->
      <nav class="flex-1 p-2 space-y-1 overflow-y-auto">
        <RouterLink
          to="/generate"
          class="nav-link flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition"
          :class="isSidebarCollapsed ? 'justify-center !px-0' : ''"
          active-class="active"
          :title="isSidebarCollapsed ? '📄 简历生成' : ''"
        >
          <span class="text-base shrink-0">📄</span>
          <span v-show="!isSidebarCollapsed" class="truncate">简历生成</span>
        </RouterLink>

        <RouterLink
          to="/knowledge"
          class="nav-link flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition"
          :class="isSidebarCollapsed ? 'justify-center !px-0' : ''"
          active-class="active"
          :title="isSidebarCollapsed ? '🧠 知识库' : ''"
        >
          <span class="text-base shrink-0">🧠</span>
          <span v-show="!isSidebarCollapsed" class="truncate">知识库</span>
        </RouterLink>

        <RouterLink
          to="/workspace"
          class="nav-link flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition"
          :class="isSidebarCollapsed ? 'justify-center !px-0' : ''"
          active-class="active"
          :title="isSidebarCollapsed ? '💼 求职工作台' : ''"
        >
          <span class="text-base shrink-0">💼</span>
          <span v-show="!isSidebarCollapsed" class="truncate">求职工作台</span>
        </RouterLink>

        <RouterLink
          to="/templates"
          class="nav-link flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition"
          :class="isSidebarCollapsed ? 'justify-center !px-0' : ''"
          active-class="active"
          :title="isSidebarCollapsed ? '🎨 模板管理' : ''"
        >
          <span class="text-base shrink-0">🎨</span>
          <span v-show="!isSidebarCollapsed" class="truncate">模板管理</span>
        </RouterLink>

        <RouterLink
          to="/settings"
          class="nav-link flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition"
          :class="isSidebarCollapsed ? 'justify-center !px-0' : ''"
          active-class="active"
          :title="isSidebarCollapsed ? '⚙️ 设置' : ''"
        >
          <span class="text-base shrink-0">⚙️</span>
          <span v-show="!isSidebarCollapsed" class="truncate">设置</span>
        </RouterLink>
      </nav>

      <!-- 底部用户信息与折叠控制按钮 -->
      <div class="p-2 border-t border-slate-200 flex items-center" :class="isSidebarCollapsed ? 'justify-center' : 'justify-between'">
        <div v-show="!isSidebarCollapsed" class="text-xs text-slate-400 truncate pl-1">
          刘仁晓君
        </div>
        <button
          class="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition text-xs flex items-center gap-1 font-medium"
          :title="isSidebarCollapsed ? '展开全局侧边栏' : '收起全局侧边栏'"
          @click="toggleSidebar"
        >
          <span v-if="isSidebarCollapsed">»</span>
          <span v-else>« 收起侧栏</span>
        </button>
      </div>
    </aside>

    <!-- 主内容 -->
    <main class="flex-1 min-h-0 flex flex-col overflow-y-auto p-3 sm:p-4 transition-all duration-300">
      <RouterView />
    </main>
  </div>
</template>