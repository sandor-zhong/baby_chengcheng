"""
AI助手功能蓝图
包含：AI聊天、分析时光记录、健康建议等功能
"""
import os
import json
import hashlib
import time
from datetime import datetime, timedelta, timezone, date
from flask import Blueprint, render_template, request, jsonify, current_app
from models import db, Event, Moment
from sqlalchemy import func
from functools import wraps

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)

# 创建蓝图
ai_bp = Blueprint('ai', __name__)

# AI配置 - 使用免费的本地模型
AI_MODEL_TYPE = "ollama"  # 可选: "openai", "ollama", "mock"
OLLAMA_BASE_URL = "http://localhost:11434"  # Ollama默认地址
AI_FAST_MODE = True  # 快速模式：减少回答长度，提高速度

# 缓存装饰器
def cache_response(timeout=300):
    """缓存响应装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成缓存键
            cache_key = hashlib.md5(f"{f.__name__}{args}{kwargs}".encode()).hexdigest()
            
            # 检查缓存（这里使用简单的内存缓存，生产环境建议使用Redis）
            if hasattr(cache_response, 'cache'):
                if cache_key in cache_response.cache:
                    cached_data, timestamp = cache_response.cache[cache_key]
                    if time.time() - timestamp < timeout:
                        return cached_data
            
            # 执行函数
            result = f(*args, **kwargs)
            
            # 存储到缓存
            if not hasattr(cache_response, 'cache'):
                cache_response.cache = {}
            cache_response.cache[cache_key] = (result, time.time())
            
            return result
        return decorated_function
    return decorator

def get_baby_profile():
    """获取宝宝信息"""
    profile_path = os.path.join(current_app.instance_path, 'profile.json')
    if os.path.exists(profile_path):
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def ai_chat(prompt, context=""):
    """AI聊天功能 - 支持多种免费模型"""
    try:
        # 构建系统提示
        if AI_FAST_MODE:
            system_prompt = """你是育儿助手。请用简洁、实用的语言回答育儿问题。回答要简短（100字以内），直接给出3-5个要点建议。用中文回答。"""
        else:
            system_prompt = """你是一个专业的育儿助手，专门帮助新手父母解决育儿问题。请用温暖、专业、易懂的语言回答育儿相关问题。
            
            你的回答应该：
            1. 基于科学的育儿知识
            2. 考虑宝宝的安全和健康
            3. 提供实用的建议
            4. 用温和、鼓励的语气
            5. 如果涉及医疗问题，建议咨询专业医生
            
            请用中文回答，语言要亲切自然。"""
        
        # 如果有上下文信息，添加到提示中
        if context:
            full_prompt = f"上下文信息：{context}\n\n用户问题：{prompt}"
        else:
            full_prompt = prompt
        
        if AI_MODEL_TYPE == "ollama":
            return ai_chat_ollama(full_prompt, system_prompt)
        elif AI_MODEL_TYPE == "openai":
            return ai_chat_openai(full_prompt, system_prompt)
        else:
            return ai_chat_mock(full_prompt)
            
    except Exception as e:
        return f"AI助手暂时无法回答，请稍后再试。错误：{str(e)}"

def ai_chat_ollama(prompt, system_prompt):
    """使用Ollama本地模型（带缓存优化）"""
    try:
        import requests
        import hashlib

        # 简单的缓存机制
        cache_key = hashlib.md5(prompt.encode()).hexdigest()[:8]
        cache_file = f"cache/ai_cache_{cache_key}.txt"

        # 检查缓存
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_response = f.read()
                if cached_response and len(cached_response) > 10:
                    return f"[缓存回答] {cached_response}"

        # 使用已安装的模型
        model_name = "gemma3:1b"  # 使用您已安装的模型
        
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", 
                               json={
                                   "model": model_name,
                                   "prompt": f"{system_prompt}\n\n{prompt}",
                                   "stream": False,
                                   "options": {
                                       "temperature": 0.7,
                                       "top_p": 0.9,
                                       "max_tokens": 300,  # 限制回答长度，提高速度
                                       "num_predict": 200,  # 预测token数量
                                       "repeat_penalty": 1.1,
                                       "stop": ["\n\n", "用户:", "问题:"]
                                   }
                               }, timeout=15)  # 减少超时时间
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get('response', '抱歉，无法生成回答。')
            
            # 保存到缓存
            try:
                os.makedirs('cache', exist_ok=True)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(ai_response)
            except:
                pass  # 缓存失败不影响主要功能
            
            return ai_response
        else:
            return f"Ollama服务错误：{response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return "无法连接到Ollama服务，请确保Ollama已启动。\n\n安装方法：\n1. 访问 https://ollama.ai/\n2. 下载并安装Ollama\n3. 运行: ollama pull qwen\n4. 启动Ollama服务"
    except Exception as e:
        return f"Ollama调用失败：{str(e)}"

def ai_chat_openai(prompt, system_prompt):
    """使用OpenAI API"""
    try:
        import openai
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI调用失败：{str(e)}"

def ai_chat_mock(prompt):
    """智能模拟AI回答（根据问题内容匹配回答）"""
    # 关键词匹配回答
    prompt_lower = prompt.lower()
    
    # 哭闹相关问题
    if any(keyword in prompt_lower for keyword in ['哭', '闹', '哭闹', '哭闹', '烦躁', '不安']):
        return "宝宝哭闹是很正常的现象，可以尝试以下方法：\n1. 检查是否饿了、困了或需要换尿布\n2. 轻柔的抚摸和轻声安慰\n3. 抱着宝宝轻轻摇晃\n4. 播放轻柔的音乐\n5. 如果持续哭闹，建议咨询儿科医生"
    
    # 睡眠相关问题
    elif any(keyword in prompt_lower for keyword in ['睡觉', '睡眠', '哄睡', '入睡', '不睡', '夜醒']):
        return "关于宝宝睡眠，建议：\n1. 建立规律的睡眠时间\n2. 创造安静、舒适的睡眠环境\n3. 睡前进行轻柔的活动（如洗澡、按摩）\n4. 避免过度刺激\n5. 保持耐心，每个宝宝的睡眠习惯都不同"
    
    # 喂养相关问题
    elif any(keyword in prompt_lower for keyword in ['吃', '喂', '奶', '饭', '不吃饭', '厌食', '挑食']):
        return "关于宝宝喂养，建议：\n1. 保持规律的喂食时间\n2. 创造愉快的用餐环境\n3. 不要强迫宝宝进食\n4. 尝试不同的食物和口味\n5. 如果持续不吃饭，建议咨询儿科医生"
    
    # 健康相关问题
    elif any(keyword in prompt_lower for keyword in ['发烧', '感冒', '生病', '体温', '健康', '症状']):
        return "关于宝宝健康，建议：\n1. 定期测量体温，正常体温为36.5-37.5°C\n2. 注意观察宝宝的精神状态\n3. 保持宝宝周围环境清洁\n4. 如有异常症状，及时咨询儿科医生\n5. 预防胜于治疗，注意日常护理"
    
    # 发育相关问题
    elif any(keyword in prompt_lower for keyword in ['发育', '成长', '身高', '体重', '里程碑', '能力']):
        return "关于宝宝发育，建议：\n1. 每个宝宝的发育速度都不同，不要过度比较\n2. 多与宝宝互动，促进大脑发育\n3. 提供丰富的感官刺激\n4. 定期进行体检，关注发育指标\n5. 如有发育疑虑，及时咨询儿科医生"
    
    # 安全相关问题
    elif any(keyword in prompt_lower for keyword in ['安全', '危险', '防护', '意外', '受伤']):
        return "关于宝宝安全，建议：\n1. 确保宝宝周围环境安全，移除危险物品\n2. 使用安全座椅和防护用品\n3. 不要让宝宝独自留在高处\n4. 学习基本的急救知识\n5. 定期检查玩具和用品的安全性"
    
    # 情感相关问题
    elif any(keyword in prompt_lower for keyword in ['情感', '情绪', '心理', '安全感', '依恋']):
        return "关于宝宝情感发展，建议：\n1. 多与宝宝进行眼神交流和身体接触\n2. 及时回应宝宝的需求\n3. 创造温暖、安全的家庭环境\n4. 建立稳定的日常作息\n5. 给予宝宝足够的关爱和关注"
    
    # 默认回答
    else:
        return "感谢您的提问！作为育儿助手，我建议：\n1. 保持耐心，每个宝宝都是独特的\n2. 多观察宝宝的行为和需求\n3. 建立规律的日常作息\n4. 及时咨询专业医生\n5. 相信自己的育儿直觉，您是最了解宝宝的人"

def ai_analyze_moments():
    """AI分析时光记录"""
    try:
        # 获取最近的时光记录
        recent_moments = Moment.query.order_by(Moment.timestamp.desc()).limit(10).all()
        
        if not recent_moments:
            return "暂无时光记录可供分析"
        
        # 构建分析内容
        moments_text = ""
        for moment in recent_moments:
            moments_text += f"时间：{moment.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
            moments_text += f"内容：{moment.content}\n"
            if moment.image_path:
                moments_text += f"包含图片\n"
            if moment.video_path:
                moments_text += f"包含视频\n"
            moments_text += "---\n"
        
        prompt = f"请分析以下宝宝的成长记录，提供专业的观察和建议：\n\n{moments_text}"
        
        return ai_chat(prompt)
    except Exception as e:
        return f"分析失败：{str(e)}"

def ai_health_advice():
    """AI健康建议"""
    try:
        # 获取宝宝信息
        profile = get_baby_profile()
        baby_age = profile.get('age', '未知')
        baby_birth = profile.get('birth', '未知')
        
        # 获取最近的喂奶记录
        recent_feeds = Event.query.filter(Event.type == 'feed').order_by(Event.timestamp.desc()).limit(5).all()
        feed_summary = ""
        if recent_feeds:
            total_ml = sum(f.amount_ml for f in recent_feeds if f.amount_ml)
            feed_summary = f"最近5次喂奶总量：{total_ml}ml"
        
        context = f"宝宝年龄：{baby_age}\n出生日期：{baby_birth}\n{feed_summary}"
        
        prompt = "请根据宝宝的年龄和喂养情况，提供专业的健康建议和注意事项。"
        
        return ai_chat(prompt, context)
    except Exception as e:
        return f"获取健康建议失败：{str(e)}"

@ai_bp.route('/ai')
def ai_page():
    """AI助手页面"""
    return render_template('ai.html')

@ai_bp.route('/api/ai/chat', methods=['POST'])
def ai_chat_api():
    """AI聊天API"""
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({'success': False, 'error': '请输入问题'})
    
    # 获取宝宝信息作为上下文
    profile = get_baby_profile()
    context = f"宝宝年龄：{profile.get('age', '未知')}\n出生日期：{profile.get('birth', '未知')}"
    
    answer = ai_chat(question, context)
    
    return jsonify({'success': True, 'answer': answer})

@ai_bp.route('/api/ai/analyze', methods=['POST'])
def ai_analyze_api():
    """AI分析时光记录API"""
    analysis = ai_analyze_moments()
    return jsonify({'success': True, 'analysis': analysis})

@ai_bp.route('/api/ai/health', methods=['POST'])
def ai_health_api():
    """AI健康建议API"""
    advice = ai_health_advice()
    return jsonify({'success': True, 'advice': advice})
