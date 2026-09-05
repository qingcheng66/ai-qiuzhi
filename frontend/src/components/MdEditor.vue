<script setup lang="ts">
import { ref, watch } from 'vue'
import MarkdownPreview from './MarkdownPreview.vue'

const props = defineProps<{ modelValue: string; placeholder?: string; rows?: number }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const value = ref(props.modelValue ?? '')
watch(() => props.modelValue, (v) => (value.value = v ?? ''))
watch(value, (v) => emit('update:modelValue', v))

const previewOn = ref(false)
</script>

<template>
  <div>
    <div class="flex gap-2 mb-1">
      <button
        type="button"
        class="text-xs px-2 py-0.5 rounded bg-slate-100 hover:bg-slate-200"
        :class="previewOn ? 'text-slate-400' : 'text-primary-600'"
        @click="previewOn = false"
      >
        编辑
      </button>
      <button
        type="button"
        class="text-xs px-2 py-0.5 rounded bg-slate-100 hover:bg-slate-200"
        :class="previewOn ? 'text-primary-600' : 'text-slate-400'"
        @click="previewOn = true"
      >
        预览
      </button>
      <span class="text-xs text-slate-400 self-center">支持 Markdown</span>
    </div>
    <textarea
      v-if="!previewOn"
      v-model="value"
      :rows="rows ?? 3"
      :placeholder="placeholder ?? ''"
      class="input font-mono text-xs"
    />
    <div v-else class="border border-slate-200 rounded-lg p-3 min-h-[60px] bg-white">
      <MarkdownPreview :text="value || '*（空内容）*'" />
    </div>
  </div>
</template>