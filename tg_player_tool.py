import os
import sys
import time
import threading
import tkinter as tk
import cv2
import numpy as np
import pyautogui
import win32gui
import win32con

# ====== 运行状态与配置 ======
is_running = False
direction = 'right'  # 当前连播方向：'left' 或 'right'
IDLE_THRESHOLD = 1.8 # 视频画面静止判定(秒)
CHECK_INTERVAL = 0.35

# ====== 屏幕正中醒目黑色倒计时弹窗 ======
class CenterCountdownToast:
    def __init__(self, root):
        self.root = root
        self.win = None
        self.lbl = None

    def show(self, on_finish_callback):
        def _run_ui():
            if self.win:
                try: self.win.destroy()
                except: pass

            self.win = tk.Toplevel(self.root)
            self.win.overrideredirect(True)
            self.win.attributes('-topmost', True)
            self.win.configure(bg='#FFE600')  # 醒目的亮黄背景
            self.win.attributes('-alpha', 0.95)

            self.lbl = tk.Label(
                self.win, 
                text="3秒之后会切换下一个视频 3", 
                font=('SimHei', 22, 'bold'), 
                fg='#000000',  # 纯黑字体
                bg='#FFE600', 
                padx=35, 
                pady=18
            )
            self.lbl.pack()
            self.win.update_idletasks()
            sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
            w, h = self.win.winfo_width(), self.win.winfo_height()
            self.win.geometry(f"+{(sw - w)//2}+{(sh - h)//2}")

            # 启动 3 -> 2 -> 1 倒计时
            self._countdown(3, on_finish_callback)

        self.root.after(0, _run_ui)

    def _countdown(self, count, callback):
        if not self.win:
            return
        if count > 0:
            self.lbl.config(text=f"3秒之后会切换下一个视频 {count}")
            self.root.after(1000, lambda: self._countdown(count - 1, callback))
        else:
            try:
                self.win.destroy()
                self.win = None
            except:
                pass
            if callback:
                callback()

# ====== Telegram 窗口检索与控制 ======
def get_tg_hwnd():
    target = None
    def enum_cb(h, _):
        nonlocal target
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            c = win32gui.GetClassName(h)
            if ("媒体查看器" in t or "Media viewer" in t) and "Qt5" in c:
                target = h
    win32gui.EnumWindows(enum_cb, None)
    return target

def send_switch(key):
    hwnd = get_tg_hwnd()
    if not hwnd:
        return
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.1)
        pyautogui.press(key)  # 仅发送方向键，不要盲目发送空格以免导致自动播放的视频暂停
    except Exception:
        pass

def grab_screen(hwnd):
    try:
        rect = win32gui.GetWindowRect(hwnd)
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        if w < 200 or h < 200:
            return None
        # 截取画面中心 60% 区域，避开边缘控制条干扰
        x1, y1 = rect[0] + int(w * 0.2), rect[1] + int(h * 0.2)
        sw, sh = int(w * 0.6), int(h * 0.6)
        shot = pyautogui.screenshot(region=(x1, y1, sw, sh))
        return cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)
    except:
        return None

