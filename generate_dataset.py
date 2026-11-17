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

# Read scene metadata.
scenes_csv = image_root / "scenes.csv"

if not scenes_csv.is_file():
    sys.exit(f"ERROR: scene metadata file not found: {scenes_csv}")

scenes = {}

try:
    with scenes_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        required_columns = {"id", "description", "people"}
        if not required_columns.issubset(reader.fieldnames or []):
            sys.exit(
                "ERROR: scenes.csv must contain columns: id, description, people"
            )

        for line_number, row in enumerate(reader, start=2):
            scene_id = (row["id"] or "").strip()
            description = (row["description"] or "").strip()
            people_text = (row["people"] or "").strip()

            if not scene_id:
                sys.exit(f"ERROR: missing scene ID on CSV line {line_number}")

            if scene_id in scenes:
                sys.exit(f"ERROR: duplicate scene ID: {scene_id}")

            if not description:
                sys.exit(
                    f"ERROR: missing description for {scene_id} "
                    f"on CSV line {line_number}"
                )

            try:
                people = int(people_text)
                if people < 0:
                    raise ValueError
            except ValueError:
                sys.exit(
                    f"ERROR: invalid people count for {scene_id} "
                    f"on CSV line {line_number}: {people_text!r}"
                )

            scenes[scene_id] = {
                "description": description,
                "people": people
            }

except (OSError, csv.Error) as e:
    sys.exit(f"ERROR: could not read {scenes_csv}: {e}")

if not scenes:
    sys.exit("ERROR: scenes.csv contains no scene records.")

records = []
scene_count = 0
bucket_count = 0
found_scene_ids = set()

# Expected: images/scene_id/image_type/image-file
# Recursively includes image files below each image_type directory.
for scene_dir in sorted(
    (p for p in image_root.iterdir() if p.is_dir()), key=lambda p: p.name
):
    scene_id = scene_dir.name

    if scene_id not in scenes:
        sys.exit(
            f"ERROR: scene folder '{scene_id}' has no entry in scenes.csv."
        )

    found_scene_ids.add(scene_id)
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
                "scene_id": scene_id,
                "image_type": type_dir.name,
                "path": image_file.relative_to(project_root).as_posix()
            })

# Ensure every CSV scene has a corresponding image folder.
missing_folders = set(scenes) - found_scene_ids

if missing_folders:
    sys.exit(
        "ERROR: these scenes appear in scenes.csv but have no image folder: "
        + ", ".join(sorted(missing_folders))
    )

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

# Private Google Sheets template.
with tsv_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f, delimiter="\t", lineterminator="\n")
    writer.writerow([
        "scene_id", "image_type", "image_path", "description", "actual_people"
    ])

    for record in records:
        metadata = scenes[record["scene_id"]]

        writer.writerow([
            record["scene_id"],
            record["image_type"],
            record["path"],
            metadata["description"],
            metadata["people"]
        ])

print(f"Read {len(scenes)} scene records from {scenes_csv}.")
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
    "Keep the spreadsheet private."
)
