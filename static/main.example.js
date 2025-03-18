let currentEventSource = null;

function createTask() {
    const promptInput = document.getElementById('prompt-input');
    const prompt = promptInput.value.trim();

    if (!prompt) {
        alert("Please enter a valid prompt");
        promptInput.focus();
        return;
    }

    if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
    }

    const container = document.getElementById('task-container');
    container.innerHTML = '<div class="loading">Initializing task...</div>';
    document.getElementById('input-container').classList.add('bottom');

    fetch('/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ prompt })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw new Error(err.detail || 'Request failed') });
        }
        return response.json();
    })
    .then(data => {
        if (!data.task_id) {
            throw new Error('Invalid task ID');
        }
        setupSSE(data.task_id);
        loadHistory();
        promptInput.value = '';
    })
    .catch(error => {
        container.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        console.error('Failed to create task:', error);
    });
}

function setupSSE(taskId) {
    let retryCount = 0;
    const maxRetries = 3;
    const retryDelay = 2000;
    let lastResultContent = '';

    const container = document.getElementById('task-container');

    function connect() {
        const eventSource = new EventSource(`/tasks/${taskId}/events`);
        currentEventSource = eventSource;

        let heartbeatTimer = setInterval(() => {
            container.innerHTML += '<div class="ping">·</div>';
        }, 5000);

        // Initial polling
        fetch(`/tasks/${taskId}`)
            .then(response => response.json())
            .then(task => {
                updateTaskStatus(task);
            })
            .catch(error => {
                console.error('Initial status fetch failed:', error);
            });

        const handleEvent = (event, type) => {
            clearInterval(heartbeatTimer);
            try {
                const data = JSON.parse(event.data);
                container.querySelector('.loading')?.remove();
                container.classList.add('active');

                const stepContainer = ensureStepContainer(container);
                const { formattedContent, timestamp } = formatStepContent(data, type);
                const step = createStepElement(type, formattedContent, timestamp);

                stepContainer.appendChild(step);
                autoScroll(stepContainer);

                fetch(`/tasks/${taskId}`)
                    .then(response => response.json())
                    .then(task => {
                        updateTaskStatus(task);
                    })
                    .catch(error => {
                        console.error('Status update failed:', error);
                    });
            } catch (e) {
                console.error(`Error handling ${type} event:`, e);
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

                container.innerHTML += `
                    <div class="complete">
                        <div>✅ Task completed</div>
                        <pre>${lastResultContent}</pre>
                    </div>
                `;

                fetch(`/tasks/${taskId}`)
                    .then(response => response.json())
                    .then(task => {
                        updateTaskStatus(task);
                    })
                    .catch(error => {
                        console.error('Final status update failed:', error);
                    });

                eventSource.close();
                currentEventSource = null;
            } catch (e) {
                console.error('Error handling complete event:', e);
            }
        });

        eventSource.addEventListener('error', (event) => {
            clearInterval(heartbeatTimer);
            try {
                const data = JSON.parse(event.data);
                container.innerHTML += `
                    <div class="error">
                        ❌ Error: ${data.message}
                    </div>
                `;
                eventSource.close();
                currentEventSource = null;
            } catch (e) {
                console.error('Error handling failed:', e);
            }
        });

        eventSource.onerror = (err) => {
            if (eventSource.readyState === EventSource.CLOSED) return;

            console.error('SSE connection error:', err);
            clearInterval(heartbeatTimer);
            eventSource.close();

            fetch(`/tasks/${taskId}`)
                .then(response => response.json())
                .then(task => {
                    if (task.status === 'completed' || task.status === 'failed') {
                        updateTaskStatus(task);
                        if (task.status === 'completed') {
                            container.innerHTML += `
                                <div class="complete">
                                    <div>✅ Task completed</div>
                                </div>
                            `;
                        } else {
                            container.innerHTML += `
                                <div class="error">
                                    ❌ Error: ${task.error || 'Task failed'}
                                </div>
                            `;
                        }
                    } else if (retryCount < maxRetries) {
                        retryCount++;
                        container.innerHTML += `
                            <div class="warning">
                                ⚠ Connection lost, retrying in ${retryDelay/1000} seconds (${retryCount}/${maxRetries})...
                            </div>
                        `;
                        setTimeout(connect, retryDelay);
                    } else {
                        container.innerHTML += `
                            <div class="error">
                                ⚠ Connection lost, please try refreshing the page
                            </div>
                        `;
                    }
                })
                .catch(error => {
                    console.error('Task status check failed:', error);
                    if (retryCount < maxRetries) {
                        retryCount++;
                        setTimeout(connect, retryDelay);
                    }
                });
        };
    }

    connect();
}

