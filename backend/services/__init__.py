"""
服务包（services）—— 放“和具体 HTTP 路由无关”的底层能力

目前只有 hybridbci_client.py：负责与华南脑控 HybridBCI 平台建立 TCP 连接、
收发 IPC 协议帧，并把平台结果翻译成 Unity 指令。它与路由解耦，方便复用与测试。
"""
