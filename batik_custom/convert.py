
import json
from pathlib import Path

source_path = Path("color_palettes_24.json")
output_path = Path("color_palette_fixture.json")

with source_path.open("r", encoding="utf-8") as f:
    data = json.load(f)

if isinstance(data, list) and data and "model" in data[0]:
    print("JSON sudah berformat fixture.")
    fixture = data
else:
    palettes = data["color_palettes"]
    fixture = [
        {
            "model": "batik_custom.colorpalette",
            "pk": i,
            "fields": {
                "name": palette["name"],
                "description": palette.get("description", ""),
                "colors": palette.get("colors", []),
                "is_active": True,
            },
        }
        for i, palette in enumerate(palettes, start=1)
    ]

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(fixture, f, ensure_ascii=False, indent=2)

    print(f"Berhasil membuat fixture untuk {len(fixture)} palet.")
    print(f"File: {output_path}")
