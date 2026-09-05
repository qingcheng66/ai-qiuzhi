<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiWorkspace } from '@/api'

const emit = defineEmits<{
  select: [companyId: number, positionId: number, companyName: string, positionTitle: string]
}>()

const companies = ref<any[]>([])
const positions = ref<any[]>([])
const selectedCompanyId = ref<number | null>(null)
const selectedPositionId = ref<number | null>(null)
const loading = ref(false)
const showNewCompany = ref(false)
const newCompany = ref({ name: '', website: '', industry: '' })
const newPositionTitle = ref('')

async function loadCompanies() {
  loading.value = true
  try {
    companies.value = await apiWorkspace.companies.list()
  } finally {
    loading.value = false
  }
}

async function loadPositions() {
  if (!selectedCompanyId.value) {
    positions.value = []
    return
  }
  positions.value = await apiWorkspace.positions.list(selectedCompanyId.value)
}

async function createCompany() {
  if (!newCompany.value.name.trim()) return
  const c = await apiWorkspace.companies.create(newCompany.value)
  companies.value.push(c)
  selectedCompanyId.value = c.id
  showNewCompany.value = false
  newCompany.value = { name: '', website: '', industry: '' }
  await loadPositions()
}

async function createPosition() {
  if (!selectedCompanyId.value || !newPositionTitle.value.trim()) return
  const p = await apiWorkspace.positions.create({
    company_id: selectedCompanyId.value,
    title: newPositionTitle.value,
    jd_raw: '',
    jd_structured: {},
  })
  positions.value.push(p)
  selectedPositionId.value = p.id
  newPositionTitle.value = ''
}

function confirm() {
  if (!selectedCompanyId.value || !selectedPositionId.value) return
  const co = companies.value.find(c => c.id === selectedCompanyId.value)
  const po = positions.value.find(p => p.id === selectedPositionId.value)
  emit('select', selectedCompanyId.value, selectedPositionId.value, co?.name || '', po?.title || '')
}

onMounted(loadCompanies)
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 gap-4">
      <!-- 选择公司 -->
      <div>
        <label class="label">选择公司</label>
        <div class="flex gap-2">
          <select v-model="selectedCompanyId" class="input flex-1" @change="selectedPositionId = null; loadPositions()">
            <option :value="null" disabled>选择公司</option>
            <option v-for="c in companies" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <button class="btn-secondary !text-xs" @click="showNewCompany = !showNewCompany">新建</button>
        </div>
        <div v-if="showNewCompany" class="mt-2 space-y-2 border border-primary-200 rounded-lg p-3">
          <input v-model="newCompany.name" class="input !text-sm" placeholder="公司名 *" />
          <input v-model="newCompany.website" class="input !text-sm" placeholder="网站" />
          <input v-model="newCompany.industry" class="input !text-sm" placeholder="行业" />
          <div class="flex justify-end gap-2">
            <button class="btn-secondary !text-xs" @click="showNewCompany = false">取消</button>
            <button class="btn-primary !text-xs" @click="createCompany" :disabled="!newCompany.name.trim()">创建</button>
          </div>
        </div>
      </div>

      <!-- 选择岗位 -->
      <div>
        <label class="label">选择岗位</label>
        <div class="flex gap-2">
          <select v-model="selectedPositionId" class="input flex-1" :disabled="!selectedCompanyId">
            <option :value="null" disabled>选择岗位</option>
            <option v-for="p in positions" :key="p.id" :value="p.id">{{ p.title }}</option>
          </select>
          <button class="btn-secondary !text-xs" :disabled="!selectedCompanyId" @click="newPositionTitle = ''">新建</button>
        </div>
        <div v-if="newPositionTitle !== ''" class="mt-2 border border-primary-200 rounded-lg p-3">
          <input v-model="newPositionTitle" class="input !text-sm" placeholder="岗位名称 *" />
          <div class="flex justify-end gap-2 mt-2">
            <button class="btn-secondary !text-xs" @click="newPositionTitle = ''">取消</button>
            <button class="btn-primary !text-xs" @click="createPosition" :disabled="!newPositionTitle.trim()">创建</button>
          </div>
        </div>
      </div>
    </div>

    <div class="mt-4 flex justify-end">
      <button class="btn-primary" :disabled="!selectedCompanyId || !selectedPositionId" @click="confirm">
        确认关联
      </button>
    </div>
  </div>
</template>