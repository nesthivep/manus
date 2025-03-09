<p align="left">
    <a href="README_zh.md">中文</a>&nbsp ｜ &nbspEnglish&nbsp
</p>

<p align="left">
    <a href="https://discord.gg/6dn7Sa3a"><img src="https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat" alt="Discord Follow"></a>
</p>

# OpenManus 🙋
Manus is incredible, but OpenManus can achieve any ideas without an Invite Code 🛫!

**New Feature:** The brand new Web application interface, passionately crafted by **Yunqi AI**, is now available! Interact with OpenManus more intuitively and conveniently, bringing your ideas to life instantly!

Thanks to the MetaGPT team for providing the basic framework for OpenManus.

Enjoy your own agent with OpenManus!

## Project Demo

<img src="assets/webapp.png" alt="OpenManus Web App" width="800" />

## Installation

1. Create a new conda environment:

```bash
conda create -n open_manus python=3.12
conda activate open_manus
```

2. Clone the repository:

```bash
git clone https://github.com/mannaandpoem/OpenManus.git
cd OpenManus
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

OpenManus requires configuration for the LLM APIs it uses. Follow these steps to set up your configuration:

1. Create a `config.toml` file in the `config` directory (you can copy from the example):

```bash
cp config/config.example.toml config/config.toml
```

2. Edit `config/config.toml` to add your API keys and customize settings:

```toml
# Global LLM configuration
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Replace with your actual API key
max_tokens = 4096
temperature = 0.0

# Optional configuration for specific LLM models
[llm.vision]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Replace with your actual API key
```

## Quick Start

### Terminal Mode
Run OpenManus from the terminal:

```bash
python main.py
```

### Web Interface Mode
Experience the new interactive web interface developed by **Yunqi AI**:

```bash
python main.py --web
# or directly use
python web_run.py
```

The web interface allows you to interact with OpenManus through your browser, making it more intuitive and convenient to bring your ideas to life!

For unstable version, you also can run:

```bash
python run_flow.py
```

## How to contribute
We welcome any friendly suggestions and helpful contributions! Just create issues or submit pull requests.

Or contact @mannaandpoem via 📧email: mannaandpoem@gmail.com

## Roadmap
- [ ] Better Planning
- [ ] Live Demos
- [ ] Replay
- [ ] RL Fine-tuned Models
- [ ] Comprehensive Benchmarks
- [ ] Web Interface Enhancements

## Community Group
Join our networking group on Feishu and share your experience with other developers!

<div align="center" style="display: flex; gap: 20px;">
    <img src="assets/community_group.jpg" alt="OpenManus 交流群" width="300" />
</div>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mannaandpoem/OpenManus&type=Date)](https://star-history.com/#mannaandpoem/OpenManus&Date)

## Acknowledgement

Thanks to [anthropic-computer-use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo) and [broswer-use](https://github.com/browser-use/browser-use) for providing basic support for this project!

OpenManus is built by **Yunqi AI** based on the framework from MetaGPT community. Huge thanks to this agent community!
