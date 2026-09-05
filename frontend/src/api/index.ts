import http from './http'

const USER_ID = 1

export interface GenerateResult {
  resume_id: number
  jd_structured: { company: string; title: string; skills_required: string[]; responsibilities: string[]; description_summary: string }
  matches: WikiMatchItem[]
  used_source: string
  resume: any
}

export interface WikiMatchItem {
  source: 'kb' | 'wiki'
  type: string
  name: string
  content: string
  score: number
  meta: any
}

export const apiResume = {
  generate: (jd: string) => http.post<GenerateResult>('/resume/generate', { jd, user_id: USER_ID }).then((r) => r.data),
  get: (id: number) => http.get(`/resume/${id}`).then((r) => r.data),
  update: (id: number, data: any) => http.put(`/resume/${id}`, data).then((r) => r.data),
  export: (id: number, format: 'html' | 'pdf' | 'docx', template_id?: number) => http.post(`/resume/${id}/export`, { format, template_id }, { responseType: 'blob' }).then((r) => r.data),
  list: () => http.get(`/resume/?user_id=${USER_ID}`).then((r) => r.data),
  // 新接口
  createDraft: (data?: any) => http.post('/resume/create-draft', { ...data, user_id: USER_ID }).then((r) => r.data),
  aiGenerate: (id: number, jd: string) => http.post(`/resume/${id}/ai-generate`, { jd }).then((r) => r.data),
  generateReference: (id: number, jd: string, selected_materials: any[] = []) => http.post(`/resume/${id}/generate-reference`, { jd, selected_materials }).then((r) => r.data),
  updateSection: (id: number, section: string, content: any) => http.put(`/resume/${id}/section/${section}`, { content }).then((r) => r.data),
  regenerateSection: (id: number, section: string, jd: string, extra?: any) => http.post(`/resume/${id}/regenerate-section/${section}`, { jd, ...extra }).then((r) => r.data),
  linkPosition: (id: number, positionId: number) => http.post(`/resume/${id}/link-position`, { position_id: positionId }).then((r) => r.data),
  finalize: (id: number, changeLog?: string) => http.post(`/resume/${id}/finalize`, { change_log: changeLog || '定稿' }).then((r) => r.data),
  getByPosition: (positionId: number) => http.get(`/resume/by-position/${positionId}`).then((r) => r.data),
  getVersions: (id: number) => http.get(`/resume/${id}/versions`).then((r) => r.data),
  mockInterview: (id: number) => http.post(`/resume/${id}/mock-interview`).then((r) => r.data),
  getStage: (id: number) => http.get(`/resume/${id}/stage?user_id=${USER_ID}`).then((r) => r.data),
  setStage: (id: number, target_stage: number) => http.post(`/resume/${id}/stage?user_id=${USER_ID}`, { target_stage }).then((r) => r.data),
  remove: (id: number) => http.delete(`/resume/${id}?user_id=${USER_ID}`).then((r) => r.data),
}

export const apiJd = {
  structurize: (text: string) => http.post('/jd/structurize', { text, user_id: USER_ID }).then((r) => r.data),
  match: (skills: string[], job_title = '') => http.post('/wiki/match', { skills, job_title, user_id: USER_ID }).then((r) => r.data),
}

export const apiOcr = {
  parse: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/ocr/parse', fd).then((r) => r.data)
  },
}

export const apiTemplates = {
  list: () => http.get('/templates/?user_id=' + USER_ID).then((r) => r.data),
  create: (data: any) => http.post('/templates/', data).then((r) => r.data),
  update: (id: number, data: any) => http.put(`/templates/${id}`, data).then((r) => r.data),
  remove: (id: number) => http.delete(`/templates/${id}`).then((r) => r.data),
  render: (id: number, content: any) => http.post(`/templates/${id}/render`, { content }).then((r) => r.data),
  importFile: (file: File, name = '') => {
    const fd = new FormData()
    fd.append('file', file)
    if (name) fd.append('name', name)
    return http.post(`/templates/import?user_id=${USER_ID}`, fd).then((r) => r.data)
  },
}

