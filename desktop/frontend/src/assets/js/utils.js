import axios from "axios"
import { ElMessage } from 'element-plus'
import { Greet } from '@/../wailsjs/go/main/App.js'

/** axios start */
// 创建 axios 实例
const $axios = axios.create({
  baseURL: "api",
  timeout: 12000
})

// 请求拦截器
$axios.interceptors.request.use(
  (config) => {
    config.headers["token"] = ''
    if (config.method == "post" || config.method == "put") {
      delNullProperty(config.data)
      fomateDateProperty(config.data)
    } else if (config.method == "get" || config.method == "delete") {
      delNullProperty(config.params)
      fomateDateProperty(config.params)
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
$axios.interceptors.response.use(
  (response) => {
    //  console.log("response:", response)
    if (response.status == 200) {
      return response.data
    } else {
      pop("请求错误:" + response.status)
    }
  },
  (error) => {
    console.log("error:" + JSON.stringify(error))
    if (error.response == undefined || error.response == null) {
      pop("未知请求错误!")
    } else if (error.response.status == 500) {
      pop("请求后台服务异常,请稍后重试!")
    } else {
      pop("请求错误:" + error)
    }
    return Promise.reject(error)
  }
)

function get(url, param) {
  return $axios.get(url, { params: param })
}

async function awaitGet(url, param) {
  return await $axios.get(url, { params: param })
}

function post(url, param) {
  return $axios.post(url, param)
}

async function awaitPost(url, param) {
  return await $axios.post(url, param)
}

function del(url, param) {
  return $axios.delete(url, { params: param })
}

async function awaitDel(url, param) {
  return await $axios.delete(url, { params: param })
}

/**
 * demo 调用 go 接口
 */
function greet(name) {
  return Greet(name).then(resp => {
    console.log("greet resp:", resp)
    return resp
  })
}

/**
 * 判断对象为空
 */
function isNull(obj) {
  return obj == undefined || obj == null
}

/**
 * 判断对象非空
 */
function notNull(obj) {
  return obj != undefined && obj != null
}

/**
 * 判断空字符串
 */
function isBlank(str) {
  return str == undefined || str == null || /^s*$/.test(str)
}

/**
 * 判断不为空字符串
 */
function notBlank(str) {
  return !isBlank(str)
}

/**
* 判断数组为空
*/
function isEmpty(arr) {
  return arr == undefined || arr == null || (arr instanceof Array && arr.length == 0)
}

/**
 * 判断数组非空
 */
function notEmpty(arr) {
  return arr != undefined && arr != null && arr instanceof Array && arr.length > 0
}

/**
 * 判断对象为true
 */
function isTrue(obj) {
  return obj == true || obj == 'true'
}

/**
 * 判断对象为false
 */
function isFalse(obj) {
  return !isTrue(obj)
}

/** 获取字符串中某字符的个数
* @param {string} str - 要搜索的字符串
* @param {string} char - 要查找的字符
* @returns {number} - 字符在字符串中出现的次数
*/
function getCharCount(str, char) {
  // 使用g表示整个字符串都要匹配
  var regex = new RegExp(char, 'g')
  // match方法可在字符串内检索指定的值，或找到一个或多个正则表达式的匹配
  var result = str.match(regex)
  var count = !result ? 0 : result.length
  return count
}

/**
 * 日期格式化
 * 默认格式为yyyy-MM-dd HH:mm:ss
 */
function dateFormat(date, format) {
  if (date == undefined || date == null || date == '') {
    return date
  }
  if (format == undefined || format == null
    || format == '' || format == 0
    || format == "datetime" || format == 'date_time'
    || format == 'DATE_TIME' || format == 'DATETIME') {
    format = "yyyy-MM-dd HH:mm:ss"
  } else if (format == 'date' || format == 'DATE' || format == 1) {
    format = "yyyy-MM-dd"
  }
  date = new Date(date)
  const Y = date.getFullYear() + '',
    M = date.getMonth() + 1,
    D = date.getDate(),
    H = date.getHours(),
    m = date.getMinutes(),
    s = date.getSeconds()
  return format.replace(/YYYY|yyyy/g, Y)
    .replace(/YY|yy/g, Y.substring(2, 2))
    .replace(/MM/g, (M < 10 ? '0' : '') + M)
    .replace(/dd/g, (D < 10 ? '0' : '') + D)
    .replace(/HH|hh/g, (H < 10 ? '0' : '') + H)
    .replace(/mm/g, (m < 10 ? '0' : '') + m)
    .replace(/ss/g, (s < 10 ? '0' : '') + s)
}

/**
 * 遍历对象中的日期,并进行格式化
 */
function fomateDateProperty(obj) {
  for (let i in obj) {
    //遍历对象中的属性
    if (obj[i] == null) {
      continue
    } else if (obj[i] instanceof Date) {
      // 格式化为yyyy-MM-dd HH:mm:ss
      obj[i] = dateFormat(obj[i])
    } else if (obj[i].constructor === Object) {
      //如果发现该属性的值还是一个对象，再判空后进行迭代调用
      if (Object.keys(obj[i]).length > 0) {
        //判断对象上是否存在属性，如果为空对象则删除
        fomateDateProperty(obj[i])
      }
    } else if (obj[i].constructor === Array) {
      //对象值如果是数组，判断是否为空数组后进入数据遍历判空逻辑
      if (obj[i].length > 0) {
        for (let j = 0; j < obj[i].length; j++) {
          //遍历数组
          fomateDateProperty(obj[i][j])
        }
      }
    }
  }
}


// 遍历删除对象中的空值属性
function delNullProperty(obj) {
  for (let i in obj) {
    //遍历对象中的属性
    if (obj[i] === undefined || obj[i] === null || obj[i] === "") {
      //首先除去常规空数据，用delete关键字
      delete obj[i]
    } else if (obj[i].constructor === Object) {
      //如果发现该属性的值还是一个对象，再判空后进行迭代调用
      if (Object.keys(obj[i]).length === 0) delete obj[i]
      //判断对象上是否存在属性，如果为空对象则删除
      delNullProperty(obj[i])
    } else if (obj[i].constructor === Array) {
      //对象值如果是数组，判断是否为空数组后进入数据遍历判空逻辑
      if (obj[i].length === 0) {
        //如果数组为空则删除
        delete obj[i]
      } else {
        for (let index = 0; index < obj[i].length; index++) {
          //遍历数组
          if (obj[i][index] === undefined || obj[i][index] === null || obj[i][index] === "" || JSON.stringify(obj[i][index]) === "{}") {
            obj[i].splice(index, 1)
            //如果数组值为以上空值则修改数组长度，移除空值下标后续值依次提前
            index--
            //由于数组当前下标内容已经被替换成下一个值，所以计数器需要自减以抵消之后的自增
          }
          if (obj[i].constructor === Object) {
            //如果发现数组值中有对象，则再次进入迭代
            delNullProperty(obj[i])
          }
        }
      }
    }
  }
}

/**
  * 弹出消息框
  * @param msg 消息内容
  * @param type
  */
function pop(msg, type) {
  ElMessage({ message: msg, type: type })
}

function popNoData(data) {
  if (data == undefined || data == null || (data instanceof Array && data.length == 0)) {
    ElMessage("暂无数据!")
  }
}

/**
 * 当前时间字符串
 */
function nowDatetimeStr() {
  const date = new Date()
  const datetimeStr = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  return datetimeStr
}

/**
 * 构建分页
 */
function buildPage(source, target) {
  target.pageNum = source.pageNum
  target.pageSize = source.pageSize
  target.total = source.total
  target.pages = source.pages
  copyArray(source.list, target.list)
}
/**
 * 清空数组
 */
function clearArray(arr) {
  if (arr == undefined || arr == null || arr.length == 0) {
    return
  }
  arr.splice(0, arr.length)
}
/**
 * 清空属性
 */
function clearProps(obj) {
  if (obj == undefined || obj == null) {
    return
  }
  for (let i in obj) {
    obj[i] = null
  }
}

/**
 * 复制对象属性
 */
function copyProps(source, target) {
  if (target == undefined || target == null) {
    target = {}
  }
  if (source == undefined || source == null) {
    source = new Object()
  }
  for (let i in target) {
    target[i] = (source[i] != undefined ? source[i] : null)
  }
}
/**
 * 复制数组
 */
function copyArray(source, target) {
  if (target == undefined || target == null) {
    return
  }
  // 先清空数组
  if (target.length > 0) {
    target.splice(0, target.length)
    /* while (target.length > 0) {
        target.pop()
    } */
  }
  if (source == undefined || source == null) {
    return
  }
  for (let i of source) {
    target.push(i)
  }
}

/**
 * 发生变更的属性
 */
function dfProps(origin, target) {
  if (origin == undefined || origin == null || target == undefined || target == null) {
    return target
  }
  var dfObj = {}
  for (let i in target) {
    if (target[i] != null && target[i] != origin[i]) {
      dfObj[i] = target[i]
    }
  }
  return dfObj
}


/**
 * 是否存在不同属性
 */
function hasDfProps(origin, target) {
  const df = dfProps(origin, target)
  for (let i in df) {
    if (df[i] != null) {
      return true
    }
  }
  return false
}

/**
 * 所有字段为空
 */
function isAllPropsNull(target) {
  if (target == undefined || target == null) {
    return true
  }
  for (let i in target) {
    if (target[i] != null) {
      return false
    }
  }
  return true
}

function colorByLabel(label) {
  if ('ADD' == label) {
    return 'bg-success'
  }
  if ('UPD' == label) {
    return 'bg-primary'
  }
  if ('DEL' == label) {
    return 'bg-danger'
  }
  if ('step' == label) {
    return 'bg-primary'
  }
  if ('log' == label) {
    return 'bg-success'
  }
  if ('tool' == label) {
    return 'bg-primary'
  }
  if ('think' == label) {
    return 'bg-danger'
  }
  if ('run' == label) {
    return 'bg-success'
  }
  if ('message' == label) {
    return 'bg-success'
  }
  if ('act' == label) {
    return 'bg-danger'
  }


}

function descByLabel(label) {
  if ('ADD' == label) {
    return '新增'
  }
  if ('UPD' == label) {
    return '更新'
  }
  if ('DEL' == label) {
    return '删除'
  }
  return label
}

/**
 * 重试调用
 */
function retry(method) {
  const params = []
  for (var i = 1; i < arguments.length; i++) {
    params.push(arguments[i])
  }
  setTimeout(() => {
    method(params)
  }, 500)
}

/**
 * 根据opts编码匹配中文
 */
function resolveLabelFromOpts(keyOrVal, opts) {
  if (isEmpty(opts)) {
    return keyOrVal
  }
  for (let opt of opts) {
    if (opt.key == keyOrVal || opt.value == keyOrVal) {
      return opt.label
    }
  }
  return keyOrVal
}

/** 下划线转首字母小写驼峰 */
function underScoreToCamelCase(underscore) {
  if (isNull(underscore) || !underscore.includes('_')) {
    return underscore
  }
  const words = underscore.split('_')
  for (let i = 1; i < words.length; i++) {
    if (words[i] == "") {
      words[i] = ""
      continue
    }
    words[i] = words[i].substring(0, 1).toUpperCase() + words[i].substring(1, words[i].length)
  }
  return words.join("")
}

/** 防抖函数 */
function debounce(func, delay) {
  let timer
  return function () {
    const context = this
    const args = arguments

    clearTimeout(timer)
    timer = setTimeout(() => {
      func.apply(context, args)
    }, delay)
  }
}

export default {
  /**
   * http请求 GET请求
   */
  get,

  /**
   * http请求, 异步等待 GET请求
   */
  awaitGet,

  /**
   * http请求 POST请求
   */
  post,

  /**
   * http请求, 异步等待 POST请求
   */
  awaitPost,

  /**
   * http请求 DELETE请求
   */
  del,

  /**
   * http请求, 异步等待 DELETE请求
   */
  awaitDel,

  /**
   * 判断对象为空
   */
  isNull,

  /**
   * 判断对象非空
   */
  notNull,

  isBlank,

  notBlank,

  /**
   * 判断数组为空
   */
  isEmpty,

  /**
   * 判断数组非空
   */
  notEmpty,

  isTrue,

  isFalse,

  getCharCount,

  /**
   * 弹出消息提示
   */
  pop,

  /**
   * 判定数据是否为空, 如果为空则提示暂无数据
   */
  popNoData,

  /**
   * 遍历删除对象中的空值属性
   */
  delNullProperty,

  /**
   * 
   * 当前时间字符串
   */
  nowDatetimeStr,

  /**
   * 构建分页
   */
  buildPage,

  /**
   * 清空数组
   */
  clearArray,

  /**
   * 清空属性
   */
  clearProps,

  /**
   * 复制对象属性
   */
  copyProps,

  /**
   * 复制数组
   */
  copyArray,

  /**
   * 日期格式化
   * 默认格式为yyyy-MM-dd HH:mm:ss
   */
  dateFormat,

  /**
   * 遍历对象中的日期,并进行格式化
   */
  fomateDateProperty,

  /**
   * 发生变更的属性
   */
  dfProps,

  hasDfProps,

  isAllPropsNull,

  colorByLabel,

  descByLabel,

  /**
   * 重试调用
   */
  retry,

  resolveLabelFromOpts,

  underScoreToCamelCase,

  debounce,

}