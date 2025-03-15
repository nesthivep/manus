let currentEventSource = null;

function createTask() {
    const promptInput = document.getElementById('prompt-input');
    const prompt = promptInput.value.trim();

    if (!prompt) {
        alert("Please enter a valid task prompt");
        promptInput.focus();
        return;
    }

    if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
    }

    const taskContainer = document.getElementById('task-container');
    const stepsContainer = document.getElementById('steps-container');
    const resultContainer = document.getElementById('result-container');
    
    // 隐藏结果面板
    hideResultPanel();
    
    // 隐藏欢迎信息，显示步骤加载状态
    const welcomeMessage = taskContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.style.display = 'none';
    }
    
    stepsContainer.innerHTML = '<div class="loading">Initializing task...</div>';
    resultContainer.innerHTML = '';

    fetch('/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ prompt })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw new Error(err.detail || '请求失败') });
        }
        return response.json();
    })
    .then(data => {
        if (!data.task_id) {
            throw new Error('无效的任务ID');
        }
        setupSSE(data.task_id);
        loadHistory();
        promptInput.value = '';
    })
    .catch(error => {
        stepsContainer.innerHTML = `<div class="error">错误: ${error.message}</div>`;
        updateResultPanel({result: error.message}, 'error');
        showResultPanel();
        console.error('创建任务失败:', error);
    });
}

function setupSSE(taskId) {
    let retryCount = 0;
    const maxRetries = 3;
    const retryDelay = 2000;
    let lastResultContent = '';

    const stepsContainer = document.getElementById('steps-container');
    const resultContainer = document.getElementById('result-container');
    
    // 默认隐藏结果面板
    hideResultPanel();

    function connect() {
        const eventSource = new EventSource(`/tasks/${taskId}/events`);
        currentEventSource = eventSource;

        let heartbeatTimer = setInterval(() => {
            const pingDiv = document.createElement('div');
            pingDiv.className = 'ping';
            pingDiv.innerHTML = '·';
            stepsContainer.appendChild(pingDiv);
        }, 5000);

        // Initial polling
        fetch(`/tasks/${taskId}`)
            .then(response => response.json())
            .then(task => {
                updateTaskStatus(task);
            })
            .catch(error => {
                console.error('初始状态获取失败:', error);
            });

        const handleEvent = (event, type) => {
            clearInterval(heartbeatTimer);
            try {
                const data = JSON.parse(event.data);
                const loadingDiv = stepsContainer.querySelector('.loading');
                if (loadingDiv) loadingDiv.remove();

                const { formattedContent, timestamp } = formatStepContent(data, type);
                const step = createStepElement(type, formattedContent, timestamp);

                // 移除其他步骤的active状态
                document.querySelectorAll('.step-item').forEach(item => {
                    item.classList.remove('active');
                });
                
                // 为当前步骤添加active状态
                step.classList.add('active');
                
                stepsContainer.appendChild(step);
                autoScroll(stepsContainer);
                
                // 更新结果面板并显示（但仅对某些类型的步骤）
                if (type === 'tool' || type === 'act' || type === 'result') {
                    updateResultPanel(data, type);
                    showResultPanel();
                }

                fetch(`/tasks/${taskId}`)
                    .then(response => response.json())
                    .then(task => {
                        updateTaskStatus(task);
                    })
                    .catch(error => {
                        console.error('状态更新失败:', error);
                    });
            } catch (e) {
                console.error(`处理 ${type} 事件时出错:`, e);
            }
        };

        const eventTypes = ['think', 'tool', 'act', 'log', 'run', 'message'];
        eventTypes.forEach(type => {
            eventSource.addEventListener(type, (event) => handleEvent(event, type));
        });

        eventSource.addEventListener('complete', (event) => {
            clearInterval(heartbeatTimer);
            try {
                const data = JSON.parse(event.data);
                lastResultContent = data.result || '';

                const completeDiv = document.createElement('div');
                completeDiv.className = 'complete';
                completeDiv.innerHTML = '<div>✅ 任务完成</div>';
                stepsContainer.appendChild(completeDiv);
                
                updateResultPanel({result: lastResultContent}, 'complete');
                showResultPanel();

                fetch(`/tasks/${taskId}`)
                    .then(response => response.json())
                    .then(task => {
                        updateTaskStatus(task);
                    })
                    .catch(error => {
                        console.error('最终状态更新失败:', error);
                    });

                eventSource.close();
                currentEventSource = null;
            } catch (e) {
                console.error('处理完成事件时出错:', e);
            }
        });

        eventSource.addEventListener('error', (event) => {
            clearInterval(heartbeatTimer);
            try {
                const data = JSON.parse(event.data);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error';
                errorDiv.innerHTML = `<div>❌ 错误: ${data.message}</div>`;
                stepsContainer.appendChild(errorDiv);
                
                updateResultPanel({result: data.message}, 'error');
                showResultPanel();
                
                eventSource.close();
                currentEventSource = null;
            } catch (e) {
                console.error('处理错误时出错:', e);
            }
        });

        eventSource.onerror = (err) => {
            if (eventSource.readyState === EventSource.CLOSED) return;

            console.error('SSE连接错误:', err);
            clearInterval(heartbeatTimer);
            eventSource.close();

            fetch(`/tasks/${taskId}`)
                .then(response => response.json())
                .then(task => {
                    if (task.status === 'completed' || task.status === 'failed') {
                        updateTaskStatus(task);
                        if (task.status === 'completed') {
                            const completeDiv = document.createElement('div');
                            completeDiv.className = 'complete';
                            completeDiv.innerHTML = '<div>✅ 任务完成</div>';
                            stepsContainer.appendChild(completeDiv);
                            
                            if (task.steps && task.steps.length > 0) {
                                const lastStep = task.steps[task.steps.length - 1];
                                updateResultPanel({result: lastStep.result}, 'complete');
                                showResultPanel();
                            }
                        } else {
                            const errorDiv = document.createElement('div');
                            errorDiv.className = 'error';
                            errorDiv.innerHTML = `<div>❌ 错误: ${task.error || '任务失败'}</div>`;
                            stepsContainer.appendChild(errorDiv);
                            
                            updateResultPanel({result: task.error || '任务失败'}, 'error');
                            showResultPanel();
                        }
                    } else if (retryCount < maxRetries) {
                        retryCount++;
                        const warningDiv = document.createElement('div');
                        warningDiv.className = 'warning';
                        warningDiv.innerHTML = `<div>⚠ 连接断开，${retryDelay/1000}秒后重试 (${retryCount}/${maxRetries})...</div>`;
                        stepsContainer.appendChild(warningDiv);
                        setTimeout(connect, retryDelay);
                    } else {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'error';
                        errorDiv.innerHTML = '<div>⚠ 连接断开，请刷新页面重试</div>';
                        stepsContainer.appendChild(errorDiv);
                        
                        updateResultPanel({result: '连接断开，请刷新页面重试'}, 'error');
                        showResultPanel();
                    }
                })
                .catch(error => {
                    console.error('任务状态检查失败:', error);
                    if (retryCount < maxRetries) {
                        retryCount++;
                        setTimeout(connect, retryDelay);
                    }
                });
        };
    }

    connect();
}

