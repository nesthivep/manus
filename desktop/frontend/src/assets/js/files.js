import utils from '@/assets/js/utils'

// 临时缓存文件信息
function cache(fileObj, $event) {
    console.log('cache fileObj start:', fileObj, $event.target, $event.dataTransfer)
    console.log('typeof fileObj:', Array.isArray(fileObj))
    // 如果fileObj是数组,创建一个新的元素,追加到数组
    // event.target.files和event.dataTransfer.files是JavaScript中与文件上传和拖放相关的事件属性。
    // event.target.files：这个属性是在HTML的文件输入元素（<input type="file">）上使用时，
    // 当用户选择文件并触发change事件时，可以通过event.target.files获取到用户选择的文件列表。
    // event.dataTransfer.files：这个属性是在用户拖放文件到一个元素上时，
    // 可以通过event.dataTransfer.files获取到拖放的文件列表。
    console.log('$event:', $event, $event.type)
    let files
    if ($event.type == 'change') {
        files = $event.target.files
    } else if ($event.type == 'drop') {
        files = $event.dataTransfer.files
    } else {
        console.error("无法识别的事件")
        return
    }
    const file = files[0]
    console.log("file:", file)
    const fileInfo = Array.isArray(fileObj) ? new Object() : fileObj
    fileInfo.file = file
    let URL = window.URL || window.webkitURL
    fileInfo.fileUrl = URL.createObjectURL(file)
    const fileType = file.type
    console.log(fileType, typeof (fileType))
    if (utils.notNull(fileType) && fileType.startsWith("image")) {
        fileInfo.imgUrl = fileInfo.fileUrl
    }
    fileInfo.fileName = file.name
    console.log('cache fileObj end:', fileInfo)
    if (Array.isArray(fileObj)) {
        // 操作成功后追加到数组末尾
        fileObj.push(fileInfo)
    }
    if ($event.type == 'change') {
        // 解决选择相同的文件 不触发change事件的问题,放在最后清理
        $event.target.value = null
    }
}

// 上传文件
async function upload(fileObj) {
    console.log("准备开始上传文件！", fileObj, fileObj.file, fileObj.fileId)
    // 当前地址
    if (utils.isNull(fileObj.file)) {
        if (utils.notNull(fileObj.fileId) && fileObj.remark != fileObj.remarkUpd) {
            let remark = null
            if (utils.notNull(fileObj.remarkUpd)) {
                remark = fileObj.remarkUpd
            }
            await updRemark(fileObj.fileId, remark)
        }
        return
    }
    console.log("开始上传文件！", fileObj, fileObj.file, fileObj.fileId)
    const url = '/common/file/upload'
    const formData = new FormData()
    formData.append('file', fileObj.file)
    if (utils.notNull(fileObj.remark)) {
        formData.append('remark', fileObj.remark)
    } else if (utils.notNull(fileObj.remarkUpd)) {
        formData.append('remark', fileObj.remarkUpd)
    }
    const data = await utils.awaitPost(url, formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
    Object.assign(fileObj, data)
    console.log("文件同步上传处理完毕", fileObj)
    return fileObj
}

// 更新文件备注
async function updRemark(fileId, remarkUpd) {
    const param = {
        fileId: fileId,
        remark: remarkUpd
    }
    await utils.awaitPost('/common/file/updRemark', param)
    console.log("更新文件备注成功")
}

// 批量上传文件
async function uploads(fileObjs) {
    if (utils.isEmpty(fileObjs)) {
        return
    }
    for (let index in fileObjs) {
        console.log('fileObjs[index]:', fileObjs, index, fileObjs.length, fileObjs[index])
        await upload(fileObjs[index])
        console.log("uploads index:", index, "上传文件完毕", fileObjs[index])
    }
}

// 上传文件(onChange时)
function upOnChg(fileObj, $event) {
    const file = $event.target.files[0] || $event.dataTransfer.files[0]
    // 当前地址
    let URL = window.URL || window.webkitURL
    // 转成 blob地址
    fileObj.fileUrl = URL.createObjectURL(file)
    const url = '/common/file/upload'
    const formData = new FormData()
    formData.append('file', file)
    formData.append('remark', fileObj.remark)
    utils.post(url, formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    }).then((data) => {
        console.log("文件上传结果:", data)
        Object.assign(fileObj, data)
        fileObj.remarkUpd = data.remark
    })
}

function add(fileList) {
    const comp = {
        index: fileList.length,
        file: null,
        fileId: null,
        fileName: null,
        fileUrl: null,
        imgUrl: null,
        remark: null
    }
    fileList.push(comp)
}

function del(fileObj, index) {
    console.log("fileObj,index:", fileObj, index)
    if (Array.isArray(fileObj)) {
        fileObj.splice(index, 1)
    } else {
        utils.clearProps(fileObj)
    }
}

function trans(javaFile, jsFile) {
    if (jsFile == undefined || jsFile == null) {
        return
    }
    // 如果是数组，先清空数组
    if (jsFile instanceof Array) {
        jsFile.splice(0, jsFile.length)
    } else {
        utils.clearProps(jsFile)
    }

    if (javaFile == undefined || javaFile == null) {
        return
    }
    // 数组类型
    if (jsFile instanceof Array) {
        for (let java of javaFile) {
            const js = {}
            java.remarkUpd = java.remark
            Object.assign(js, java)
            jsFile.push(js)
        }
    } else {
        // 对象类型
        console.log("对象类型", jsFile instanceof Array)
        javaFile.remarkUpd = javaFile.remark
        Object.assign(jsFile, javaFile)
    }
}

// 从Comps中收集fileId
function fileIds(fileList) {
    return fileList.map(comp => comp.fileId).join(',')
}

export default {

    // onChange时缓存
    cache,
    // 上传文件
    upload,
    // 上传文件
    uploads,
    // 上传文件
    upOnChg,
    // onChange时上传
    upOnChg,
    // 添加到组件列表
    add,
    // 从组件列表中删除组件
    del,
    // 文件Java对象与js对象转换
    trans,
    // 从Comps中收集fileId
    fileIds

}