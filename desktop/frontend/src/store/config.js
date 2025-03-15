import { defineStore } from "pinia"

export const useConfig = defineStore("config", {
  state: () => {
    return {
      // 全局
      // aside是否收缩
      shrink: false,
      isDark: false,
      // 侧边栏
      // 菜单是否折叠
      menuCollapse: false,
      selectedModel: null,
      modelList: ['qwen2.5-7b', 'deepseek-r1-7b'],
      selectedLang: { code: 'en', name: 'English' },
      langList: [{ code: 'en', name: 'English' }, { code: 'zhCn', name: '简体中文' }],
      taskHistory: [
        // taskId, prompt, stepList, status, createdDt
      ]
    }
  },
  actions: {

    getShrink() {
      return this.shrink
    },
    setShrink(shrink) {
      this.shrink = shrink
    },

    getIsDark() {
      return this.isDark
    },

    getMenuCollapse() {
      return this.menuCollapse
    },

    setMenuCollapse(menuCollapse) {
      this.menuCollapse = menuCollapse
    },

    getSelectedModel() {
      return this.selectedModel
    },

    setSelectedModel(selectedModel) {
      this.selectedModel = selectedModel
    },

    getModelList() {
      return this.modelList
    },

    setModelList(modelList) {
      utils.copyArray(modelList, this.modelList)
    },

    getSelectedLang() {
      return this.selectedLang
    },

    setSelectedLang(selectedLang) {
      this.selectedLang = selectedLang
    },

    getLangList() {
      return this.langList
    },

    getTaskHistory() {
      return this.taskHistory
    },

    setTaskHistory(taskHistory) {
      utils.copyArray(taskHistory, this.taskHistory)
    },

    addTaskHistory(task) {
      // 添加到数组开头
      this.taskHistory.unshift(task)
    },

    // 获取当前, 任务列表中第一个
    getCurrTask() {
      if (this.taskHistory.length == 0) {
        return {}
      }
      return this.taskHistory[0]
    },

  },
  persist: {
    key: "config",
  }
})
