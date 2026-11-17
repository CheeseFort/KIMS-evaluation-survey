# Fusion evaluation survey

A static GitHub Pages survey with a Google Apps Script endpoint and a private Google Sheet.

## Important design choices

- A new participant ID is generated each time the survey page loads.
- Trial selection is deterministic for that participant ID.
- The selector groups records by `scene_id + image_type`; it selects 10 distinct groups.
- One image is selected at random from each chosen group. The selection is deterministic for the participant ID.
- `fusion_01`, `fusion_02`, etc. are treated as distinct image types.
- Trials 1–5 show the image until the participant answers.
- Trials 6–10 show only the preloaded image for 1,000 ms. The image then disappears and the questions appear.
- No timer or countdown is shown.
- The browser receives image paths only. The correct count and description stay in the private Google Sheet and are added by Apps Script when responses arrive.
- Responses are submitted as 10 rows in one batch.
- The Google Sheet and scene annotations are kept private. `dataset.tsv` and `scenes.csv` are not tracked or published on the website.


## Dataset generation

Two Python scripts help create and populate the survey dataset.

Install the required library:

```bash
pip install pillow
```

### Generate the dataset files

`generate_dataset.py` scans the image folders and creates:

- `dataset.json`: the public image manifest required for the survey website.
- `dataset.tsv`: a tab-separated template for populating the private Google Sheets `Dataset` tab.

The expected directory structure is:

```text
images/
├── scenes.csv
├── scene_01/
│   ├── rgb/
│   ├── ir/
│   ├── fusion_01/
│   ├── fusion_02/
│   └── ...
└── scene_02/
    └── ...
```

The `scenes.csv` file must exist and contain these columns:

```csv
id,description,people
scene_01,scene 01,2
scene_02,scene 02,0
```

The TSV includes the scene ID, image type, image path, description, and actual people count. Paste its contents into the private Google Sheet's `Dataset` tab.

### Generate test images

`generate_test_images.py` creates sample JPEG images for testing.

Run from the project root:

```bash
python generate_test_images.py
```

By default, it creates 10 scene folders under `images/`. Each scene contains 1–5 randomly generated images in each of these folders:

- `rgb`
- `ir`
- `fusion_01`
- `fusion_02`

Each image displays its file path. Existing files may be overwritten.

Optional arguments:

```bash
python generate_test_images.py --scenes 20
python generate_test_images.py --seed 42
python generate_test_images.py test_images
python generate_test_images.py --clean
```

Use `--seed` to make the random image counts repeatable. Use `--clean` to remove the existing output directory before generating images.
