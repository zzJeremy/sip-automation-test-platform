import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue')
  },
  {
    path: '/suites',
    name: 'Suites',
    component: () => import('../views/SuiteManagement.vue')
  },
  {
    path: '/scenarios',
    name: 'Scenarios',
    component: () => import('../views/ScenarioEditor.vue')
  },
  {
    path: '/executions',
    name: 'Executions',
    component: () => import('../views/ExecutionMonitor.vue')
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('../views/ReportCenter.vue')
  },
  {
    path: '/test-cases',
    name: 'TestCases',
    component: () => import('../views/TestCaseBrowser.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router