<p align="left">
    中文&nbsp ｜ &nbsp<a href="README.md">English</a>&nbsp
</p>

<p align="left">
    <a href="https://discord.gg/6dn7Sa3a"><img src="https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat" alt="Discord Follow"></a>
</p>

# OpenManus 🙋  

Manus 非常棒，但 OpenManus 无需邀请码即可实现任何创意 🛫！

**新功能：** 由 **云栖AI** 倾力打造的全新Web应用界面现已推出！更直观、便捷地与OpenManus进行交互，让您的创意即刻实现！

感谢 MetaGPT 团队提供的 OpenManus 基础框架。

用 OpenManus 开启你的智能体之旅吧！

## 项目演示  

<img src="assets/webapp.png" alt="OpenManus Web App" width="800" />

## 安装指南

1. 创建新的 conda 环境：

```bash
conda create -n open_manus python=3.12
conda activate open_manus
```

2. 克隆仓库：

```bash
git clone https://github.com/mannaandpoem/OpenManus.git
cd OpenManus
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

## 配置说明

OpenManus 需要配置使用的 LLM API，请按以下步骤设置：

1. 在 `config` 目录创建 `config.toml` 文件（可从示例复制）：

```bash
cp config/config.example.toml config/config.toml
```

2. 编辑 `config/config.toml` 添加 API 密钥和自定义设置：

```toml
# 全局 LLM 配置
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # 替换为真实 API 密钥
max_tokens = 4096
temperature = 0.0

# 可选特定 LLM 模型配置
[llm.vision]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # 替换为真实 API 密钥
```

## 快速启动

### 命令行模式
通过终端运行 OpenManus：

```bash
python main.py
```

### Web 界面模式
体验由 **云栖AI** 开发的全新Web交互界面：

```bash
python main.py --web
# 或直接使用
python web_run.py
```

Web界面让您可以通过浏览器直观地与OpenManus交流，更加便捷地实现您的创意！

如需体验开发中版本，可运行：

```bash
python run_flow.py
```

## 贡献指南
我们欢迎任何友好的建议和有价值的贡献！可以直接创建 issue 或提交 pull request。

或通过📧邮件联系 @mannaandpoem：mannaandpoem@gmail.com

## 发展路线
- [ ] 更优的规划系统
- [ ] 实时演示功能
- [ ] 运行回放
- [ ] 强化学习微调模型
- [ ] 全面的性能基准测试
- [ ] Web界面功能增强

## 交流群
加入我们的飞书交流群，与其他开发者分享经验！

<div align="center" style="display: flex; gap: 20px;">
    <img src="assets/community_group.jpg" alt="OpenManus 交流群" width="300" />
</div>

## Star 数量

[![Star History Chart](https://api.star-history.com/svg?repos=mannaandpoem/OpenManus&type=Date)](https://star-history.com/#mannaandpoem/OpenManus&Date)

## 致谢

特别感谢 [anthropic-computer-use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo) 和 [broswer-use](https://github.com/browser-use/browser-use) 为本项目提供的基础支持！

OpenManus 由 **云栖AI** 基于 MetaGPT 社区的框架共同构建，感谢这个充满活力的智能体开发者社区！
