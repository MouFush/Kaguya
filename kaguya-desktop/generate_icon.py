#!/usr/bin/env python3
"""
生成辉夜IDE应用图标
使用Pillow创建各平台所需的图标格式
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")


def create_icon():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[ERROR] Pillow not installed. Run: pip install Pillow")
        return

    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 10
    radius = 50
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=(124, 106, 255, 255),
    )

    gradient_overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(gradient_overlay)
    for y in range(margin, size - margin):
        alpha = int(40 * (1 - (y - margin) / (size - 2 * margin)))
        grad_draw.line([(margin + radius, y), (size - margin - radius, y)], fill=(255, 255, 255, alpha))

    img = Image.alpha_composite(img, gradient_overlay)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 120)
    except Exception:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)
        except Exception:
            font = ImageFont.load_default()

    text = "K"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) / 2
    y = (size - text_h) / 2 - 10
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    os.makedirs(ASSETS_DIR, exist_ok=True)

    png_path = os.path.join(ASSETS_DIR, "kaguya.png")
    img.save(png_path, "PNG")
    print(f"[OK] PNG icon: {png_path}")

    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = []
    for s in sizes:
        resized = img.resize((s, s), Image.LANCZOS)
        icons.append(resized)

    ico_path = os.path.join(ASSETS_DIR, "kaguya.ico")
    icons[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=icons[1:],
    )
    print(f"[OK] ICO icon: {ico_path}")

    icns_path = os.path.join(ASSETS_DIR, "kaguya.icns")
    try:
        mac_sizes = [16, 32, 64, 128, 256, 512]
        mac_icons = []
        for s in mac_sizes:
            resized = img.resize((s, s), Image.LANCZOS)
            mac_icons.append(resized)
        mac_icons[0].save(icns_path, format="ICNS", append_images=mac_icons[1:])
        print(f"[OK] ICNS icon: {icns_path}")
    except Exception as e:
        print(f"[WARN] ICNS creation failed (requires macOS): {e}")
        png_512 = os.path.join(ASSETS_DIR, "kaguya_512.png")
        img.resize((512, 512), Image.LANCZOS).save(png_512, "PNG")
        print(f"[OK] PNG 512x512 (for ICNS conversion): {png_512}")

    print("\n[DONE] All icons generated!")


if __name__ == "__main__":
    create_icon()
