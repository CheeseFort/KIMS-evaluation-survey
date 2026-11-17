/*
 * Image perception survey.
 * Image selection is deterministic for a participant ID.
 * A scene + image-type bucket can appear only once; one image is selected
 * from that bucket. "fusion_01", "fusion_02", etc. are separate types.
 */

const CONFIG = {
  // Use a relative path for images stored in this GitHub repository.
  // For external image hosting, use a full HTTPS base URL instead.
  imageBaseUrl: "",
  manifestUrl: "dataset.json",
  // Replace with the deployed Google Apps Script Web App URL.
  appsScriptUrl: "https://script.google.com/macros/s/AKfycbxAaaTC9A-ZNB4DJP1oQxx5C9f61Pwbco2mYLgCDD2qM2N0kBRp43WmRVGI9di5WlU/exec",
  trialsPerParticipant: 10,
  normalTrials: 5,
  timedExposureMs: 1000
};

const $ = (id) => document.getElementById(id);
const sections = ["welcome", "instructions-normal", "trial",
                  "instructions-timed", "complete", "fatal-error"];

let participantId = "";
let assignment = [];
let currentTrialIndex = 0;
let trialStartedAt = null;
let currentImageVisibleAt = null;
let responses = [];
let isSubmitting = false;
let surveySubmitted = false;

window.addEventListener("beforeunload", (event) => {
  if (surveySubmitted) return;

  event.preventDefault();
  event.returnValue = "";
});

function showSection(id) {
  sections.forEach((sectionId) => $(sectionId).classList.toggle("hidden", sectionId !== id));
}

function createParticipantId() {
  return "P-" + crypto.randomUUID();
}

