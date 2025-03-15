<template>
  <!-- 全局配置 -->
  <el-config-provider :size="size" :z-index="zIndex" :locale="locale" :button="config" :message="config"
    :value-on-clear="null" :empty-values="[undefined, null]">
    <RouterView />
  </el-config-provider>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import en from 'element-plus/es/locale/lang/en'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
/** 暗黑主题 */
import { useDark, useStorage } from '@vueuse/core'

const size = 'default'
const zIndex = 2000

const localConfig = localStorage.getItem('config') ? JSON.parse(localStorage.getItem('config')) : {}

const localeStr = localConfig.selectedLang ? localConfig.selectedLang.code : 'en'
const locale = localeStr == 'en'? en : zhCn

const isDark = useDark()
// 存储用户的喜好
const userPrefersDark = ref(null)
onMounted(() => {

  // 使用 useStorage 钩子来同步 isDark 和本地存储
  useStorage(
    'user-prefers-dark',
    userPrefersDark,
    localStorage,
    isDark.value ? 'dark' : 'light'
  )
})

// 监听 isDark 变化，并更新本地存储
watch(isDark, (newValue) => {
  userPrefersDark.value = newValue ? 'dark' : 'light'
})


/* 全局配置 */
const config = reactive({
  // 按钮-中文字符中间自动插入空格
  autoInsertSpace: true,
  // 消息-可同时显示的消息最大数量
  max: 3,
})
</script>

<style scoped></style>
