#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cookie Clicker 实时监控 / 修改工具 (Tkinter)
==============================================
- 本地 HTTP 桥接服务（127.0.0.1:8089）：
    * 游戏页面(bridge.js)周期性 POST /report 上报 {cookies, cps, heavenly}
    * 本工具通过 GET /command 向游戏下发“设置饼干数 / 天堂碎片”指令
- GUI 实时显示当前饼干数 / 每秒产量 / 天堂碎片，并支持直接修改
- 需配合已注入 bridge.js 的 Cookie Clicker 页面（经本地服务器打开）使用
"""

import threading
import time

import tkinter as tk
from tkinter import messagebox, scrolledtext

# 桥接服务（HTTP 协议 + 共享状态）独立模块，GUI 仅做展示与指令下发
from bridge_server import (
    latest, latest_lock, pending_set, pending_set_heavenly, pending_set_lumps,
    pending_spawn_golden, pending_lock,
    start_bridge_server, TOOL_PORT,
)


def fmt(n):
    try:
        n = float(n)
    except Exception:
        return "0"
    if n == int(n):
        return "{:,}".format(int(n))
    return "{:,.2f}".format(n)


# ===== GUI =====
root = tk.Tk()
root.title("Cookie Clicker 实时工具")
root.geometry("470x640")
root.resizable(True, True)

top = tk.Frame(root, padx=16, pady=12)
top.pack(fill=tk.X)

tk.Label(top, text="Cookie Clicker 实时监控 / 修改",
         font=("Microsoft YaHei", 14, "bold")).pack(anchor=tk.W)

conn_var = tk.StringVar(value="○ 未连接游戏")
conn_label = tk.Label(top, textvariable=conn_var, font=("Microsoft YaHei", 10), fg="#a33")
conn_label.pack(anchor=tk.W, pady=(4, 0))

# ---- 状态展示区（饼干 / 每秒 / 天堂碎片）----
stat = tk.Frame(root, padx=16, pady=4)
stat.pack(fill=tk.X)

cookie_var = tk.StringVar(value="0")
cps_var = tk.StringVar(value="每秒产量：0")
heaven_var = tk.StringVar(value="0")
lumps_var = tk.StringVar(value="未解锁")

tk.Label(stat, text="当前饼干数：", font=("Microsoft YaHei", 11)).pack(anchor=tk.W, pady=(6, 0))
tk.Label(stat, textvariable=cookie_var, font=("Consolas", 22, "bold"), fg="#0b57d0").pack(anchor=tk.W)
tk.Label(stat, textvariable=cps_var, font=("Microsoft YaHei", 10), fg="#555").pack(anchor=tk.W, pady=(2, 0))

tk.Label(stat, text="天堂碎片 (Heavenly Chips)：", font=("Microsoft YaHei", 11)).pack(anchor=tk.W, pady=(10, 0))
tk.Label(stat, textvariable=heaven_var, font=("Consolas", 22, "bold"), fg="#e0a800").pack(anchor=tk.W)

tk.Label(stat, text="糖果块 (Sugar Lumps)：", font=("Microsoft YaHei", 11)).pack(anchor=tk.W, pady=(10, 0))
tk.Label(stat, textvariable=lumps_var, font=("Consolas", 22, "bold"), fg="#c2185b").pack(anchor=tk.W)


def submit_set(target):
    """target: 'cookies' / 'heavenly' / 'lumps'"""
    ev = entry_cookie_var if target == "cookies" else (
        entry_heaven_var if target == "heavenly" else entry_lumps_var)
    raw = ev.get().strip().replace(",", "")
    try:
        v = float(raw)
    except ValueError:
        messagebox.showerror("输入错误", "请输入有效数字：%s" % raw)
        return
    if v < 0:
        messagebox.showerror("输入错误", "数值不能为负。")
        return
    if target == "cookies":
        with pending_lock:
            pending_set[0] = v
        app_log("[指令] 已下发设置饼干数：%s\n" % fmt(v))
    elif target == "heavenly":
        with pending_lock:
            pending_set_heavenly[0] = v
        app_log("[指令] 已下发设置天堂碎片：%s\n" % fmt(v))
    else:
        with pending_lock:
            pending_set_lumps[0] = v
        app_log("[指令] 已下发设置糖果块：%s\n" % fmt(v))


def quick_op(val, kind, target):
    """快捷操作：add 加 / mul 乘 / set 直接设"""
    with latest_lock:
        base = latest["cookies"] if target == "cookies" else (
            latest["heavenly"] if target == "heavenly" else latest["lumps"])
    if kind == "add":
        new = base + val
    elif kind == "mul":
        new = base * val
    else:
        new = val
    new = max(0.0, new)
    if target == "cookies":
        with pending_lock:
            pending_set[0] = new
        app_log("[指令] 饼干快捷 %s -> %s\n" % (kind, fmt(new)))
    elif target == "heavenly":
        with pending_lock:
            pending_set_heavenly[0] = new
        app_log("[指令] 天堂碎片快捷 %s -> %s\n" % (kind, fmt(new)))
    else:
        with pending_lock:
            pending_set_lumps[0] = new
        app_log("[指令] 糖果块快捷 %s -> %s\n" % (kind, fmt(new)))


def trigger_golden():
    """召唤一个黄金饼干（一次性指令）"""
    with pending_lock:
        pending_spawn_golden[0] = True
    app_log("[指令] 已下发：召唤黄金饼干\n")


# ---- 饼干修改区 ----
mid = tk.Frame(root, padx=16, pady=6)
mid.pack(fill=tk.X)
tk.Label(mid, text="设为饼干数：", font=("Microsoft YaHei", 11)).pack(side=tk.LEFT)
entry_cookie_var = tk.StringVar()
entry_cookie = tk.Entry(mid, textvariable=entry_cookie_var, width=18, font=("Consolas", 11))
entry_cookie.pack(side=tk.LEFT, padx=(4, 8))
tk.Button(mid, text="设置", width=8, height=1,
          bg="#1565c0", fg="white", font=("Microsoft YaHei", 10, "bold"),
          command=lambda: submit_set("cookies")).pack(side=tk.LEFT)

# 饼干快捷按钮
qf = tk.Frame(root, padx=16, pady=2)
qf.pack(fill=tk.X)
for label, val, kind in [
    ("+1e3", 1e3, "add"), ("+1e6", 1e6, "add"), ("+1e9", 1e9, "add"),
    ("×2", 2.0, "mul"), ("÷2", 0.5, "mul"), ("清零", 0.0, "set"),
]:
    tk.Button(qf, text=label, width=8, height=1, font=("Microsoft YaHei", 10),
              command=lambda v=val, k=kind: quick_op(v, k, "cookies")).pack(side=tk.LEFT, padx=4, pady=4)

# ---- 天堂碎片修改区 ----
hm = tk.Frame(root, padx=16, pady=6)
hm.pack(fill=tk.X)
tk.Label(hm, text="设为天堂碎片：", font=("Microsoft YaHei", 11)).pack(side=tk.LEFT)
entry_heaven_var = tk.StringVar()
entry_heaven = tk.Entry(hm, textvariable=entry_heaven_var, width=18, font=("Consolas", 11))
entry_heaven.pack(side=tk.LEFT, padx=(4, 8))
tk.Button(hm, text="设置", width=8, height=1,
          bg="#e0a800", fg="white", font=("Microsoft YaHei", 10, "bold"),
          command=lambda: submit_set("heavenly")).pack(side=tk.LEFT)

# 天堂碎片快捷按钮
hf = tk.Frame(root, padx=16, pady=2)
hf.pack(fill=tk.X)
for label, val, kind in [
    ("+1", 1.0, "add"), ("+10", 10.0, "add"), ("+100", 100.0, "add"),
    ("×2", 2.0, "mul"), ("÷2", 0.5, "mul"), ("清零", 0.0, "set"),
]:
    tk.Button(hf, text=label, width=8, height=1, font=("Microsoft YaHei", 10),
              command=lambda v=val, k=kind: quick_op(v, k, "heavenly")).pack(side=tk.LEFT, padx=4, pady=4)

# ---- 糖果块修改区 ----
lm = tk.Frame(root, padx=16, pady=6)
lm.pack(fill=tk.X)
tk.Label(lm, text="设为糖果块：", font=("Microsoft YaHei", 11)).pack(side=tk.LEFT)
entry_lumps_var = tk.StringVar()
entry_lumps = tk.Entry(lm, textvariable=entry_lumps_var, width=18, font=("Consolas", 11))
entry_lumps.pack(side=tk.LEFT, padx=(4, 8))
tk.Button(lm, text="设置", width=8, height=1,
          bg="#c2185b", fg="white", font=("Microsoft YaHei", 10, "bold"),
          command=lambda: submit_set("lumps")).pack(side=tk.LEFT)

# 糖果块快捷按钮
lf = tk.Frame(root, padx=16, pady=2)
lf.pack(fill=tk.X)
for label, val, kind in [
    ("+1", 1.0, "add"), ("+10", 10.0, "add"), ("+100", 100.0, "add"),
    ("×2", 2.0, "mul"), ("÷2", 0.5, "mul"), ("清零", 0.0, "set"),
]:
    tk.Button(lf, text=label, width=8, height=1, font=("Microsoft YaHei", 10),
              command=lambda v=val, k=kind: quick_op(v, k, "lumps")).pack(side=tk.LEFT, padx=4, pady=4)

# ---- 黄金饼干按钮 ----
gf = tk.Frame(root, padx=16, pady=6)
gf.pack(fill=tk.X)
tk.Button(gf, text="✦ 召唤黄金饼干", width=20, height=1,
          bg="#f9a825", fg="white", font=("Microsoft YaHei", 11, "bold"),
          command=trigger_golden).pack(side=tk.LEFT)

# ---- 日志 ----
log_frame = tk.Frame(root, padx=16, pady=8)
log_frame.pack(fill=tk.BOTH, expand=True)
log_box = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
log_box.pack(fill=tk.BOTH, expand=True)


def app_log(text):
    try:
        log_box.after(0, _append_log, text)
    except Exception:
        pass


def _append_log(text):
    log_box.insert(tk.END, text)
    log_box.see(tk.END)


def refresh():
    with latest_lock:
        cookies = latest["cookies"]
        cps = latest["cps"]
        heavenly = latest["heavenly"]
        lumps = latest["lumps"]
        ts = latest["ts"]
    cookie_var.set(fmt(cookies))
    cps_var.set("每秒产量：" + fmt(cps))
    heaven_var.set(fmt(heavenly))
    if lumps is not None and lumps >= 0:
        lumps_var.set(fmt(lumps))
    else:
        lumps_var.set("未解锁（需先赚够饼干）")
    if ts > 0 and (time.time() - ts) < 5:
        conn_var.set("● 已连接游戏  (桥接 http://127.0.0.1:%d)" % TOOL_PORT)
        conn_label.config(fg="#1a8a3c")
    else:
        conn_var.set("○ 未连接游戏（请先在浏览器打开已注入 bridge 的游戏页面）")
        conn_label.config(fg="#a33")
    root.after(300, refresh)


app_log("[就绪] 桥接服务已启动：http://127.0.0.1:%d\n" % TOOL_PORT)
app_log("[提示] 请通过本地服务器打开 Cookie Clicker（已注入 bridge.js），本工具才能读取/修改饼干数与天堂碎片。\n")

# 后台启动桥接 HTTP 服务
def _start_bridge():
    try:
        start_bridge_server()
    except OSError as e:
        app_log("[错误] 桥接端口 %d 被占用，可能无法接收游戏数据：%s\n" % (TOOL_PORT, e))
        app_log("[提示] 请先关闭其它正在运行的 Cookie Clicker 工具实例。\n")

threading.Thread(target=_start_bridge, daemon=True).start()

root.after(300, refresh)
root.mainloop()
