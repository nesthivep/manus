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
        // 关闭之前的WebSocket连接（如果有）
        if (currentWebSocket) {
            currentWebSocket.close();
        }
        
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`;
            
            const ws = new WebSocket(wsUrl);
            currentWebSocket = ws;
            
            ws.onopen = function() {
                console.log('WebSocket连接已建立');
            };
            
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    
                    // 处理思考步骤更新
                    if (data.thinking_steps && data.thinking_steps.length > 0) {
                        updateThinkingSteps(data.thinking_steps);
                    }
                    
                    if (data.status === 'completed' && data.result) {
                        addMessage(data.result, 'ai');
                        statusIndicator.textContent = '';
                        sendButton.disabled = false;
                        stopButton.disabled = true;
                        processingRequest = false;
                        ws.close();
                    } else if (data.status === 'error') {
                        statusIndicator.textContent = '处理请求时发生错误';
                        statusIndicator.className = 'status-indicator error';
                        sendButton.disabled = false;
                        stopButton.disabled = true;
                        processingRequest = false;
                        ws.close();
                    }
                    
                    // 更新日志
                    if (data.log && data.log.length > 0) {
                        updateLog(data.log);
                    }
                } catch (error) {
                    console.error('处理WebSocket消息错误:', error);
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
                stepContent.innerHTML = `<span class="communication-direction">${step.message}:</span>`;
                
                const detailsElement = document.createElement('div');
                detailsElement.className = 'communication-details';
                detailsElement.textContent = step.details || '';
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
            
            // 根据类型添加到适当的容器
            if (step.type === 'communication') {
                // 如果不存在通信容器，创建一个
                let communicationContainer = document.getElementById('communication-steps');
                if (!communicationContainer) {
                    communicationContainer = document.createElement('div');
                    communicationContainer.id = 'communication-steps';
                    communicationContainer.className = 'communication-steps';
                    
                    // 添加标题
                    const title = document.createElement('h3');
                    title.textContent = 'AI通信记录';
                    communicationContainer.appendChild(title);
                    
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

    // 添加更新进度条的函数
    function updateProgressBar(percentage, currentStep) {
        let progressBar = document.getElementById('progress-bar');
        let progressText = document.getElementById('progress-text');
        
        if (!progressBar || !progressText) {
            // 如果进度条不存在，创建一个
            const progressContainer = document.createElement('div');
            progressContainer.className = 'progress-container';
            
            progressBar = document.createElement('div');
            progressBar.id = 'progress-bar';
            progressBar.className = 'progress-bar';
            
            progressText = document.createElement('div');
            progressText.id = 'progress-text';
            progressText.className = 'progress-text';
            
            progressContainer.appendChild(progressBar);
            progressContainer.appendChild(progressText);
            
            // 添加到页面
            const logContainer = document.querySelector('.log-container');
            if (logContainer) {
                logContainer.insertBefore(progressContainer, logContainer.firstChild);
            }
        }
        
        // 设置进度条
        progressBar.style.width = `${percentage}%`;
        
        // 设置进度文本
        progressText.textContent = `${percentage}% - ${currentStep}`;
    }

    // 修改updateThinkingSteps函数，增强通信内容显示
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
});
