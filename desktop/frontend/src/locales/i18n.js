// i18n配置
import { createI18n } from "vue-i18n"
import zhCn from "./zh-cn"
import en from "./en"

const config = localStorage.getItem('config') ? JSON.parse(localStorage.getItem('config')) : {}

// 创建i18n
const i18n = createI18n({
  // 语言标识
  locale: config.selectedLang ? config.selectedLang.code : 'zhCn',
  // 全局注入,可以直接使用$t
  globalInjection: true,
  // 处理报错: Uncaught (in promise) SyntaxError: Not available in legacy mode (at message-compiler.esm-bundler.js:54:19)
  legacy: false,
  messages: {
    zhCn,
    en
  }
})

export default i18n
