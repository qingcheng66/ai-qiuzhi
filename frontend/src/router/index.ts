import { createRouter, createWebHistory } from 'vue-router'

import GenerateResume from '../views/GenerateResume.vue'
import KnowledgeBase from '../views/KnowledgeBase.vue'
import Workspace from '../views/Workspace.vue'
import CompanyDetail from '../views/CompanyDetail.vue'
import PositionDetail from '../views/PositionDetail.vue'
import Templates from '../views/Templates.vue'
import Settings from '../views/Settings.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/generate' },
    { path: '/generate', name: 'generate', component: GenerateResume, meta: { title: '简历生成' } },
    { path: '/knowledge', name: 'knowledge', component: KnowledgeBase, meta: { title: '知识库' } },
    { path: '/workspace', name: 'workspace', component: Workspace, meta: { title: '工作台' } },
    { path: '/companies/:id', name: 'company', component: CompanyDetail, meta: { title: '公司详情' } },
    { path: '/positions/:id', name: 'position', component: PositionDetail, meta: { title: '岗位详情' } },
    { path: '/templates', name: 'templates', component: Templates, meta: { title: '模板' } },
    { path: '/settings', name: 'settings', component: Settings, meta: { title: '设置' } },
  ],
})

export default router