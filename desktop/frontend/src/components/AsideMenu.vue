<template>
  <el-menu class="el-menu-custom" :default-active="activeMenu()" :collapse="menuCollapse" @open="handleOpen"
    @close="handleClose">

    <el-menu-item index="M02" @click="routeTo('/task')">
      <el-icon>
        <List />
      </el-icon>
      <span>{{ getMenuNameByCode('M02') }}</span>
    </el-menu-item>

    <el-menu-item index="M03" @click="routeTo('/history')">
      <el-icon>
        <Clock />
      </el-icon>
      <span>{{ getMenuNameByCode('M03') }}</span>
    </el-menu-item>

    <el-sub-menu index="M99" v-if="hasMenuPerm('M99')">
      <template #title>
        <el-icon>
          <setting />
        </el-icon>
        <span>{{ getMenuNameByCode('M99') }}</span>
      </template>
      <el-menu-item v-if="listSubMenu('M99') != null" v-for="secMenu in listSubMenu('M99')" :index="secMenu.index"
        @click="routeTo(secMenu.href)">
        {{ secMenu.menuName }}
      </el-menu-item>
    </el-sub-menu>
  </el-menu>
</template>

<script setup>
import { ChatDotRound, List, Clock, Setting } from '@element-plus/icons-vue'
import { ref, inject, onMounted, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useConfig } from '@/store/config'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'

const utils = inject('utils')
const { t } = useI18n()
const router = useRouter()
const config = useConfig()
const { menuCollapse } = storeToRefs(config)

const handleOpen = (key, keyPath) => {
  // console.log(key, keyPath)
}
const handleClose = (key, keyPath) => {
  // console.log(key, keyPath)
}

// 菜单
const menuList = [
  {
    index: "M02",
    menuName: "menu.task",
    href: "/task"
  },
  {
    index: "M03",
    menuName: "menu.history",
    href: "/history"
  },
  {
    index: "M99",
    menuName: "menu.config.settings",
    href: null,
    subMenuList: [
      {
        index: "M9901",
        menuName: "menu.config.general",
        href: "/config/general"
      },
      {
        index: "M9902",
        menuName: "menu.config.llm",
        href: "/config/llm"
      },
      {
        index: "M9903",
        menuName: "menu.config.theme",
        href: "/config/theme"
      }
    ]
  },
]

onMounted(() => {
  // 页面刷新后,检查菜单定位
  // activeMenu()
})

function hasMenuPerm(menuCode) {
  return menuList.some(menuLv1 => menuLv1.index == menuCode)
}

function listSubMenu(menuCode) {
  const matchedMenu = menuList.find(menuLv1 => menuLv1.index == menuCode)
  if (matchedMenu != null) {
    return matchedMenu.subMenuList
  }
  return null
}

watch(() => router.currentRoute.value.path, (newValue, oldValue) => {
  // console.log('LeftMenu侦听到router.currentRoute.value.path发生更新', newValue, oldValue)
  // 路由发生变更后,检查菜单定位
  activeMenu()
})

// 检查激活的菜单
function activeMenu() {
  const currRoute = router.currentRoute
  const path = currRoute.value.path
  // console.log("currRoute path:", path)
  let index = getIndexByPath(path)
  // console.log("index:", index)
  if (utils.notNull(index)) {
    return index
  }
  return "1"
}

// 根据路径查询菜单index
function getIndexByPath(path) {
  for (let fstMenu of menuList) {
    // console.log(fstMenu.index, fstMenu.href == path)
    if (fstMenu.href == path) {
      // console.log("完整1级菜单匹配上")
      return fstMenu.index
    }
    const secMenuList = fstMenu.subMenuList
    if (utils.notEmpty(secMenuList)) {
      for (let secMenu of secMenuList) {
        // console.log(secMenu.index, secMenu.href == path)
        if (secMenu.href == path) {
          return secMenu.index
        }
        const thdMenuList = secMenu.subMenuList
        if (utils.notEmpty(thdMenuList)) {
          for (let thdMenu of thdMenuList) {
            if (thdMenu.href == path) {
              return thdMenu.index
            }
          }
          // 三级菜单path都没匹配上,取路由配置中的to进行匹配
          for (let thdMenu of thdMenuList) {
            const nodeList = routeMap.get(path)
            if (utils.isEmpty(nodeList)) {
              continue
            }
            for (let node of nodeList) {
              if (node.to == thdMenu.href) {
                // console.log("匹配上node.to:", node.to)
                return thdMenu.index
              }
            }
          }
        }
      }
      // 二级菜单都没匹配上,取路由配置中的to进行匹配
      for (let secMenu of secMenuList) {
        // console.log(secMenu.index, secMenu.href == path)
        const nodeList = routeMap.get(path)
        if (utils.isEmpty(nodeList)) {
          continue
        }
        for (let node of nodeList) {
          if (node.to == secMenu.href) {
            // console.log("匹配上node.to:", node.to)
            return secMenu.index
          }
        }
      }
    }
    // 一级菜单都没匹配上,取路由配置中的to进行匹配

  }
}

// 获取routes配置
const routes = router.options.routes;
// console.log("routes:", routes)
const routeMap = new Map()
routes.forEach(lv1 => {
  // console.log("lv1:", lv1)
  buildRoutePer(lv1)
})
// console.log(routeMap)

function buildRoutePer(lv1) {
  const lv2List = lv1.children
  if (utils.isEmpty(lv2List)) {
    const node1 = {
      title: lv1.meta.title
    }
    const nodeList = [node1]
    routeMap.set(lv1.path, nodeList)
    return
  }
  lv2List.forEach(lv2 => {
    // console.log("lv2:", lv2)
    const node1 = {
      title: lv1.meta.title
    }
    const node2 = {
      title: lv2.meta.title
    }
    const nodeList = [node1, node2]
    if (utils.notNull(lv2.meta.subTitle)) {
      const node3 = {
        title: lv2.meta.subTitle,
        to: null
      }
      nodeList.push(node3)
    }
    routeMap.set(lv1.path + '/' + lv2.path, nodeList)
  })
}

function routeTo(href) {
  if (href == undefined || href == null || href == '') {
    return
  }
  router.push(href)
}

function getMenuNameByCode(code) {
  for (let menu of menuList) {
    if (menu.index == code) {
      return t(menu.menuName)
    }
    if (menu.subMenuList != null) {
      for (let subMenu of menu.subMenuList) {
        if (subMenu.index == code) {
          return t(subMenu.menuName)
        }
      }
    }
  }
  return code
}



</script>

<style scoped>
span {
  /* 防止双击选中 */
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

span {
  /* 字体大小 */
  font-size: 16px;
}

li {
  /* 字体大小 */
  font-size: 15px;
}

/** 菜单折叠时hover菜单项高度这里必须再定义一次 */
.el-menu-item {
  min-width: 44px;
  height: 36px;
  line-height: 36px;
}

.el-menu-custom {
  border-right: none;
  --el-menu-item-height: 40px;
  --el-menu-sub-item-height: 36px;
  padding-top: 10px;
  padding-bottom: 10px;
}

.el-menu-custom .el-menu--collapse {
  width: 44px;
}

.el-menu-custom:not(.el-menu--collapse) {
  width: 200px;
}
</style>
