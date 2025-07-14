# backend/controller/controller_instance.py



# ⚠️ 创建控制器上下文模拟器（可选）
# 或者通过 wsgi 或 app_manager 获取已运行的实例

# 假设你在主启动器已加载 PathIntentController

# 在这里暴露 controller_instance = 已经注册的 PathIntentController
# 通常你可以通过 app_manager.lookup_service_brick 来获取

# backend/controller/controller_instance.py

from ryu.base.app_manager import lookup_service_brick
import time
def get_controller_instance(timeout=5):
    """
    等待 Ryu 注册控制器实例，避免 None
    """
    for i in range(timeout):
        instance = lookup_service_brick("PathIntentController")
        if instance is not None:
            return instance
        time.sleep(1)
    return None

