<template>
  <div class="main-content">
    <el-card>
      <template #header>
        <div class="title fxsb">
          <div>基本信息</div>
          <div>
            <el-link type="primary" class="no-select plr-6" @click="clearCache()">清理缓存</el-link>
          </div>
        </div>
      </template>
    </el-card>
  </div>

</template>

<script setup>
import { ref, reactive, inject, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfig } from '@/store/config'
import { useI18n } from 'vue-i18n'

const utils = inject('utils')
const router = useRouter()
const config = useConfig()
const { t } = useI18n()

function clearCache() {
  config.$reset()
  utils.pop(t('clearCacheSuccess'))
}

</script>

<style scoped></style>
