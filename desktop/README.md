# OpenManus-Desktop Project

## Project Overview

OpenManus-Desktop is a desktop application built on the Wails framework, combining Go backend and Vue3 frontend technologies. The project utilizes Vite as the frontend build tool, offering an efficient development experience.

## Technology Stack

- Backend: Go
- Frontend: Vue3 + Vite
- UI Framework: Element Plus
- State Management: Pinia
- Routing: Vue Router
- Build Tool: Wails

## Development Environment Requirements

- Go 1.18+
- Node.js 20+
- Wails CLI v2+

## Getting Started

### 1. Install Development Environment

#### 1.1. Install Golang Environment

Golang environment : https://go.dev/dl/

#### 1.2. Install Wails Client

wails: https://wails.io/

    // For users in mainland China, use a proxy
    go env -w GOPROXY=https://goproxy.cn
    go install github.com/wailsapp/wails/v2/cmd/wails@latest

Run the following command to check if the Wails client is installed successfully:

    wails doctor

#### 1.3. Install Node.js Environment

nodejs: https://nodejs.org/en

### 2. Install Project Dependencies

    cd .\desktop\frontend
    npm install

### 3. Run the Project

To run the project:

    cd .\desktop
    wails dev 

To start the backend service:

    cd .\OpenManus-front-end
    python app.py

### 4. Package the Project

To build the application:

    wails build

The built application will be located in the project’s dist directory.




