from backend.net_simulation import mininet_manager as mm
from backend.utils.logger import start_new_intent_log, get_latest_log_file
from backend.utils.ryu_utils import get_all_switch_ids
from ryu_app.auto_generate_path_intents import build_and_send_all_path_intents
import json
import os
import requests
import time

class TopologyAgent:
    def __init__(self):
        pass

    def create_topology(self, instruction: dict) -> str:
        start_new_intent_log()
        result = mm.rebuild_topology(instruction)

        if mm.global_net:
            net = mm.global_net
            expected_hosts = len(net.hosts)
            if self._wait_for_all_hosts(expected=expected_hosts):
                build_and_send_all_path_intents(net)
                print("[INTENT] 路径流表下发完成 ✅")
            else:
                print(f"[INTENT] ❌ 等待超时，期望注册 {expected_hosts} 台主机，实际不足")
        return result

    def shutdown_topology(self) -> str:
        return mm.stop_topology()

    def link_down(self, instruction: dict) -> str:
        try:
            resp = requests.post(
                "http://localhost:8081/intent/link_down",
                json={"link": instruction.get("link", [])},
                timeout=2
            )
            return resp.text if resp.status_code == 200 else f"❌ 控制器返回错误: {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"❌ 无法连接控制器 REST 接口: {e}"

    def link_up(self, instruction: dict) -> str:
        log_path = get_latest_log_file()
        if not log_path or not os.path.exists(log_path):
            return "❌ 当前 session 没有找到日志文件，无法执行 link_up"

        try:
            from backend.net_simulation.instruction_executor import execute_instruction, SKIP_ACTIONS_ON_RECOVERY

            target_link = instruction.get("link", [])
            link_variants = [target_link, target_link[::-1]]
            with open(log_path, "r", encoding="utf-8") as f:
                blocks = f.read().split("\n\n")
                instructions = []
                for block in blocks:
                    if not block.strip():
                        continue
                    entry = json.loads(block)
                    instr = entry.get("instruction", {})
                    if not instr:
                        continue
                    if instr.get("action") == "link_down" and instr.get("link") in link_variants:
                        continue
                    if instr.get("action") in SKIP_ACTIONS_ON_RECOVERY:
                        continue
                    instructions.append(instr)

            mm.stop_topology()

            results = []
            for idx, instr in enumerate(instructions):
                result = execute_instruction(instr)
                results.append(f"[REPLAY 回放动作 {idx+1}] [{instr.get('action')}] => {result}")
            return "✅ link_up 完成，已恢复拓扑并保留其他断链操作\n" + "\n".join(results)

        except Exception as e:
            return f"❌ link_up 执行失败: {e}"

    def _wait_for_all_hosts(self, expected=9, timeout=10):
        for _ in range(timeout):
            try:
                resp = requests.get("http://localhost:8081/intent/valid_hosts")
                if resp.status_code == 200:
                    hosts = resp.json()
                    if len(hosts) >= expected:
                        return True
            except Exception:
                pass
            time.sleep(1)
        return False
