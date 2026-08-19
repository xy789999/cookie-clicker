#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cookie Clicker 本地服务器 - 图形界面版 (Tkinter)
================================================
- 可编辑监听 IP 与端口（服务器停止时）
- 实时显示“当前访问地址”，所有按钮（启动/打开浏览器/复制地址）都跟随该地址
- 点击“启动服务器”自动打开浏览器；关闭窗口即停止服务
"""

import http.server
import os
import socket
import socketserver
import sys
import threading
import webbrowser

import tkinter as tk
from tkinter import scrolledtext, messagebox

# ===== 默认配置（仅作初始值，可在界面修改）=====
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
GAME_DIR_NAME = "cookieclicker"   # 游戏目录名（与本程序同级）


def _base_dir():
    """定位游戏根目录：优先用 exe 所在目录（打包后），否则用脚本目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


GAME_DIR = os.path.join(_base_dir(), GAME_DIR_NAME)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=GAME_DIR, **kwargs)

    def log_message(self, fmt, *args):
        app_log("[访问] %s - %s\n" % (self.address_string(), fmt % args))


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


# ===== 全局状态 =====
server = None
server_thread = None
running_host = None
running_port = None


def is_valid_ip(ip):
    try:
        socket.inet_aton(ip)
        return True
    except OSError:
        return False


def validate_inputs(host, port):
    """校验 IP 与端口，返回 (ok, errmsg)。"""
    if not is_valid_ip(host):
        return False, "IP 地址无效：%s（示例 127.0.0.1 或 0.0.0.0）" % host
    try:
        p = int(port)
    except ValueError:
        return False, "端口必须是整数：%s" % port
    if not (1 <= p <= 65535):
        return False, "端口需在 1~65535 之间：%s" % port
    return True, ""


def browser_url(host, port):
    """浏览器打开用的地址：监听 0.0.0.0 时用本机回环，便于本地访问。"""
    if host in ("0.0.0.0", ""):
        return "http://127.0.0.1:%d/" % port
    return "http://%s:%d/" % (host, port)


def find_free_port(host, start_port, max_tries=50):
    for p in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    return None


def start_server():
    global server, server_thread, running_host, running_port
    if server is not None:
        app_log("[提示] 服务器已在运行中。\n")
        return
    if not os.path.isdir(GAME_DIR):
        messagebox.showerror("目录缺失", "未找到游戏目录：\n" + GAME_DIR)
        return

    host = ip_var.get().strip()
    port = port_var.get().strip()
    ok, err = validate_inputs(host, port)
    if not ok:
        messagebox.showerror("参数错误", err)
        return

    # 首选输入端口；被占用时在 (port, port+50) 内寻找空闲端口
    free = find_free_port(host, int(port))
    if free is None:
        messagebox.showerror("端口占用", "端口 %s~%s 均被占用，请换一个端口。" % (port, int(port) + 50))
        return

    running_host = host
    running_port = free
    if free != int(port):
        app_log("[提示] 端口 %s 被占用，已自动改用 %d。\n" % (port, free))
        port_var.set(str(free))

    try:
        server = ReusableTCPServer((host, free), QuietHandler)
    except OSError as e:
        messagebox.showerror("启动失败", str(e))
        return

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    url = browser_url(host, free)
    app_log("[已启动] 监听 %s:%d\n" % (host, free))
    app_log("[访问] 浏览器打开：%s\n" % url)
    app_log("[目录] %s\n" % GAME_DIR)
    try:
        webbrowser.open(url)
        app_log("[浏览器] 已自动打开游戏页面。\n")
    except Exception:
        app_log("[浏览器] 未能自动打开，请手动复制地址到浏览器。\n")
    update_status()


def stop_server():
    global server, server_thread, running_host, running_port
    if server is None:
        app_log("[提示] 服务器未运行。\n")
        return
    try:
        server.shutdown()
        server.server_close()
    except Exception as e:
        app_log("[警告] 关闭时：%s\n" % e)
    server = None
    server_thread = None
    running_host = None
    running_port = None
    app_log("[已停止] 服务器已关闭。\n")
    update_status()


def open_browser():
    if running_port is None:
        messagebox.showinfo("未运行", "请先启动服务器，再打开浏览器。")
        return
    url = browser_url(running_host, running_port)
    try:
        webbrowser.open(url)
        app_log("[浏览器] 已打开：%s\n" % url)
    except Exception:
        app_log("[浏览器] 打开失败：%s\n" % url)


def copy_address():
    if running_port is not None:
        url = browser_url(running_host, running_port)
    else:
        host = ip_var.get().strip()
        try:
            p = int(port_var.get().strip())
        except ValueError:
            p = DEFAULT_PORT
        url = browser_url(host, p)
    try:
        root.clipboard_clear()
        root.clipboard_append(url)
        app_log("[复制] 地址已复制到剪贴板：%s\n" % url)
    except Exception:
        app_log("[复制] 复制失败：%s\n" % url)


def app_log(text):
    """线程安全地写入日志框。"""
    try:
        log_box.after(0, _append_log, text)
    except Exception:
        pass


def _append_log(text):
    log_box.insert(tk.END, text)
    log_box.see(tk.END)


