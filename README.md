# Fusion evaluation survey

A static GitHub Pages survey with a Google Apps Script endpoint and a private Google Sheet.

## Important design choices

- The participant ID is generated once in the browser and saved in `localStorage`.
- Trial selection is deterministic for that participant ID.
- The selector groups records by `scene_id + image_type`; it selects 10 distinct groups.
- One image is selected at random from each chosen group. The selection is deterministic for the participant ID.
- `fusion_01`, `fusion_02`, etc. are treated as distinct image types.
- Trials 1–5 show the image until the participant answers.
- Trials 6–10 show only the preloaded image for 1,000 ms. The image then disappears and the questions appear.
- No timer or countdown is shown.
- The browser receives image paths only. The correct count and description stay in the private Google Sheet and are added by Apps Script when responses arrive.
- Responses are submitted as 10 rows in one batch.

## 1. Create the Google Sheet

Create a spreadsheet. Add a tab named `Dataset` with these exact headers in row 1:

| scene_id | image_type | image_path | description | actual_people |
|---|---|---|---|---|

Add one row per image file. Example:

| scene_id | image_type | image_path | description | actual_people |
|---|---|---|---|---:|
| scene_01 | rgb | images/scene_01/rgb/01.png | Hallway | 2 |
| scene_01 | rgb | images/scene_01/rgb/02.png | Hallway | 2 |
| scene_01 | ir | images/scene_01/ir/01.png | Hallway | 2 |
| scene_01 | fusion_01 | images/scene_01/fusion_01/01.png | Hallway | 2 |
| scene_01 | fusion_02 | images/scene_01/fusion_02/01.png | Hallway | 2 |

Keep this spreadsheet private. `actual_people` must be one of 0, 1, 2, 3, or 4 for the current survey UI.

**Selection rule:** each distinct `scene_id + image_type` pair is one selection bucket. If a bucket has several images, the survey picks one of them deterministically for the participant ID. Thus `scene_01/rgb/01.png` and `scene_01/rgb/02.png` do not create two chances to select `scene_01/rgb`; they are alternatives within one bucket.

There must be at least 10 distinct scene/type buckets.

## 2. Set up Apps Script

1. Open https://script.google.com and create a project.
2. Replace the starter code with `Code.gs` from this project.
3. Replace `PASTE_YOUR_GOOGLE_SPREADSHEET_ID_HERE` with the ID from the Google Sheet URL.
4. Save.
5. Deploy > New deployment > Web app.
6. Set **Execute as** to **Me**.
7. Set **Who has access** to **Anyone**.
8. Deploy and authorize.
9. Copy the Web app URL.

The script creates the `Responses` tab and its headers on the first valid submission. It looks up the ground-truth people count and description in the private `Dataset` tab. The respondent's browser does not receive those fields.

## 3. Configure the website

1. In `survey.js`, replace `PASTE_YOUR_APPS_SCRIPT_WEB_APP_URL_HERE` with the deployed Web app URL.
2. Fill `dataset.json` with all image paths. It is a public manifest, so do not put descriptions or ground-truth counts in it.
3. Upload the image files to the repository, preserving the paths in `dataset.json`.
4. Commit the files.

Example repository layout:

```text
my-survey/
  index.html
  styles.css
  survey.js
  dataset.json
  Code.gs                 # Apps Script source; not executed by GitHub Pages
  images/
    scene_01/
      rgb/
        01.png
        02.png
      ir/
        01.png
      fusion_01/
        01.png
      fusion_02/
        01.png
```

For external image hosting, set `imageBaseUrl` in `survey.js` to the HTTPS base URL and use paths relative to that base in `dataset.json`, or put full HTTPS URLs in `path`.

## 4. Enable GitHub Pages

In the repository: Settings > Pages > Deploy from a branch > `main` > `/(root)` > Save.

## 5. Test before sharing

1. Open the published URL in a private browser window.
2. Complete all 10 trials.
3. Check that the `Responses` tab contains 10 rows.
4. Check that trials 1–5 have a blank Exposure ms value and trials 6–10 have 1000.
5. Check that the same participant ID cannot submit twice.
6. Test a different browser or clear the site data to create a new participant ID.

## Operational and research notes

- The participant ID is stored in browser `localStorage`. Clearing browser data or using another browser creates a new ID. This is not strong identity verification and cannot prevent a determined person from participating more than once.
- The Apps Script web app is public. Anyone who obtains its URL can send requests. The script validates the payload and checks every image against the private Dataset tab, but public endpoints can still be abused. Add a stronger anti-abuse measure if the survey will be widely distributed.
- Browser `no-cors` mode does not let the page read the Apps Script response. The completion page can say the submission was sent, but it cannot confirm that Google Sheets stored it. Always test the endpoint and inspect the sheet.
- A one-second display is scheduled after the image has preloaded. Browser scheduling is not a laboratory-grade display system; screen refresh, browser load, and device performance can affect actual exposure. If exact exposure timing is critical, use a controlled experiment platform and validated display hardware.
- This starter does not implement pause/resume or partial response recovery. Keep participants on the page until they submit.
- The current answer choices are 0–4, as requested. Update the front-end choices and Apps Script validation together if you later change that range.
