# OpenManus-Desktop 项目

## 项目简介

OpenManus-Desktop 是一个基于Wails框架构建的桌面应用程序，结合了Go后端和Vue3前端技术栈。项目采用Vite作为前端构建工具，提供了高效的开发体验。

## 技术栈

- 后端: Go
- 前端: Vue3 + Vite
- UI 框架: Element Plus
- 状态管理: Pinia
- 路由: Vue Router
- 构建工具: Wails

## 开发环境要求

- Go 1.18+
- Node.js 20+
- Wails CLI v2+

## 快速开始

### 1. 安装开发环境

#### 1.1. 安装Go语言环境

Go环境下载: https://go.dev/dl/

#### 1.2. 安装wails客户端

wails官网: https://wails.io/

    // 中国大陆使用代理
    go env -w GOPROXY=https://goproxy.cn
    go install github.com/wailsapp/wails/v2/cmd/wails@latest

执行以下命名令检查wails客户端安装是否成功:

    wails doctor

#### 1.3. 安装Node.js环境

nodejs官网安装: https://nodejs.org/en

### 2. 安装项目依赖

    cd .\OpenManus-Desktop\frontend
    npm install

### 3. 运行项目

运行项目:

    cd .\OpenManus-Desktop
    wails dev 

启动服务端:

    cd .\OpenManus-front-end
    python app.py

### 4. 打包项目

构建应用:

    wails build

构建好的应用在项目dist目录下




