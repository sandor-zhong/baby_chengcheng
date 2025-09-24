# Ollama AI模型安装指南

## 🚀 什么是Ollama？

Ollama是一个完全免费的本地AI模型运行工具，可以运行各种开源AI模型，包括：
- **Qwen**：阿里云开源的中文AI模型
- **Llama2**：Meta开源的大语言模型
- **ChatGLM**：清华开源的中文对话模型
- **Baichuan**：百川智能开源模型

## 📥 安装步骤

### 1. 下载Ollama
- 访问：https://ollama.ai/
- 点击"Download for Windows"
- 下载并安装Ollama

### 2. 安装中文AI模型
打开命令行，运行以下命令：

```bash
# 安装Qwen模型（推荐，中文支持好）
ollama pull qwen

# 或者安装其他模型
ollama pull llama2
ollama pull chatglm
```

### 3. 启动Ollama服务
```bash
ollama serve
```

### 4. 验证安装
打开新的命令行窗口，测试：
```bash
ollama run qwen
```

## 🔧 配置应用

### 1. 确保应用配置正确
在 `app.py` 中确认：
```python
AI_MODEL_TYPE = "ollama"
OLLAMA_BASE_URL = "http://localhost:11434"
```

### 2. 重启应用
```bash
python app.py
```

## 🎯 使用体验

### 安装完成后，您将获得：
- ✅ **真正的AI对话**：不是预设答案
- ✅ **中文支持**：完全支持中文问答
- ✅ **完全免费**：无需API密钥
- ✅ **数据隐私**：所有数据本地处理
- ✅ **离线使用**：无需网络连接

### 测试AI功能：
1. 访问 `http://localhost:9000/ai`
2. 提问："宝宝哭闹怎么办？"
3. 获得真正的AI回答，而不是预设答案

## 🛠️ 故障排除

### 问题1：Ollama连接失败
**解决方案**：
```bash
# 确保Ollama服务正在运行
ollama serve

# 检查端口是否被占用
netstat -an | findstr 11434
```

### 问题2：模型下载慢
**解决方案**：
```bash
# 使用国内镜像源
set OLLAMA_HOST=0.0.0.0:11434
ollama pull qwen
```

### 问题3：内存不足
**解决方案**：
```bash
# 使用较小的模型
ollama pull qwen:7b  # 7B参数版本
```

## 📊 模型对比

| 模型 | 大小 | 中文支持 | 性能 | 推荐度 |
|------|------|----------|------|--------|
| qwen | 14B | 优秀 | 高 | ⭐⭐⭐⭐⭐ |
| qwen:7b | 7B | 优秀 | 中 | ⭐⭐⭐⭐ |
| llama2 | 13B | 一般 | 高 | ⭐⭐⭐ |
| chatglm | 6B | 优秀 | 中 | ⭐⭐⭐⭐ |

## 🎉 完成！

安装完成后，您就可以享受真正的AI对话了！

- **不再是预设答案**
- **真正的智能回答**
- **完全免费使用**
- **数据完全隐私**

开始您的AI育儿助手之旅吧！🤖💕