def current_preview_url():
    host = ip_var.get().strip()
    try:
        p = int(port_var.get().strip())
    except ValueError:
        p = DEFAULT_PORT
    return browser_url(host, p)


def update_preview():
    """实时预览地址（跟随 IP/端口输入框）。"""
    preview_var.set("当前访问地址： " + current_preview_url())


def update_status():
    if server is not None:
        url = browser_url(running_host, running_port)
        status_var.set("● 运行中   %s" % url)
        status_label.config(fg="#1a8a3c")
        btn_start.config(state=tk.DISABLED)
        btn_stop.config(state=tk.NORMAL)
        btn_open.config(state=tk.NORMAL)
        btn_copy.config(state=tk.NORMAL)
        ip_entry.config(state=tk.DISABLED)
        port_entry.config(state=tk.DISABLED)
    else:
        status_var.set("○ 已停止")
        status_label.config(fg="#a33")
        btn_start.config(state=tk.NORMAL)
        btn_stop.config(state=tk.DISABLED)
        btn_open.config(state=tk.DISABLED)
        btn_copy.config(state=tk.NORMAL)
        ip_entry.config(state=tk.NORMAL)
        port_entry.config(state=tk.NORMAL)
    update_preview()


def on_close():
    stop_server()
    root.destroy()


# ===== 构建界面 =====
root = tk.Tk()
root.title("Cookie Clicker 本地服务器")
root.geometry("600x460")
root.resizable(False, False)

top = tk.Frame(root, padx=16, pady=14)
top.pack(fill=tk.X)

title = tk.Label(top, text="Cookie Clicker 一键开服（GUI）", font=("Microsoft YaHei", 14, "bold"))
title.pack(anchor=tk.W)

# ---- 配置区：IP / 端口 ----
cfg = tk.Frame(top, pady=10)
cfg.pack(fill=tk.X)

tk.Label(cfg, text="监听 IP：", font=("Microsoft YaHei", 11)).pack(side=tk.LEFT)
ip_var = tk.StringVar(value=DEFAULT_HOST)
ip_entry = tk.Entry(cfg, textvariable=ip_var, width=16, font=("Consolas", 11))
ip_entry.pack(side=tk.LEFT, padx=(0, 14))
ip_entry.bind("<KeyRelease>", lambda e: update_preview())

tk.Label(cfg, text="端口：", font=("Microsoft YaHei", 11)).pack(side=tk.LEFT)
port_var = tk.StringVar(value=str(DEFAULT_PORT))
port_entry = tk.Entry(cfg, textvariable=port_var, width=8, font=("Consolas", 11))
port_entry.pack(side=tk.LEFT, padx=(0, 6))
port_entry.bind("<KeyRelease>", lambda e: update_preview())

# ---- 实时地址预览（跟随输入框）----
preview_var = tk.StringVar()
preview_label = tk.Label(top, textvariable=preview_var, font=("Microsoft YaHei", 10, "bold"), fg="#0b57d0")
preview_label.pack(anchor=tk.W, pady=(0, 2))

status_var = tk.StringVar(value="○ 已停止")
status_label = tk.Label(top, textvariable=status_var, font=("Microsoft YaHei", 11), fg="#a33")
status_label.pack(anchor=tk.W)

note = tk.Label(top, text="停止时可修改 IP/端口；启动后按钮与地址均跟随当前设置。关闭窗口即停止服务。",
                font=("Microsoft YaHei", 9), fg="#666")
note.pack(anchor=tk.W, pady=(2, 0))

# ---- 按钮区（全部跟随当前地址）----
btns = tk.Frame(root, padx=16, pady=8)
btns.pack(fill=tk.X)

btn_start = tk.Button(btns, text="启动服务器", width=12, height=2,
                      bg="#2e7d32", fg="white", font=("Microsoft YaHei", 11, "bold"),
                      command=lambda: threading.Thread(target=start_server, daemon=True).start())
btn_start.pack(side=tk.LEFT, padx=5)

btn_stop = tk.Button(btns, text="停止服务器", width=12, height=2,
                     bg="#c62828", fg="white", font=("Microsoft YaHei", 11, "bold"),
                     command=stop_server, state=tk.DISABLED)
btn_stop.pack(side=tk.LEFT, padx=5)

btn_open = tk.Button(btns, text="打开浏览器", width=12, height=2,
                     font=("Microsoft YaHei", 11),
                     command=open_browser, state=tk.DISABLED)
btn_open.pack(side=tk.LEFT, padx=5)

btn_copy = tk.Button(btns, text="复制地址", width=12, height=2,
                     font=("Microsoft YaHei", 11),
                     command=copy_address)
btn_copy.pack(side=tk.LEFT, padx=5)

# ---- 日志区 ----
log_frame = tk.Frame(root, padx=16, pady=8)
log_frame.pack(fill=tk.BOTH, expand=True)

log_box = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
log_box.pack(fill=tk.BOTH, expand=True)

app_log("[就绪] 游戏目录：%s\n" % GAME_DIR)
if not os.path.isdir(GAME_DIR):
    app_log("[警告] 游戏目录不存在！请确认 cookieclicker/ 与本程序在同一文件夹。\n")

root.protocol("WM_DELETE_WINDOW", on_close)
update_status()
root.mainloop()