function updateResultPanel(data, type) {
    const resultContainer = document.getElementById('result-container');
    const currentStep = document.getElementById('current-step');
    
    if (!resultContainer || !currentStep) return;
    
    // 更新顶部步骤信息（红框部分）
    currentStep.innerHTML = `<span class="emoji-icon">${getEventIcon(type)}</span> ${getEventLabel(type)}:`;
    
    // 更新内容区域（蓝框部分）
    let content = '';
    
    if (data.result) {
        content = data.result;
    } else if (data.message) {
        content = data.message;
    } else {
        content = JSON.stringify(data, null, 2);
    }
    
    // 清空之前的内容，添加新内容
    resultContainer.innerHTML = '';
    
    // 创建内容高亮区域
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('content-highlight');
    contentDiv.innerHTML = `<pre>${content}</pre>`;
    resultContainer.appendChild(contentDiv);
}

function loadHistory() {
    fetch('/tasks')
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                throw new Error(`请求失败: ${response.status} - ${text.substring(0, 100)}`);
            });
        }
        return response.json();
    })
    .then(tasks => {
        const listContainer = document.getElementById('task-list');
        if (tasks.length === 0) {
            listContainer.innerHTML = '<div class="info">暂无历史任务</div>';
            return;
        }
        
        listContainer.innerHTML = tasks.map(task => `
            <div class="task-card" data-task-id="${task.id}" onclick="loadTask('${task.id}')">
                <div>${task.prompt}</div>
                <div class="task-meta">
                    ${new Date(task.created_at).toLocaleString()} -
                    <span class="status status-${task.status ? task.status.toLowerCase() : 'unknown'}">
                        ${task.status || '未知状态'}
                    </span>
                </div>
            </div>
        `).join('');
    })
    .catch(error => {
        console.error('加载历史记录失败:', error);
        const listContainer = document.getElementById('task-list');
        listContainer.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    });
}

