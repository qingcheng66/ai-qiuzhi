import { defineStore } from 'pinia'
import { apiWorkspace } from '@/api'

interface StageMeta {
  stages: string[]
  keys: string[]
  max: number
}

export const useAppStore = defineStore('app', {
  state: () => ({
    stageMeta: { stages: [], keys: [], max: 0 } as StageMeta,
  }),
  actions: {
    async loadStages() {
      if (this.stageMeta.max) return
      try {
        const meta = await apiWorkspace.stages()
        this.stageMeta = meta
      } catch {
        /* ignore */
      }
    },
  },
})