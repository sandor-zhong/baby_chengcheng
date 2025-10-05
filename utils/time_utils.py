"""
时间工具模块
"""
from datetime import datetime, timezone, timedelta, date
from typing import Optional


# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)


def format_elapsed(delta: timedelta) -> str:
    """格式化时间差为 HH:MM 格式"""
    total_minutes = int(delta.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def calc_age_months(birth_date: date) -> int:
    """计算年龄（月数）"""
    today = date.today()
    years = today.year - birth_date.year
    months = today.month - birth_date.month
    
    if today.day < birth_date.day:
        months -= 1
    
    return years * 12 + months


def add_months(d: date, months: int) -> date:
    """给日期添加指定月数"""
    year = d.year
    month = d.month + months
    
    while month > 12:
        year += 1
        month -= 12
    
    while month < 1:
        year -= 1
        month += 12
    
    # 处理月末日期
    try:
        return date(year, month, d.day)
    except ValueError:
        # 如果目标月份没有对应日期，使用该月最后一天
        if month == 12:
            return date(year + 1, 1, 1) - timedelta(days=1)
        else:
            return date(year, month + 1, 1) - timedelta(days=1)