function loadTask(taskId) {
    if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
    }
    
    const taskContainer = document.getElementById('task-container');
    const stepsContainer = document.getElementById('steps-container');
    const resultContainer = document.getElementById('result-container');
    
    // 隐藏欢迎信息
    const welcomeMessage = taskContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.style.display = 'none';
    }
    
    // 默认隐藏结果面板
    hideResultPanel();
    
    stepsContainer.innerHTML = '<div class="loading">加载任务...</div>';
    resultContainer.innerHTML = '';
    
    fetch(`/tasks/${taskId}`)
        .then(response => response.json())
        .then(task => {
            const taskCards = document.querySelectorAll('.task-card');
            taskCards.forEach(card => {
                card.classList.remove('active');
                if (card.getAttribute('data-task-id') === taskId) {
                    card.classList.add('active');
                }
            });
            
            stepsContainer.innerHTML = '';
            if (task.steps && task.steps.length > 0) {
                task.steps.forEach((step, index) => {
                    const stepElement = createStepElement(
                        step.type, 
                        step.result, 
                        new Date(task.created_at).toLocaleTimeString()
                    );
                    
                    // 设置最后一个步骤为展开状态，其他为折叠状态
                    if (index !== task.steps.length - 1) {
                        setTimeout(() => {
                            const logBody = stepElement.querySelector('.log-body');
                            if (logBody) logBody.style.display = 'none';
                            stepElement.classList.add('minimized');
                        }, 10);
                    } else {
                        // 最后一个步骤添加高亮标记
                        stepElement.classList.add('active');
                    }
                    
                    stepsContainer.appendChild(stepElement);
                    
                    // 显示最后一个步骤的结果，但不自动显示结果面板
                    if (index === task.steps.length - 1) {
                        updateResultPanel({result: step.result}, step.type);
                    }
                });
            } else {
                stepsContainer.innerHTML = '<div class="info">该任务没有记录步骤</div>';
            }
            
            updateTaskStatus(task);
        })
        .catch(error => {
            console.error('加载任务失败:', error);
            stepsContainer.innerHTML = `<div class="error">错误: ${error.message}</div>`;
        });
}

function formatStepContent(data, eventType) {
    return {
        formattedContent: data.result || (data.message || JSON.stringify(data)),
        timestamp: new Date().toLocaleTimeString()
    };
}

function createStepElement(type, content, timestamp) {
    const step = document.createElement('div');

    // Executing step
    const stepRegex = /Executing step (\d+)\/(\d+)/;
    if (type === 'log' && stepRegex.test(content)) {
        const match = content.match(stepRegex);
        const currentStep = parseInt(match[1]);
        const totalSteps = parseInt(match[2]);

        step.className = 'step-divider';
        step.innerHTML = `
            <div class="step-circle">${currentStep}</div>
            <div class="step-line"></div>
            <div class="step-info">${currentStep}/${totalSteps}</div>
        `;
    } else if (type === 'act') {
        // Check if it contains information about file saving
        const saveRegex = /Content successfully saved to (.+)/;
        const match = content.match(saveRegex);

        step.className = `step-item ${type}`;
        step.dataset.type = type;
        
        let stepContentHtml = '';
        if (match && match[1]) {
            const filePath = match[1].trim();
            const fileName = filePath.split('/').pop();
            const fileExtension = fileName.split('.').pop().toLowerCase();

            // Handling different types of files
            let fileInteractionHtml = '';

            if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(fileExtension)) {
                fileInteractionHtml = `
                    <div class="file-interaction image-preview">
                        <img src="${filePath}" alt="${fileName}" class="preview-image" onclick="showFullImage('${filePath}')">
                        <a href="/download?file_path=${filePath}" download="${fileName}" class="download-link">⬇️ 下载图片</a>
                    </div>
                `;
            } else if (['mp3', 'wav', 'ogg'].includes(fileExtension)) {
                fileInteractionHtml = `
                    <div class="file-interaction audio-player">
                        <audio controls src="${filePath}"></audio>
                        <a href="/download?file_path=${filePath}" download="${fileName}" class="download-link">⬇️ 下载音频</a>
                    </div>
                `;
            } else if (['html', 'js', 'py'].includes(fileExtension)) {
                fileInteractionHtml = `
                    <div class="file-interaction code-file">
                        <button onclick="simulateRunPython('${filePath}')" class="run-button">▶️ 模拟运行</button>
                        <a href="/download?file_path=${filePath}" download="${fileName}" class="download-link">⬇️ 下载文件</a>
                    </div>
                `;
            } else {
                fileInteractionHtml = `
                    <div class="file-interaction">
                        <a href="/download?file_path=${filePath}" download="${fileName}" class="download-link">⬇️ 下载文件: ${fileName}</a>
                    </div>
                `;
            }

            stepContentHtml = `
                <div class="log-content">
                    <pre>${content}</pre>
                    ${fileInteractionHtml}
                </div>
            `;
        } else {
            stepContentHtml = `
                <div class="log-content">
                    <pre>${content}</pre>
                </div>
            `;
        }

        step.innerHTML = `
            <div class="log-header" onclick="toggleStepContent(this)">
                <span class="log-prefix">${getEventIcon(type)} [${timestamp}] ${getEventLabel(type)}</span>
                <div class="step-controls">
                    <span class="minimize-btn" onclick="minimizeStep(event, this)"></span>
                </div>
            </div>
            <div class="log-body">${stepContentHtml}</div>
        `;
    } else {
        step.className = `step-item ${type}`;
        step.dataset.type = type;

        step.innerHTML = `
            <div class="log-header" onclick="toggleStepContent(this)">
                <span class="log-prefix">${getEventIcon(type)} [${timestamp}] ${getEventLabel(type)}</span>
                <div class="step-controls">
                    <span class="minimize-btn" onclick="minimizeStep(event, this)"></span>
                </div>
            </div>
            <div class="log-body">
                <div class="log-content">
                    <pre>${content}</pre>
                </div>
            </div>
        `;
    }
    
    return step;
}

