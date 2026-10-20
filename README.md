# Telegram 视频全自动连播工具 (TG Video Auto Switcher)

专为 Windows 端 Telegram Desktop 打造的轻量级视频自动连续播放工具。支持播放完毕自动切换、3 秒醒目倒计时、防误卡顿起播及双向切片控制。

---

## 🌟 核心功能

- **智能播放检测**：通过画面动静差分算法，视频自然播完（画面静止）立即触发切片。
- **居中醒目倒计时**：视频停止播放后，屏幕正中央弹出亮黄色提示框，显示 `3秒之后会切换下一个视频`（3 → 2 → 1 倒计时）。
- **防暂停起播保护**：智能适配视频加载缓冲，杜绝切换后画面停滞或误暂停的问题。
- **双向控制面板**：提供直观 GUI，支持一键开始/暂停连播，以及 `◄ 向左` 与 `向右 ►` 手动切换。
- **免安装绿色运行**：无需安装配置 Python 环境，下载 `.exe` 单文件即可直接运行。

---

## 📥 下载与使用

### 1. 下载运行
前往本仓库右侧的 [Releases](../../releases) 页面，下载最新的 `Telegram连播神器.exe`。

### 2. 使用方法
1. 打开 **Telegram Desktop**，双击打开任意视频进入**全屏媒体查看器 (Media Viewer)**。
2. 双击打开 `Telegram连播神器.exe`，点击控制面板上的 **「开始连播」**。
3. 视频播放完毕后，屏幕中央将倒计时 3 秒并自动切换到下一个视频。

---

## 🛠️ 源码运行与打包 (开发者)

```bash
# 安装依赖
pip install opencv-python numpy pyautogui pywin32 pillow

# 运行源码
python tg_player_tool.py

# 单文件打包 exe
pip install pyinstaller
pyinstaller --noconsole --onefile --name "Telegram连播神器" tg_player_tool.py
