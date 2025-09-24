# AI功能设置说明

## 功能特性

### 🤖 AI育儿助手
- **智能问答**：回答各种育儿问题
- **成长分析**：分析宝宝的成长记录
- **健康建议**：基于宝宝年龄和喂养情况提供个性化建议
- **育儿贴士**：提供实用的育儿技巧

## 设置步骤

### 1. 获取OpenAI API密钥
1. 访问 [OpenAI官网](https://platform.openai.com/)
2. 注册账号并登录
3. 在API Keys页面创建新的API密钥
4. 复制API密钥

### 2. 配置API密钥
有三种方式配置：

#### 方式一：环境变量（推荐）
```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-actual-api-key-here"

# Windows CMD
set OPENAI_API_KEY=sk-your-actual-api-key-here

# Linux/Mac
export OPENAI_API_KEY="sk-your-actual-api-key-here"
```

#### 方式二：创建.env文件
在项目根目录创建 `.env` 文件：
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

#### 方式三：修改代码（临时测试用）
在 `app.py` 第18行修改：
```python
openai.api_key = 'sk-your-actual-api-key-here'
```

**注意**：请将 `sk-your-actual-api-key-here` 替换为您的实际API密钥。

### 3. 启动应用
```bash
python app.py
```

### 4. 访问AI功能
- 打开浏览器访问 `http://localhost:9000`
- 点击封面右下角的机器人图标
- 开始使用AI助手功能

## 功能说明

### 💬 智能问答
- 输入育儿问题，获得专业回答
- 支持中文问答
- 基于宝宝信息提供个性化建议

### 📊 成长分析
- AI分析最近的时光记录
- 提供专业的观察和建议
- 帮助了解宝宝的发展状况

### ❤️ 健康建议
- 基于宝宝年龄和喂养情况
- 提供个性化的健康建议
- 关注宝宝的安全和健康

### 💡 育儿贴士
- 随机显示实用的育儿技巧
- 帮助新手父母学习育儿知识

## 注意事项

1. **API费用**：使用OpenAI API会产生费用，请合理使用
2. **网络连接**：需要稳定的网络连接
3. **数据隐私**：AI分析会使用您的记录数据，请确保数据安全
4. **医疗建议**：AI建议仅供参考，涉及医疗问题请咨询专业医生

## 故障排除

### 常见问题

1. **API密钥错误**
   - 检查API密钥是否正确
   - 确认API密钥有足够的额度

2. **网络连接问题**
   - 检查网络连接
   - 确认可以访问OpenAI服务

3. **AI回答异常**
   - 检查问题是否清晰明确
   - 尝试重新提问

4. **OpenAI API版本兼容性问题**
   - 如果遇到 `openai.ChatCompletion` 错误，说明使用的是新版本OpenAI库
   - 应用已自动适配新版本API，无需手动修改
   - 如果仍有问题，可以尝试降级：`pip install openai==0.28`

## 技术支持

如有问题，请检查：
1. API密钥配置
2. 网络连接
3. 应用日志
4. OpenAI服务状态
