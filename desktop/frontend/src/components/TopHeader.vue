<template>
  <!-- 导航栏 -->
  <div class="nav-bar">
    <!-- 左侧固定下拉 -->
    <el-dropdown trigger="click" @command="handleSwitchModel" class="fxc plr-16">
      <span class="el-dropdown-link">
        {{ selectedModel }}
        <el-icon class="el-icon--right">
          <arrow-down />
        </el-icon>
      </span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item v-for="mod in modelList" :key="mod" :command="mod">
            {{ mod }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>

    <!-- 右侧固定下拉 -->
    <el-dropdown trigger="click" @command="handleSwitchLang" class="fxc plr-16">
      <span class="el-dropdown-link">
        {{ selectedLang.name }}
        <el-icon class="el-icon--right">
          <arrow-down />
        </el-icon>
      </span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item v-for="lang in langList" :key="lang" :command="lang">
            {{ lang.name }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { useConfig } from '@/store/config'

const config = useConfig()

const modelList = ref(config.modelList)

const selectedModel = ref(config.selectedModel != null ? config.selectedModel : modelList.value[0])


function handleSwitchModel(mod) {
  // console.log("handleSwitchModel:", model)
  selectedModel.value = mod
}

const langList = ref(config.langList)

const selectedLang = ref(config.selectedLang != null ? config.selectedLang : langList.value[0])

console.log("selectedLang:", selectedLang)

function handleSwitchLang(lang) {
  selectedLang.value = lang
  config.setSelectedLang(lang)
  // i18n.locale = lang.code
  location.reload()
}
</script>

<style scoped>
.nav-bar {
  display: flex;
  height: 44px;
  width: 100%;
  justify-content: space-between;
}

.el-dropdown-link {
  text-align: center;
  cursor: pointer;
  min-width: 80px;
  color: var(--el-color-primary);
  display: flex;
  align-items: center;
  /* 禁止双击选中文字 */
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

.nav-menu {
  height: 100%;
  text-align: left;
  vertical-align: middle;
  display: flex;
  justify-content: start;
  align-items: center;
}

.nav-menu .item {
  width: 50px;
}

.nav-menu .profile {
  width: 100px;
}

.nav-menu .profile img {
  width: 40px;
  height: 30px;
  padding: 0 5px;
}
</style>