function hashString(value) {
  // FNV-1a 32-bit hash.
  let hash = 0x811c9dc5;
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

function seededRandom(seed) {
  // Mulberry32 deterministic PRNG.
  return function () {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function seededShuffle(items, seed) {
  const result = [...items];
  const random = seededRandom(seed);
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

function normalizeManifest(manifest) {
  if (!manifest || !Array.isArray(manifest.images)) {
    throw new Error("dataset.json must contain an 'images' array.");
  }

  const valid = manifest.images.filter((item) =>
    item &&
    typeof item.scene_id === "string" &&
    typeof item.image_type === "string" &&
    typeof item.path === "string" &&
    item.path.length > 0
  );

  // Group images by scene + type. A bucket can contribute only one trial.
  const buckets = new Map();
  valid.forEach((item) => {
    const key = `${item.scene_id}::${item.image_type}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(item);
  });

  return [...buckets.entries()].map(([key, images]) => ({ key, images }));
}

function selectTrials(buckets, id) {
  if (buckets.length < CONFIG.trialsPerParticipant) {
    throw new Error(
      `The dataset has ${buckets.length} unique scene/type combinations. ` +
      `At least ${CONFIG.trialsPerParticipant} are required.`
    );
  }

  const orderedBuckets = seededShuffle(buckets, hashString(id));
  const selectedBuckets = orderedBuckets.slice(0, CONFIG.trialsPerParticipant);

  return selectedBuckets.map((bucket, index) => {
    const imageSeed = hashString(`${id}|${bucket.key}|image`);
    const selectedImage = seededShuffle(bucket.images, imageSeed)[0];
    return {
      trial_number: index + 1,
      scene_id: selectedImage.scene_id,
      image_type: selectedImage.image_type,
      image_path: selectedImage.path
    };
  });
}

function getImageUrl(path) {
  if (/^https:\/\//i.test(path)) return path;
  const cleanPath = path.replace(/^\/+/, "");
  if (CONFIG.imageBaseUrl) {
    const base = CONFIG.imageBaseUrl.replace(/\/$/, "") + "/";
    return new URL(cleanPath, base).href;
  }
  // Resolve relative to the deployed site folder. This works for project
  // Pages URLs such as username.github.io/repository/images/...
  return new URL(cleanPath, document.baseURI).href;
}

function preloadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Could not load image: ${url}`));
    image.src = url;
  });
}

function getRadioValue(name) {
  const selected = document.querySelector(`input[name="${name}"]:checked`);
  return selected ? selected.value : "";
}

function updateNextButton() {
  $("next-button").disabled = !(getRadioValue("people") !== "" &&
                                 getRadioValue("confidence") !== "");
}

function clearAnswers() {
  document.querySelectorAll('input[name="people"], input[name="confidence"]')
    .forEach((input) => { input.checked = false; });
  updateNextButton();
}

function setImageVisible(visible) {
  $("trial-image").classList.toggle("hidden", !visible);
  $("image-placeholder").classList.add("hidden");
}

async function renderTrial() {
  const trial = assignment[currentTrialIndex];
  const isTimed = currentTrialIndex >= CONFIG.normalTrials;

  $("stage-label").textContent = isTimed ? "Timed viewing" : "Normal viewing";
  $("trial-title").textContent = `Trial ${currentTrialIndex + 1}`;
  $("trial-count").textContent = `${currentTrialIndex + 1} of ${CONFIG.trialsPerParticipant}`;
  $("image-type-label").textContent = `Image type: ${trial.image_type}`;
  $("next-button").textContent = currentTrialIndex === CONFIG.trialsPerParticipant - 1
    ? "Submit survey" : "Next";

  clearAnswers();
  $("response-form").classList.add("hidden");
  $("image-frame").classList.remove("hidden");
  $("trial-image").classList.add("hidden");
  $("image-placeholder").classList.add("hidden");

  const url = getImageUrl(trial.image_path);
  try {
    // Preload before exposure so network loading time is not counted.
    const loaded = await preloadImage(url);
    $("trial-image").src = loaded.src;
    if (isTimed) {
      // In timed trials, show only the image during the 1-second exposure.
      // Questions are revealed after the image has been removed.
      $("response-form").classList.add("hidden");
      $("image-frame").classList.remove("hidden");
      $("trial-image").classList.remove("hidden");
      $("image-type-label").classList.add("hidden");
      currentImageVisibleAt = performance.now();

      window.setTimeout(() => {
        // Hide only if the participant is still on this trial.
        if (currentTrialIndex >= CONFIG.normalTrials &&
            assignment[currentTrialIndex] === trial) {
          setImageVisible(false);
          $("image-frame").classList.add("hidden");
          $("response-form").classList.remove("hidden");
          trialStartedAt = performance.now();
        }
      }, CONFIG.timedExposureMs);
    } else {
      $("response-form").classList.remove("hidden");
      $("image-frame").classList.remove("hidden");
      $("trial-image").classList.remove("hidden");
      $("image-type-label").classList.add("hidden");
      trialStartedAt = performance.now();
    }
  } catch (error) {
    $("image-placeholder").textContent =
      "The image could not be loaded. Please contact the survey administrator.";
    $("image-placeholder").classList.remove("hidden");
    $("response-form").classList.remove("hidden");
    $("image-frame").classList.remove("hidden");
    $("image-type-label").classList.remove("hidden");
    // Do not allow an invalid/missing image to be answered.
    $("next-button").disabled = true;
    console.error(error);
  }
}

function showTrial() {
  showSection("trial");
  renderTrial();
}

function safeText(value) {
  return String(value ?? "").replace(/[\r\n\t]/g, " ").slice(0, 500);
}

async function submitAllResponses() {
  if (isSubmitting) return;
  isSubmitting = true;
  $("next-button").disabled = true;
  $("next-button").textContent = "Submitting...";

  const payload = {
    participant_id: participantId,
    submitted_at_client: new Date().toISOString(),
    responses,
    website: ""
  };

  try {
    // Apps Script ContentService does not provide a normal CORS response.
    // no-cors + text/plain avoids a browser preflight. The response is opaque,
    // so the page cannot prove server-side receipt; verify with a test row.
    await fetch(CONFIG.appsScriptUrl, {
      method: "POST",
      mode: "no-cors",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify(payload)
    });

    surveySubmitted = true;
    showSection("complete");
    $("completion-id").textContent = participantId;
    $("completion-message").textContent =
      "Your submission has been sent. Thank you for participating.";
  } catch (error) {
    isSubmitting = false;
    $("next-button").disabled = false;
    $("next-button").textContent = "Retry submission";
    alert("We could not send your responses. Check your connection and try again.");
    console.error(error);
  }
}

async function handleResponseSubmit(event) {
  event.preventDefault();

  const people = getRadioValue("people");
  const confidence = getRadioValue("confidence");
  if (people === "" || confidence === "") return;

  const trial = assignment[currentTrialIndex];
  const answerTime = trialStartedAt === null ? null : Math.round(performance.now() - trialStartedAt);

  responses.push({
    trial_number: trial.trial_number,
    stage: currentTrialIndex < CONFIG.normalTrials ? "normal" : "timed",
    scene_id: trial.scene_id,
    image_type: trial.image_type,
    image_path: trial.image_path,
    reported_people: Number(people),
    confidence: Number(confidence),
    exposure_ms: currentTrialIndex < CONFIG.normalTrials ? null : CONFIG.timedExposureMs,
    response_time_ms: answerTime
  });

  currentTrialIndex++;

  if (currentTrialIndex === CONFIG.normalTrials) {
    showSection("instructions-timed");
  } else if (currentTrialIndex < CONFIG.trialsPerParticipant) {
    showTrial();
  } else {
    await submitAllResponses();
  }
}

async function init() {
  participantId = createParticipantId();
  $("participant-label").textContent = `Participant ID: ${participantId}`;
  $("welcome-participant-id").textContent = participantId;

  try {
    const response = await fetch(CONFIG.manifestUrl, { cache: "no-store" });
    if (!response.ok) throw new Error("Could not load dataset.json.");
    const manifest = await response.json();
    const buckets = normalizeManifest(manifest);

    assignment = selectTrials(buckets, participantId);

    if (assignment.length !== CONFIG.trialsPerParticipant) {
      throw new Error("Participant assignment is not valid.");
    }

    $("begin-button").addEventListener("click", () => showSection("instructions-normal"));
    $("start-normal-button").addEventListener("click", showTrial);
    $("start-timed-button").addEventListener("click", showTrial);
    $("response-form").addEventListener("change", updateNextButton);
    $("response-form").addEventListener("submit", handleResponseSubmit);
    showSection("welcome");
  } catch (error) {
    $("fatal-message").textContent = error.message;
    showSection("fatal-error");
    console.error(error);
  }
}

init();
