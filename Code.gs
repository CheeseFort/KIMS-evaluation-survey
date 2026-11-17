/*
 * Google Apps Script backend.
 *
 * Required private Google Sheet tabs:
 *
 * Dataset columns:
 * A: scene_id
 * B: image_type
 * C: image_path
 * D: description
 * E: actual_people
 *
 * Responses tab: created automatically if it does not exist.
 *
 * Deploy as a Web App:
 *   Execute as: Me
 *   Who has access: Anyone
 */

const SPREADSHEET_ID = "PASTE_YOUR_GOOGLE_SPREADSHEET_ID_HERE";
const DATASET_TAB = "Dataset";
const RESPONSES_TAB = "Responses";
const EXPECTED_TRIALS = 10;
const NORMAL_TRIALS = 5;
const ALLOWED_PEOPLE = [0, 1, 2, 3, 4];
const ALLOWED_CONFIDENCE = [1, 2, 3, 4, 5];

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    const payload = JSON.parse(e.postData.contents || "{}");
    validatePayload_(payload);

    // Reject repeated submissions for the same participant ID.
    const props = PropertiesService.getScriptProperties();
    const submissionKey = "submitted_" + hash_(payload.participant_id);
    if (props.getProperty(submissionKey)) {
      return output_("This participant ID has already submitted.");
    }

    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const dataset = loadPrivateDataset_(ss);
    const responseRows = payload.responses.map((r) => {
      const key = r.scene_id + "::" + r.image_type + "::" + r.image_path;
      const answer = dataset[key];
      if (!answer) throw new Error("A submitted image is not in the private dataset.");

      return [
        safeCell_(payload.participant_id),
        Number(r.trial_number),
        r.stage,
        safeCell_(r.scene_id),
        safeCell_(r.image_type),
        safeCell_(r.image_path),
        answer.actual_people,
        answer.description,
        Number(r.reported_people),
        Number(r.confidence),
        r.exposure_ms === null ? "" : Number(r.exposure_ms),
        r.response_time_ms === null ? "" : Number(r.response_time_ms),
        new Date()
      ];
    });

    lock.waitLock(20000);
    // Recheck after acquiring lock to prevent near-simultaneous duplicates.
    if (props.getProperty(submissionKey)) {
      lock.releaseLock();
      return output_("This participant ID has already submitted.");
    }

    let sheet = ss.getSheetByName(RESPONSES_TAB);
    if (!sheet) {
      sheet = ss.insertSheet(RESPONSES_TAB);
      sheet.appendRow([
        "Participant ID", "Trial", "Stage", "Scene ID", "Image Type",
        "Image Path", "Actual People", "Description", "Reported People",
        "Confidence", "Exposure ms", "Response Time ms", "Submitted At"
      ]);
    }

    const firstRow = sheet.getLastRow() + 1;
    sheet.getRange(firstRow, 1, responseRows.length, responseRows[0].length)
      .setValues(responseRows);

    props.setProperty(submissionKey, new Date().toISOString());
    lock.releaseLock();
    return output_("Success");
  } catch (err) {
    try { lock.releaseLock(); } catch (ignored) {}
    console.error(err);
    return output_("Error: " + err.message);
  }
}

function validatePayload_(p) {
  if (!p || typeof p.participant_id !== "string" ||
      !/^[A-Za-z0-9_-]{3,100}$/.test(p.participant_id)) {
    throw new Error("Invalid participant ID.");
  }
  if (!Array.isArray(p.responses) || p.responses.length !== EXPECTED_TRIALS) {
    throw new Error("Exactly 10 trial responses are required.");
  }

  const seen = {};
  p.responses.forEach((r, i) => {
    if (Number(r.trial_number) !== i + 1) throw new Error("Trial order is invalid.");
    const expectedStage = i < NORMAL_TRIALS ? "normal" : "timed";
    if (r.stage !== expectedStage) throw new Error("Trial stage is invalid.");
    if (!ALLOWED_PEOPLE.includes(Number(r.reported_people))) throw new Error("Invalid people count.");
    if (!ALLOWED_CONFIDENCE.includes(Number(r.confidence))) throw new Error("Invalid confidence score.");
    if (!r.scene_id || !r.image_type || !r.image_path) throw new Error("Trial image details are missing.");

    const sceneType = r.scene_id + "::" + r.image_type;
    if (seen[sceneType]) throw new Error("A scene and image type cannot repeat.");
    seen[sceneType] = true;

    if (i < NORMAL_TRIALS && r.exposure_ms !== null) throw new Error("Normal exposure value is invalid.");
    if (i >= NORMAL_TRIALS && Number(r.exposure_ms) !== 1000) throw new Error("Timed exposure value is invalid.");
  });
}

function loadPrivateDataset_(ss) {
  const sheet = ss.getSheetByName(DATASET_TAB);
  if (!sheet) throw new Error("The private Dataset tab was not found.");

  const values = sheet.getDataRange().getValues();
  const result = {};
  for (let i = 1; i < values.length; i++) {
    const [sceneId, imageType, imagePath, description, actualPeople] = values[i];
    if (!sceneId || !imageType || !imagePath) continue;
    const count = Number(actualPeople);
    if (!ALLOWED_PEOPLE.includes(count)) continue;
    const key = String(sceneId) + "::" + String(imageType) + "::" + String(imagePath);
    result[key] = { description: String(description || ""), actual_people: count };
  }
  return result;
}

function safeCell_(value) {
  const text = String(value == null ? "" : value).slice(0, 500);
  // Prevent spreadsheet formula injection from submitted strings.
  return /^[=+\-@]/.test(text) ? "'" + text : text;
}

function hash_(value) {
  const bytes = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256, value, Utilities.Charset.UTF_8
  );
  return Utilities.base64EncodeWebSafe(bytes).replace(/=+$/, "");
}

function output_(message) {
  return ContentService.createTextOutput(message)
    .setMimeType(ContentService.MimeType.TEXT);
}
