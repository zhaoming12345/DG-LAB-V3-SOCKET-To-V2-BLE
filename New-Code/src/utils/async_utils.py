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
                # 如果事件循环已经在运行，创建一个任务
                # 使用ensure_future而不是create_task，以便更好地处理任务嵌套
                future = asyncio.ensure_future(func(*args, **kwargs))
                # 返回future以便调用者可以等待结果
                return future
            else:
                # 如果事件循环未运行，使用run_until_complete
                return loop.run_until_complete(func(*args, **kwargs))
        return wrapper
    return decorator


def run_in_executor(func):
    """
    装饰器，用于在线程池执行器中运行同步函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, lambda: func(*args, **kwargs))
    return wrapper

def run_async(func):
    """
    装饰器，用于运行异步函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        # 检查当前是否已经在事件循环中运行
        if loop.is_running():
            # 如果已经在事件循环中，使用ensure_future而不是create_task
            return asyncio.ensure_future(func(*args, **kwargs))
        else:
            # 如果不在事件循环中，使用run_until_complete
            return loop.run_until_complete(func(*args, **kwargs))
    return wrapper