# -*- coding: utf-8 -*-
"""工具函数：二维码、连接判断、配对+连接。"""

from PyQt6.QtGui import QPixmap, QImage

from adb_helper import run_adb, adb_pair


def make_qr_pixmap(text: str, box_size: int = 8) -> QPixmap:
    """根据字符串生成二维码 QPixmap。"""
    import qrcode
    qr = qrcode.QRCode(box_size=box_size, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.convert("RGB")
    w, h = img.size
    data = img.tobytes("raw", "RGB")
    qimg = QImage(data, w, h, w * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)


def is_success_connect_output(out: str) -> bool:
    s = (out or "").lower()
    return ("connected to " in s) or ("already connected to " in s)


def is_success_pair_output(out: str) -> bool:
    return "Successfully paired" in (out or "")


def pair_then_connect(
    pair_host: str,
    pair_port: int,
    code: str,
    connect_host: str,
    connect_port: int,
):
    """先配对再连接，返回 (code, out, err)。"""
    code1, out1, err1 = adb_pair(pair_host, pair_port, code)
    if code1 != 0 or not is_success_pair_output(out1):
        return code1, f"[pair]\n{out1}", f"[pair stderr]\n{err1}"
    code2, out2, err2 = run_adb("connect", f"{connect_host}:{connect_port}", timeout=15)
    out = "\n\n".join(
        [x for x in ["[pair]\n" + (out1 or "").rstrip(), "[connect]\n" + (out2 or "").rstrip()] if x.strip()]
    )
    err = "\n\n".join(
        [
            x
            for x in [
                "[pair stderr]\n" + (err1 or "").rstrip(),
                "[connect stderr]\n" + (err2 or "").rstrip(),
            ]
            if x.strip()
        ]
    )
    return code2, out, err


def connect_only(host: str, port: int):
    """仅连接，返回 (code, out, err)。"""
    return run_adb("connect", f"{host}:{port}", timeout=15)
