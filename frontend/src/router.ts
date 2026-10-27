import { createRouter, createWebHashHistory } from 'vue-router'

export default createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/market' },
    { path: '/market', component: () => import('./views/MarketView.vue'), meta: { title: '盯盘' } },
    { path: '/us', component: () => import('./views/UsView.vue'), meta: { title: '美股' } },
    { path: '/review', component: () => import('./views/ReviewView.vue'), meta: { title: '复盘' } },
    { path: '/valuation', component: () => import('./views/ValuationView.vue'), meta: { title: '估值' } },
    { path: '/news', component: () => import('./views/NewsView.vue'), meta: { title: '新闻' } },
    { path: '/profile', component: () => import('./views/ProfileView.vue'), meta: { title: '详情' } },
  ],
})
