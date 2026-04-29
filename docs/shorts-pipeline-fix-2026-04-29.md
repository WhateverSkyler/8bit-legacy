# Shorts Pipeline Fix — 2026-04-29 — Better Subject Centering + QA Preview

## Problem reported (2026-04-29 ~12:30 PM ET)

Tristan reported recurring centering issues on auto-posted shorts:
- Today's ~12:30 PM short had him **entirely off-centered** (he's the subject in front of the arcade machine)
- Other recent shorts have shown subject **slightly left-aligned**
- **Weird visible cuts** on some clips: when source camera angle swaps, the vertical-crop centering "takes a second to catch up" creating ugly transitions
- Zero QA gates — render → schedule → post pipeline runs unreviewed

## Root cause analysis

Per `scripts/podcast/render_clip.py` (lines 222–343), vertical cropping uses:
- OpenCV Haar **frontal-face** cascade only — fails on profile/angled poses, partial occlusion, backlight
- `FACE_MIN_SIZE = 90` — rejected faces smaller than 90px wide; the "Tristan in front of arcade" angle had him at ~70–110px
- When detection fails → hardcoded `CENTER_CROP_X = 656` (dead-center) — wrong if the subject isn't at the source-frame center
- No scene-to-scene continuity — each scene's crop independently calculated, abrupt cuts at scene boundaries
- No human review step before scheduling

## Fixes shipped this commit

### 1. Multi-cascade face detection (frontal + profile, both directions)

`_face_center_for_range()` now accepts a list of cascades and tries them in order per frame:
1. **Frontal** Haar cascade (existing behavior)
2. **Profile** Haar cascade on horizontally-flipped frame — catches LEFT-facing profiles (the most common podcast pose where the subject looks at their guests)
3. **Profile** Haar cascade on the original frame — catches RIGHT-facing profiles

The flipped-search trick is necessary because OpenCV's `haarcascade_profileface.xml` only detects right-facing profiles. Mirroring the search image (and mirroring the result X back) lets the same XML detect left-facing profiles without any new model file.

Both cascades ship with stock OpenCV (`cv2.data.haarcascades`). No model deployment to the NAS container required.

### 2. Lowered detection thresholds

- `FACE_MIN_SIZE`: 90 → **60** — catches Tristan's distance-from-camera pose
- `FACE_SAMPLES_PER_SCENE`: 3 → **5** — better recall on scenes with brief angled poses
- `scaleFactor`: 1.2 → **1.1** in detectMultiScale — denser pyramid for smaller faces
- `minNeighbors`: 5 → **4** — slightly more permissive, still rejects noise

### 3. Scene continuity fallback

When a scene's face detection fails, instead of snapping to dead-center (`CENTER_CROP_X = 656`), the code now uses:
1. The most recent successful crop_x from a prior scene in this clip (preserves continuity across detection misses)
2. Falls back to `CENTER_CROP_X` only if NO scene in the clip has succeeded yet

Plus **leading-scene backfill**: if scenes 0+1 missed but scene 2 hit, scenes 0+1 get retroactively assigned scene 2's crop_x. Eliminates the "first 3 seconds dead-center, then snap" pattern.

### 4. QA preview generation (2x2 contact sheet)

After every successful render, `_generate_preview()` extracts 4 still frames at 25/50/75/95% of the clip and tiles them into a 1080×1920 contact sheet at:

```
data/podcast/clips/<episode>/preview/<clip_id>.jpg
```

Each tile shows:
- The 9:16 framing as it will appear to viewers
- An annotation strip with `t=Xs cx=Y` (timestamp + scene's crop_x in source coords)

This is a **visual QA artifact**, not a hard gate. The pipeline still auto-publishes via Zernio. But Tristan can browse `preview/` before scheduled posts go live and pull anything that looks bad. Fast next iteration: add a pre-publish check that requires a `preview/<clip_id>.approved` flag file (defer until preview proves useful).

Failure to generate the preview is **non-fatal** — the primary render succeeds regardless.

## What's NOT in this commit (deferred)

These are higher-effort changes that need testing on real footage before deployment:

- **DNN-based face detection** (OpenCV's `FaceDetectorYN` or ResNet-SSD). Significantly better than Haar for profiles, angles, occlusion. Needs the model file (~10 MB) deployed to the NAS container. Plan: pilot in next session, gate behind `--use-dnn` flag.
- **Person/body detection fallback** when no face found. OpenCV's HOG person detector is built-in; YOLOv5/8 is more accurate but requires model deployment. Useful for the arcade angle where Tristan's body is fully visible even when his face is at an awkward angle.
- **Temporal smoothing across scene transitions** — interpolate crop_x over a 0.3s ramp at scene boundaries. Requires ffmpeg's expression-based crop (`crop=W:H:'expr':0`) which is more complex to assemble. Plan: pilot after DNN detector is in.
- **Hard QA gate** — block posts until preview is reviewed. Plan: add `--require-approval` flag that creates `pending/<clip_id>` directory; `schedule_shorts.py` only picks up clips moved to `approved/`.

## Deployment to production

The pipeline runs in a container on TrueNAS (192.168.4.2) at `/mnt/pool/apps/podcast-pipeline/` (or similar). To deploy these changes:

```bash
# From the macbook (after pulling this commit):
ssh truenas "docker cp /tmp/render_clip.py podcast-pipeline:/app/scripts/podcast/render_clip.py"
# Or whatever the container/path actually is — see reference_truenas_access.md
```

OR more reliably, since the repo is git-synced via Syncthing:
1. Commit + push from macbook → GitHub
2. SSH into the container's host
3. `git pull` inside the container (if the container's repo is bind-mounted from a git checkout)

**Action item:** Tristan should verify the deployment path and update `docs/podcast-automation-runbook.md` if the deployment process is undocumented.

## Test plan before deploying

Before pushing this to the production NAS container, render ONE existing clip locally with the new code:

```bash
# Pick a clip from the existing queue (preferably one that previously had centering issues):
python3 scripts/podcast/render_clip.py \
    --clip-id <some-id-from-_all.json> \
    --episode "Episode April 14th 2026"
```

Then visually inspect:
- The output `data/podcast/clips/<episode>/<clip_id>.mp4` — subject should be properly centered
- The preview `data/podcast/clips/<episode>/preview/<clip_id>.jpg` — should show 4 framed frames

Iterate on parameters if the test render is still bad. Only deploy to NAS once a local test passes visual QA.

## Files changed

- `scripts/podcast/render_clip.py` — face detection + preview generation
- `docs/shorts-pipeline-fix-2026-04-29.md` — this doc