# ====== 监控线程 ======
def monitor_loop():
    global is_running, direction
    last_frame = None
    stagnant_sec = 0.0
    is_counting_down = False

    while is_running:
        hwnd = get_tg_hwnd()
        if not hwnd:
            update_status_ui("未检测到媒体查看器，等待打开视频...")
            time.sleep(1.0)
            continue

        dir_str = "右向 (下一个)" if direction == 'right' else "左向 (上一个)"
        update_status_ui(f"正在监控播放 | 方向: {dir_str}")

        if is_counting_down:
            time.sleep(0.3)
            continue

        frame = grab_screen(hwnd)
        if frame is None:
            time.sleep(CHECK_INTERVAL)
            continue

        if last_frame is not None and last_frame.shape == frame.shape:
            diff = np.mean(cv2.absdiff(last_frame, frame))
            if diff < 1.0:  # 画面静止
                stagnant_sec += CHECK_INTERVAL
            else:
                stagnant_sec = 0.0

            # 达到静止阈值 -> 判定播完，触发正中倒计时
            if stagnant_sec >= IDLE_THRESHOLD and not is_counting_down:
                is_counting_down = True
                stagnant_sec = 0.0

                def on_finish():
                    nonlocal is_counting_down, last_frame
                    send_switch(direction)
                    time.sleep(1.8) # 给予新视频充足的加载与自动起播时间(1.8秒)
                    
                    # 只有当新画面 1.8秒后依然完全静止时，才认为可能未自动播放，此时发送一次 space 强制播放
                    temp_frame = grab_screen(hwnd)
                    if temp_frame is not None:
                        time.sleep(0.4)
                        post_frame = grab_screen(hwnd)
                        if post_frame is not None and post_frame.shape == temp_frame.shape:
                            if np.mean(cv2.absdiff(temp_frame, post_frame)) < 1.0:
                                pyautogui.press('space') # 静止，尝试激活播放
                                time.sleep(0.5)

                    last_frame = None
                    is_counting_down = False

                toast.show(on_finish)
                continue
        else:
            stagnant_sec = 0.0

        last_frame = frame
        time.sleep(CHECK_INTERVAL)

# ====== UI 界面 ======
def toggle_start():
    global is_running
    if not is_running:
        is_running = True
        btn_start.config(text="暂停连播", bg="#FFF0F0")
        t = threading.Thread(target=monitor_loop, daemon=True)
        t.start()
    else:
        is_running = False
        btn_start.config(text="开始连播", bg="#FFFFFF")
        update_status_ui(f"已暂停 | 方向: {'右向' if direction=='right' else '左向'}")

def manual_left():
    global direction
    direction = 'left'
    update_status_ui("手动切换: 左向 | 正在切换...")
    send_switch('left')

def manual_right():
    global direction
    direction = 'right'
    update_status_ui("手动切换: 右向 | 正在切换...")
    send_switch('right')

def exit_app():
    global is_running
    is_running = False
    root.destroy()
    sys.exit(0)

def update_status_ui(txt):
    root.after(0, lambda: lbl_status.config(text=f"状态: {txt}"))

root = tk.Tk()
root.title("TG 视频连播控制台")
root.geometry("450x170")
root.attributes('-topmost', True)
root.resizable(False, False)
root.configure(bg="#F2F2F2")

toast = CenterCountdownToast(root)

# 状态栏
lbl_status = tk.Label(root, text="状态: 已就绪 | 方向: 右向", font=("SimHei", 10, "bold"), fg="#0066CC", bg="#F2F2F2")
lbl_status.pack(pady=8)

# 顶部功能按钮行（开始连播 + 关闭退出）
f_top = tk.Frame(root, bg="#F2F2F2")
f_top.pack(fill='x', padx=15, pady=2)

btn_start = tk.Button(f_top, text="开始连播", font=("SimHei", 10), bg="#FFFFFF", width=18, relief="solid", bd=1, command=toggle_start)
btn_start.pack(side='left', expand=True, fill='x', padx=(0, 5))

btn_close = tk.Button(f_top, text="关闭退出 [x]", font=("SimHei", 10), bg="#CC2222", fg="#FFFFFF", width=18, relief="flat", command=exit_app)
btn_close.pack(side='right', expand=True, fill='x', padx=(5, 0))

# 底部方向控制大按钮
f_bottom = tk.Frame(root, bg="#F2F2F2")
f_bottom.pack(fill='x', padx=15, pady=10)

btn_prev = tk.Button(f_bottom, text="◄  向左播放上一个", font=("SimHei", 11, "bold"), bg="#E0E0E0", height=2, relief="groove", command=manual_left)
btn_prev.pack(side='left', expand=True, fill='x', padx=(0, 5))

btn_next = tk.Button(f_bottom, text="向右播放下一个  ►", font=("SimHei", 11, "bold"), bg="#E0E0E0", height=2, relief="groove", command=manual_right)
btn_next.pack(side='right', expand=True, fill='x', padx=(5, 0))

root.mainloop()
