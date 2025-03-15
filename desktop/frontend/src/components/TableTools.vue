<template>
  <div class="fxsb table-tools">
    <div v-show="!advSearch">
      <el-button type="default" @click="baseSearch">
        <el-icon :size="20">
          <Refresh />
        </el-icon>
      </el-button>
      <el-button type="primary" @click="toAddPage" style="vertical-align: middle;">
        <el-icon :size="20" class="pr-4">
          <Plus />
        </el-icon>
        新增
      </el-button>
      <el-button type="danger" class="ml-10" @click="delSelected" :disabled="selectedRows.length == 0">
        <el-icon :size="20" class="pr-4">
          <Delete />
        </el-icon>
        删除
      </el-button>
    </div>
    <div v-show="advSearch">
      <el-button @click="resetSearch">重置</el-button>
      <el-button type="primary" @click="search">查询</el-button>
    </div>
    <div>
      <el-input v-model="searchForm.kw" @input="baseSearch" clearable v-show="!advSearch" class="mr-8" />

      <el-button-group>
        <el-button type="default" @click="advSearchSwitch">
          <el-icon :size="20">
            <Search />
          </el-icon>
        </el-button>
        <el-button type="default">
          <el-dropdown :hide-on-click="false">
            <el-icon :size="20">
              <Grid />
            </el-icon>
            <template #dropdown>
              <el-dropdown-menu class="dropdown-max">
                <el-dropdown-item :command=item.prop v-for="(item, index) in tableColumns" :key="index">
                  <el-checkbox :label="item.label" :value="item.isShow" :checked="item.isShow"
                    @change="checkTableColumn($event, item.prop)" />
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-button>
      </el-button-group>
    </div>
  </div>
</template>

<script setup>
import { Refresh, Search, Grid, Plus, Delete } from '@element-plus/icons-vue'

const props = defineProps({
  advSearch: {
    default: false
  },
  searchForm: {
    default: () => ({
      kw: null
    })
  },
  tableColumns: {
    default: () => []
  },
  selectedRows: {
    default: []
  },
  addable: {
    default: false
  }
})

const emits = defineEmits([
  'search',
  'baseSearch',
  'advSearchSwitch',
  'checkTableColumn',
  'delSelected',
  'resetSearch',
  'toAddPage',
])

const baseSearch = () => {
  console.log('baseSearch')
  emits('baseSearch')
}

const search = () => {
  emits('search')
}

const delSelected = () => {
  emits('delSelected')
}

const advSearchSwitch = () => {
  emits('advSearchSwitch')
}

const checkTableColumn = (isCheck, prop) => {
  console.log('checkTableColumn:', isCheck, prop)
  emits('checkTableColumn', isCheck, prop)
}

const resetSearch = () => {
  emits('resetSearch')
}

const toAddPage = () => {
  emits('toAddPage')
}
</script>

<style scoped>
.table-tools {
  width: 100%;
}
</style>
