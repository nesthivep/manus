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
});