// 切换步骤内容的显示/隐藏
function toggleStepContent(header) {
    const stepItem = header.closest('.step-item');
    if (!stepItem) return;
    
    const logBody = stepItem.querySelector('.log-body');
    if (!logBody) return;
    
    if (logBody.style.display === 'none') {
        logBody.style.display = 'block';
        stepItem.classList.remove('minimized');
    } else {
        logBody.style.display = 'none';
        stepItem.classList.add('minimized');
    }
    
    // 高亮当前步骤
    highlightStep(stepItem);
    
    // 更新结果面板并显示
    const type = stepItem.dataset.type;
    const content = stepItem.querySelector('pre')?.textContent || '';
    updateResultPanel({result: content}, type);
    showResultPanel();
}

// 最小化步骤
function minimizeStep(event, btn) {
    event.stopPropagation(); // 阻止事件冒泡
    
    const stepItem = btn.closest('.step-item');
    if (!stepItem) return;
    
    stepItem.classList.toggle('minimized');
    
    const logBody = stepItem.querySelector('.log-body');
    if (logBody) {
        if (stepItem.classList.contains('minimized')) {
            logBody.style.display = 'none';
        } else {
            logBody.style.display = 'block';
        }
    }
}

// 切换结果面板的显示状态
function toggleResultPanel() {
    const resultPanel = document.getElementById('result-panel');
    const container = document.querySelector('.container');
    if (!resultPanel) return;
    
    // 如果面板已经是最小化状态，则完全显示
    if (resultPanel.classList.contains('minimized')) {
        resultPanel.classList.remove('minimized');
        container.classList.add('with-result');
    } else {
        // 否则最小化面板
        resultPanel.classList.add('minimized');
        container.classList.remove('with-result');
    }
}

// 隐藏结果面板
function hideResultPanel() {
    const resultPanel = document.getElementById('result-panel');
    const container = document.querySelector('.container');
    if (resultPanel) {
        resultPanel.classList.add('hidden');
        resultPanel.classList.remove('minimized'); // 确保隐藏时重置最小化状态
        container.classList.remove('with-result'); // 移除容器样式
    }
}

// 显示结果面板
function showResultPanel() {
    const resultPanel = document.getElementById('result-panel');
    const container = document.querySelector('.container');
    if (resultPanel) {
        resultPanel.classList.remove('hidden');
        resultPanel.classList.remove('minimized'); // 确保显示时不是最小化状态
        container.classList.add('with-result'); // 添加容器样式
    }
}

function autoScroll(element) {
    requestAnimationFrame(() => {
        element.scrollTo({
            top: element.scrollHeight,
            behavior: 'smooth'
        });
    });
    setTimeout(() => {
        element.scrollTop = element.scrollHeight;
    }, 100);
}

