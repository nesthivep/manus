<template>
  <!-- 预览图片列表 -->
  <div class="wp-100" v-if="isImgType" v-for="(file, index) in fileList">
    <div class="center img-container" v-show="file.imgUrl != null">
      <img :src="file.imgUrl" alt="" class="imgSize max-wp-100" />
      <div class="edit" v-show="file.imgUrl != null">
        <el-text tag="label">
          <el-icon :size="32">
            <Edit />
          </el-icon>
          <input type="file" :accept="accept" @change="files.cache(file, $event)" />
        </el-text>
        <el-text tag="label">
          <el-icon :size="32">
            <Delete @click="files.del(fileList, index)" />
          </el-icon>
        </el-text>
      </div>
    </div>
    <div class="wp-100 mlr-auto mt-0-5" v-if="desc">
      <el-input type="textarea" v-model="file.remarkUpd" placeholder="请添加描述" />
    </div>
    <el-divider v-if="index < fileList.length - 1" />
  </div>

  <!-- 预览单个图片 -->
  <div class="wp-100" v-if="isImgType && file != null && file.imgUrl != null">
    <div class="center img-container">
      <img :src="file.imgUrl" alt="" class="imgSize max-wp-100" />
      <div class="edit">
        <el-text tag="label">
          <el-icon :size="32">
            <Edit />
          </el-icon>
          <input type="file" :accept="accept" @change="files.cache(file, $event)" />
        </el-text>
        <el-text tag="label" style="text-align: right;">
          <el-icon :size="32">
            <Delete @click="files.del(file)" />
          </el-icon>
        </el-text>
      </div>
    </div>
    <div class="wp-100 mlr-auto mt-0-5" v-if="desc">
      <el-input type="textarea" v-model="file.remarkUpd" placeholder="请添加描述" />
    </div>
  </div>

  <!-- 预览文件列表 -->
  <div class="file-preview" v-if="isFileType" v-for="(file, index) in fileList">
    <el-text type="primary" class="min-w-360" style="text-align: left;">{{ file.fileName }}</el-text>
    <el-text tag="label" style="text-align: right;">
      <el-icon c:size="16">
        <Delete @click="files.del(fileList, index)" />
      </el-icon>
    </el-text>
  </div>

  <!-- 预览文件 -->
  <div class="file-preview" v-if="isFileType && file != null && file.fileUrl != null">
    <el-text type="primary" class="min-w-360" style="text-align: left;">{{ file.fileName }}</el-text>
    <el-text tag="label">
      <el-icon c:size="16">
        <Delete @click="files.del(file)" />
      </el-icon>
    </el-text>
  </div>

  <!-- 添加文件列表 -->
  <div class="add" v-if="fileList != undefined && fileList != null" :class="isDragover ? 'is-dragover' : ''"
    @dragover.prevent="handleDragOver" @dragleave="handleDragLeave($event)"
    @drop.prevent="handleDrop(fileList, $event)">
    <el-text>点击按钮上传</el-text>
    <el-text tag="label">
      <el-icon :size="32">
        <UploadFilled />
      </el-icon>
      <input type="file" :accept="accept" @change="files.cache(fileList, $event)" />
    </el-text>
    <el-text>或将文件拖动到此处</el-text>
  </div>

  <!-- 添加单个文件 -->
  <div class="add" v-if="file != undefined && file != null && file.fileUrl == null && file.imgUrl == null"
    :class="addCss, isDragover ? 'is-dragover' : ''" @dragover.prevent="handleDragOver"
    @dragleave="handleDragLeave($event)" @drop.prevent="handleDrop(file, $event)">
    <el-text>点击按钮上传</el-text>
    <el-text tag="label">
      <el-icon :size="32">
        <UploadFilled />
      </el-icon>
      <input type="file" :accept="accept" @change="files.cache(file, $event)" />
    </el-text>
    <el-text>或将文件拖动到此处</el-text>
  </div>

</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { Edit, Delete, UploadFilled } from '@element-plus/icons-vue'


const utils = inject('utils')
const files = inject('files')

const props = defineProps(['title', 'file', 'fileList', 'accept', 'type', 'desc', 'w', 'h', 'addCss'])

const title = computed(() => {
  return utils.notNull(props.title) ? props.title : "选择文件"
})

const accept = computed(() => {
  return utils.notNull(props.accept) ? props.accept : "*"
})

const type = computed(() => {
  return utils.notNull(props.type) ? props.type : 'file'
})

const desc = computed(() => {
  return utils.notNull(props.desc) ? props.desc : false
})

const w = computed(() => {
  if (utils.notNull(props.w)) {
    return props.w + 'px'
  }
  return null
})

const h = computed(() => {
  if (utils.notNull(props.h)) {
    return props.h + 'px'
  }
  return null
})

const addCss = computed(() => {
  return utils.notNull(props.addCss) ? props.addCss : ""
})

const isImgType = computed(() => {
  return props.type == 'img'
})

const isFileType = computed(() => {
  return props.type == undefined || props.type == null || props.type == 'file'
})

const isDragover = ref(false)
// 改变样式表示可以放置
// event.target.style.backgroundColor = 'lightblue';
function handleDragOver() {
  console.log("handleDragOver")
  isDragover.value = true
}

function handleDragLeave($event) {
  console.log("handleDragLeave")
  // 防抖处理
  if ($event.currentTarget.contains($event.relatedTarget)) {
    isDragover.value = true
  } else {
    isDragover.value = false
  }
}

function handleDrop(fileObj, $event) {
  console.log("handleDrop:", fileObj)
  isDragover.value = false
  files.cache(fileObj, $event)
}
onMounted(() => {
  console.log("file,fileList:", props.file, props.fileList)
})
</script>

<style scoped>
input[type=file] {
  display: none;
}

.el-text {
  margin-left: 10px;
  margin-right: 10px;
  color: var(--el-text-color);
  background-color: none;
  text-align: center;
  vertical-align: middle;
}

.el-text:hover {
  color: var(--el-color-primary);
}

/* 图片hover按钮-start */
.img-container {
  position: relative;
  display: inline-block;
  min-height: 60px;
  width: 100%;
  /*防止撑开父元素*/
  min-width: 0;
  border-radius: 6px;
}

.img-container i {
  animation: blink 2s infinite;
}

.img-container img {
  margin: 0 auto;
  display: block;
  opacity: 0.7;
  transition: 0.5s ease;
}

.img-container div {
  min-height: 60px;
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

div.add {
  width: 100%;
  min-height: 60px;
  margin: 9px 14px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  display: flex;
  justify-content: center;
  align-items: center;
}

div:hover.add {
  border: 1px dashed var(--el-color-primary);
}

.is-dragover {
  padding: calc(var(--el-upload-dragger-padding-horizontal) - 1px) calc(var(--el-upload-dragger-padding-vertical) - 1px);
  background-color: var(--el-color-primary-light-9);
  border: 2px dashed var(--el-color-primary)
}

div.file-preview {
  display: flex;
  justify-content: space-between !important;
  align-items: center;
  width: 100%;
  border-radius: 6px;
  padding: 0px;
  margin-top: 9px;
  margin-bottom: 9px;
}

div:hover.file-preview {
  background-color: var(--el-color-primary-light-9);
}

i {
  cursor: pointer;
}

textarea {
  height: 30px;
}

.imgSize {
  width: v-bind(w);
  height: v-bind(h);
}
</style>