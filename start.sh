#!/bin/bash

# 输出启动信息
echo "Starting OpenManus Web Interface..."

# 尝试激活conda环境
if command -v conda &> /dev/null; then
    # 方法1: 使用source激活conda
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate open_manus || echo "Failed to activate conda environment, trying to start service directly"
    
    # 如果上面的方法失败，尝试方法2
    if [ $? -ne 0 ]; then
        # 方法2: 直接使用conda环境中的python
        CONDA_BASE=$(conda info --base)
        PYTHON_PATH="$CONDA_BASE/envs/open_manus/bin/python"
        if [ -f "$PYTHON_PATH" ]; then
            echo "Using Python from conda environment directly"
            PYTHON_CMD="$PYTHON_PATH"
        else
            echo "Conda environment not found, using system Python"
            PYTHON_CMD="python"
        fi
    else
        PYTHON_CMD="python"
    fi
else
    echo "Conda not found, using system Python"
    PYTHON_CMD="python"
fi

# 启动web服务器
echo "Starting web server, please visit http://localhost:8000 in your browser"
$PYTHON_CMD web_server.py

# 检查退出状态
if [ $? -ne 0 ]; then
    echo "Web server failed to start, please check error messages above"
    read -p "Press Enter to continue..."
fi