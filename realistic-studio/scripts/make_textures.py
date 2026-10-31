"""Small, deterministic original texture assets; no network or external licences."""
from pathlib import Path
import math
import random
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent / 'assets' / 'textures'
ROOT.mkdir(exist_ok=True)
rng = random.Random(41)
for kind in ('plaster', 'stone', 'wood', 'tile', 'grass', 'fabric'):
    size = 512
    image = Image.new('RGB', (size, size))
    rough = Image.new('RGB', (size, size))
    normal = Image.new('RGB', (size, size), (128, 128, 255))
    pixels = image.load()
    rp = rough.load()
    np = normal.load()
    for y in range(size):
        for x in range(size):
            noise = rng.uniform(-1, 1)
            if kind == 'wood':
                grain = math.sin(x * 0.14 + math.sin(y * 0.025) * 2 + math.sin(y * 0.007) * 4) * 0.5 + math.sin(x * 0.7 + y * 0.013) * 0.2
                v = 0.66 + grain * 0.12 + noise * 0.06
                rgb = (v, v * 0.76, v * 0.48)
                r = 155
            elif kind == 'tile':
                seam = x % 256 < 3 or y % 256 < 3
                v = 0.48 if seam else 0.91 + noise * 0.015 + math.sin(x * 0.016 + y * 0.011) * 0.015
                rgb = (v, v * 0.99, v * 0.96)
                r = 120 if not seam else 220
            elif kind == 'stone':
                seam = y % 128 < 4 or (x + (128 if y // 128 % 2 else 0)) % 256 < 4
                v = 0.42 if seam else 0.74 + noise * 0.1 + math.sin(x * 0.029 + y * 0.015) * 0.05
                rgb = (v, v * 0.96, v * 0.88)
                r = 215
            elif kind == 'grass':
                v = 0.6 + noise * 0.22
                rgb = (v * 0.55, v, v * 0.32)
                r = 245
            elif kind == 'fabric':
                v = 0.83 + noise * 0.05 + (0.035 if (x + y) % 4 == 0 else 0)
                rgb = (v, v, v)
                r = 240
            else:
                v = 0.93 + noise * 0.045
                rgb = (v, v * 0.99, v * 0.97)
                r = 220
            pixels[x, y] = tuple((max(0, min(255, round(c * 255))) for c in rgb))
            rv = max(0, min(255, int(r + noise * 12)))
            rp[x, y] = (rv, rv, rv)
            strength = 5 if kind in ('plaster', 'fabric') else 10
            np[x, y] = (int(128 + noise * strength), int(128 + rng.uniform(-1, 1) * strength), 254)
    for label, img in [('color', image), ('roughness', rough), ('normal', normal)]:
        img.save(ROOT / f'{kind}_{label}.png', optimize=True)
print('Created original PBR texture sets:', ROOT)
