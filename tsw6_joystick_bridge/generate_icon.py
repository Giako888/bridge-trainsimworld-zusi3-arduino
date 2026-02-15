"""Generate TSW6 Arduino Bridge icon with train signal LEDs theme."""
from PIL import Image, ImageDraw, ImageFont
import math, os

SIZES = [256, 128, 64, 48, 32, 16]

def draw_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size  # shorthand
    p = s / 256  # scale factor

    # --- Background: rounded dark rectangle ---
    r = int(28 * p)
    bg_color = (30, 30, 46, 255)       # #1e1e2e
    border_color = (137, 180, 250, 255) # #89b4fa accent blue
    # Outer border rounded rect
    d.rounded_rectangle([0, 0, s-1, s-1], radius=r, fill=border_color)
    # Inner fill
    bw = max(int(4 * p), 1)
    d.rounded_rectangle([bw, bw, s-1-bw, s-1-bw], radius=r-bw, fill=bg_color)

    # --- Top section: "TSW6" text ---
    try:
        fsize = max(int(42 * p), 8)
        font = ImageFont.truetype("seguisb.ttf", fsize)
    except:
        font = ImageFont.load_default()
    text = "TSW6"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (s - tw) // 2
    ty = int(22 * p)
    d.text((tx, ty), text, fill=(137, 180, 250, 255), font=font)

    # --- Signal panel: dark rounded rect in center ---
    panel_top = int(78 * p)
    panel_bot = int(210 * p)
    panel_left = int(28 * p)
    panel_right = s - int(28 * p)
    panel_r = int(12 * p)
    d.rounded_rectangle(
        [panel_left, panel_top, panel_right, panel_bot],
        radius=panel_r,
        fill=(24, 24, 37, 255),  # #181825
        outline=(69, 71, 90, 200),   # #45475a
        width=max(int(2 * p), 1)
    )

    # --- 12 LED circles (4x3 grid) - Charlieplexing 12 LEDs ---
    led_colors = [
        (166, 227, 161, 255),  # green - SIFA
        (249, 226, 175, 255),  # yellow - PZB 70
        (243, 139, 168, 255),  # red - PZB 85
        (137, 180, 250, 255),  # blue - LZB

        (166, 227, 161, 255),  # green
        (249, 226, 175, 255),  # yellow
        (243, 139, 168, 255),  # red
        (137, 180, 250, 255),  # blue

        (166, 227, 161, 200),  # green dim
        (249, 226, 175, 200),  # yellow dim
        (137, 180, 250, 200),  # blue dim
        (243, 139, 168, 200),  # red dim
    ]
    
    cols, rows = 4, 3
    grid_left = panel_left + int(18 * p)
    grid_right = panel_right - int(18 * p)
    grid_top = panel_top + int(14 * p)
    grid_bot = panel_bot - int(14 * p)
    
    cell_w = (grid_right - grid_left) / cols
    cell_h = (grid_bot - grid_top) / rows
    led_r = int(min(cell_w, cell_h) * 0.32)

    for row in range(rows):
        for col in range(cols):
            idx = row * cols + col
            cx = int(grid_left + cell_w * (col + 0.5))
            cy = int(grid_top + cell_h * (row + 0.5))
            color = led_colors[idx]
            
            # Glow effect
            glow_r = int(led_r * 1.6)
            glow_color = (color[0], color[1], color[2], 60)
            d.ellipse([cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r], fill=glow_color)
            
            # Main LED
            d.ellipse([cx - led_r, cy - led_r, cx + led_r, cy + led_r], fill=color)
            
            # Highlight
            hl_r = max(int(led_r * 0.4), 1)
            hl_x = cx - int(led_r * 0.2)
            hl_y = cy - int(led_r * 0.2)
            d.ellipse([hl_x - hl_r, hl_y - hl_r, hl_x + hl_r, hl_y + hl_r],
                      fill=(255, 255, 255, 100))

    # --- Bottom: Arduino chip icon ---
    chip_top = int(218 * p)
    chip_bot = int(248 * p)
    chip_left = int(80 * p)
    chip_right = s - int(80 * p)
    chip_r = int(4 * p)
    chip_color = (69, 71, 90, 255)  # #45475a
    d.rounded_rectangle(
        [chip_left, chip_top, chip_right, chip_bot],
        radius=chip_r,
        fill=chip_color,
        outline=(88, 91, 112, 255),
        width=max(int(1 * p), 1)
    )
    
    # Chip pins (left/right)
    pin_w = max(int(4 * p), 1)
    pin_h = max(int(3 * p), 1)
    pin_color = (166, 173, 200, 255)  # #a6adc8
    num_pins = 4
    chip_h = chip_bot - chip_top
    for i in range(num_pins):
        py_pos = chip_top + int(chip_h * (i + 0.5) / num_pins)
        # Left pins
        d.rectangle([chip_left - pin_w - 1, py_pos - pin_h//2,
                     chip_left - 1, py_pos + pin_h//2], fill=pin_color)
        # Right pins
        d.rectangle([chip_right + 1, py_pos - pin_h//2,
                     chip_right + pin_w + 1, py_pos + pin_h//2], fill=pin_color)

    return img


# Generate all sizes
images = [draw_icon(sz) for sz in SIZES]

# Save as .ico
ico_path = os.path.join(os.path.dirname(__file__), "tsw6_bridge.ico")
images[0].save(ico_path, format="ICO", sizes=[(sz, sz) for sz in SIZES],
               append_images=images[1:])
print(f"Icon saved: {ico_path}")
