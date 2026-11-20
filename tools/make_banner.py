"""Generate the Railway Self banner from the approved artwork.

Run from any directory:
    python tools/make_banner.py

The source artwork is stored beside this script as banner_source.png.
The output is written to assets/banner.jpg in the project root.
"""
from pathlib import Path
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
SOURCE = HERE / "banner_source.png"
OUT = PROJECT_ROOT / "assets" / "banner.jpg"
SIZE = (1200, 800)


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Banner source not found: {SOURCE}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE) as original:
        image = ImageOps.fit(
            original.convert("RGB"),
            SIZE,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        image.save(OUT, "JPEG", quality=95, optimize=True, progressive=True)

    print(f"Banner saved: {OUT} ({SIZE[0]}x{SIZE[1]})")


if __name__ == "__main__":
    main()
