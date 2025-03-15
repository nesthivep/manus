import utils from '@/assets/js/utils'

/** 英文编码正则 */
const codeReg = /^[A-Za-z0-9_\-\.]+$/

/** 手机号正则 */
const mobileReg = /^1[3456789]\d{9}$/

/** 大陆身份证正则 */
const idNoReg = /^(^[1-9]\d{7}((0\d)|(1[0-2]))(([0|1|2]\d)|3[0-1])\d{3}$)|(^[1-9]\d{5}[1-9]\d{3}((0\d)|(1[0-2]))(([0|1|2]\d)|3[0-1])((\d{4})|\d{3}[Xx])$)$/

/** email正则 */
const emailReg = /^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$/

const commonValidator = (rule, value, callback) => {
  if (utils.isNull(value)) {
    callback()
  } else {
    callback()
  }
}

const notBlankValidator = (rule, value, callback) => {
  if (utils.isBlank(value)) {
    callback(new Error('输入不能为空'))
  } else {
    callback()
  }
}

const nameValidator = (rule, value, callback) => {
  if (utils.isBlank(value)) {
    callback()
  } else if (value.length > 50) {
    callback(new Error('字符数不能超过50'))
  } else {
    callback()
  }
}

const mobileValidator = (rule, value, callback) => {
  if (utils.isNull(value)) {
    callback()
  } else if (!mobileReg.test(value)) {
    callback(new Error('手机号格式错误'))
  } else {
    callback()
  }
}

const idNoValidator = (rule, value, callback) => {
  if (utils.isNull(value)) {
    callback()
  } else if (!idNoReg.test(value)) {
    callback(new Error('手机号格式错误'))
  } else {
    callback()
  }
}

const emailValidator = (rule, value, callback) => {
  if (utils.isNull(value)) {
    callback()
  } else if (!emailReg.test(value)) {
    callback(new Error('手机号格式错误'))
  } else {
    callback()
  }
}

const codeValidator = (rule, value, callback) => {
  if (utils.isBlank(value)) {
    callback()
  } else if (!codeReg.test(value)) {
    callback(new Error('编码格式错误'))
  } else {
    callback()
  }
}

const intValidator = (rule, value, callback) => {
  if (utils.isBlank(value)) {
    callback()
  } else if (!Number.isInteger(value)) {
    callback(new Error('请输入整数'))
  } else {
    callback()
  }
}

function validator() {
  console.log("arguments:", arguments)
  if (arguments.length <= 1) {
    const type = arguments[0]
    // 默认校验逻辑, 不含有特殊字符
    if (utils.isBlank(type)) {
      return commonValidator
    } else if (type == 'notBlank') {
      return notBlankValidator
    } else if (type == 'name') {
      return nameValidator
    } else if (type == 'mobile') {
      return mobileValidator
    } else if (type == 'idNo') {
      return idNoValidator
    } else if (type == 'email') {
      return emailValidator
    } else if (type == 'code') {
      return codeValidator
    } else if (type == 'int') {
      return intValidator
    } else {
      return commonValidator
    }
  }
  // 复合校验器 
  const complexValidator = (rule, value, callback) => {
    for (let i = 0; i < arguments.length; i++) {
      const typeStr = arguments[i]
      if (typeStr == 'notBlank' && utils.isBlank(value)) {
        callback(new Error('输入不能为空'))
        break
      } else if (typeStr == 'code' && !codeReg.test(value)) {
        callback(new Error('编码格式错误'))
        break
      } else if (typeStr == 'int' && Number.isInteger(value)) {
        callback(new Error('请输入整数'))
        break
      }
    }
    // 兜底callback()只会触发一次
    callback()
  }
  return complexValidator
}

export default {

  username: (username) => {
    if (typeof (username) == "undefined" || username == null) {
      return "账号不能为空"
    }
    username = username.trim()
    if (username.length < 4) {
      return "账号字符不能小于4位"
    }
    if (username.length > 20) {
      return "账号字符不能大于20位"
    }
    const reg = /^[A-Za-z0-9]+$/
    if (!reg.test(username)) {
      return "账号为必须为字母和数字"
    }
    return null
  },

  password: (password) => {
    if (typeof (password) == "undefined" || password == null) {
      return "密码不能为空"
    }
    password = password.trim()
    if (password.length < 4) {
      return "密码字符不能小于4位"
    }
    if (password.length > 20) {
      return "密码字符不能大于20位"
    }
    const reg = /^[A-Za-z0-9\.\-\_\+]+$/
    if (!reg.test(password)) {
      return "密码为必须为字母和数字或.-+_"
    }
    return null
  },

  email: (email) => {
    if (typeof (email) == "undefined" || email == null) {
      return "邮箱不能为空"
    }
    const reg = /^[A-Za-z0-9._%-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,4}$/
    if (!reg.test(email)) {
      return "邮箱格式不正确"
    }
    return null
  },

  validCode: (validCode) => {
    if (typeof (validCode) == "undefined" || validCode == null) {
      return "验证码不能为空"
    }
    validCode = validCode.trim()
    if (validCode.length != 6) {
      return "验证码必须为6位"
    }
    const reg = /^[A-Za-z0-9]{6}$/
    if (!reg.test(validCode)) {
      return "验证码格式不正确"
    }
    return null
  },

  validator,


}