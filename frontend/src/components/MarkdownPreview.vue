<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{ text: string }>()

const html = computed(() => marked(props.text || '', { breaks: true }))
</script>

<template>
  <div class="prose max-w-none text-sm" v-html="html" />
</template>