function getEventIcon(type) {
    switch (type) {
        case 'think': return '🤔';
        case 'tool': return '🛠️';
        case 'act': return '🚀';
        case 'log': return '📝';
        case 'run': return '▶️';
        case 'message': return '💬';
        case 'complete': return '✅';
        case 'error': return '❌';
        default: return '📌';
    }
}

function getEventLabel(type) {
    switch (type) {
        case 'think': return 'Thinking';
        case 'tool': return 'Using Tool';
        case 'act': return 'Taking Action';
        case 'log': return 'Log';
        case 'run': return 'Running';
        case 'message': return 'Message';
        case 'complete': return 'Completed';
        case 'error': return 'Error';
        default: return 'Step';
    }
}

function updateTaskStatus(task) {
    const statusBar = document.getElementById('status-bar');
    if (!statusBar) return;

    if (task.status === 'completed') {
        statusBar.innerHTML = `<span class="status-complete">✅ 任务完成</span>`;

        if (currentEventSource) {
            currentEventSource.close();
            currentEventSource = null;
        }
    } else if (task.status === 'failed') {
        statusBar.innerHTML = `<span class="status-error">❌ 任务失败: ${task.error || '未知错误'}</span>`;

        if (currentEventSource) {
            currentEventSource.close();
            currentEventSource = null;
        }
    } else {
        statusBar.innerHTML = `<span class="status-running">⚙️ 任务运行中: ${task.status}</span>`;
    }
}

function showFullImage(imageSrc) {
    let modal = document.getElementById('image-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'image-modal';
        modal.className = 'image-modal';
        modal.innerHTML = `
            <span class="close-modal">&times;</span>
            <img src="${imageSrc}" class="modal-content" id="full-image">
        `;
        document.body.appendChild(modal);

        const closeBtn = modal.querySelector('.close-modal');
        closeBtn.addEventListener('click', () => {
            modal.classList.remove('active');
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    } else {
        document.getElementById('full-image').src = imageSrc;
    }
    
    modal.classList.add('active');
}

function simulateRunPython(filePath) {
    let modal = document.getElementById('python-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'python-modal';
        modal.className = 'python-modal';
        modal.innerHTML = `
            <div class="python-console">
                <div class="close-modal">&times;</div>
                <div class="python-output">正在加载Python文件内容...</div>
            </div>
        `;
        document.body.appendChild(modal);

        const closeBtn = modal.querySelector('.close-modal');
        closeBtn.addEventListener('click', () => {
            modal.classList.remove('active');
        });
    }

    modal.classList.add('active');

    // Load Python file content
    fetch(filePath)
        .then(response => response.text())
        .then(code => {
            const outputDiv = modal.querySelector('.python-output');
            outputDiv.innerHTML = '';

            const codeElement = document.createElement('pre');
            codeElement.textContent = code;
            codeElement.style.marginBottom = '20px';
            codeElement.style.padding = '10px';
            codeElement.style.borderBottom = '1px solid #444';
            outputDiv.appendChild(codeElement);

            // Add simulation run results
            const resultElement = document.createElement('div');
            resultElement.innerHTML = `
                <div style="color: #4CAF50; margin-top: 10px; margin-bottom: 10px;">
                    > 模拟运行输出结果:</div>
                <pre style="color: #f8f8f8;">
# 这是Python代码模拟运行结果
# 实际运行结果可能会有所不同

# 运行 ${filePath.split('/').pop()}...
print("Hello from Python Simulated environment!")

# 代码执行完成
</pre>
            `;
            outputDiv.appendChild(resultElement);
        })
        .catch(error => {
            console.error('加载Python文件错误:', error);
            const outputDiv = modal.querySelector('.python-output');
            outputDiv.innerHTML = `加载文件错误: ${error.message}`;
        });
}

// 高亮显示当前选中的步骤
function highlightStep(stepElement) {
    // 移除其他步骤的高亮
    document.querySelectorAll('.step-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 为当前步骤添加高亮
    stepElement.classList.add('active');
}

document.addEventListener('DOMContentLoaded', () => {
    loadHistory();

    document.getElementById('prompt-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            createTask();
        }
    });

    // 添加键盘事件监听器关闭模态框
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const imageModal = document.getElementById('image-modal');
            if (imageModal && imageModal.classList.contains('active')) {
                imageModal.classList.remove('active');
            }

            const pythonModal = document.getElementById('python-modal');
            if (pythonModal && pythonModal.classList.contains('active')) {
                pythonModal.classList.remove('active');
            }
        }
    });
});
