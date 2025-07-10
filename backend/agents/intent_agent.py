from openai import OpenAI

client = OpenAI(api_key="sk-692005762cca46ac9faf28703ae6efe0", base_url="https://api.deepseek.com")

class IntentAgent:
    def __init__(self):
        pass

    def intent_to_code(self, intent_text: str) -> str:
        prompt = f"""
你是一个精通网络仿真的工程师助手，专门使用 Mininet 工具创建网络拓扑。

根据用户的网络意图，生成符合以下要求的完整 Python 代码，代码用于 Mininet 网络仿真：

1. 使用远程控制器 RemoteController，控制器 IP 地址为 '127.0.0.1'，端口为 6633。
2. 代码中必须包含对远程控制器的添加，如：
   net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
3. 代码必须包含从 mininet.net 导入 Mininet，从 mininet.cli 导入 CLI，从 mininet.log 导入 setLogLevel，从 mininet.node 导入 RemoteController。
4. 所有主机和交换机名称严格使用意图中给出的名称（如 h1, s1 等）。
5. 主机必须与交换机连接，交换机之间根据意图连接。
6. 代码必须包括启动网络（net.start()）、进入CLI（CLI(net)）、以及停止网络（net.stop()）。
7. 只输出Python代码，不要解释或多余文字，且不要包含 markdown 格式（如 ```python ```）。
8. 请不要包含 `CLI(net)` 或 `input()` 等交互代码
9. 请勿调用 net.stop()，网络创建后应保持运行状态
示例：

意图：创建一个包含 h1, h2 两台主机，以及 s1 一个交换机的网络拓扑，s1 连接 h1 和 h2。

输出：

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.node import RemoteController

setLogLevel('info')

net = Mininet(controller=RemoteController)

c0 = net.addController('c0', controller=RemoteController, ip='10.20.33.108', port=6633)

h1 = net.addHost('h1')
h2 = net.addHost('h2')
s1 = net.addSwitch('s1')

net.addLink(h1, s1)
net.addLink(h2, s1)

net.start()
CLI(net)
net.stop()

---

用户意图：
{intent_text}

请严格遵循上述要求，仅返回Python代码：
"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Translate user intent to Mininet Python code."},
            {"role": "user", "content": prompt}
        ]

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        code = response.choices[0].message.content.strip()

        if not code:
            raise Exception("LLM 返回为空，请检查提示词")

        print("LLM 返回原始内容:\n", code)
        return code
