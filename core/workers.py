# -*- coding: utf-8 -*-
"""后台线程：Worker、Zeroconf 配对监听。"""

import socket
from PyQt6.QtCore import QThread, pyqtSignal, QObject


class Worker(QThread):
    """在后台执行可调用对象，避免阻塞 UI。"""
    finished = pyqtSignal(int, str, str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            if isinstance(result, tuple) and len(result) == 3:
                self.finished.emit(*result)
            else:
                self.finished.emit(0, str(result), "")
        except Exception as e:
            self.finished.emit(-1, "", str(e))


class PairingNotifier(QObject):
    """供 zeroconf 回调跨线程通知主线程：发现配对服务。"""
    pair_found = pyqtSignal(str, int, str)  # host, port, password


class PairingListener:
    """mDNS 监听 _adb-tls-pairing，发现后通过 notifier 发出 host/port/密码。"""
    def __init__(self, notifier: PairingNotifier, password: str):
        self.notifier = notifier
        self.password = password

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        if not info or not info.addresses:
            return
        host = socket.inet_ntoa(info.addresses[0])
        port = info.port
        self.notifier.pair_found.emit(host, port, self.password)

    def remove_service(self, zeroconf, service_type, name):
        pass

    def update_service(self, zeroconf, service_type, name):
        pass


class ZeroconfThread(QThread):
    """在后台运行 zeroconf 监听配对服务，发现后由 notifier 发信号。"""
    def __init__(self, notifier: PairingNotifier, password: str):
        super().__init__()
        self.notifier = notifier
        self.password = password
        self._running = True
        self._zc = None

    def run(self):
        try:
            from zeroconf import Zeroconf, ServiceBrowser
            self._zc = Zeroconf()
            listener = PairingListener(self.notifier, self.password)
            ServiceBrowser(
                self._zc,
                "_adb-tls-pairing._tcp.local.",
                listener,
            )
            while self._running:
                self.msleep(300)
        except Exception:
            pass
        finally:
            if self._zc is not None:
                try:
                    self._zc.close()
                except Exception:
                    pass
                self._zc = None

    def stop(self):
        self._running = False
