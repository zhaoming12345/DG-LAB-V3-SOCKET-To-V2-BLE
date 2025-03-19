import functools
import asyncio
from PySide6.QtCore import QObject, Slot

def asyncSlot(*args, **kwargs):
    """异步槽函数装饰器
    
    用于将异步函数转换为Qt槽函数，使其可以在Qt信号系统中使用。
    这个装饰器会自动处理异步函数的执行。
    
    Args:
        *args: 传递给Slot装饰器的参数
        **kwargs: 传递给Slot装饰器的关键字参数
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @functools.wraps(func)
        @Slot(*args, **kwargs)
        def wrapper(*args, **kwargs):
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已经在运行，创建一个新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(func(*args, **kwargs))
        return wrapper
    return decorator 