document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const logMessages = document.getElementById('log-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const clearButton = document.getElementById('clear-btn');
    const stopButton = document.getElementById('stop-btn');
    const statusIndicator = document.getElementById('status-indicator');
    
    let currentWebSocket = null;
    let currentSessionId = null;
    let processingRequest = false;
    
    // 初始状态设置
    stopButton.disabled = true;
    
    // 获取或创建思考步骤区域
    let thinkingStepsContainer = document.getElementById('thinking-steps');
    if (!thinkingStepsContainer) {
        // 如果不存在，创建思考步骤容器
        thinkingStepsContainer = document.createElement('div');
        thinkingStepsContainer.id = 'thinking-steps';
        thinkingStepsContainer.className = 'thinking-steps';
        logMessages.appendChild(thinkingStepsContainer);
    }
    
    // 文件查看器相关元素
    const fileViewer = document.getElementById('file-viewer');
    const fileViewerTitle = document.getElementById('file-viewer-title');
    const fileContent = document.getElementById('file-content');
    const closeFileViewer = document.getElementById('close-file-viewer');
    const filesList = document.getElementById('files-list');
    
    // 隐藏文件查看器（初始状态）
    if (fileViewer) {
        fileViewer.style.display = 'none';
    }
    
    // 关闭文件查看器
    if (closeFileViewer) {
        closeFileViewer.addEventListener('click', function() {
            fileViewer.style.display = 'none';
        });
    }
    
    // 发送消息按钮点击事件
    sendButton.addEventListener('click', sendMessage);
    
    // 文本框按下Enter键事件（Shift+Enter为换行）
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // 清除对话按钮点击事件
    clearButton.addEventListener('click', function() {
        chatMessages.innerHTML = '';
        logMessages.innerHTML = '';
        
        // 重新创建思考步骤容器
        thinkingStepsContainer = document.createElement('div');
        thinkingStepsContainer.id = 'thinking-steps';
        thinkingStepsContainer.className = 'thinking-steps';
        logMessages.appendChild(thinkingStepsContainer);
        
        statusIndicator.textContent = '';
        statusIndicator.className = 'status-indicator';
        
        // 清空文件列表
        if (filesList) {
            filesList.innerHTML = '';
        }
        
        // 隐藏文件查看器
        if (fileViewer) {
            fileViewer.style.display = 'none';
        }

        // 清空终端输出
        const terminalContent = document.getElementById('terminal-content');
        if (terminalContent) {
            terminalContent.innerHTML = '';
        }
    });
    
    // 停止按钮点击事件
    stopButton.addEventListener('click', async function() {
        if (currentSessionId) {
            try {
                const response = await fetch(`/api/chat/${currentSessionId}/stop`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    addLog('处理已停止', 'warning');
                }
            } catch (error) {
                console.error('停止请求错误:', error);
            }
            
            if (currentWebSocket) {
                currentWebSocket.close();
                currentWebSocket = null;
            }
            
            statusIndicator.textContent = '请求已停止';
            statusIndicator.className = 'status-indicator warning';
            sendButton.disabled = false;
            stopButton.disabled = true;
            processingRequest = false;
        }
    });
    
    // 发送消息处理函数
    async function sendMessage() {
        const prompt = userInput.value.trim();
        
        if (!prompt || processingRequest) return;
        
        processingRequest = true;
        
        // 添加用户消息到聊天区域
        addMessage(prompt, 'user');
        
        // 清空输入框
        userInput.value = '';
        
        // 禁用发送按钮，启用停止按钮
        sendButton.disabled = true;
        stopButton.disabled = false;
        statusIndicator.textContent = '正在处理您的请求...';
        statusIndicator.className = 'status-indicator processing';
        
        try {
            // 发送API请求创建会话
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ prompt })
            });
            
            if (!response.ok) {
                throw new Error('网络请求失败');
            }
            
            const data = await response.json();
            currentSessionId = data.session_id;
            
            // 先尝试WebSocket连接，出错时自动降级到轮询
            try {
                connectWebSocket(currentSessionId);
            } catch (wsError) {
                console.warn('WebSocket连接失败，降级到轮询模式', wsError);
                // WebSocket失败时不报错，仅记录日志
            }
            
            // 同时定期轮询获取最终结果
            pollResults(currentSessionId);
            
        } catch (error) {
            console.error('Error:', error);
            statusIndicator.textContent = '发生错误: ' + error.message;
            statusIndicator.className = 'status-indicator error';
            sendButton.disabled = false;
            stopButton.disabled = true;
            processingRequest = false;
        }
    }
    
    // 通过WebSocket连接接收实时更新
    function connectWebSocket(sessionId) {
        try {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
            const wsUrl = `${wsProtocol}://${window.location.host}/ws/${sessionId}`;
            const ws = new WebSocket(wsUrl);
            currentWebSocket = ws;
            
            // 定义全局变量以跟踪系统日志消息
            window.lastSystemLogMessage = null;
            window.lastSystemLogTimestamp = 0;
            
            ws.onopen = function() {
                console.log('WebSocket连接已建立');
                statusIndicator.textContent = '已连接到服务器...';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                // 单独处理聊天日志和系统日志
                if (data.chat_logs && data.chat_logs.length > 0) {
                    console.log('收到聊天日志消息:', data.chat_logs.length);
                    // 将日志显示为聊天消息
                    addSystemLogsToChat(data.chat_logs);
                }
                else if (data.system_logs && data.system_logs.length > 0) {
                    console.log('收到系统日志消息:', data.system_logs.length);
                    // 更新系统日志面板
                    updateSystemLogs(data.system_logs);
                    
                    // 同时将系统日志添加到对话窗口
                    addSystemLogsToChat(data.system_logs);
                }
                
                // 更新思考步骤
                if (data.thinking_steps && data.thinking_steps.length > 0) {
                    updateThinkingSteps(data.thinking_steps);
                }
                
                // 更新终端输出
                if (data.terminal_output && data.terminal_output.length > 0) {
                    updateTerminalOutput(data.terminal_output);
                }
                
                // 更新请求状态
                if (data.status && data.status !== 'processing') {
                    processingRequest = false;
                    statusIndicator.textContent = data.status === 'completed' ? '' : `状态: ${data.status}`;
                    statusIndicator.className = `status-indicator ${data.status}`;
                    sendButton.disabled = false;
                    stopButton.disabled = true;
                }
                
                // 显示结果，如果有的话
                if (data.result && !chatContainsResult(data.result)) {
                    addMessage(data.result, 'ai');
                }
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket错误:', error);
                statusIndicator.textContent = '使用轮询模式获取结果...';
                // WebSocket出错，但不影响用户体验，依赖轮询获取结果
            };
            
            ws.onclose = function() {
                console.log('WebSocket连接已关闭');
                currentWebSocket = null;
            };
            
            return ws;
        } catch (error) {
            console.error('创建WebSocket连接失败:', error);
            throw error;
        }
    }
    
    // 轮询API获取结果
    async function pollResults(sessionId) {
        let attempts = 0;
        const maxAttempts = 60; // 最多尝试60次，大约5分钟
        
        const poll = async () => {
            if (attempts >= maxAttempts || !processingRequest) {
                if (attempts >= maxAttempts) {
                    statusIndicator.textContent = '请求超时';
                    statusIndicator.className = 'status-indicator error';
                }
                sendButton.disabled = false;
                stopButton.disabled = true;
                processingRequest = false;
                return;
            }
            
            try {
                const response = await fetch(`/api/chat/${sessionId}`);
                if (!response.ok) {
                    throw new Error('获取结果失败');
                }
                
                const data = await response.json();
                
                if (data.status === 'completed') {
                    if (data.result && !chatContainsResult(data.result)) {
                        addMessage(data.result, 'ai');
                    }
                    statusIndicator.textContent = '';
                    sendButton.disabled = false;
                    stopButton.disabled = true;
                    processingRequest = false;
                    return;
                } else if (data.status === 'error') {
                    statusIndicator.textContent = '处理请求时发生错误';
                    statusIndicator.className = 'status-indicator error';
                    sendButton.disabled = false;
                    stopButton.disabled = true;
                    processingRequest = false;
                    return;
                } else if (data.status === 'stopped') {
                    statusIndicator.textContent = '处理已停止';
                    statusIndicator.className = 'status-indicator warning';
                    sendButton.disabled = false;
                    stopButton.disabled = true;
                    processingRequest = false;
                    return;
                }
                
                // 更新日志
                if (data.log && data.log.length > 0) {
                    updateLog(data.log);
                }
                
                // 如果还在处理中，继续轮询
                attempts++;
                setTimeout(poll, 3000);
                
                // 轮询终端输出
                try {
                    const terminalResponse = await fetch(`/api/terminal/${sessionId}`);
                    if (terminalResponse.ok) {
                        const terminalData = await terminalResponse.json();
                        if (terminalData.terminal_output && terminalData.terminal_output.length > 0) {
                            updateTerminalOutput(terminalData.terminal_output);
                        }
                    }
                } catch (terminalError) {
                    console.error('获取终端输出错误:', terminalError);
                }
                
            } catch (error) {
                console.error('轮询错误:', error);
                attempts++;
                setTimeout(poll, 3000);
            }
        };
        
        // 开始轮询
        setTimeout(poll, 3000);

        // 添加轮询进度信息的功能
        const pollProgress = async () => {
            if (!processingRequest) return;
            
            try {
                const response = await fetch(`/api/progress/${sessionId}`);
                if (response.ok) {
                    const data = await response.json();
                    updateProgressBar(data.percentage, data.current_step);
                }
                
                if (processingRequest) {
                    setTimeout(pollProgress, 1000); // 每秒更新一次进度
                }
            } catch (error) {
                console.error('Progress polling error:', error);
                if (processingRequest) {
                    setTimeout(pollProgress, 1000);
                }
            }
        };
        
        // 开始轮询进度
        pollProgress();
    }
    
    // 更新日志面板
    function updateLog(logs) {
        if (!Array.isArray(logs) || logs.length === 0) return;
        
        // 获取上次显示的日志数量，防止重复显示
        const existingLogs = logMessages.querySelectorAll('.log-entry').length;
        
        // 只显示新的日志
        for (let i = existingLogs; i < logs.length; i++) {
            addLog(logs[i].message, logs[i].level || 'info');
        }
    }
    
    // 添加单条日志
    function addLog(message, level) {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${level}`;
        
        const timestamp = new Date().toLocaleTimeString();
        const logContent = document.createElement('div');
        logContent.innerHTML = `<span class="log-time">[${timestamp}]</span> ${message}`;
        
        logEntry.appendChild(logContent);
        logMessages.appendChild(logEntry);
        
        // 滚动到底部
        logMessages.scrollTop = logMessages.scrollHeight;
    }
    
    // 检查聊天区域是否已包含特定结果
    function chatContainsResult(result) {
        return Array.from(chatMessages.querySelectorAll('.ai-message .message-content'))
            .some(el => el.textContent.includes(result));
    }
    
    // 添加消息到聊天区域
    function addMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const headerDiv = document.createElement('div');
        headerDiv.className = 'message-header';
        headerDiv.textContent = sender === 'user' ? '您' : 'OpenManus';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // 检测和格式化代码块
        if (sender === 'ai') {
            content = formatCodeBlocks(content);
            contentDiv.innerHTML = content;
        } else {
            contentDiv.textContent = content;
        }
        
        messageDiv.appendChild(headerDiv);
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        
        // 滚动到底部
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // 格式化代码块
    function formatCodeBlocks(text) {
        // 简单的代码块检测和格式化
        let formattedText = text;
        
        // 处理Markdown风格的代码块
        formattedText = formattedText.replace(/```([a-zA-Z]*)\n([\s\S]*?)\n```/g, 
            '<pre><code class="language-$1">$2</code></pre>');
        
        // 将换行符转换为<br>
        formattedText = formattedText.replace(/\n/g, '<br>');
        
        return formattedText;
    }
    
    // 添加更新思考步骤的函数
    function updateThinkingSteps(steps) {
        if (!Array.isArray(steps) || steps.length === 0) return;
        
        steps.forEach(step => {
            // 检查是否已经显示了这个步骤
            const existingStep = document.querySelector(`.thinking-step[data-timestamp="${step.timestamp}"]`);
            if (existingStep) return;
            
            // 创建新的思考步骤元素
            const stepElement = document.createElement('div');
            stepElement.className = `thinking-step ${step.type}`;
            stepElement.dataset.timestamp = step.timestamp;
            
            const stepContent = document.createElement('div');
            stepContent.className = 'thinking-step-content';
            
            // 根据步骤类型不同显示不同样式
            if (step.type === 'communication') {
                // 通信类型消息特殊处理
                const isExpanded = false; // 默认折叠
                
                // 创建通信头部（可点击展开/折叠）
                const headerDiv = document.createElement('div');
                headerDiv.className = 'communication-header';
                headerDiv.innerHTML = `<span class="communication-direction">${step.message}</span> <span class="toggle-icon">▶</span>`;
                headerDiv.onclick = function() {
                    const detailsElement = this.nextElementSibling;
                    const toggleIcon = this.querySelector('.toggle-icon');
                    
                    if (detailsElement.style.display === 'none' || !detailsElement.style.display) {
                        detailsElement.style.display = 'block';
                        toggleIcon.textContent = '▼';
                    } else {
                        detailsElement.style.display = 'none';
                        toggleIcon.textContent = '▶';
                    }
                };
                
                // 创建通信内容（默认隐藏）
                const detailsElement = document.createElement('div');
                detailsElement.className = 'communication-details';
                detailsElement.style.display = 'none';
                
                // 美化通信内容
                if (step.message.includes("发送到LLM")) {
                    detailsElement.innerHTML = `<div class="prompt-wrapper">${formatCommunicationContent(step.details)}</div>`;
                } else {
                    detailsElement.innerHTML = `<div class="response-wrapper">${formatCommunicationContent(step.details)}</div>`;
                }
                
                stepContent.appendChild(headerDiv);
                stepContent.appendChild(detailsElement);
                
            } else {
                // 普通思考步骤
                stepContent.textContent = step.message;
                
                // 如果有详细信息，显示展开/折叠控件
                if (step.details) {
                    const detailsToggle = document.createElement('div');
                    detailsToggle.className = 'details-toggle';
                    detailsToggle.textContent = '显示详情 ▼';
                    detailsToggle.onclick = function() {
                        const detailsElement = this.nextElementSibling;
                        if (detailsElement.style.display === 'none') {
                            detailsElement.style.display = 'block';
                            this.textContent = '隐藏详情 ▲';
                        } else {
                            detailsElement.style.display = 'none';
                            this.textContent = '显示详情 ▼';
                        }
                    };
                    
                    const detailsElement = document.createElement('div');
                    detailsElement.className = 'step-details';
                    detailsElement.textContent = step.details;
                    detailsElement.style.display = 'none';
                    
                    stepContent.appendChild(detailsToggle);
                    stepContent.appendChild(detailsElement);
                }
            }
            
            stepElement.appendChild(stepContent);
            
            // 确定放置位置
            if (step.type === 'communication') {
                // 如果不存在通信容器，创建一个
                let communicationContainer = document.getElementById('communication-steps');
                if (!communicationContainer) {
                    communicationContainer = document.createElement('div');
                    communicationContainer.id = 'communication-steps';
                    communicationContainer.className = 'communication-steps';
                    
                    // 添加标题和说明
                    const headerDiv = document.createElement('div');
                    headerDiv.className = 'communications-header';
                    headerDiv.innerHTML = `
                        <h3>AI通信记录</h3>
                        <p class="communications-info">点击每条记录可查看详细内容</p>
                    `;
                    communicationContainer.appendChild(headerDiv);
                    
                    // 添加到页面
                    const logContainer = document.querySelector('.log-container');
                    if (logContainer) {
                        logContainer.appendChild(communicationContainer);
                    }
                }
                communicationContainer.appendChild(stepElement);
            } else {
                thinkingStepsContainer.appendChild(stepElement);
            }
            
            // 添加简单的淡入效果
            setTimeout(() => {
                stepElement.style.opacity = 1;
            }, 10);
        });
        
        // 滚动到底部
        thinkingStepsContainer.scrollTop = thinkingStepsContainer.scrollHeight;
        
        // 如果有通信容器也滚动到底部
        const communicationContainer = document.getElementById('communication-steps');
        if (communicationContainer) {
            communicationContainer.scrollTop = communicationContainer.scrollHeight;
        }
    }

    // 格式化通信内容，美化JSON等
    function formatCommunicationContent(content) {
        if (!content) return '(无内容)';
        
        // 尝试解析JSON
        try {
            if (content.startsWith('{') && content.endsWith('}')) {
                const jsonObj = JSON.parse(content);
                return `<pre class="json-content">${JSON.stringify(jsonObj, null, 2)}</pre>`;
            }
        } catch (e) {
            // 不是有效的JSON，继续常规处理
        }
        
        // 转义HTML并保留换行
        const htmlEscaped = content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')  // 修复这里的正则表达式错误
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
        
        // 保留换行并添加语法高亮
        return htmlEscaped.replace(/\n/g, '<br>');
    }

    // 新增：获取生成的文件列表
    async function fetchGeneratedFiles() {
        try {
            const response = await fetch('/api/files');
            if (!response.ok) {
                throw new Error('获取文件列表失败');
            }
            
            const data = await response.json();
            
            // 检查API是否返回工作区结构
            if (data.workspaces) {
                updateWorkspaceList(data.workspaces);
            } else if (data.files) {
                // 兼容旧格式
                updateFilesList(data.files);
            }
        } catch (error) {
            console.error('获取文件列表错误:', error);
        }
    }
    
    // 新增：显示工作区文件列表
    function updateWorkspaceList(workspaces) {
        if (!filesList) return;
        
        // 清空现有列表
        filesList.innerHTML = '';
        
        if (!workspaces || workspaces.length === 0) {
            filesList.innerHTML = '<div class="no-files">暂无工作区文件</div>';
            return;
        }
        
        // 创建工作区列表
        const workspaceList = document.createElement('div');
        workspaceList.className = 'workspace-list';
        
        workspaces.forEach(workspace => {
            const workspaceItem = document.createElement('div');
            workspaceItem.className = 'workspace-item';
            
            // 工作区标题
            const workspaceHeader = document.createElement('div');
            workspaceHeader.className = 'workspace-header';
            
            const timestamp = new Date(workspace.modified * 1000);
            const formattedDate = timestamp.toLocaleDateString() + ' ' + timestamp.toLocaleTimeString();
            
            workspaceHeader.innerHTML = `
                <div>${workspace.name}</div>
                <div class="workspace-date">${formattedDate}</div>
            `;
            
            // 工作区内容（文件列表）
            const workspaceContent = document.createElement('div');
            workspaceContent.className = 'workspace-content';
            
            // 添加每个文件
            if (workspace.files && workspace.files.length > 0) {
                workspace.files.forEach(file => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    
                    // 确定文件图标
                    let fileIcon = '📄';
                    if (file.type === 'md') fileIcon = '📝';
                    else if (file.type === 'html') fileIcon = '🌐';
                    else if (file.type === 'css') fileIcon = '🎨';
                    else if (file.type === 'js') fileIcon = '⚙️';
                    else if (file.type === 'py') fileIcon = '🐍';
                    else if (file.type === 'json') fileIcon = '📋';
                    
                    // 格式化修改时间
                    const modifiedDate = new Date(file.modified * 1000).toLocaleString();
                    
                    fileItem.innerHTML = `
                        <div class="file-icon">${fileIcon}</div>
                        <div class="file-details">
                            <div class="file-name">${file.name}</div>
                            <div class="file-meta">${getReadableFileSize(file.size)} · ${modifiedDate}</div>
                        </div>
                    `;
                    
                    // 点击文件查看内容
                    fileItem.addEventListener('click', () => viewFile(file.path));
                    
                    workspaceContent.appendChild(fileItem);
                });
            } else {
                workspaceContent.innerHTML = '<div class="no-files">工作区内无文件</div>';
            }
            
            // 切换工作区内容的展开/折叠
            workspaceHeader.addEventListener('click', () => {
                workspaceContent.classList.toggle('expanded');
            });
            
            workspaceItem.appendChild(workspaceHeader);
            workspaceItem.appendChild(workspaceContent);
            workspaceList.appendChild(workspaceItem);
        });
        
        filesList.appendChild(workspaceList);
        
        // 默认展开第一个工作区
        const firstWorkspace = workspaceList.querySelector('.workspace-content');
        if (firstWorkspace) {
            firstWorkspace.classList.add('expanded');
        }
    }
    
    // 新增：显示文件列表
    function updateFilesList(files) {
        if (!filesList) return;
        
        // 清空现有列表
        filesList.innerHTML = '';
        
        if (!files || files.length === 0) {
            filesList.innerHTML = '<div class="no-files">暂无生成的文件</div>';
            return;
        }
        
        // 创建文件列表
        files.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            // 确定文件图标
            let fileIcon = '📄';
            if (file.type === 'md') fileIcon = '📝';
            else if (file.type === 'html') fileIcon = '🌐';
            else if (file.type === 'css') fileIcon = '🎨';
            else if (file.type === 'js') fileIcon = '⚙️';
            
            // 格式化修改时间
            const modifiedDate = new Date(file.modified * 1000).toLocaleString();
            
            fileItem.innerHTML = `
                <div class="file-icon">${fileIcon}</div>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-meta">${getReadableFileSize(file.size)} · ${modifiedDate}</div>
                </div>
            `;
            
            // 点击文件查看内容
            fileItem.addEventListener('click', () => viewFile(file.path));
            
            filesList.appendChild(fileItem);
        });
    }
    
    // 新增：获取并显示文件内容
    async function viewFile(filePath) {
        try {
            const response = await fetch(`/api/files/${filePath}`);
            if (!response.ok) {
                throw new Error('获取文件内容失败');
            }
            
            const data = await response.json();
            
            // 显示文件内容
            if (fileViewer && fileViewerTitle && fileContent) {
                fileViewerTitle.textContent = data.name;
                fileContent.textContent = data.content; // 简单显示内容，可以扩展为语法高亮等
                fileViewer.style.display = 'block';
                
                // 如果是代码文件，添加语法高亮类
                fileContent.className = 'file-content';
                if (['js', 'html', 'css'].includes(data.type)) {
                    fileContent.classList.add(`language-${data.type}`);
                }
            }
        } catch (error) {
            console.error('获取文件内容错误:', error);
            alert('获取文件内容失败: ' + error.message);
        }
    }
    
    // 工具函数：将字节大小格式化为人类可读格式
    function getReadableFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + sizes[i];
    }

    // 初始加载文件列表
    fetchGeneratedFiles();

    // 终端输出相关元素
    const terminalOutput = document.getElementById('terminal-output');
    const terminalContent = document.getElementById('terminal-content');
    const toggleTerminal = document.getElementById('toggle-terminal');
    const clearTerminal = document.getElementById('clear-terminal');
    
    // 默认隐藏终端内容
    if (terminalContent) {
        terminalContent.style.display = 'none';
    }
    
    // 切换终端显示状态
    if (toggleTerminal) {
        toggleTerminal.addEventListener('click', function() {
            if (terminalContent.style.display === 'none') {
                terminalContent.style.display = 'block';
                toggleTerminal.textContent = '折叠';
            } else {
                terminalContent.style.display = 'none';
                toggleTerminal.textContent = '展开';
            }
        });
    }
    
    // 清空终端内容
    if (clearTerminal) {
        clearTerminal.addEventListener('click', function() {
            if (terminalContent) {
                terminalContent.innerHTML = '';
            }
        });
    }

    // 更新终端输出区域
    function updateTerminalOutput(outputs) {
        if (!Array.isArray(outputs) || outputs.length === 0 || !terminalContent) return;
        
        outputs.forEach(output => {
            const lineElement = document.createElement('div');
            lineElement.className = `terminal-line ${output.type}`;
            lineElement.textContent = output.content;
            
            terminalContent.appendChild(lineElement);
        });
        
        // 滚动到底部
        terminalContent.scrollTop = terminalContent.scrollHeight;
        
        // 如果有新内容，显示终端和设置提示徽章
        if (terminalOutput.style.display === 'none') {
            const badge = document.createElement('span');
            badge.className = 'terminal-badge';
            badge.textContent = '新';
            
            const header = terminalOutput.querySelector('.terminal-header h3');
            if (header && !header.querySelector('.terminal-badge')) {
                header.appendChild(badge);
            }
        }
    }

    // 将系统日志更新到系统日志面板
    function updateSystemLogs(logs) {
        const systemLogsContainer = document.getElementById('systemLogsContainer');
        if (!systemLogsContainer) return;
        
        // 清空"等待加载"消息
        if (systemLogsContainer.querySelector('p')?.textContent === '等待日志加载...') {
            systemLogsContainer.innerHTML = '';
        }
        
        // 添加新日志
        logs.forEach(log => {
            const logLine = document.createElement('p');
            logLine.className = 'log-line';
            logLine.textContent = log;
            systemLogsContainer.appendChild(logLine);
        });
        
        // 滚动到底部
        systemLogsContainer.scrollTop = systemLogsContainer.scrollHeight;
    }

    // 将系统日志作为聊天消息添加到对话窗口
    function addSystemLogsToChat(logs) {
        console.log('添加系统日志到聊天窗口:', logs.length);
        
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) {
            console.error('未找到聊天消息容器元素');
            return;
        }
        
        const now = Date.now();
        
        // 如果距离上一条系统日志消息不超过5秒，则合并显示
        if (window.lastSystemLogMessage && 
            window.lastSystemLogMessage.parentNode === chatMessages && 
            now - window.lastSystemLogTimestamp < 5000) {
            
            // 获取已有的日志内容元素
            const logContent = window.lastSystemLogMessage.querySelector('.system-log-content');
            if (logContent) {
                console.log('合并到现有消息');
                // 追加新的日志内容
                logContent.textContent += '\n' + logs.join('\n');
                
                // 更新时间戳
                window.lastSystemLogTimestamp = now;
                
                // 滚动到底部
                chatMessages.scrollTop = chatMessages.scrollHeight;
                return;
            }
        }
        
        console.log('创建新的系统日志消息');
        // 创建一个新的OpenManus回复消息
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system-message';
        
        // 创建消息头部
        const messageHeader = document.createElement('div');
        messageHeader.className = 'message-header';
        messageHeader.innerHTML = '<span class="avatar system">🤖</span><span class="sender">OpenManus</span>';
        
        // 创建消息内容
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content log-message';
        
        // 添加日志内容
        const logContent = document.createElement('pre');
        logContent.className = 'system-log-content';
        logContent.textContent = logs.join('\n');
        
        // 组装消息
        messageContent.appendChild(logContent);
        messageDiv.appendChild(messageHeader);
        messageDiv.appendChild(messageContent);
        
        // 添加到对话窗口
        chatMessages.appendChild(messageDiv);
        
        // 更新最后的系统日志消息引用和时间戳
        window.lastSystemLogMessage = messageDiv;
        window.lastSystemLogTimestamp = now;
        
        // 滚动到底部
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
