<template>
  <el-container class="layout-container">
    <el-aside width="collapse" class="layout-aside" :class="shrink ? 'shrink' : ''">
      <div :class="menuCollapse ? 'fixed-menu-collapse fxc' : 'fixed-menu-expand fxsb'">
        <div v-show="!menuCollapse" class="menu-logo">
          <el-link type="primary" @click="refresh" class="pl-20 pr-4">
            <img src="@/assets/img/logo-sm.png" class="fxc" height="34px" alt="logo" />
          </el-link>
        </div>
        <el-link class="plr-10 w-56" @click="menuToggle">
          <el-icon :size="20">
            <Fold v-show="!menuCollapse" />
            <Expand v-show="menuCollapse" />
          </el-icon>
        </el-link>
      </div>

      <el-scrollbar class="scrollbar-menu-wrapper" :class="shrink ? 'shrink' : ''">
        <AsideMenu />
      </el-scrollbar>
    </el-aside>
    <el-container>
      <el-header>
        <TopHeader />
      </el-header>
      <el-main>
        <el-scrollbar style="width: 100%;">
          <!-- 路由展示区 -->
          <!-- { Component }指当前路由所对应的组件 -->
          <RouterView v-slot="{ Component }">
            <!-- 添加过渡动画 需要确保插入的component元素只有一个根节点, 否则报错. component中的根元素的transition会覆盖transitionName的样式
             而且需要保证component中根元素的宽度相同所以最好是统一给component添加一个根元素 -->
            <transition :name="transitionName">
              <KeepAlive>
                <Component :is="Component" v-if="keepAlive" :key="$route.path" />
              </KeepAlive>
            </transition>
            <!-- 添加过渡动画 需要确保插入的component元素只有一个根节点 -->
            <transition :name="transitionName">
              <Component :is="Component" v-if="!keepAlive" :key="$route.path" />
            </transition>
          </RouterView>
        </el-scrollbar>
      </el-main>
    </el-container>
    <div class="aside-menu-shade">

    </div>
  </el-container>
</template>

<script setup>
import TopHeader from '@/components/TopHeader.vue'
import AsideMenu from '@/components/AsideMenu.vue'
import { ref, reactive, computed, watch, onBeforeMount } from 'vue'
import { useRouter, RouterView } from 'vue-router'
import { Expand, Fold } from '@element-plus/icons-vue'
import { showShade, closeShade } from '@/assets/js/shade'
import { useConfig } from '@/store/config'
import { useEventListener } from '@vueuse/core'
import { storeToRefs } from 'pinia'

const router = useRouter()
const config = useConfig()

const { shrink, menuCollapse } = storeToRefs(config)
const currentRoute = reactive(router.currentRoute)

// 默认动画效果, 向左滑动
let transitionName = 'slide-left'

const keepAlive = computed(() => {
  return currentRoute.value.meta.keepAlive
})

/** 固定菜单头展开折叠动画时间 刷新页面时菜单不会展开或折叠, 设置持续时间为0, 不产生动画 */
const menuAnimationDuration = ref(0)

// 菜单折叠展开切换
function menuToggle() {
  menuAnimationDuration.value = '300ms'

  if (menuCollapse.value) {
    // console.log("折叠状态下, 进行展开菜单")
    if (shrink.value) {
      // 收缩时, 展开遮罩
      showShade(() => {
        // console.log("这里定义关闭遮罩回调函数, 关闭遮罩后, 折叠菜单")
        config.setMenuCollapse(true)
      })
    }
  } else {
    // console.log("展开状态下, 进行折叠菜单, 关闭掉侧栏遮罩")
    closeShade()
  }
  // 切换菜单折叠状态
  config.setMenuCollapse(!menuCollapse.value)
}

function onAdaptiveLayout() {
  // 获取当前窗口宽度
  const clientWidth = document.body.clientWidth
  // console.log("menuCollapse:", menuCollapse.value, config.getMenuCollapse(), "clientWidth:", clientWidth)
  // 设定aside是否收缩
  if (clientWidth < 800) {
    config.setShrink(true)
    if (!menuCollapse.value) {
      // 展开状态下, 收起菜单
      menuToggle()
    }
  } else {
    config.setShrink(false)
  }
}

onBeforeMount(() => {
  onAdaptiveLayout()
  useEventListener(window, 'resize', onAdaptiveLayout)
})

watch(() => router.currentRoute.value.path, (newValue, oldValue) => {
  // console.log("路由变化,如果是收缩状态,则收起菜单:", newValue, oldValue)
  if (shrink.value && !menuCollapse.value) {
    // console.log("收缩状态下, 且菜单展开时, 收起菜单")
    menuToggle()
  }

})

function refresh() {
  // console.log("刷新页面")
  location.reload()
}

</script>

<style scoped>
.layout-container {
  height: 100vh;
}

header {
  width: 100%;
  height: 44px;
  padding: 0px;
  background-color: var(--el-bg-color);
  display: flex;
  justify-content: center;
  align-items: center;
}

aside {
  background-color: var(--el-fg-color);
}

aside.shrink {
  width: 44px;
}

.layout-aside {
  margin: 0;
  height: 100vh;
  overflow: hidden;
  transition: width .3s ease;
}

main {
  width: 100%;
  padding: 0px;
  overflow: hidden;
}

.menu-logo {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/** 菜单折叠 */
@keyframes menuCollapse {
  0% {
    width: 200px;
  }

  100% {
    width: 44px;
  }
}

/** 菜单展开 */
@keyframes menuExpand {
  0% {
    width: 44px;
  }

  100% {
    width: 200px;
  }
}

.fixed-menu-collapse {
  position: fixed;
  z-index: 9999;
  height: 44px;
  width: 44px;
  /* 引用上面定义的@keyframes名称 */
  animation-name: menuCollapse;
  /* 动画持续时间 */
  animation-duration: v-bind('menuAnimationDuration');
  animation-timing-function: ease-in-out;
  background-color: var(--el-fg-color);
}

.fixed-menu-expand {
  position: fixed;
  z-index: 9999;
  height: 44px;
  width: 200px;
  /* 引用上面定义的@keyframes名称 */
  animation-name: menuExpand;
  /* 动画持续时间 */
  animation-duration: v-bind('menuAnimationDuration');
  animation-timing-function: ease-in-out;
  background-color: var(--el-fg-color);
  z-index: 9999999
}

.scrollbar-menu-wrapper {
  top: 44px;
  height: calc(100vh - 44px);
  background-color: var(--el-fg-color);
}

.scrollbar-menu-wrapper.shrink {
  position: fixed;
  left: 0;
  z-index: 9999999
}
</style>
