import argparse
import csv
import json
import sys
from pathlib import Path

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"
}

parser = argparse.ArgumentParser(
    description="Generate dataset.json and a Google Sheets TSV template."
)
parser.add_argument("image_root", nargs="?", default="images")
parser.add_argument("json_output", nargs="?", default="dataset.json")
parser.add_argument("tsv_output", nargs="?", default="dataset.tsv")
args = parser.parse_args()

project_root = Path.cwd().resolve()
image_root = Path(args.image_root).resolve()

if not image_root.is_dir():
    sys.exit(f"ERROR: image directory does not exist: {image_root}")

try:
    image_root.relative_to(project_root)
except ValueError:
    sys.exit(
        "ERROR: image directory must be inside the current project directory "
        "so generated paths work on GitHub Pages."
    )

records = []
scene_count = 0
bucket_count = 0

# Expected: images/scene_id/image_type/image-file
# Recursively includes image files below each image_type directory.
for scene_dir in sorted(
    (p for p in image_root.iterdir() if p.is_dir()), key=lambda p: p.name
):
    scene_count += 1

    for type_dir in sorted(
        (p for p in scene_dir.iterdir() if p.is_dir()), key=lambda p: p.name
    ):
        image_files = sorted(
            (
                p for p in type_dir.rglob("*")
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            ),
            key=lambda p: p.as_posix()
        )

        if not image_files:
            continue

        bucket_count += 1
        for image_file in image_files:
            records.append({
                "scene_id": scene_dir.name,
                "image_type": type_dir.name,
                "path": image_file.relative_to(project_root).as_posix()
            })

records.sort(key=lambda r: (r["scene_id"], r["image_type"], r["path"]))

if not records:
    sys.exit(
        "ERROR: no supported image files found. Expected folders such as "
        "images/scene_01/rgb/01.png."
    )

json_path = Path(args.json_output)
tsv_path = Path(args.tsv_output)
json_path.parent.mkdir(parents=True, exist_ok=True)
tsv_path.parent.mkdir(parents=True, exist_ok=True)

# Public website manifest: deliberately contains no annotations.
with json_path.open("w", encoding="utf-8") as f:
    json.dump({"images": records}, f, indent=2, ensure_ascii=False)
    f.write("\n")

# Private Google Sheets template. Fill in description and actual_people.
with tsv_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f, delimiter="\t", lineterminator="\n")
    writer.writerow([
        "scene_id", "image_type", "image_path", "description", "actual_people"
    ])
    for record in records:
        writer.writerow([
            record["scene_id"], record["image_type"], record["path"], "", ""
        ])

print(f"Found {scene_count} scene folders.")
print(f"Found {bucket_count} scene/type combinations.")
print(f"Found {len(records)} image files.")
print(f"Wrote public manifest: {json_path}")
print(f"Wrote annotation template: {tsv_path}")
if bucket_count < 10:
    print(
        "WARNING: fewer than 10 distinct scene/type combinations found. "
        "The survey needs at least 10.",
        file=sys.stderr
    )
print(
    "\nPaste dataset.tsv into the private Google Sheet's Dataset tab. "
    "Fill in description and actual_people there. Keep the spreadsheet private."
)
