# -*- coding: utf-8 -*-
"""从 adb.png 生成 adb.ico，供 PyInstaller 在 Windows 下用作 exe 图标。"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
PNG = ROOT / "adb.png"
ICO = ROOT / "adb.ico"
SIZES = [(16, 16), (32, 32), (48, 48), (256, 256)]


def main():
    if not PNG.is_file():
        raise SystemExit(f"找不到 {PNG}")
    img = Image.open(PNG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")
    img.save(ICO, format="ICO", sizes=SIZES)
    print(f"已生成 {ICO}")


if __name__ == "__main__":
    main()
