# 项目架构文档

## 项目结构

```
flask_baby_reminder/
├── app.py                 # 应用工厂函数和主入口
├── config.py             # 配置管理
├── models.py             # 数据模型
├── requirements.txt      # 依赖管理
├── blueprints/           # 蓝图模块
│   ├── __init__.py
│   ├── main.py          # 主要功能（喂奶、换尿布等）
│   ├── moments.py       # 时光记录功能
│   ├── ai.py            # AI助手功能
│   ├── profile.py       # 用户资料管理
│   └── auth.py          # 用户认证
├── services/            # 服务层
│   ├── __init__.py
│   ├── user_service.py  # 用户服务
│   └── event_service.py # 事件服务
├── utils/               # 工具模块
│   ├── __init__.py
│   ├── decorators.py    # 装饰器
│   ├── time_utils.py    # 时间工具
│   └── static_utils.py  # 静态资源工具
├── templates/           # 模板文件
├── static/             # 静态资源
├── migrations/         # 数据库迁移
└── instance/           # 实例文件夹
```

## 架构设计原则

### 1. 分层架构
- **表示层（Presentation Layer）**: 蓝图和模板
- **业务逻辑层（Business Logic Layer）**: 服务层
- **数据访问层（Data Access Layer）**: 模型层

### 2. 关注点分离
- **配置管理**: `config.py` 统一管理所有配置
- **业务逻辑**: 服务层处理复杂的业务逻辑
- **数据模型**: 模型层只负责数据定义和基础操作
- **工具函数**: 工具模块提供可复用的功能

### 3. 依赖注入
- 使用Flask的应用工厂模式
- 通过配置类管理不同环境的配置
- 服务层通过静态方法提供服务

## 模块说明

### 配置管理 (`config.py`)
- 基础配置类 `Config`
- 开发环境配置 `DevelopmentConfig`
- 生产环境配置 `ProductionConfig`
- 支持环境变量覆盖

### 数据模型 (`models.py`)
- `User`: 用户模型，包含认证信息
- `Event`: 事件模型（喂奶、换尿布记录）
- `Moment`: 时光记录模型
- 每个模型包含基础的数据验证和序列化方法

### 服务层 (`services/`)
- `UserService`: 用户相关业务逻辑
- `EventService`: 事件相关业务逻辑
- 提供静态方法，便于测试和复用

### 工具模块 (`utils/`)
- `decorators.py`: 装饰器（登录验证、权限控制、缓存等）
- `time_utils.py`: 时间相关工具函数
- `static_utils.py`: 静态资源管理

### 蓝图模块 (`blueprints/`)
- 每个蓝图负责特定的功能模块
- 使用统一的装饰器进行权限控制
- 通过服务层处理业务逻辑

## 最佳实践

### 1. 错误处理
- 使用装饰器统一处理异常
- 在服务层进行业务逻辑验证
- 在蓝图层处理HTTP响应

### 2. 权限控制
- `@login_required`: 登录验证
- `@premium_required`: 会员权限验证
- 在装饰器中统一处理权限逻辑

### 3. 缓存策略
- 使用装饰器实现响应缓存
- 静态资源设置长期缓存
- 动态内容禁用缓存

### 4. 数据库优化
- 在模型定义中创建索引
- 使用复合索引优化查询
- 在应用启动时创建必要索引

### 5. 配置管理
- 使用环境变量管理敏感信息
- 不同环境使用不同配置类
- 支持配置继承和覆盖

## 扩展指南

### 添加新功能
1. 在 `models.py` 中定义数据模型
2. 在 `services/` 中创建对应的服务类
3. 在 `blueprints/` 中创建蓝图
4. 在 `app.py` 中注册蓝图

### 添加新的装饰器
1. 在 `utils/decorators.py` 中定义
2. 在需要的蓝图中导入使用

### 添加新的工具函数
1. 在 `utils/` 中创建对应的模块
2. 按功能分类组织工具函数
3. 提供清晰的文档和类型提示