function loadHistory() {
    fetch('/tasks')
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                throw new Error(`request failure: ${response.status} - ${text.substring(0, 100)}`);
            });
        }
        return response.json();
    })
    .then(tasks => {
        const listContainer = document.getElementById('task-list');
        listContainer.innerHTML = tasks.map(task => `
            <div class="task-card" data-task-id="${task.id}">
                <div>${task.prompt}</div>
                <div class="task-meta">
                    ${new Date(task.created_at).toLocaleString()} -
                    <span class="status status-${task.status ? task.status.toLowerCase() : 'unknown'}">
                        ${task.status || 'Unknown state'}
                    </span>
                </div>
            </div>
        `).join('');
    })
    .catch(error => {
        console.error('Failed to load history records:', error);
        const listContainer = document.getElementById('task-list');
        listContainer.innerHTML = `<div class="error">Load Fail: ${error.message}</div>`;
    });
}


function ensureStepContainer(container) {
    let stepContainer = container.querySelector('.step-container');
    if (!stepContainer) {
        container.innerHTML = '<div class="step-container"></div>';
        stepContainer = container.querySelector('.step-container');
    }
    return stepContainer;
}

function formatStepContent(data, eventType) {
    return {
        formattedContent: data.result,
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

            step.innerHTML = `
                <div class="log-line">
                    <span class="log-prefix">${getEventIcon(type)} [${timestamp}] ${getEventLabel(type)}:</span>
                    <pre>${content}</pre>
                    ${fileInteractionHtml}
                </div>
            `;
        } else {
            step.innerHTML = `
                <div class="log-line">
                    <span class="log-prefix">${getEventIcon(type)} [${timestamp}] ${getEventLabel(type)}:</span>
                    <pre>${content}</pre>
                </div>
            `;
        }
    } else {
        step.className = `step-item ${type}`;
        step.innerHTML = `
            <div class="log-line">
                <span class="log-prefix">${getEventIcon(type)} [${timestamp}] ${getEventLabel(type)}:</span>
                <pre>${content}</pre>
            </div>
        `;
    }
    return step;
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


function getEventIcon(eventType) {
    const icons = {
        'think': '🤔',
        'tool': '🛠️',
        'act': '🚀',
        'result': '🏁',
        'error': '❌',
        'complete': '✅',
        'log': '📝',
        'run': '⚙️'
    };
    return icons[eventType] || 'ℹ️';
}

function getEventLabel(eventType) {
    const labels = {
        'think': 'Thinking',
        'tool': 'Using Tool',
        'act': 'Action',
        'result': 'Result',
        'error': 'Error',
        'complete': 'Complete',
        'log': 'Log',
        'run': 'Running'
    };
    return labels[eventType] || 'Info';
}

function updateTaskStatus(task) {
    const statusBar = document.getElementById('status-bar');
    if (!statusBar) return;

    if (task.status === 'completed') {
        statusBar.innerHTML = `<span class="status-complete">✅ Task completed</span>`;

        if (currentEventSource) {
            currentEventSource.close();
            currentEventSource = null;
        }
    } else if (task.status === 'failed') {
        statusBar.innerHTML = `<span class="status-error">❌ Task failed: ${task.error || 'Unknown error'}</span>`;

        if (currentEventSource) {
            currentEventSource.close();
            currentEventSource = null;
        }
    } else {
        statusBar.innerHTML = `<span class="status-running">⚙️ Task running: ${task.status}</span>`;
    }
}

// Display full screen image
function showFullImage(imageSrc) {
    const modal = document.getElementById('image-modal');
    if (!modal) {
        const modalDiv = document.createElement('div');
        modalDiv.id = 'image-modal';
        modalDiv.className = 'image-modal';
        modalDiv.innerHTML = `
            <span class="close-modal">&times;</span>
            <img src="${imageSrc}" class="modal-content" id="full-image">
        `;
        document.body.appendChild(modalDiv);

        const closeBtn = modalDiv.querySelector('.close-modal');
        closeBtn.addEventListener('click', () => {
            modalDiv.classList.remove('active');
        });

        modalDiv.addEventListener('click', (e) => {
            if (e.target === modalDiv) {
                modalDiv.classList.remove('active');
            }
        });

        setTimeout(() => modalDiv.classList.add('active'), 10);
    } else {
        document.getElementById('full-image').src = imageSrc;
        modal.classList.add('active');
    }
}

// Simulate running Python files
function simulateRunPython(filePath) {
    let modal = document.getElementById('python-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'python-modal';
        modal.className = 'python-modal';
        modal.innerHTML = `
            <div class="python-console">
                <div class="close-modal">&times;</div>
                <div class="python-output">Loading Python file contents...</div>
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
                    > Simulated operation output:</div>
                <pre style="color: #f8f8f8;">
#This is the result of Python code simulation run
#The actual operational results may vary

# Running ${filePath.split('/').pop()}...
print("Hello from Python Simulated environment!")

# Code execution completed
</pre>
            `;
            outputDiv.appendChild(resultElement);
        })
        .catch(error => {
            console.error('Error loading Python file:', error);
            const outputDiv = modal.querySelector('.python-output');
            outputDiv.innerHTML = `Error loading file: ${error.message}`;
        });
}