export const apiWorkspace = {
  companies: {
    list: () => http.get('/companies?user_id=' + USER_ID).then((r) => r.data),
    create: (d: any) => http.post('/companies', { ...d, user_id: USER_ID }).then((r) => r.data),
    update: (id: number, d: any) => http.put(`/companies/${id}`, d).then((r) => r.data),
    remove: (id: number) => http.delete(`/companies/${id}`).then((r) => r.data),
  },
  positions: {
    list: (company_id?: number) => http.get(`/positions?user_id=${USER_ID}${company_id ? `&company_id=${company_id}` : ''}`).then((r) => r.data),
    create: (d: any) => http.post('/positions', { ...d, user_id: USER_ID }).then((r) => r.data),
    remove: (id: number) => http.delete(`/positions/${id}`).then((r) => r.data),
  },
  applications: {
    list: () => http.get('/applications?user_id=' + USER_ID).then((r) => r.data),
    create: (d: any) => http.post('/applications', { ...d, user_id: USER_ID }).then((r) => r.data),
    get: (id: number) => http.get(`/applications/${id}`).then((r) => r.data),
    advance: (id: number, target?: number) => http.post(`/applications/${id}/stage`, { target }).then((r) => r.data),
    remove: (id: number) => http.delete(`/applications/${id}`).then((r) => r.data),
  },
  interviews: {
    create: (d: any) => http.post('/interviews', d).then((r) => r.data),
    update: (id: number, d: any) => http.put(`/interviews/${id}`, d).then((r) => r.data),
    remove: (id: number) => http.delete(`/interviews/${id}`).then((r) => r.data),
  },
  stats: () => http.get('/stats?user_id=' + USER_ID).then((r) => r.data),
  stages: () => http.get('/stages/meta').then((r) => r.data),
}

export const apiKb = {
  bundle: () => http.get('/kb/bundle?user_id=' + USER_ID).then((r) => r.data),
  profile: {
    get: () => http.get(`/kb/profile?user_id=${USER_ID}`).then((r) => r.data),
    upsert: (d: any) => http.put('/kb/profile', d, { params: { user_id: USER_ID } }).then((r) => r.data),
  },
  projects: {
    list: () => http.get(`/kb/projects?user_id=${USER_ID}`).then((r) => r.data),
    create: (d: any) => http.post('/kb/projects', d, { params: { user_id: USER_ID } }).then((r) => r.data),
    update: (id: number, d: any) => http.put(`/kb/projects/${id}`, d, { params: { user_id: USER_ID } }).then((r) => r.data),
    remove: (id: number) => http.delete(`/kb/projects/${id}`, { params: { user_id: USER_ID } }).then((r) => r.data),
  },
  skills: {
    list: () => http.get(`/kb/skills?user_id=${USER_ID}`).then((r) => r.data),
    create: (d: any) => http.post('/kb/skills', d, { params: { user_id: USER_ID } }).then((r) => r.data),
    update: (id: number, d: any) => http.put(`/kb/skills/${id}`, d, { params: { user_id: USER_ID } }).then((r) => r.data),
    remove: (id: number) => http.delete(`/kb/skills/${id}`, { params: { user_id: USER_ID } }).then((r) => r.data),
  },
  highlights: {
    list: () => http.get(`/kb/highlights?user_id=${USER_ID}`).then((r) => r.data),
    create: (d: any) => http.post('/kb/highlights', d, { params: { user_id: USER_ID } }).then((r) => r.data),
    update: (id: number, d: any) => http.put(`/kb/highlights/${id}`, d, { params: { user_id: USER_ID } }).then((r) => r.data),
    remove: (id: number) => http.delete(`/kb/highlights/${id}`, { params: { user_id: USER_ID } }).then((r) => r.data),
  },
  experiences: {
    list: () => http.get(`/kb/experiences?user_id=${USER_ID}`).then((r) => r.data),
    create: (d: any) => http.post('/kb/experiences', d, { params: { user_id: USER_ID } }).then((r) => r.data),
    update: (id: number, d: any) => http.put(`/kb/experiences/${id}`, d, { params: { user_id: USER_ID } }).then((r) => r.data),
    remove: (id: number) => http.delete(`/kb/experiences/${id}`, { params: { user_id: USER_ID } }).then((r) => r.data),
  },
  categories: {
    create: (d: any) => http.post('/kb/categories', d, { params: { user_id: USER_ID } }).then((r) => r.data),
    update: (id: number, d: any) => http.put(`/kb/categories/${id}`, d, { params: { user_id: USER_ID } }).then((r) => r.data),
    remove: (id: number) => http.delete(`/kb/categories/${id}`, { params: { user_id: USER_ID } }).then((r) => r.data),
  },
  chunks: {
    create: (categoryId: number, d: any) => http.post(`/kb/categories/${categoryId}/chunks`, d, { params: { user_id: USER_ID } }).then((r) => r.data),
    update: (id: number, d: any) => http.put(`/kb/chunks/${id}`, d, { params: { user_id: USER_ID } }).then((r) => r.data),
    remove: (id: number) => http.delete(`/kb/chunks/${id}`, { params: { user_id: USER_ID } }).then((r) => r.data),
    toggle: (id: number, enabled: boolean) => http.patch(`/kb/chunks/${id}/toggle`, { enabled }, { params: { user_id: USER_ID } }).then((r) => r.data),
  },
  import: (content: string) => http.post('/kb/import', { content, user_id: USER_ID }).then((r) => r.data),
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}