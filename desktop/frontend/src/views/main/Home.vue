<template>

  <div class="main-content">
    <el-card>
      <template #header>
        <div class="title fxsb">
          <div>基本信息</div>
          <div>
            <el-link type="primary" class="no-select plr-6" @click="createTab()">创建表</el-link>
            <el-link type="primary" class="no-select plr-6" @click="insertData()">插入数据</el-link>
            <el-link type="primary" class="no-select plr-6" @click="select()">查询</el-link>
          </div>
        </div>
      </template>

      <el-form ref="ruleFormRef" :model="request" status-icon :rules="rules">
        <div class="card-row-wrap">

          <div class="card-row-item wp-100">
            <el-text>目标地址:</el-text>
            <div class="fxsb">
              <el-select v-model="request.method" class="w-85 pr-10">
                <el-option v-for="opt in methodOpts" :key="opt.key" :value="opt.value" :label="opt.label" />
              </el-select>
              <el-form-item prop="targetUrl" class="wp-100">
                <el-input autosize v-model="request.targetUrl" class="wp-100" />
              </el-form-item>
            </div>
          </div>

          <div class="card-row-item wp-100">
            <el-text>请求头:</el-text>
            <el-form-item prop="header">
              <el-input type="textarea" :autosize="{ minRows: 2, maxRows: 6 }" v-model="request.header" />
            </el-form-item>
          </div>

          <div class="card-row-item wp-100">
            <el-text>请求参数:</el-text>
            <el-form-item prop="param">
              <el-input type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" v-model="request.param" />
            </el-form-item>
          </div>

          <div class="card-row-item">
            <el-text>分页大小:</el-text>
            <el-form-item prop="pageSize">
              <el-input type="number" v-model="request.pageSize" />
            </el-form-item>
          </div>

          <div class="card-row-item">
            <el-text>分页起始页:</el-text>
            <el-form-item prop="pageNumStart">
              <el-input type="number" v-model="request.pageNumStart" />
            </el-form-item>
          </div>

          <div class="card-row-item">
            <el-text>分页终止页:</el-text>
            <el-form-item prop="pageNumEnd">
              <el-input type="number" v-model="request.pageNumEnd" />
            </el-form-item>
          </div>

          <div class="card-row-aline fxc">
            <el-button class="mlr-10" @click="reset">重置</el-button>
            <el-button type="primary" class="mlr-10" @click="submitForm">发起请求</el-button>
            <el-button type="danger" class="mlr-10" @click="stop">停止</el-button>
          </div>
        </div>
      </el-form>



      <div class="card-row-wrap">
        <div class="card-row-aline">
          <el-input type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" v-model="response.data" />
        </div>
      </div>
    </el-card>
  </div>

</template>

<script setup>
import { ref, reactive, inject, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Upload from '@/components/Upload.vue'

const utils = inject('utils')
const files = inject('files')
const verify = inject('verify')
const router = useRouter()

const methodOpts = reactive([
  { key: "GET", value: "GET", label: "GET" },
  { key: "POST", value: "POST", label: "POST" }
])

// 请求对象
const request = reactive({
  method: 'GET',
  targetUrl: null,
  header: null,
  param: null,
  pageSize: 10,
  pageNumStart: 1,
  pageNumEnd: 100
})

// 响应对象
const response = reactive({
  data: null
})

const submitForm = async () => {
  try {
    await ruleFormRef.value.validate();
    ElMessage.success('验证通过，提交表单')
  } catch (error) {
    ElMessage.error('参数验证失败')
    return
  }
  sendRequest()
}

/**
 * 发起请求
 */
function sendRequest() {
  if (request.method == 'GET') {
    console.log('发起GET请求', request)
    utils.get(request.targetUrl, request.param, request.header).then(data => {
      // 更新响应数据
      console.log('data', data)
      response.data = data
    })
  } else if (request.method == 'POST') {
    utils.get('/sys/role/search').then((data) => {
      console.log('data', data)
    })
  }
}

</script>

<style scoped></style>
