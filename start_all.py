# start_all.py
import threading
import logging
import os
import sys
from ryu import cfg
from ryu.base import app_manager
from ryu.controller.controller import Datapath
from ryu.app import wsgi

# ✅ 加载你的 Ryu 控制器和 API 控制模块
import backend.controller.PathIntentController  # 注册 controller
import backend.controller.ryu_topology_rest    # REST API for topology
import ryu.app.ofctl_rest
import ryu.app.rest_topology
import ryu.topology.switches

# ✅ Flask App 导入
from backend.api.app import app as flask_app

# from backend.coordinator.coordinator_agent import CoordinatorAgent
from backend.agents.flow_agent import FlowAgent
from backend.agents.qa_agent import QAAgent
from backend.agents.topology_agent import TopologyAgent
from backend.agents.json_builder_agent import JSONBuilderAgent
from backend.agents.intent_agent import IntentAgent
from backend.agents.executor_agent import ExecutorAgent



def main():
    # ✅ 初始化所有 Agent（独立，互不依赖）
    flow_agent = FlowAgent()
    qa_agent = QAAgent()
    topo_agent = TopologyAgent()
    json_builder_agent = JSONBuilderAgent()
    # coordinator = CoordinatorAgent()
    intent_agent = IntentAgent()
    executor_agent = ExecutorAgent()
    print("✅ 所有 Agent 初始化完成")

# ✅ 设置 Ryu 日志写入文件（避免和 Flask 冲突）
def setup_ryu_logging():
    log_path = "/data/gjw/logs/ryu.log"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger = logging.getLogger("RYU")
    handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger


def start_ryu():
    CONF = cfg.CONF
    CONF(args=[
        '--observe-links',
        '--ofp-tcp-listen-port', '6633',
        '--wsapi-port', '8081'
    ])

    logger = setup_ryu_logging()
    logger.info("✅ 正在启动 Ryu 控制器...")

    app_mgr = app_manager.AppManager.get_instance()
    app_mgr.run_apps([
        'ryu.app.ofctl_rest',
        'ryu.app.rest_topology',
        'ryu.topology.switches',
        'backend.controller.PathIntentController',
        'backend.controller.ryu_topology_rest'
    ])


def start_flask():
    # Flask 输出到控制台即可
    print("✅ 正在启动 Flask Web API at http://localhost:5000")
    flask_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
    # ✅ 启动 Ryu（在子线程中）
    t1 = threading.Thread(target=start_ryu, daemon=True)
    t1.start()

    # ✅ 启动 Flask（主线程）
    start_flask()
