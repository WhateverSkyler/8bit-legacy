# Podcast Shoot Day Checklist

Master checklist used every podcast recording day. Add new items here as they come up.

## Pre-shoot prep

- [ ] FL Studio recording template open, all 3 mic tracks armed
- [ ] All 3 cameras charged + memory cards cleared
- [ ] Lighting set, no backlight issues on subject (especially the arcade-machine angle — known to cause vertical-crop centering misses)
- [ ] Topic outline prepped (see latest in `docs/podcast-content-pipeline.md`)
- [ ] Backdrops + props in position

## Recording (in order)

- [ ] Intro / cold open
- [ ] Main topic discussion (natural conversation — don't worry about segmenting; AI editing handles cuts)
- [ ] **Self-sponsorship segment** — 45–90s standalone clip describing 8-Bit Legacy (the script lives in `docs/podcast-content-pipeline.md` under "Self-Sponsorship Section"). Re-record occasionally for freshness; save standalone so it can be inserted into multiple episodes. Pair with animated graphic in post (logo + 8bitlegacy.com URL + product montage). Placement: ~30 min into full episodes, ~5 min into topic-cut videos.
- [ ] Outro / call to action
- [ ] B-roll of arcade / store / setup if needed

## Post-shoot (same day)

- [ ] Offload all camera + audio files to NAS `/mnt/pool/NAS/Media/8-Bit Legacy/podcast/raw/<episode>/`
- [ ] Drop final assembled `full.mp4` (with self-sponsorship segment edited in) into `/mnt/pool/NAS/Media/8-Bit Legacy/podcast/incoming/<episode>/` to trigger the auto-pipeline
- [ ] Verify drop_watcher detected the drop and pipeline started (check container logs)

## Post-shoot (within 48h)

- [ ] Spot-check first 2–3 generated shorts in `data/podcast/clips/<episode>/preview/<clip_id>.jpg` (QA contact sheet — added 2026-04-29) for centering quality before they auto-post
- [ ] If any clip looks bad, manually re-render with `--crop-x <px>` override or remove from the schedule queue
- [ ] Verify the self-sponsorship segment landed where intended in the YouTube full-episode upload
- [ ] Update `docs/podcast-content-pipeline.md` if format/script for self-sponsorship evolved this shoot