document.addEventListener('DOMContentLoaded', () => {
    loadHistory();

    document.getElementById('prompt-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            createTask();
        }
    });

    const historyToggle = document.getElementById('history-toggle');
    if (historyToggle) {
        historyToggle.addEventListener('click', () => {
            const historyPanel = document.getElementById('history-panel');
            if (historyPanel) {
                historyPanel.classList.toggle('open');
                historyToggle.classList.toggle('active');
            }
        });
    }

    const clearButton = document.getElementById('clear-btn');
    if (clearButton) {
        clearButton.addEventListener('click', () => {
            document.getElementById('prompt-input').value = '';
            document.getElementById('prompt-input').focus();
        });
    }

    // Add keyboard event listener to close modal boxes
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

// 动态生成数字雨内容
function generateDigitalRain() {
    const columns = document.querySelectorAll('.rain-column');
    
    // 为每列数字雨随机生成0和1
    columns.forEach((column, index) => {
        // 清空原有内容
        column.innerHTML = '';
        
        // 生成随机数量的0和1
        const charCount = Math.floor(Math.random() * 8) + 10; // 10-18个字符
        
        // 不同列使用不同字符集
        let characters = ['0', '1'];
        if (index % 5 === 0) {
            characters = ['0', '1', '7', '9'];
        } else if (index % 5 === 1) {
            characters = ['0', '1', 'A', 'F'];
        } else if (index % 5 === 2) {
            characters = ['0', '1', 'X', 'Y'];
        } else if (index % 5 === 3) {
            characters = ['φ', 'Δ', '0', '1'];
        } else if (index % 5 === 4) {
            characters = ['*', '+', '0', '1'];
        }
        
        for (let i = 0; i < charCount; i++) {
            const span = document.createElement('span');
            const randomChar = characters[Math.floor(Math.random() * characters.length)];
            span.textContent = randomChar;
            
            // 设置随机透明度变化
            const baseOpacity = Math.random() * 0.5 + 0.5; // 0.5-1.0
            span.style.opacity = baseOpacity.toString();
            
            // 获取CSS变量
            const styles = getComputedStyle(document.documentElement);
            const colorOptions = [
                styles.getPropertyValue('--accent-green').trim(),
                styles.getPropertyValue('--accent-color-5').trim(),
                styles.getPropertyValue('--accent-blue').trim(),
                styles.getPropertyValue('--accent-color-1').trim(),
                styles.getPropertyValue('--accent-color-2').trim(),
                styles.getPropertyValue('--accent-purple').trim(),
                styles.getPropertyValue('--accent-pink').trim(),
                styles.getPropertyValue('--accent-teal').trim(),
                styles.getPropertyValue('--accent-color-3').trim(),
                styles.getPropertyValue('--accent-color-4').trim(),
                styles.getPropertyValue('--accent-yellow').trim()
            ];
            
            // 第一个字符有特殊样式
            if (i === 0) {
                // 使用随机颜色
                const randomColor = colorOptions[Math.floor(Math.random() * colorOptions.length)];
                
                span.style.color = randomColor;
                span.style.opacity = '1';
                span.style.textShadow = `0 0 15px ${randomColor}, 0 0 20px ${randomColor}`;
                span.style.fontSize = '22px';
            } else if (i % 3 === 0) {
                // 每隔几个字符使用不同颜色
                const randomColor = colorOptions[Math.floor(Math.random() * colorOptions.length)];
                span.style.color = randomColor;
                span.style.opacity = '0.8';
            }
            
            column.appendChild(span);
        }
    });
}

// 动态产生随机粒子
function createRandomParticle() {
    const container = document.querySelector('.particle-container');
    
    if (!container) return;
    
    setInterval(() => {
        const particle = document.createElement('div');
        particle.className = 'particle';
        
        // 随机位置
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.top = '100%';
        
        // 随机大小
        const size = Math.random() * 2 + 1;
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;
        
        // 获取CSS变量
        const styles = getComputedStyle(document.documentElement);
        const colorOptions = [
            styles.getPropertyValue('--accent-green').trim(),
            styles.getPropertyValue('--accent-color-5').trim(),
            styles.getPropertyValue('--accent-blue').trim(),
            styles.getPropertyValue('--accent-color-1').trim()
        ];
        
        // 随机颜色
        const randomColor = colorOptions[Math.floor(Math.random() * colorOptions.length)];
        particle.style.backgroundColor = randomColor;
        particle.style.boxShadow = `0 0 5px ${randomColor}`;
        
        // 随机透明度
        particle.style.opacity = (Math.random() * 0.5 + 0.3).toString();
        
        // 添加到容器
        container.appendChild(particle);
        
        // 设置动画结束后移除元素
        setTimeout(() => {
            particle.remove();
        }, 5000);
    }, 600); // 每600ms创建一个新粒子
}

// 添加主题选项动画效果
function animateThemeOptions() {
    const themeOptions = document.querySelectorAll('.theme-option');
    themeOptions.forEach((option, index) => {
        // 直接显示元素，不使用动画过渡
        option.style.opacity = '1';
    });
}

// 页面加载完成后初始化效果
document.addEventListener('DOMContentLoaded', function() {
    // 初始化粒子效果
    createRandomParticle();
    
    // 初始化主题选项动画
    animateThemeOptions();
});
