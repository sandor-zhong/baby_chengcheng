@echo off
echo 🚀 正在安装Ollama AI模型...
echo.

echo 📥 步骤1: 下载Ollama
echo 请访问: https://ollama.ai/
echo 下载并安装Ollama
echo.
pause

echo 📦 步骤2: 安装中文AI模型
echo 正在安装Qwen模型（中文支持最好）...
ollama pull qwen
echo.

echo 🔧 步骤3: 启动Ollama服务
echo 正在启动Ollama服务...
start ollama serve
echo.

echo ⏳ 等待服务启动...
timeout /t 5 /nobreak > nul

echo 🧪 步骤4: 测试AI模型
echo 正在测试Qwen模型...
ollama run qwen "你好，请介绍一下自己"
echo.

echo ✅ 安装完成！
echo.
echo 🎯 现在您可以：
echo 1. 访问 http://localhost:9000/ai
echo 2. 享受真正的AI对话
echo 3. 获得智能的育儿建议
echo.
echo 💡 注意：首次运行可能需要一些时间来加载模型
echo.
pause
