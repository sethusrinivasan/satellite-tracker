#!/usr/bin/env python3
"""
Generate Google Play Store and Amazon Appstore submission graphics:
- High-res App Icon (512x512, 32-bit PNG)
- Small Icon (114x114, Amazon Appstore)
- Feature Graphic (1024x500)
- Store Screenshots (1080x1920 phone, 1200x1920 7-in tablet, 1600x2560 10-in tablet)
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def draw_satellite_icon(size=512):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Background rounded rect
    margin = int(size * 0.04)
    r = int(size * 0.22)
    
    # Gradient background
    for y in range(margin, size - margin):
        t = (y - margin) / float(size - 2 * margin)
        # Deep space cyber navy to twilight
        r_c = int(8 + (15 - 8) * t)
        g_c = int(14 + (23 - 14) * t)
        b_c = int(26 + (42 - 26) * t)
        draw.line([(margin, y), (size - margin, y)], fill=(r_c, g_c, b_c, 255))
        
    # Mask to rounded rect
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([margin, margin, size - margin, size - margin], radius=r, fill=255)
    
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg.paste(img, (0, 0), mask=mask)
    draw = ImageDraw.Draw(bg)
    
    center_x = size // 2
    center_y = size // 2
    
    # Outer glow / subtle border
    draw.rounded_rectangle([margin, margin, size - margin, size - margin], radius=r, outline=(56, 189, 248, 140), width=int(size * 0.015))
    
    # Starfield dots
    stars = [
        (0.2, 0.25, 2), (0.28, 0.18, 1.5), (0.78, 0.22, 2.5), (0.82, 0.35, 1.5),
        (0.18, 0.72, 1.5), (0.75, 0.78, 2), (0.68, 0.82, 1), (0.32, 0.85, 2)
    ]
    for sx, sy, sr in stars:
        px, py = int(sx * size), int(sy * size)
        draw.ellipse([px - sr, py - sr, px + sr, py + sr], fill=(224, 242, 254, 220))

    # Earth curve at bottom-left
    earth_r = int(size * 0.75)
    earth_center = (int(size * 0.15), int(size * 1.05))
    draw.arc(
        [earth_center[0] - earth_r, earth_center[1] - earth_r, earth_center[0] + earth_r, earth_center[1] + earth_r],
        start=230, end=350, fill=(14, 165, 233, 200), width=int(size * 0.02)
    )
    # Atmosphere glow
    draw.arc(
        [earth_center[0] - earth_r - 8, earth_center[1] - earth_r - 8, earth_center[0] + earth_r + 8, earth_center[1] + earth_r + 8],
        start=230, end=350, fill=(56, 189, 248, 80), width=int(size * 0.035)
    )

    # Elliptical orbit rings
    orbit_w = int(size * 0.78)
    orbit_h = int(size * 0.38)
    # Orbit 1 (cyan)
    draw.ellipse(
        [center_x - orbit_w // 2, center_y - orbit_h // 2, center_x + orbit_w // 2, center_y + orbit_h // 2],
        outline=(56, 189, 248, 210), width=int(size * 0.018)
    )
    # Orbit 2 (indigo/violet angled via points)
    pts = []
    angle_tilt = math.radians(-32)
    for deg in range(0, 360, 4):
        rad = math.radians(deg)
        x0 = (orbit_w * 0.44) * math.cos(rad)
        y0 = (orbit_h * 0.44) * math.sin(rad)
        # rotate by angle_tilt
        xr = center_x + x0 * math.cos(angle_tilt) - y0 * math.sin(angle_tilt)
        yr = center_y + x0 * math.sin(angle_tilt) + y0 * math.cos(angle_tilt)
        pts.append((xr, yr))
    draw.line(pts + [pts[0]], fill=(168, 85, 247, 180), width=int(size * 0.014))

    # Satellite spacecraft in center
    sat_size = int(size * 0.22)
    body_w = int(sat_size * 0.45)
    body_h = int(sat_size * 0.45)
    
    # Solar Panels (Left and Right wings)
    panel_w = int(sat_size * 0.55)
    panel_h = int(sat_size * 0.28)
    gap = int(sat_size * 0.12)
    
    # Left wing
    lx1 = center_x - body_w // 2 - gap - panel_w
    ly1 = center_y - panel_h // 2
    draw.rounded_rectangle([lx1, ly1, lx1 + panel_w, ly1 + panel_h], radius=4, fill=(14, 165, 233, 240), outline=(224, 242, 254, 255), width=2)
    # Left panel grid
    for i in range(1, 3):
        gx = lx1 + (panel_w * i // 3)
        draw.line([(gx, ly1), (gx, ly1 + panel_h)], fill=(12, 74, 110, 200), width=2)
    draw.line([(lx1, center_y), (lx1 + panel_w, center_y)], fill=(12, 74, 110, 200), width=2)
    
    # Left connector rod
    draw.line([(lx1 + panel_w, center_y), (center_x - body_w // 2, center_y)], fill=(203, 213, 225, 255), width=4)

    # Right wing
    rx1 = center_x + body_w // 2 + gap
    ry1 = center_y - panel_h // 2
    draw.rounded_rectangle([rx1, ry1, rx1 + panel_w, ry1 + panel_h], radius=4, fill=(14, 165, 233, 240), outline=(224, 242, 254, 255), width=2)
    for i in range(1, 3):
        gx = rx1 + (panel_w * i // 3)
        draw.line([(gx, ry1), (gx, ry1 + panel_h)], fill=(12, 74, 110, 200), width=2)
    draw.line([(rx1, center_y), (rx1 + panel_w, center_y)], fill=(12, 74, 110, 200), width=2)
    # Right connector rod
    draw.line([(center_x + body_w // 2, center_y), (rx1, center_y)], fill=(203, 213, 225, 255), width=4)

    # Bus / Chassis
    bx1 = center_x - body_w // 2
    by1 = center_y - body_h // 2
    draw.rounded_rectangle([bx1, by1, bx1 + body_w, by1 + body_h], radius=6, fill=(241, 245, 249, 255), outline=(56, 189, 248, 255), width=3)
    
    # Gold foil thermal core
    core_pad = int(body_w * 0.22)
    draw.rectangle([bx1 + core_pad, by1 + core_pad, bx1 + body_w - core_pad, by1 + body_h - core_pad], fill=(245, 158, 11, 255))
    
    # Dish Antenna (top)
    dish_w = int(sat_size * 0.32)
    dish_h = int(sat_size * 0.16)
    dish_y = by1 - dish_h - 6
    draw.arc([center_x - dish_w // 2, dish_y, center_x + dish_w // 2, dish_y + dish_h * 2], start=180, end=360, fill=(224, 242, 254, 255), width=3)
    draw.line([(center_x, dish_y + dish_h), (center_x, by1)], fill=(203, 213, 225, 255), width=3)
    draw.ellipse([center_x - 3, dish_y - 2, center_x + 3, dish_y + 4], fill=(56, 189, 248, 255))

    # Signal pulse waves
    wave_r = int(size * 0.16)
    draw.arc([center_x - wave_r, center_y + body_h // 2 + 6, center_x + wave_r, center_y + body_h // 2 + 6 + wave_r], start=45, end=135, fill=(56, 189, 248, 190), width=3)
    wave_r2 = int(size * 0.24)
    draw.arc([center_x - wave_r2, center_y + body_h // 2 + 10, center_x + wave_r2, center_y + body_h // 2 + 10 + wave_r2], start=50, end=130, fill=(56, 189, 248, 110), width=2)

    return bg

def draw_feature_graphic(width=1024, height=500):
    img = Image.new("RGB", (width, height), (8, 14, 26))
    draw = ImageDraw.Draw(img)

    # Space background gradient
    for x in range(width):
        t = x / float(width)
        r = int(8 + (15 - 8) * t)
        g = int(14 + (23 - 14) * (1 - t * 0.5))
        b = int(26 + (50 - 26) * t)
        draw.line([(x, 0), (x, height)], fill=(r, g, b))

    # Starfield
    for i in range(120):
        sx = int((math.sin(i * 17.1) * 0.5 + 0.5) * width)
        sy = int((math.cos(i * 31.7) * 0.5 + 0.5) * height)
        br = int((math.sin(i * 5.3) * 0.5 + 0.5) * 180 + 75)
        rad = 1 if i % 4 != 0 else 2
        draw.ellipse([sx - rad, sy - rad, sx + rad, sy + rad], fill=(br, br, 255))

    # Orbital lines in background
    orbit_cx = int(width * 0.72)
    orbit_cy = int(height * 0.52)
    for idx, (ow, oh, col) in enumerate([(480, 240, (56, 189, 248, 160)), (620, 310, (168, 85, 247, 130)), (360, 180, (16, 185, 129, 140))]):
        pts = []
        tilt = math.radians(-25 + idx * 15)
        for deg in range(0, 360, 5):
            rad = math.radians(deg)
            x0 = (ow // 2) * math.cos(rad)
            y0 = (oh // 2) * math.sin(rad)
            xr = orbit_cx + x0 * math.cos(tilt) - y0 * math.sin(tilt)
            yr = orbit_cy + x0 * math.sin(tilt) + y0 * math.cos(tilt)
            pts.append((xr, yr))
        draw.line(pts + [pts[0]], fill=col[:3], width=2)

    # Earth arc at bottom right
    e_center = (int(width * 0.82), int(height * 1.15))
    e_r = int(height * 0.75)
    draw.arc([e_center[0] - e_r, e_center[1] - e_r, e_center[0] + e_r, e_center[1] + e_r], start=180, end=320, fill=(14, 165, 233), width=6)
    draw.arc([e_center[0] - e_r - 8, e_center[1] - e_r - 8, e_center[0] + e_r + 8, e_center[1] + e_r + 8], start=180, end=320, fill=(56, 189, 248), width=3)

    # Overlay satellite icon on feature graphic
    icon_small = draw_satellite_icon(size=260)
    img.paste(icon_small, (int(width * 0.65), int(height * 0.22)), mask=icon_small)

    # Left typography area
    # Title
    font_large = None
    font_med = None
    font_small = None
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 46)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except Exception:
        font_large = ImageFont.load_default()
        font_med = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((60, 110), "SATELLITE TLE TRACKER", fill=(248, 250, 252), font=font_large)
    draw.text((60, 172), "Real-Time 2D/3D Orbit Propagation & Telemetry", fill=(56, 189, 248), font=font_med)
    draw.text((60, 206), "Complete On-Device SGP4 Engine • Offline Ready", fill=(148, 163, 184), font=font_med)

    # Feature badges
    badges = [
        ("🛰️ 60+ Preloaded Satellites", (16, 185, 129)),
        ("⚡ 100% Offline SGP4 Engine", (56, 189, 248)),
        ("🌐 3D Interactive WebGL Globe", (168, 85, 247)),
        ("✨ Optional Remote AI Queries", (245, 158, 11)),
    ]
    
    by = 280
    for text, col in badges:
        # draw badge pill
        draw.rounded_rectangle([60, by, 60 + 380, by + 34], radius=17, fill=(15, 23, 42), outline=col, width=2)
        draw.text((80, by + 8), text, fill=(241, 245, 249), font=font_small)
        by += 44

    return img

def draw_screenshot(title, subtitle, tab_name, width=1080, height=1920):
    img = Image.new("RGB", (width, height), (11, 15, 25))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        font_tab = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        font_hud = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        font_code = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 26)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_tab = ImageFont.load_default()
        font_hud = ImageFont.load_default()
        font_code = ImageFont.load_default()

    # Top banner / Showcase Header
    draw.rectangle([0, 0, width, 240], fill=(15, 23, 42))
    draw.line([(0, 240), (width, 240)], fill=(56, 189, 248), width=3)
    
    draw.text((48, 64), title, fill=(248, 250, 252), font=font_title)
    draw.text((48, 140), subtitle, fill=(56, 189, 248), font=font_sub)

    # Phone Frame representation
    phone_x = 48
    phone_y = 280
    phone_w = width - 96
    phone_h = height - 340
    
    # Phone bezel
    draw.rounded_rectangle([phone_x, phone_y, phone_x + phone_w, phone_y + phone_h], radius=40, fill=(3, 7, 18), outline=(56, 189, 248, 180), width=4)

    # Top App Bar
    appbar_y = phone_y + 30
    draw.rounded_rectangle([phone_x + 20, appbar_y, phone_x + phone_w - 20, appbar_y + 80], radius=16, fill=(17, 24, 39))
    draw.text((phone_x + 50, appbar_y + 24), "📡 SATELLITE TRACKER", fill=(248, 250, 252), font=font_tab)
    # Green status pill
    draw.rounded_rectangle([phone_x + phone_w - 380, appbar_y + 18, phone_x + phone_w - 40, appbar_y + 62], radius=14, fill=(6, 78, 59), outline=(16, 185, 129), width=2)
    draw.text((phone_x + phone_w - 360, appbar_y + 26), "● 100% SGP4 LOCAL", fill=(110, 231, 183), font=font_hud)

    # Content Area mockup based on tab_name
    cx = phone_x + 30
    cy = appbar_y + 110
    cw = phone_w - 60
    ch = phone_h - 260

    if tab_name == "2d":
        # 2D Map Canvas mockup
        draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=20, fill=(15, 23, 42), outline=(30, 41, 59), width=3)
        # Grid lines (lat / long)
        for gx in range(cx + 80, cx + cw, 120):
            draw.line([(gx, cy), (gx, cy + ch)], fill=(30, 41, 59, 120), width=1)
        for gy in range(cy + 80, cy + ch, 120):
            draw.line([(cx, gy), (cx + cw, gy)], fill=(30, 41, 59, 120), width=1)
        
        # Equator
        draw.line([(cx, cy + ch // 2), (cx + cw, cy + ch // 2)], fill=(51, 65, 85), width=2)
        
        # Day/Night terminator wave
        pts = []
        for x_step in range(cx, cx + cw, 10):
            norm_x = (x_step - cx) / float(cw)
            y_val = (cy + ch // 2) + math.sin(norm_x * 2 * math.pi) * (ch * 0.28)
            pts.append((x_step, y_val))
        draw.line(pts, fill=(245, 158, 11, 160), width=2)

        # Orbit Ground Tracks
        # ISS Track (Cyan)
        iss_pts = []
        for x_step in range(cx, cx + cw, 10):
            norm_x = (x_step - cx) / float(cw)
            y_val = (cy + ch // 2) + math.sin((norm_x + 0.2) * 2 * math.pi) * (ch * 0.35)
            iss_pts.append((x_step, y_val))
        draw.line(iss_pts, fill=(56, 189, 248), width=4)

        # Satellite icon marker & footprint
        iss_x = cx + int(cw * 0.58)
        iss_y = cy + int(ch * 0.42)
        # Footprint circle
        fp_r = 140
        draw.ellipse([iss_x - fp_r, iss_y - fp_r, iss_x + fp_r, iss_y + fp_r], outline=(56, 189, 248, 180), width=2)
        draw.ellipse([iss_x - 14, iss_y - 14, iss_x + 14, iss_y + 14], fill=(56, 189, 248), outline=(255, 255, 255), width=3)
        draw.text((iss_x + 24, iss_y - 14), "ISS (ZARYA) • 420 km", fill=(255, 255, 255), font=font_code)

        # Telemetry Card at bottom of map
        hud_y = cy + ch - 220
        draw.rounded_rectangle([cx + 20, hud_y, cx + cw - 20, hud_y + 190], radius=16, fill=(15, 23, 42, 230), outline=(56, 189, 248), width=2)
        draw.text((cx + 40, hud_y + 20), "TELEMETRY — ISS (ZARYA) [NORAD 25544]", fill=(56, 189, 248), font=font_tab)
        draw.text((cx + 40, hud_y + 64), "Lat: 28.572° N  |  Lng: 80.648° W", fill=(241, 245, 249), font=font_hud)
        draw.text((cx + 40, hud_y + 104), "Altitude: 419.8 km  |  Velocity: 7.66 km/s (17,135 mph)", fill=(241, 245, 249), font=font_hud)
        draw.text((cx + 40, hud_y + 144), "Period: 92.9 min  |  Inclination: 51.64°  |  Footprint: 4,450 km", fill=(148, 163, 184), font=font_hud)

    elif tab_name == "3d":
        # 3D Globe Mockup
        draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=20, fill=(8, 14, 26), outline=(30, 41, 59), width=3)
        globe_cx = cx + cw // 2
        globe_cy = cy + ch // 2 - 40
        globe_r = int(cw * 0.36)

        # Earth globe
        draw.ellipse([globe_cx - globe_r, globe_cy - globe_r, globe_cx + globe_r, globe_cy + globe_r], fill=(15, 45, 80), outline=(56, 189, 248), width=3)
        # Atmosphere ring
        draw.ellipse([globe_cx - globe_r - 12, globe_cy - globe_r - 12, globe_cx + globe_r + 12, globe_cy + globe_r + 12], outline=(56, 189, 248, 90), width=6)

        # Earth continents approximation
        draw.ellipse([globe_cx - 60, globe_cy - 70, globe_cx + 80, globe_cy + 50], fill=(16, 78, 59))
        draw.ellipse([globe_cx - 120, globe_cy - 40, globe_cx - 20, globe_cy + 90], fill=(16, 78, 59))

        # 3D Orbit rings tilted in space
        for idx, (tilt_deg, col, name) in enumerate([(51.6, (56, 189, 248), "ISS"), (98.2, (168, 85, 247), "Landsat 9"), (55.0, (16, 185, 129), "GPS-III")]):
            tilt = math.radians(tilt_deg)
            pts = []
            rw = globe_r + 90 + idx * 40
            rh = int(rw * 0.38)
            for deg in range(0, 360, 4):
                rad = math.radians(deg)
                x0 = rw * math.cos(rad)
                y0 = rh * math.sin(rad)
                xr = globe_cx + x0 * math.cos(tilt) - y0 * math.sin(tilt)
                yr = globe_cy + x0 * math.sin(tilt) + y0 * math.cos(tilt)
                pts.append((xr, yr))
            draw.line(pts + [pts[0]], fill=col, width=3)
            # marker on orbit
            mx, my = pts[idx * 25]
            draw.ellipse([mx - 10, my - 10, mx + 10, my + 10], fill=col, outline=(255, 255, 255), width=2)
            draw.text((mx + 16, my - 12), name, fill=(255, 255, 255), font=font_code)

        # Bottom 3D controls
        hud_y = cy + ch - 160
        draw.rounded_rectangle([cx + 40, hud_y, cx + cw - 40, hud_y + 120], radius=16, fill=(15, 23, 42), outline=(168, 85, 247), width=2)
        draw.text((cx + 60, hud_y + 24), "🌐 Real-Time 3D Orbital Projection (Three.js)", fill=(168, 85, 247), font=font_tab)
        draw.text((cx + 60, hud_y + 68), "Touch drag to rotate • Pinch to zoom • ECI to ECEF True Anomaly", fill=(203, 213, 225), font=font_hud)

    elif tab_name == "catalog":
        # Catalog Search & Filter Mockup
        draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=20, fill=(15, 23, 42), outline=(30, 41, 59), width=3)
        # Search bar
        draw.rounded_rectangle([cx + 30, cy + 30, cx + cw - 30, cy + 96], radius=14, fill=(30, 41, 59), outline=(56, 189, 248), width=2)
        draw.text((cx + 60, cy + 46), "🔍 Search 60+ satellites by name, NORAD ID…", fill=(148, 163, 184), font=font_hud)

        # Category Chips
        chips = ["All (64)", "Stations (2)", "Starlink (12)", "Weather (8)", "GPS (10)", "Science (8)"]
        chip_x = cx + 30
        chip_y = cy + 120
        for idx, chip in enumerate(chips):
            cw_chip = len(chip) * 16 + 24
            active = idx == 0
            bg_c = (14, 165, 233) if active else (30, 41, 59)
            fg_c = (255, 255, 255) if active else (203, 213, 225)
            draw.rounded_rectangle([chip_x, chip_y, chip_x + cw_chip, chip_y + 44], radius=12, fill=bg_c)
            draw.text((chip_x + 14, chip_y + 10), chip, fill=fg_c, font=font_hud)
            chip_x += cw_chip + 14
            if chip_x > cx + cw - 160 and idx < 4:
                break

        # Satellite Cards
        sats = [
            ("ISS (ZARYA)", "NORAD 25544 • LEO (420 km) • Inc: 51.6°", "TRACKING", (16, 185, 129)),
            ("HUBBLE SPACE TELESCOPE", "NORAD 20580 • LEO (535 km) • Inc: 28.5°", "TRACK", (56, 189, 248)),
            ("TIANGONG (CSS)", "NORAD 48274 • LEO (385 km) • Inc: 41.5°", "TRACK", (56, 189, 248)),
            ("NOAA 20 (JPSS-1)", "NORAD 43013 • SSO (824 km) • Inc: 98.7°", "TRACK", (56, 189, 248)),
            ("GPS III-05", "NORAD 48859 • MEO (20,180 km) • Inc: 55.0°", "TRACK", (56, 189, 248)),
        ]
        card_y = chip_y + 70
        for sname, ssub, btn_txt, btn_col in sats:
            draw.rounded_rectangle([cx + 30, card_y, cx + cw - 30, card_y + 110], radius=16, fill=(17, 24, 39), outline=(30, 41, 59), width=2)
            draw.text((cx + 50, card_y + 20), sname, fill=(248, 250, 252), font=font_tab)
            draw.text((cx + 50, card_y + 60), ssub, fill=(148, 163, 184), font=font_hud)
            
            # Action button
            draw.rounded_rectangle([cx + cw - 180, card_y + 30, cx + cw - 50, card_y + 80], radius=12, fill=btn_col)
            draw.text((cx + cw - 165, card_y + 44), btn_txt, fill=(255, 255, 255), font=font_tab)
            card_y += 128

    elif tab_name == "passes":
        # Pass Predictor Mockup
        draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=20, fill=(15, 23, 42), outline=(30, 41, 59), width=3)
        # Observer Header
        draw.rounded_rectangle([cx + 30, cy + 30, cx + cw - 30, cy + 110], radius=14, fill=(17, 24, 39), outline=(16, 185, 129), width=2)
        draw.text((cx + 50, cy + 44), "📍 Observer: Current GPS Location (37.77° N, 122.41° W)", fill=(248, 250, 252), font=font_tab)
        draw.text((cx + 50, cy + 74), "Searching upcoming visible passes next 48 hours for ISS", fill=(110, 231, 183), font=font_hud)

        # Passes List
        passes = [
            ("Pass 1: Tonight at 21:14 (In 42 mins)", "Max Elevation: 78° (Nearly Overhead)", "Rise: 21:11 SW  |  Set: 21:17 NE  |  Duration: 6m 12s", "EXCELLENT", (16, 185, 129)),
            ("Pass 2: Tonight at 22:51", "Max Elevation: 24° (Low North)", "Rise: 22:49 WNW  |  Set: 22:53 NNW  |  Duration: 4m 05s", "MODERATE", (245, 158, 11)),
            ("Pass 3: Tomorrow at 20:26", "Max Elevation: 62° (High Horizon)", "Rise: 20:23 SSW  |  Set: 20:30 ENE  |  Duration: 6m 40s", "GREAT", (16, 185, 129)),
            ("Pass 4: Tomorrow at 22:03", "Max Elevation: 38° (Mid Sky)", "Rise: 22:00 W  |  Set: 22:06 NNE  |  Duration: 5m 22s", "GOOD", (56, 189, 248)),
        ]
        py = cy + 130
        for ptitle, pelev, pdetail, qual, qcol in passes:
            draw.rounded_rectangle([cx + 30, py, cx + cw - 30, py + 130], radius=16, fill=(17, 24, 39), outline=(30, 41, 59), width=2)
            draw.text((cx + 50, py + 18), ptitle, fill=(248, 250, 252), font=font_tab)
            draw.text((cx + 50, py + 56), pelev, fill=qcol, font=font_hud)
            draw.text((cx + 50, py + 92), pdetail, fill=(148, 163, 184), font=font_hud)
            
            draw.rounded_rectangle([cx + cw - 190, py + 22, cx + cw - 50, py + 62], radius=10, fill=qcol)
            draw.text((cx + cw - 175, py + 32), qual, fill=(255, 255, 255), font=font_tab)
            py += 150

    elif tab_name == "ai":
        # AI Orbital Assistant Mockup
        draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=20, fill=(15, 23, 42), outline=(30, 41, 59), width=3)
        # Providers Selector Bar
        draw.rounded_rectangle([cx + 30, cy + 30, cx + cw - 30, cy + 90], radius=14, fill=(17, 24, 39))
        draw.text((cx + 50, cy + 46), "Provider: Google Gemini • OpenAI • Anthropic • Ollama (Local)", fill=(203, 213, 225), font=font_hud)

        # Chat Bubble 1 (User)
        draw.rounded_rectangle([cx + 180, cy + 120, cx + cw - 30, cy + 200], radius=16, fill=(14, 165, 233))
        draw.text((cx + 210, cy + 144), "Which Earth observation satellites are passing over North America now?", fill=(255, 255, 255), font=font_hud)

        # Chat Bubble 2 (AI Assistant)
        draw.rounded_rectangle([cx + 30, cy + 220, cx + cw - 120, cy + 450], radius=16, fill=(17, 24, 39), outline=(168, 85, 247), width=2)
        draw.text((cx + 50, cy + 240), "✨ Orbital Discovery Engine:", fill=(168, 85, 247), font=font_tab)
        draw.text((cx + 50, cy + 280), "Currently 2 primary observation satellites are in range:", fill=(241, 245, 249), font=font_hud)
        draw.text((cx + 50, cy + 320), "1. LANDSAT 9 (NORAD 49260): Alt 705 km, Inc 98.2° SSO", fill=(56, 189, 248), font=font_hud)
        draw.text((cx + 50, cy + 360), "2. SENTINEL-2A (NORAD 40697): Alt 786 km, multispectral", fill=(56, 189, 248), font=font_hud)
        draw.text((cx + 50, cy + 400), "SGP4 ground track passes above Great Lakes in ~12 mins.", fill=(148, 163, 184), font=font_hud)

        # One-tap Action Card
        draw.rounded_rectangle([cx + 50, cy + 470, cx + cw - 50, cy + 540], radius=12, fill=(6, 78, 59), outline=(16, 185, 129), width=2)
        draw.text((cx + 80, cy + 494), "🎯 Track Landsat 9 and Sentinel-2A on Map Now", fill=(110, 231, 183), font=font_tab)

        # Input Box
        draw.rounded_rectangle([cx + 30, cy + ch - 110, cx + cw - 30, cy + ch - 30], radius=16, fill=(30, 41, 59), outline=(56, 189, 248), width=2)
        draw.text((cx + 60, cy + ch - 80), "Ask any orbital query or SQL filter…", fill=(148, 163, 184), font=font_hud)

    # Bottom Android Navigation Bar (5 tabs)
    nav_y = phone_y + phone_h - 110
    draw.rounded_rectangle([phone_x + 20, nav_y, phone_x + phone_w - 20, nav_y + 80], radius=20, fill=(17, 24, 39), outline=(30, 41, 59), width=2)
    nav_tabs = [("📡 Track", "2d"), ("🌐 Globe", "3d"), ("🔍 Catalog", "catalog"), ("⏱️ Passes", "passes"), ("✨ AI", "ai")]
    tab_w = (phone_w - 40) // 5
    for idx, (label, key) in enumerate(nav_tabs):
        tx = phone_x + 20 + idx * tab_w
        is_active = (key == tab_name)
        col = (56, 189, 248) if is_active else (148, 163, 184)
        if is_active:
            draw.rounded_rectangle([tx + 8, nav_y + 10, tx + tab_w - 8, nav_y + 70], radius=12, fill=(15, 23, 42))
        draw.text((tx + tab_w // 2 - 40, nav_y + 26), label, fill=col, font=font_tab)

    return img

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    play_dir = os.path.join(root, "fastlane", "metadata", "android", "en-US", "images")
    amazon_dir = os.path.join(root, "dist-store", "amazon")
    docs_dir = os.path.join(root, "docs", "store-assets")
    
    ensure_dir(play_dir)
    ensure_dir(os.path.join(play_dir, "phoneScreenshots"))
    ensure_dir(os.path.join(play_dir, "sevenInchScreenshots"))
    ensure_dir(os.path.join(play_dir, "tenInchScreenshots"))
    ensure_dir(amazon_dir)
    ensure_dir(docs_dir)

    print("Generating 512x512 Store Icon...")
    icon = draw_satellite_icon(512)
    icon.save(os.path.join(play_dir, "icon.png"), "PNG")
    icon.save(os.path.join(amazon_dir, "icon_512.png"), "PNG")
    icon.save(os.path.join(docs_dir, "icon_512.png"), "PNG")

    print("Generating 114x114 Amazon Small Icon...")
    icon_114 = icon.resize((114, 114), Image.Resampling.LANCZOS)
    icon_114.save(os.path.join(amazon_dir, "icon_114.png"), "PNG")
    icon_114.save(os.path.join(docs_dir, "icon_114.png"), "PNG")

    print("Generating 1024x500 Feature Graphic...")
    feat = draw_feature_graphic(1024, 500)
    feat.save(os.path.join(play_dir, "featureGraphic.png"), "PNG")
    feat.save(os.path.join(docs_dir, "featureGraphic.png"), "PNG")

    # Generate Phone Screenshots (1080x1920)
    screens = [
        ("1_2d_tracker.png", "Live 2D Multi-Orbit Tracker", "Real-time SGP4 propagation, ground tracks & footprint circles", "2d"),
        ("2_3d_globe.png", "Interactive 3D Earth Globe", "True 3D orbital inclination visualization in space", "3d"),
        ("3_catalog_search.png", "Global Satellite Catalog", "Search 60+ preloaded spacecraft with 1-tap CelesTrak sync", "catalog"),
        ("4_pass_predictor.png", "Next Visible Pass Predictor", "Observer overpass calculations with sky elevation compass", "passes"),
        ("5_ai_discovery.png", "Offline & Remote AI Discovery", "Natural language queries with optional Gemini/OpenAI key vault", "ai"),
    ]

    for fname, title, subtitle, tab in screens:
        print(f"Generating screenshot: {fname}...")
        sc = draw_screenshot(title, subtitle, tab, 1080, 1920)
        sc.save(os.path.join(play_dir, "phoneScreenshots", fname), "PNG")
        sc.save(os.path.join(amazon_dir, fname), "PNG")
        sc.save(os.path.join(docs_dir, fname), "PNG")
        
        # Tablet versions
        sc_7 = sc.resize((1200, 1920), Image.Resampling.LANCZOS)
        sc_7.save(os.path.join(play_dir, "sevenInchScreenshots", fname), "PNG")
        
        sc_10 = sc.resize((1600, 2560), Image.Resampling.LANCZOS)
        sc_10.save(os.path.join(play_dir, "tenInchScreenshots", fname), "PNG")

    print("All store assets successfully created!")

if __name__ == "__main__":
    main()
