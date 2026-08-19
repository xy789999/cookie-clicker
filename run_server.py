#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cookie Clicker 一键开服脚本
===========================
双击本文件即可启动本地服务器，并自动打开浏览器进入游戏。
游戏目录：本脚本同级的 cookieclicker/ 文件夹。
按 Ctrl+C 关闭服务器。
"""

import http.server
import os
import socketserver
import sys
import webbrowser

# 游戏目录：脚本所在目录下的 cookieclicker/
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookieclicker")

if not os.path.isdir(BASE_DIR):
    print(f"[错误] 未找到游戏目录：{BASE_DIR}")
    print("请确认 cookieclicker/ 文件夹与本脚本在同一目录下。")
    input("按回车退出...")
    sys.exit(1)

PORT = 8080
HOST = "127.0.0.1"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, fmt, *args):
        # 安静日志：只在控制台打印一行
        sys.stdout.write("[\u8bbf\u95ee] %s - %s\n" % (self.address_string(), fmt % args))


def find_free_port(host, start_port, max_tries=50):
    """从 start_port 起找一个空闲端口。"""
    import socket
    for p in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    return None


# 允许地址复用，避免重启时报 Address already in use
class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    port = find_free_port(HOST, PORT)
    if port is None:
        print(f"[错误] 端口 {PORT}~{PORT + 50} 均被占用，请先关闭占用端口的程序。")
        input("按回车退出...")
        sys.exit(1)

    url = f"http://{HOST}:{port}/"
    os.chdir(BASE_DIR)
    with ReusableTCPServer((HOST, port), Handler) as httpd:
        print("=" * 48)
        print("  Cookie Clicker 本地服务器已启动")
        print("  游戏地址：", url)
        print("  游戏目录：", BASE_DIR)
        print("  关闭：在本窗口按 Ctrl+C")
        print("=" * 48)
        try:
            webbrowser.open(url)
        except Exception:
            print("（浏览器未能自动打开，请手动复制上面的地址到浏览器）")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[关闭] 服务器已停止。")
            httpd.shutdown()


if __name__ == "__main__":
    main()
