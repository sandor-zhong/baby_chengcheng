# 免费AI模型设置指南

## 🆓 免费AI模型选项

### 1. **Ollama（推荐）** - 完全免费本地运行
- **优点**：完全免费，数据隐私，无需网络
- **缺点**：需要本地安装，占用存储空间
- **适用场景**：个人使用，数据敏感

### 2. **模拟模式** - 立即可用
- **优点**：无需安装，立即可用
- **缺点**：回答是预设的，不够智能
- **适用场景**：测试和演示

## 🚀 快速开始（模拟模式）

如果您想立即测试AI功能，可以切换到模拟模式：

1. **修改配置**：
   在 `app.py` 第19行，将：
   ```python
   AI_MODEL_TYPE = "ollama"
   ```
   改为：
   ```python
   AI_MODEL_TYPE = "mock"
   ```

2. **重启应用**：
   ```bash
   python app.py
   ```

3. **测试AI功能**：
   - 访问 `http://localhost:9000/ai`
   - 尝试提问，会得到预设的育儿建议

## 🔧 Ollama安装（推荐）

### Windows安装步骤：

1. **下载Ollama**：
   - 访问：https://ollama.ai/
   - 点击"Download for Windows"
   - 下载并安装

2. **安装AI模型**：
   ```bash
   # 安装中文模型（推荐）
   ollama pull qwen
   
   # 或者安装英文模型
   ollama pull llama2
   ```

3. **启动Ollama服务**：
   ```bash
   ollama serve
   ```

4. **配置应用**：
   在 `app.py` 中确保：
   ```python
   AI_MODEL_TYPE = "ollama"
   OLLAMA_BASE_URL = "http://localhost:11434"
   ```

5. **重启应用**：
   ```bash
   python app.py
   ```

## 🎯 其他免费AI选项

### 1. **Hugging Face Transformers**
```python
# 可以集成Hugging Face的免费模型
from transformers import pipeline

def ai_chat_huggingface(prompt):
    generator = pipeline('text-generation', model='microsoft/DialoGPT-medium')
    return generator(prompt, max_length=100)[0]['generated_text']
```

### 2. **本地LLM模型**
- **GPT4All**：完全免费的本地模型
- **ChatGLM**：清华开源的中文模型
- **Baichuan**：百川智能开源模型

## 📊 模型对比

| 模型 | 费用 | 安装难度 | 中文支持 | 性能 |
|------|------|----------|----------|------|
| Ollama | 免费 | 中等 | 优秀 | 高 |
| 模拟模式 | 免费 | 简单 | 优秀 | 低 |
| OpenAI | 付费 | 简单 | 优秀 | 最高 |
| Hugging Face | 免费 | 复杂 | 一般 | 中等 |

## 🔄 切换模型

在 `app.py` 第19行修改 `AI_MODEL_TYPE`：

```python
# 使用Ollama（推荐）
AI_MODEL_TYPE = "ollama"

# 使用模拟模式（测试用）
AI_MODEL_TYPE = "mock"

# 使用OpenAI（需要API密钥）
AI_MODEL_TYPE = "openai"
```

## 🛠️ 故障排除

### Ollama连接失败：
1. 确保Ollama已启动：`ollama serve`
2. 检查端口：默认11434
3. 检查模型是否安装：`ollama list`

### 模型下载慢：
1. 使用国内镜像源
2. 选择较小的模型
3. 使用代理加速

## 💡 推荐配置

**新手用户**：使用模拟模式，立即可用
**进阶用户**：安装Ollama，获得更好的AI体验
**专业用户**：配置OpenAI API，获得最佳性能

现在您可以选择最适合您的免费AI模型了！🎉
