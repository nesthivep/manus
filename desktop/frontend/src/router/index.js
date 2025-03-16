import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/components/MainFrame.vue'),
      meta: {
        title: "主页"
      },
      // 重定向到默认页面
      redirect: '/task',
      children: [
        {
          path: 'task',
          component: () => import('@/views/main/Task.vue'),
          meta: {
            keepAlive: false,
            title: "任务",
            index: 0
          }
        },
        {
          path: 'history',
          component: () => import('@/views/main/Home.vue'),
          meta: {
            keepAlive: false,
            title: "历史记录",
            index: 0
          }
        },
      ]
    },
    {
      path: '/config',
      component: () => import('@/components/MainFrame.vue'),
      meta: {
        title: "设置"
      },
      children: [
        {
          path: 'general',
          component: () => import('@/views/config/General.vue'),
          meta: {
            keepAlive: false,
            title: "常规设置",
            index: 0
          }
        },
        {
          path: 'llm',
          component: () => import('@/views/config/Llm.vue'),
          meta: {
            keepAlive: false,
            title: "大模型配置",
            index: 0
          }
        },
        {
          path: 'theme',
          component: () => import('@/views/config/Theme.vue'),
          meta: {
            keepAlive: false,
            title: "主题",
            index: 1
          }
        },
      ]
    },
  ]
})

export default router
