#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cookie Clicker 桥接服务（可被 GUI / 测试独立导入，无 tkinter 依赖）
=====================================================================
- POST /report  <- 游戏页面上报 {cookies, cps, heavenly, lumps}
- GET  /command -> 返回待下发的指令 {set, setHeavenly, setLumps, spawnGolden}，消费后清空
- 共享状态 latest / pending_set 由本模块持有，GUI 与 HTTP 线程均可访问
"""

import http.server
import json
import threading
import time

TOOL_PORT = 8089

# ===== 共享状态（多线程安全）=====
latest = {"cookies": 0.0, "cps": 0.0, "heavenly": 0.0, "lumps": -1.0, "ts": 0.0}
latest_lock = threading.Lock()

pending_set = [None]          # 待下发的“设置饼干数”指令，消费后清空
pending_set_heavenly = [None] # 待下发的“设置天堂碎片”指令，消费后清空
pending_set_lumps = [None]    # 待下发的“设置糖果块”指令，消费后清空
pending_spawn_golden = [False]  # 待下发的“召唤黄金饼干”一次性指令，消费后清空
pending_lock = threading.Lock()


class BridgeHandler(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, *args):
        pass  # 静默

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/command"):
            with pending_lock:
                v = pending_set[0]
                pending_set[0] = None
                vh = pending_set_heavenly[0]
                pending_set_heavenly[0] = None
                vl = pending_set_lumps[0]
                pending_set_lumps[0] = None
                sg = pending_spawn_golden[0]
                pending_spawn_golden[0] = False
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "set": v, "setHeavenly": vh, "setLumps": vl, "spawnGolden": sg
            }).encode("utf-8"))
        else:
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("CookieClickerTool bridge OK".encode("utf-8"))

    def do_POST(self):
        if self.path.startswith("/report"):
            try:
                n = int(self.headers.get("Content-Length", "0") or "0")
                body = self.rfile.read(n) if n > 0 else b"{}"
                data = json.loads(body.decode("utf-8", "replace") or "{}")
                with latest_lock:
                    latest["cookies"] = float(data.get("cookies", latest["cookies"]))
                    latest["cps"] = float(data.get("cps", latest["cps"]))
                    latest["heavenly"] = float(data.get("heavenly", latest["heavenly"]))
                    latest["lumps"] = float(data.get("lumps", latest["lumps"]))
                    latest["ts"] = time.time()
            except Exception:
                pass
            self.send_response(200)
        else:
            self.send_response(404)
        self._cors()
        self.end_headers()


def start_bridge_server(host="0.0.0.0", port=TOOL_PORT):
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    srv = http.server.ThreadingHTTPServer((host, port), BridgeHandler)
    srv.serve_forever()


if __name__ == "__main__":
    start_bridge_server()
