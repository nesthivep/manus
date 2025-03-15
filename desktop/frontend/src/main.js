import './assets/css/main.css'

import utils from '@/assets/js/utils'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import files from '@/assets/js/files'
import verify from '@/assets/js/verify'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import i18n from './locales/i18n'

// import ElementPlus from 'element-plus'
import { ElMessage } from 'element-plus'
import 'element-plus/dist/index.css'
/* 暗黑主题模式 */
import 'element-plus/theme-chalk/dark/css-vars.css'
import '@/assets/less/light.css'
import '@/assets/less/dark.css'
// 定义特性标志
window.__VUE_PROD_DEVTOOLS__ = false;
window.__VUE_PROD_HYDRATION_MISMATCH_DETAILS__ = false;

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

const app = createApp(App)

app.use(pinia)

// 全局引用router
app.use(router)

app.use(i18n)

// ElMessage需要在utils中使用,这里单独引入
app.use(ElMessage)

// 全局使用
// ElSelect.props.placeholder.default = '请选择'
// 在引入 ElementPlus 时，可以传入一个包含 size 和 zIndex 属性的全局配置对象。 
// size 用于设置表单组件的默认尺寸，zIndex 用于设置弹出组件的层级，zIndex 的默认值为 2000。
// app.use(ElementPlus, { locale, size: 'default', zIndex: 2000 })

// 使用vue3 provide注册
app.provide('utils', utils)


app.provide('files', files)
app.provide('verify', verify)

/* app.provide('uuid', uuidv4) */

app.mount('#app')

