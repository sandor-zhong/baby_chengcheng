# Render 部署指南

## 部署步骤

### 1. 准备工作
1. 确保您的代码已推送到GitHub仓库
2. 在Render注册账号并连接GitHub

### 2. 创建Web服务
1. 登录 [Render Dashboard](https://dashboard.render.com/)
2. 点击 "New +" → "Web Service"
3. 连接您的GitHub仓库
4. 选择您的 `flask_baby_reminder` 仓库

### 3. 配置服务
- **Name**: `flask-baby-reminder` (或您喜欢的名称)
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

### 4. 环境变量设置
在Render Dashboard中设置以下环境变量：

#### 必需的环境变量：
- `FLASK_ENV`: `production`
- `SECRET_KEY`: 生成一个随机密钥（可以使用 `python -c "import secrets; print(secrets.token_hex(32))"`）
- `AI_MODEL_TYPE`: `mock` (使用模拟AI，避免API费用)
- `AI_FAST_MODE`: `true`

# 已移除提醒功能相关配置

#### 其他可选的环境变量：
- `MAX_UPLOAD_MB`: `15` (最大上传文件大小，MB)

### 5. 数据库设置
1. 在Render Dashboard中创建PostgreSQL数据库：
   - 点击 "New +" → "PostgreSQL"
   - 选择免费计划
   - 记录数据库连接信息

2. 数据库会自动通过 `DATABASE_URL` 环境变量连接

### 6. 部署
1. 点击 "Create Web Service"
2. Render会自动开始构建和部署
3. 等待部署完成（通常需要5-10分钟）

### 7. 访问应用
部署完成后，您会获得一个类似 `https://your-app-name.onrender.com` 的URL

## 注意事项

### 免费计划限制：
- 应用在15分钟无活动后会自动休眠
- 重新启动需要30-60秒
- 每月有750小时运行时间限制

### 文件存储：
- Render的免费计划不支持持久化文件存储
- 上传的图片和视频会在应用重启后丢失
- 建议使用云存储服务（如AWS S3、Cloudinary等）

### AI功能：
- 部署时使用 `mock` 模式，避免API费用
- 如需真实AI功能，需要配置OpenAI API密钥

# 已移除提醒功能

## 故障排除

### 常见问题：
1. **构建失败**: 检查 `requirements.txt` 中的依赖版本
2. **数据库连接失败**: 确保PostgreSQL数据库已创建
3. **静态文件404**: 检查文件路径和权限

### 查看日志：
在Render Dashboard的 "Logs" 标签页查看详细日志

## 升级到付费计划
如需更好的性能和持久化存储，可以考虑升级到付费计划：
- 应用不会休眠
- 支持持久化文件存储
- 更好的性能
