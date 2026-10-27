"""Centre-crop deck photos to the exact aspect ratio of the box they fill on the slide (v10.1).

build_deck_v10.js writes crop_jobs.json ([{src, w, h, out}], w/h in inches) and runs this file before pptxgenjs reads the
images, so every picture is placed with plain w/h and no sizing option: its displayed ratio equals the file's pixel ratio.
Output size is capped at 300 px per inch and never upscaled. Renders with margins use fit (letterbox) in the build instead.

    /usr/bin/python3 docs/presentation/deck_v10/crop_photos.py [crop_jobs.json]
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).parent
PPI = 300


def crop(src, w_in, h_in, out):
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    W, H = im.size
    want = w_in / h_in
    if W / H > want:                       # too wide: trim the sides
        cw = round(H * want); box = ((W - cw) // 2, 0, (W - cw) // 2 + cw, H)
    else:                                  # too tall: trim top and bottom
        ch = round(W / want); box = (0, (H - ch) // 2, W, (H - ch) // 2 + ch)
    im = im.crop(box)
    tw = min(im.width, round(w_in * PPI))
    th = max(1, round(tw * im.height / im.width))
    if tw < im.width:
        im = im.resize((tw, th), Image.LANCZOS)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=88)
    return im.size


def main(jobs_file=HERE / "crop_jobs.json"):
    jobs = json.loads(Path(jobs_file).read_text())
    for j in jobs:
        size = crop(j["src"], j["w"], j["h"], j["out"])
        print(f"{Path(j['out']).name}: {size[0]}x{size[1]} for {j['w']:.3f}x{j['h']:.3f} in")


if __name__ == "__main__":
    main(*(Path(a) for a in sys.argv[1:2]))
