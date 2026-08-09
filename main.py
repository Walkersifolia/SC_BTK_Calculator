# -*- coding: utf-8 -*-
"""星际公民 BTK 计算器 — 主入口（WebView2 + HTML/CSS UI）。

启动流程：
1. 后台启动本地 HTTP 服务（数据 API + 静态 UI）
2. 用 pywebview 打开 WebView2 窗口加载 UI

依赖：pywebview（pip install pywebview），系统需安装 WebView2 Runtime（Win10/11 自带）。
"""
import sys
import threading

import backend


def main():
    # 启动后端
    srv, port = backend.start_server()
    url = "http://127.0.0.1:%d/" % port

    try:
        import webview
    except ImportError:
        print("缺少 pywebview，请先安装: pip install pywebview")
        print("临时方案：浏览器打开 %s" % url)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        return

    # 窗口图标（与 exe 图标一致）
    icon = backend_icon()

    webview.create_window(
        "星际公民 BTK 计算器",
        url,
        width=1380,
        height=880,
        min_size=(1120, 740),
        background_color="#f0f0f5",
        icon=icon,
    )
    webview.start()


def backend_icon():
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon_black.ico")
    return p if os.path.exists(p) else None


if __name__ == "__main__":
    main()
