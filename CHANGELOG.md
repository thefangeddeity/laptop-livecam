# Changelog

Newest first. Entries for 7.0.2 through 7.0.11 were reconstructed from the
release tags on 2026-10-20, having been skipped as they shipped; the older
5.x/2.x section below is not consistently ordered and has been left as it was.

## 7.0.45

- First published Windows installer. The `windows` branch could not compile
  at all: a commit stripping the Linux tree took with it the ten files
  `assets.rs` and `cv.rs` embed at build time, which they reach into `pkg/`
  for on purpose.
- The Windows mic watchdog no longer disables and re-enables the audio
  controller. It power-cycled a device node unattended, roughly every 75
  seconds for as long as it judged the mic silent, and could not tell a
  faulty device from a muted one. It now reports, and logs the exact
  commands for a human to run deliberately.
- `/api/audio/restart` and a viewer control to go with it, so the operator
  has the safe half of that remedy: the server reopens its own capture
  without touching any driver.
- Every node now configures and repairs its own HTTPS through
  `tailscale serve`. Browsers grant getUserMedia() only in a secure
  context, so a dropped serve config killed two-way audio while the viewer
  went on looking healthy. Nodes repair themselves rather than warning,
  because a warning only helps someone who knows what to type.
- ariana's serve config went from four path mappings to one. Two were
  dead: `/audio` pointed at a port with nothing on it, and `/hls`
  duplicated a proxy broadcast-api already had.

## 7.0.44

- Night mode removed entirely — key, mode, capture branch, v4l2 control
  switching and its image processing. The blur filter does more for a dark
  room than its tone curve ever did.
- The detector model is installed by both packages instead of being a file
  someone placed by hand. It is fetched from the `models-v1` release and
  checksummed.
- First published macOS installer. The DMG build had been failing since
  Oct 5 on a stale check for a renamed element.
- Viewer repaired: removing the Reset button took a `<script>` tag with it
  and the page printed its own source as text.
- `scripts/check-viewer.py` now runs in every render path — structure,
  JavaScript syntax, placeholders.

## 7.0.43

- The AV bank became a strip under the picture, as wide as the picture.
- The gallery can be browsed: arrows page through a name's pictures, and
  Delete stays open and advances.
- Everything is Laptop LiveCam / LLC. tina's masthead said HLS LightCV, and
  every node's Source link pointed at a repository that no longer exists.
- Logs went from 7.3 lines a second to zero in steady state.
- A refresh no longer forces the picture to Hide.

## 7.0.42

- Tab titles unified: `Tina | LLC 7.0.42 (ubuntu)`.
- Gallery preview with Name / Close / Delete, and single-picture delete.
- The CV key follows the CPU class, as it was always documented to — the
  rule existed and nothing called it, so a remembered timing verdict had
  tanzania marked unfit with no way to earn its way back.
- `/cams/` had been serving a five-month-old page on Debian.

## 7.0.41

- BUZZ makes a sound on the camera machine, not only in viewers' browsers.
  Alternating 1400/2100 Hz, chosen by playing candidates through a laptop
  speaker and recording the result.

## 7.0.40

- The Arch setup script needed the sudoers rule too. 7.0.39 added it to the
  Debian script only, so Arch shipped without the rule the Repair feed
  button depends on.

## 7.0.39

- The privacy mask's "Pixelate instead" renders the block-art cloak rather
  than a mosaic, so what it hides stays hidden.
- Repair feed restarts the camera server instead of just the player, and
  `/api/reset` was silently failing for want of a sudoers rule.

## 7.0.38

- **"Stretch to fill" flipped between stretched and not, once a second.**
  `videoRect()` measured `video.getBoundingClientRect()`, and `applyFitRoi`
  writes a transform onto that same element -- and `getBoundingClientRect()`
  returns the *transformed* rect. Each tick measured an already-scaled box and
  computed a fresh scale from it: 2.00, 1.00, 2.00. `paintAll` runs on the 1s
  poll, hence the once-a-second alternation. It now measures the **wrap**,
  which is never transformed and is the video's untransformed box anyway
  (`width/height: 100%`, no padding or border). The transform write is
  idempotent too.
- **No alert when there is nothing to show.** With photos and video both
  switched off, alerts still arrived naming what was seen with no way to see
  it. Skipped entirely now -- but deliberately *not* the same as evidence
  being withheld by "Never film people", where the text still goes: off is a
  choice already made, withheld is one being made now, and a silent camera is
  indistinguishable from a broken one. The gallery still gets its crop.
- README documents the trap the mask creates for its own editing: masking
  happens at the camera, so you cannot see what you are about to include --
  re-drawing means switching "Hide the rest" off first. "Pixelate instead" is
  the exception, and that is also its trade.

## 7.0.37

- **The gallery listing degrades instead of 500ing.** `/api/gallery` guarded
  its `os.listdir` with `os.path.isdir` only, which covers "missing" and not
  "there but unreadable" -- a permissions problem on the unlabelled directory
  would have raised and taken the whole listing with it, including the named
  roster, which is readable and unrelated to the failure. The macOS side was
  already written with `try/except`; found by combing the lineages against
  each other rather than reading either alone.

## 7.0.36

- **"Never film people"** -- the honest name for the mechanism. "Detect
  non-human only" described a detection filter, and this control does not
  change detection at all: it withholds the *picture*. Alerts still say a
  person was seen; they carry nothing to look at. That is also what keeps it
  distinct from unticking People in *Alert me about*, which stops human
  alerts rather than human footage.

## 7.0.35

- **"Not while someone's home" promised a safety it never had.** The name
  assumed the someone was a *resident*. A thief is also a person and the
  mechanism cannot tell them apart -- it suppresses evidence for any human in
  view, which is exactly the person you would most want a picture of. Now
  **"Detect non-human only"**, which states what is actually being chosen:
  this camera watches the animals and does not film people, whoever they turn
  out to be. Lit means the restriction is on, matching every other lamp.
- The behaviour is deliberately unchanged. Renaming does not fix the intruder
  case and must not look like it does.

## 7.0.34

- **The gallery, phase one: collect and name, no machine learning.** One crop
  kept per visit so individuals can be named later -- and, first, so the
  question that decides whether recognition is possible at all gets a measured
  answer: how many pixels a cat actually occupies crossing this room. Every
  thumbnail carries its dimensions and every filename ends in `WxH`.
- Hooked in `_send`, on the worker thread, first and outside its `try`. Not
  `_close_expired`, which holds the notifier lock while `on_promotion` calls
  in at the detection rate -- a JPEG encode and disk write there would stall
  detection for every viewer. First, so a Telegram outage cannot also stop the
  record of what was seen.
- Its own directory and retention (`/var/lib/hls-livecam/gallery`): a named
  picture of a household member must not inherit the recording's six-hour
  lifetime by accident. Pruning bounds the **unsorted** pile only -- a named
  picture is something the operator chose to keep.
- Every id reaching these endpoints is a filename from a browser. `_gal_safe`
  checks twice: the name must look like a plain filename **and** the resolved
  path must still be inside the gallery. 13 assertions, including a symlink
  planted inside the gallery pointing out of it -- which the pattern passes
  and `realpath` catches.
- **Settings impact: one row.** "Forget everyone", destructive and confirmed.
  The roster is its own surface, hidden until there is something in it,
  because a collection in a settings panel is how settings panels die. No
  threshold or sensitivity is exposed: a confidence dial is uncalibratable and
  its failure mode is confident mislabelling.

## 7.0.33

- **The clip stopped waiting for a subject that had already left.** 7.0.22
  stamped `_track_seen` on every `on_promotion` call -- but that fires for
  every *promoted* track each cycle, not every *detected* one. A track stays
  promoted while its evidence decays (`*= 0.88` per miss from a peak of
  `confidence/(1-decay)`), which from a steady 0.86 detection is ~25 passes,
  or **about sixteen seconds** of coasting at `CV_DETECT_HZ` 1.5. Each of
  those counted as a fresh sighting, so the 20s post-roll was measured from
  sixteen seconds too late and the clip ran ~36s past the exit.
  `Track.last_seen` already held the right value -- set in `Tracker.update()`
  on a **match** only, from `det.timestamp`, which is `time.time()`, the same
  clock as `item['when']`. The tail is now exactly the configured post-roll.
  Falls back to `time.time()` if a tracker lacks the field, which restores the
  old behaviour: a longer clip, never a shorter one.
- **Lamp polarity is consistent.** Three of ten lamps meant the opposite of
  the other seven, so "lit" had to be read per row rather than learned.
  "Disable buzz" lit meant buzz was *dead*. Now **Buzz**, **Server speaker**
  and **Record while people are home** -- every lamp lit means the thing is
  on. Labels and lamps only; stored state and APIs untouched.
- **"Edit visible area"** was an imperative on a switch whose lamp confines
  the *detector* -- one label over two controls, describing neither. It is now
  a caption on the buttons it describes, and the lamp states what it does:
  *Detect only here* / *Detect everywhere* / *No area set*.
- **"Stretch to fill"** moved out a level and is marked *(your view)*. Nested
  beside "Pixelate instead" it told the reader that a personal display
  preference and a privacy control were the same kind of thing.
- "Mute server speaker/headset in RTC" -> **"Server speaker"**: it was the
  longest label in the panel and its only user-facing use of that acronym.

## 7.0.32

- **One version format across the fleet.** The header read
  `mac-v1.8.0 @ariana` on one lineage and `7.0.31 @tanzania` on the other --
  the same field in two formats, with the prefix repeating what the hostname
  beside it already said. It was not decoration: the lineages genuinely tag
  differently (`mac-v1.8.0`, `win-v1.0.0`, plain `7.0.31`) and only one fed
  this label a raw version, so the difference was the *tag* leaking into the
  UI rather than a decision.
  Stripping a platform prefix and a leading `v` normalises all three with no
  per-platform branch: `mac-v1.8.0` -> `1.8.0`, `win-v1.0.0` -> `1.0.0`,
  `7.0.31` unchanged. Removing rather than adding, because `@ariana` already
  identifies the member and the version string need not encode it twice.
  The full tag and build detail stay in the hover title.

## 7.0.31

- **A drop shadow on the visible-area box in dark mode.** Over static the box
  stopped reading as an edge: a 1px line and a phosphor glow both sit inside
  the noise's own frequency range, so the eye has nothing to separate them by.
  Foliage and a patterned rug do the same thing; static is just the worst
  case. A soft dark shadow is the one cue grain cannot imitate -- it is
  low-frequency and directional, so it survives a busy picture that defeats a
  hairline.
  Dark *grey*, not black: pure black against the dark housing reads as a hole
  cut into the picture, and this has to look like the box sits above it.
- Scoped with `html:not([data-theme="light"])` rather than as a new base
  rule. Every other themed rule in the sheet states *light* and lets dark be
  the default, so a bare `.roi-box.locked` would also apply to any third
  theme that ever arrives.
- The editing box is untouched -- it already casts `0 0 12px` black alongside
  its spotlight, which does the same job.

## 7.0.30

- **"Stretch visible area for display".** With the mask on, the kept area sits
  small inside a field of black. This scales it up to fill the player, which
  is the point of setting a small region in the first place.
  It is a CSS transform on the `<video>` element and nothing else: what is
  captured, published, recorded and sent to Telegram is byte-for-byte
  unchanged, so it cannot widen what anyone can see -- only how much of the
  player the already-visible part uses. Hence per-viewer, in `localStorage`,
  rather than node state: two people watching the same camera can disagree
  about this, and `feed_mode` already shows what shared display state costs.
- Three conditions, each for a reason: with the **mask off** or **no region**
  the whole frame is already the visible area, and **while editing** it drops
  back to the full picture, because you cannot redraw a region you cannot see.
  The region outline hides while stretched -- filling the player, it would
  trace the edge of the view.
- The region's origin is measured from the *wrap*, not the video element: the
  picture is letterboxed inside the element by `object-fit: contain`, so
  `videoRect()` is the only honest origin. Fit, not fill -- `min()` of the two
  scale factors, so a wide strip keeps its aspect instead of being cropped a
  second time by the player's shape.
- Wired into `paintAll`, not just `paintRoi`: `paintAll` does not call
  `paintRoi`, so otherwise the stretch would have engaged only when the
  *region* was touched and not when the *mask* was toggled.

## 7.0.29

- **The settings say what they now do.** "Where to watch" named one of the
  three controls under it; the rectangle is shared and what differs is the
  question asked of it -- the detector's scope (`_read_detect_roi()`), what
  viewers and recordings may see (`_read_detect_roi_raw()`, which ignores the
  first), and how the rest is hidden. The group is **"What the camera sees"**,
  and since two of the three work with Detection switched off entirely, the
  heading is no longer `.detdep`; only the detector's own row dims with it.
- **"Black out the rest" became false the moment pixelation shipped** -- with
  pixel selected the label described the one thing it was not doing. Now
  "Hide the rest", with the style row beneath saying which.
- "Detection area" named the rectangle back when it had one user. The row is
  the detector's use of it, so it reads **"Detect only here"**, and its off
  state is **"Detect everywhere"** -- off never meant the detector stops, only
  that it stops being narrowed.
- **Three writers stopped swallowing.** `_write_detect_always`,
  `_write_notify_shots` and `_write_notify_video` each ended in
  `except Exception: pass` -- precisely how `notify_shots` went three releases
  persisting nothing while the panel showed the lamp move. 7.0.14 fixed the
  root-owned directory; the shape that hid it survived, and the next full disk
  would be just as quiet. They raise now and their endpoints return 500.
  macOS had the same bug in `_write_detect_always`.
- **The switch gets a round knob.** `.reset`'s pin is a 20x9 capsule in a
  30x16 track -- nearly as wide as its housing, so sliding it read as the
  whole face shifting rather than a knob travelling. 12px round, the height of
  the track, +/-7px of travel in 28px of interior. The push buttons keep the
  capsule; they do not travel.

## 7.0.28

- **The light switch is visible in the mobile header again.**
  `header .status-bar` was `display: none` below 720px, so moving the theme
  switch into the header hid it on phones. The rule predates the switch and
  its reasoning was sound for what it covered: brand, version strip and LIVE
  pill do not fit in ~390px, and the pill was the only one of the three with
  duplicates already above the fold -- the VIDEO tube's LIVE segment and the
  HLS lamp. That does not extend to the switch, which has no duplicate
  anywhere since it left Settings, so the container rule removed the only
  theme control on mobile entirely.
  The **pill** is hidden now instead of the bar around it: identical outcome
  for the pill, and the original rule's careful point still holds --
  `textContent` is readable and writable while hidden, so `paintLamps()` and
  `setStatus()` go on driving the tube's LIVE segment and the HLS lamp.
- The switch keeps its place and drops its word on mobile. ~390px is still
  ~390px, and the label is exactly what would push the product name onto two
  lines again.

## 7.0.27

- **Pixelate instead of black**, as a setting under the mask. Black stays the
  default, and the control states that these are not the same privacy rather
  than offering them as taste: a mosaic keeps coarse structure -- how many
  people, roughly where, exactly when they move -- and block size is a
  judgement about how much of that is acceptable, not a guarantee. What it
  buys is that a pixelated room still reads as a *room*, where a black one
  reads as a broken camera.
- **Failure goes to black, never to the picture.** On Linux this reuses
  `_apply_blur`, which fails *open* by design -- it returns the frame
  untouched and logs, because its usual caller is a viewer who asked for blur
  and would rather see the room than nothing. That is exactly wrong for a
  mask, so the same object coming back is treated as "it did nothing" and the
  mask falls through to black.
- macOS has no standalone blur: its mosaic lives inside `CVProcessor` and
  works on the render, not the raw frame the mask operates on. That side
  carries its own -- area-average down, nearest-neighbour up -- with `cv2`
  imported at module load rather than lazily, so a node that cannot pixelate
  falls back to black from the first frame instead of raising inside the
  capture thread.
- Fail-closed is unchanged and still black regardless of style: an
  unparseable region is not the moment to pick the weaker option.

## 7.0.26

- **Masked is the default.** An absent state file now means masked: a region
  somebody drew is private until they say otherwise, and only the literal
  `'false'` turns it off. The toggle is how you *unmask*.
  Flipping the default moved the dangerous case. Previously "on" implied a
  region existed, because the endpoint refused to switch on without one. With
  on as the default, a node that never had a region would hit the fail-closed
  path and black its own camera -- a privacy default becoming a fleet-wide
  outage. So the two failures are now distinguished: **no region file at all**
  passes the frame through (the state of every node before anyone draws a
  box, and not a failure), while a region file that **exists and will not
  parse** still blacks. The 409 that refused to switch on without a region is
  gone with it -- it would have blocked the default state itself.
- **The privacy mask on macOS.** Not a copied patch: that lineage branches
  elsewhere. `_cv_pump` reads a frame and derives all three consumers from it
  -- `_to_rec`, a numpy view for `proc.observe()`, and `dst.write(raw)` --
  so one call after the read covers all of them, including the `pending`
  path. `_drain_loop`'s shared cache is masked too. `_read_detect_roi_raw`
  was lifted above both, the same ordering hazard 7.0.25 fixed on the other
  side.
- **The Reload buttons are un-deformed.** The theme switch had been built by
  restyling `.reset` itself -- and `.reset` is a *push* button with three
  other users: both Reload buttons and the notch menu, all of which got their
  pin shifted 4px off centre. `.reset` is untouched again; the switch is
  `.reset.tog`, carried only by the theme button. Sharing a housing is not a
  reason to share a rule.

## 7.0.25

- `_privacy_mask_box` called `_read_detect_roi_raw`, defined 1100 lines below
  it. Name resolution happens at call time so this works once the module has
  loaded, but the drain thread starts before the module finishes executing --
  so with the mask on at boot the first frames would raise `NameError`, be
  caught, and fail closed to black. Fail-closed is the right outcome and the
  window is brief, so nothing visible broke; it was an accident rather than a
  decision, and it is the same hazard 7.0.24 fixed for `_apply_privacy_mask`
  and missed for its dependency. The reader now sits above both.
- Verified the mask end to end: bright content in a completed evidence
  segment is bounded by x 0.05..0.40, y 0.05..0.40 for a region of exactly
  that, with 12.2% of pixels non-black against an expected 12.25%. The
  recorder leg inherits the mask, which was the point of applying it at the
  single write to `_cam_frame`.

## 7.0.24

- **The privacy mask.** Everything outside the detection region is blacked out
  at the camera. Applied in `_drain_loop`, on the single write to
  `_cam_frame` -- the branch point that the display pipeline, the detector's
  own tap and the evidence recorder all read from. The recorder is explicitly
  fed the raw frame *before* the render branch, so masking anywhere downstream
  would leave every clip and snapshot carrying the room while the switch read
  "on". One insertion point; all three consumers inherit it by construction.
  A CSS overlay would have been easier and worthless: the HLS stream still
  carries the full picture to anyone with the `.m3u8`.
- It reuses the detection region's geometry rather than storing a second
  rectangle -- one region with a mode, since two would rot out of step. It
  reads the raw geometry, so the mask still applies when the region is
  switched off for *detection*.
- **It fails closed, deliberately against the house rule.** Every other reader
  of this geometry widens on failure, so a corrupt file cannot silently narrow
  what is watched. A privacy mask is the inverse: an unparseable or missing
  region with the mask on yields a black frame, not a clear one. The lookup is
  wrapped too, because an exception escaping it would reach `_drain_loop`'s
  only handler, which sleeps a second -- a camera stall for every viewer.
- Defined above `_drain_loop` rather than with the other state readers: the
  drain thread starts before the module finishes executing, so a frame
  arriving during import would have raised `NameError` into that same handler.
- Switching it on with no region is refused with 409 rather than blacking the
  whole picture, which is indistinguishable from a broken camera.
- Cost: ~2ms/frame at 1280x720 (~3% of the 15fps budget), and nothing at all
  when off.

## 7.0.23

- **The region line is bright in both themes.** It used `var(--phos)`, which
  is `#3fe8cd` in dark theme and `#1d332e` in light -- because `--phos` is the
  colour of *text on a near-white housing*. The region line is not on the
  housing; it is drawn over video, and video is dark in both themes. Against
  the powered-down screen it was sitting on, light theme measured **1.20:1**
  before the 0.62 locked opacity was applied on top, while dark theme measured
  12.59:1. Same rule, usable in one theme and invisible in the other.
  `--roi-line` is now pinned to the bright phosphor and deliberately *not*
  overridden per theme: 10.4:1 on the light theme's off-screen, 12.6:1 on the
  dark one. The 1px black outline already underneath carries it against a
  bright scene.
- Locked opacity .62 -> .85, plus a faint glow. Locked should be dimmer than
  editing, not dim in absolute terms.

## 7.0.22

- **The alert clip follows the subject instead of a stopwatch.** It was a
  fixed window -- 5s before the detection instant, 20s after it, 25 seconds
  regardless of what happened in them -- so a cat still in frame was cut off
  mid-visit. The end now follows the last sighting of that track:
  `_track_seen[track_id]` is stamped every cycle the track is still promoted,
  and the clip is cut once it has been gone for a whole post-roll.
  The stamp goes *before* the early returns in `on_promotion`: cooldown and
  already-notified are exactly the paths a subject that stays takes, so
  stamping below them would record one sighting and never update.
- `NOTIFY_CLIP_MAX` (default 120s) caps it. A subject that settles in and
  sleeps must not produce an unbounded file on a disk already holding six
  hours of rolling recording.
- A clip can only ever get *longer*: `post` is floored at `clip_post`, so a
  subject that leaves immediately still produces exactly the old window.

## 7.0.21

- **The detection region draws over the static.** It sat at `z-index: 6`,
  under `.switch-overlay` (20), `.crt-stage` (22) and `.hide-overlay` (15), so
  the snow painted straight over it. A region that disappears whenever the
  picture does reads as having stopped applying -- it has not; the detector is
  still watching that rectangle. Now 24, the same call already made for the
  HUD at 25 and recorded there as *"HUD should draw over static too"*. The
  region is the same kind of thing: an overlay describing what the machine is
  *doing*, not part of the picture it is showing. Under the scanlines it would
  read as footage of a box rather than a statement about the camera.
  24 rather than 25 so the HUD wins the overlap -- the box is a large shape,
  the HUD is a few lines of text, and the text is what would be lost.

## 7.0.20

- **The cursor now says which gesture a press would start.** The handles
  worked; nothing on screen said so. A handle you can see but cannot feel is
  worse than no handle -- you aim at the dot, and a press landing outside the
  window silently gives you a *new* box, which snaps back on release and reads
  as the handle refusing to be grabbed. Corners show `nwse-resize` /
  `nesw-resize`, edges `ns-resize` / `ew-resize`, inside the box `grab`
  (becoming `grabbing` for the duration of the drag), outside `cell`. The
  cursor is held for the whole drag, including when the pointer leaves the
  box, so a resize does not flicker back the moment you cross an edge.
- **The draw cursor is no longer `crosshair`.** A thin plus hovering over a
  live camera feed is the Windows snipping-tool cursor and reads as "you are
  about to take a screenshot" -- the wrong promise on a page whose subject is
  a camera. `cell` is the spreadsheet range-selection cursor: heavier hollow
  plus, same meaning, no collision.
- The 9px grab window is unchanged. It was briefly widened to 14 on the
  assumption that handles were hard to hit; they are not, and widening it
  would have made drawing a new box near an existing edge harder.

## 7.0.19

- **The detection box had one gesture, and it was the destructive one.**
  `begin()` unconditionally started a new rubber-band wherever you pressed, so
  touching the box you had just drawn threw it away. A clean tap hit the 5%
  minimum-size guard and restored the previous outline, which is why it read
  as *"it resets"*. Now three gestures: **inside** moves it with the shape
  preserved (a move that reaches the frame stops rather than squashing),
  **on a handle** resizes -- corners both axes, edges one, floor at 5% -- and
  **outside** draws a new one, the only gesture that destroys. Eight handles,
  9px visual so they do not cover the picture, 22px grab radius on a coarse
  pointer because a 9px dot is not thumb-reachable. 18 assertions over the
  zone table and the clamping.
  Libraries were surveyed (Croppr.js, Cropper.js v2, crop-select-js); they all
  crop an `<img>`, and the cropping engine is the part we must *not* have,
  since cropping happens server-side in numpy and ffmpeg. Took the pattern,
  not the package.
- **Light theme is not a setting; it is a dimmer.** Promoted to the header in
  the same `.reset` + `.rstlab` shape as Notch filters. The rule: the header
  carries controls that respond to the *environment* (light, sound), Settings
  carries *configuration*.
- `.reset` had no pressed state -- its only user was `#combToggle`, a menu
  control reporting through `aria-expanded`. A global on/off switch must show
  its position, so the pin slides and lights; the menu toggle keeps the old
  centred, unlit pin.
- **The version label was the other lineage's.** tanzania served
  `mac-v1.8.0 @tanzania` while running 7.0.18: a rendered macOS `index.html`
  had been copied into this tree and carried `var build = 'mac-v1.8.0'`, its
  explanatory comment, and a `title` of `mac-v1.8.0-129-ga573e72-dirty`.
  `/api/info` reported `version=7.0.18` correctly the whole time; the viewer
  never asked. It asks now, and shows nothing rather than a stale value if the
  call fails.

## 7.0.18

- **The panel edge was still invisible on mobile, and the two previous
  releases had barely moved it.** `.panel` used `var(--border-soft)` -- the
  one of the three raised least in 7.0.16 -- and `--border-soft` has exactly
  one consumer in the whole stylesheet: that rule. It was raised
  conservatively because of its name, without checking that its only user is
  the most visible element on the page.
  It is worse on mobile than on desktop. At `<=720px` the sidebar gives up
  its own border, shadow and radius, so the panel stops being a box inside a
  frame and becomes the only structure there is, sitting on the *page*
  background rather than on the sidebar. Against that background the edge went
  1.08:1 -> 1.40:1 across 7.0.16 and 7.0.17, which is not a perceptible
  change. `.panel` now takes `--border` (1.98:1 there), and at mobile width
  `--border-strong` (2.47:1) with a heavier shadow, since a phone is read in
  more light than a desktop and the contact shadow washes out first.
- **Focusing the message field zoomed the whole page on iOS.** Safari zooms
  when a focused input's `font-size` is under 16px and does not zoom back on
  blur, so the layout stayed scaled until pinched out by hand. Every text
  field was 11px: `.ele-in`, `.msg2` and the six `.setnum` inputs. All go to
  16px at `<=720px` -- a threshold, not a preference -- and `.setnum` widens
  70px -> 88px so the larger text still fits.

## 7.0.17

- **Light theme edges get depth, not just a darker line.** 7.0.16 darkened
  the border colours, which helped, but a light-theme edge reads as a
  *bevel* -- lit along the top, shadowed underneath -- and the shadow half
  was missing. `.panel` carried `0 1px 2px rgba(88,110,117,.14)` against dark
  theme's `0 1px 2px rgba(0,0,0,.40)`: about a third the weight, on the
  largest surface in the UI, and 0.14 at 2px is ambient only. The white inset
  highlight was already at .85, so panels were lit along the top with nothing
  underneath -- they floated, and the flat border was left carrying the whole
  edge. Every other light-theme component sits at .18-.28; the panel was the
  outlier. Now four layers: the top catching the light, the inside of the far
  wall, a tight contact shadow saying where the panel meets the page, and a
  soft ambient one lifting it.
- Buttons were second-weakest at .16, and hardcoded `border-color: #dbd9cf`
  (1.37:1) -- another faint literal the variables never reached. Now
  `#b4b2a5`, 2.06:1.
- `.pdiv` is an engraved groove: a dark line with a lit edge beneath it. The
  highlight was there and correct; the line it was meant to sit under was
  `#e4e2d8` at 1.25:1, so there was no groove to catch it. Now `#cfcdc0`,
  1.54:1.

## 7.0.16

- **Light theme borders were barely visible.** `--border` sat at 1.35:1
  against the `#fcfbf7` panel and `--border-soft` at 1.30:1. Dark theme is
  numerically no higher (1.45:1), so matching it would have changed nothing --
  dark-on-dark edges read better and have highlights doing the work. Raised on
  their own terms: `--border-soft` 1.30 -> 1.69:1, `--border` 1.35 -> 2.39:1,
  `--border-strong` 1.61 -> 2.98:1, which lands on WCAG 1.4.11's 3:1 for UI
  component boundaries with the other two stepped below it. All three keep the
  palette's warm neutral cast and were checked against the page background and
  the housing they also border, not only the panel.
- Four rules hardcoded the old values instead of the variables -- `.talk`,
  `.box` and two slider thumbs -- and were lifted to match, or they would have
  kept the faint borders the variables just left behind.
- `#dcdad0` is also a pressed-button background gradient in two places, so
  only the border declarations changed. A global replace of the old value
  would have quietly restyled every pressed control.
- **The locked detection box dimmed twice**: a 55% `color-mix` nested inside
  `opacity: .55`, about 30% in the end, and worst against a bright picture.
  One mechanism now, at 0.62 -- which also retires the `color-mix`
  `@supports` fallback added for older iOS Safari.

## 7.0.15

- **The detection region stays drawn on the picture.** It used to vanish the
  moment you pressed Set, so the only way to see what was being watched was
  to press Edit again -- which is also the one action that puts the region at
  risk of being changed. Bright while editing, dim once locked: the editing
  box is something you are working on and should dominate; the locked one has
  to sit under a live picture for hours without pulling the eye.
- The locked box marks rather than masks. The editing treatment dims the whole
  frame and casts a spotlight shadow around the box, which is right for
  choosing an area and would be wrong left on -- it would darken the live view
  for as long as a region existed. The layer also drops `pointer-events` when
  locked, or a region would swallow every click on the video.
- A region that is set but switched OFF draws nothing, because detection is
  using the whole frame at that point and a box would misreport it.

## 7.0.14

- **The state directory was never writable by the service.** It arrived as
  `root:root 755` from whichever process created it first, while the service
  runs as `http` (Arch) / `www-data` (Debian). The effect was specific and
  misleading: a state file that already existed could be written, but a NEW
  one could not be created. So every switch added since the directory
  appeared failed on first use and only on first use -- `detect_roi` in
  7.0.11, `notify_presence_pause` in 7.0.13 -- and each looked like a bug in
  the feature that happened to be new. Now `install -d -g <service> -m 2775`
  in both packaging scripts, setgid so new files inherit the group rather
  than depending on the umask of whoever wrote first, plus a one-time
  handover of the files that predate the rule.
  7.0.13's switch returned a 500 here rather than appearing to work, which is
  the only reason this was found rather than shipped.
- **The Arch install script still patched pyfakewebcam's source**, in both
  `post_install` and `post_upgrade`. 7.0.12 removed the Debian copy of this
  and missed these two. On Arch it was the worse of the two: it rewrote a
  file that the `python-pyfakewebcam` package owns, so `pacman -Qkk` would
  report that package as modified and the next upgrade of it would silently
  revert the edit. It was also a no-op -- upstream has used `tobytes()` since
  before this package declared the dependency.

## 7.0.13

- **Class toggles never reached the detector.** `cv_notify` set its alerting
  classes once, at construction, from `NOTIFY_CLASSES` in `device.env`. The
  viewer's toggles wrote `/var/lib/hls-livecam/notify_classes`, and nothing
  read it -- `NOTIFY_CLASSES_FILE` was declared in `device.env` and had no
  reader anywhere in the tree. tanzania was alerting on `['cat','dog','human']`
  while its panel showed cat alone, so unticking People did nothing and had
  never done anything. The classes are now read per event, the same shape as
  the photos and video switches beside them.
  `broadcast-api` stores the list already expanded, so there is no second copy
  of the `living`/`other` expansion table to drift from the first -- the trap
  `canonical_ms` sits in across three files. A list written by an older build
  is normalized once at startup, because a node whose operator had chosen
  "All animate beings" stored the single token `living`, which matches no
  track and would now alert on nothing.
- **Don't record while somebody is home.** A switch under "What alerts carry":
  while a person is in view, alerts still arrive but carry no photo and no
  clip, and say why. The camera keeps watching and the text still tells you a
  cat came in -- it just stops producing footage of the people who live here.
  Presence is read from the detector whether or not People is an alerting
  class, because not wanting to be *told* about yourself is the normal setup
  and is a different question from not wanting to be *recorded*. A manual
  snapshot is exempt: the operator is standing at the panel asking for that
  picture. The hold after the last sighting is `NOTIFY_PRESENCE_HOLD_SEC`
  (default 60s), not a literal -- without it, a person stepping out of frame
  for a moment restarts the recording.
- **The settings panel is grouped rather than alphabetized.** Alphabetical
  order was asked for when this was a short flat list; at seventeen controls
  it put "Detection area" between "Dogs" and "Include photos". Five groups
  now: Alert me about, Where to watch, What alerts carry, This device, Audio
  filters. "Detection area" was inside the *alert trigger* group despite being
  a detection scope, and the photos/video switches sat in the same
  undifferentiated run as the triggers; both were lifted out. They still dim
  with Detection, which they had been getting for free by sitting inside
  `.alertgrp` -- now explicit, as `.detdep`.
- A `<div class="pdiv"></div>` and the `<div class="pinrow">` after it shared
  one line, which is part of how that run read as a single blob.
- `_write_presence_pause` raises instead of swallowing, so a failed write is a
  500 rather than a lamp that changes and persists nothing -- the exact shape
  of the `notify_shots` bug found in 7.0.11.

## 7.0.12

- The Debian package stops installing software at install time. `postinst`
  used to `pip install pyfakewebcam` as root, with `--break-system-packages`
  and a trailing `|| true`, then rewrite the installed library source in
  place to swap numpy's removed `tostring()` for `tobytes()`. It needed the
  network to finish a package install, hid its own failure so a broken
  install still reported success, wrote into
  `/usr/local/lib/python3*/dist-packages` where no package manager would ever
  clean it up, and the patch had become a no-op because upstream already
  uses `tobytes()`. pyfakewebcam is now vendored in the payload under
  `/usr/share/hls-livecam-server/vendor`, byte-identical to the Arch
  `python-pyfakewebcam 0.1.0-1` copy that drives tanzania's camera.
  `broadcast-api` prefers a distro-packaged pyfakewebcam and falls back to
  the vendored one, so Arch behaviour is unchanged and only Debian moves.
  Arch was never affected: its PKGBUILD always declared the dependency.
- The import had to move. `import pyfakewebcam` sat one line *above* the
  `sys.path` insert it would need to find a vendored copy.
- README's install instructions were three versions and one package rename
  out of date: they named `hls-livecam-server_2.7.3_amd64.deb` for a package
  now called `laptop-livecam`, and the accompanying `apt install` line was
  missing four hard dependencies (`python3-flask`, `python3-pil`,
  `python3-numpy`, `python3-opencv`), so following them produced a package
  that could not start. Now documents both the Debian and Arch routes, and
  uses `apt install ./<file>.deb` rather than `dpkg -i`, which does not
  resolve `Depends` at all.
- `hosts/tina/MANIFEST.md` claimed tina ran the 6.0.7 .deb; it runs 7.0.11.
- 7.0.6 shipped as a commit but was never tagged, so the version named no
  findable tree. Tagged retroactively at the commit that declares it.

## 7.0.11

- A detection region: crop the camera so motion is only detected inside a
  chosen rectangle, with snapshots and clips cropped to match. Edit/Set
  buttons on the viewer panel, a separate toggle to apply or lift it, and a
  reset. Fractions are taken against the picture rectangle rather than the
  video element, which is letterboxed by `object-fit: contain`.
- Two silent failures surfaced while porting it to Linux: `/var/lib/hls-livecam`
  was root-owned so the service could not write the region file, which also
  revealed that `notify_shots` had not persisted since 7.0.10 because its
  writer swallowed exceptions; and the Linux `broadcast-api` imports
  `json as _json`, so a ported block using the bare name raised NameError
  and returned 400.

## 7.0.10

- Photos in alerts get the same switch video has, so snapshots can be turned
  off independently of clips.

## 7.0.9

- One version number, one tree: release from a tag, and refuse to build a
  version that is not tagged. Cut after two trees had both declared 7.0.8.

## 7.0.8

- The evidence recorder gets a switch, so clip recording can be turned off
  without turning off detection.

## 7.0.7

- Alert clips work on Linux, and record the room rather than the mode. A
  third ffmpeg leg fed from the pre-render frame writes segments straight to
  disk, so a clip is not blacked out by Hide mode and is not served over HLS
  the way a mediamtx path would be.

## 7.0.6

- Review findings from the 7.0.5 deploy. Shipped as a commit; see 7.0.12 for
  the tag it was missing.

## 7.0.5

- A deploy script for tina, failure-gated throughout, with final checks that
  do not trust what the install printed about itself. It captures tina's live
  state before installing and re-asserts unit enablement from that capture,
  because the old `prerm` destroys that information before any script of ours
  runs. It also restores `/etc/nginx/conf.d/hls-livecam.conf` afterwards:
  that file is payload with no `conffiles` declaration, so dpkg replaces it
  with no prompt and no `.dpkg-old`, and tina's copy is the only one carrying
  the TLS listener and redirect.

## 7.0.4

- Capability detection. A node measures whether it can render CV mode and
  hides the key when it cannot, while detection and alerting carry on
  regardless, running off the much cheaper `observe()`. Measured rather than
  inferred, because core count and CPU model go stale and lie on a throttled
  box. Three states, and `unknown` deliberately does not hide the key: a
  probe that failed to run is not evidence a machine is slow.
- The Debian package takes the `laptop-livecam` name, matching the Arch
  package and the repo.
- CV and Night had rendered nothing since 7.0.2, a consequence of splitting
  `observe()` out of `process()`.

## 7.0.3

- A motion gate, so furniture stops being reported as animals. This lineage
  carried no motion evidence at all, so every promoted track alerted. Tracks
  now carry `fg_consistency`, absorbed with decay — `max(det.fg, tr.fg*0.93)`
  rather than a lifetime high-water mark — and the notifier skips a track
  whose evidence has gone stale. The decay is the point: a monotonic peak
  lets one frame where a motionless object overlapped moving foreground vouch
  for it for the life of the track, which is how a black shoe under a sofa
  became a recurring cat.

## 7.0.2

- Give `CVProcessor` the three methods `broadcast-api` was calling. Detection
  had been dead since 7.0.1, logging `AttributeError: 'CVProcessor' object has
  no attribute 'set_motion_alerts'` once a second: a merge paired a
  `broadcast-api` from one lineage with a `cv_processor` from another and
  nothing checked that the calls still landed. Found by diffing what the
  caller calls against what the class defines, which showed three missing
  methods rather than the one being hit — including `observe()`, without
  which alerting is tied to whatever a viewer happened to select.

## 7.0.1

- Camera lamp reads the device, not the mode. The writer loop runs in every
  mode and only changes what it renders, so the camera goes on being read in
  Hide; reporting "off" was a privacy indicator under-reporting live capture.
- "All living beings" now means it: COCO's full animate set, person plus ten
  animals, behind one "Other" row, instead of four species.
- A "plant" class, off by default and deliberately outside "All living
  beings", so a houseplant can be named correctly and silenced rather than
  reported as a cat.
- COCO_LIVING derives from COCO_LABELS instead of restating it.
- main and cambrian-actor merged into one lineage.

## [5.5.1] - 2026-08-15
### Fixed
- **Feed-mode and message-lock persistence were silently no-ops.**
  `/var/lib/hls-livecam/` was `root:root 0755`; `broadcast-api` runs as
  `http` and could not write `feed_mode` or `msg_lock` into it. The write
  was wrapped in a bare `except: pass`, so every POST appeared to succeed
  while never reaching disk. On restart, `feed_mode` always fell back to
  `SAFE_FEED_MODE` regardless of what the operator last chose -- a
  deliberate `hide` did not survive a restart, silently replaced by `cv`.
  Found live, verified by setting `hide`, restarting, and observing the
  fallback. `feed_mode` and `msg_lock` are now included in the same
  `CAMDASH_STATE_FILES` chown/chmod loop `camdash-feed.state` and
  `cell_aspect` already used (root:www-data/http 0664), in both setup
  scripts. A live system already on 5.5.0 needs `hls-livecam-setup`
  re-run (or the two files manually chowned) to pick this up -- the
  package payload alone does not fix already-broken permissions on an
  existing install.

## [5.5.0] - 2026-08-15
### Added
- **CV Mode pivot, Phase 1.** Show/Blur/Hide + a separate B&W control is
  replaced by Show/CV Mode/Hide across the web viewer, camdash, and the
  Linux operator GUI. `/api/feed-mode` accepts `cloak` as a permanent input
  alias for the canonical `cv`; `/api/bw-mode` stays routable but is now a
  no-op. New `cv_processor.py`: a stateful temporal processor (bounded
  3-frame history, optical-flow-gated motion mask, temporal denoise, CLAHE
  tone correction, damped unsharp sharpening), wired into `broadcast-api`
  in place of the old PNG/PIL cloak render. Profiled at ~31ms/frame
  steady-state against a ~40ms budget on real captured frames. Detection
  and recording are not part of this phase.

## [5.4.0] - 2026-08-14
### Fixed
- **Feed mode persists across restarts, and defaults to `cloak`.** A restart
  previously reset the feed to `show`, exposing the clear camera after the
  operator had deliberately chosen cloak. `show` is now never reached by
  fallback -- only by explicit choice.
- **GOP regression.** Run-1's 1s keyframe interval was lost when a package
  install overwrote a live-only fix. Now sourced from `device.env` as
  `GOP_SECONDS` (default 1) and committed in `pkg/`.
- **broadcast-api now stops cleanly.** Its supervisor loops respawned the
  children that SIGTERM had just killed, so the replacement ffmpeg outlived
  the process, systemd waited out its full stop timeout, and an orphaned
  ffmpeg kept the camera device open. 90s-and-failed is now 47ms and clean.
- **Stalled streams are detected.** `hls_worker` only checked the master
  playlist for HTTP 200 -- a static file that answers 200 while the pipeline
  behind it is stopped. It now watches `EXT-X-MEDIA-SEQUENCE` and reports
  STALE, with the threshold derived from the stream's own TARGETDURATION so
  slow hardware is not misreported as broken.
- **Hide no longer derives from the camera image.** It row-shuffled and
  rolled the live frame; it now publishes black, matching the Windows node.
- Header no longer reads DEGRADED for a deliberately stopped server, or for
  a healthy one whose HLS state has not been polled yet.

### Changed
- Feed switches are covered by VHS static instead of a 16s countdown, and
  the cover is now shown to **every** viewer -- previously only the browser
  that clicked saw it.
- Hide shows viewers "No signal / The camera is switched off" rather than an
  unexplained black frame.

## [5.3.0] - 2026-08-13
### Added
- camdash-gui: PySide6 operator dashboard for Linux, ported from the macOS build.
  Installed alongside camdash — the curses monitor is unchanged and still the
  headless/SSH surface; the GUI is the desktop one.
- camdash: additive GUI-support layer (API_BASE/RTSP_PORT/HLS_PORT/API_PORT,
  `camera_present_cached()`, `_cpu_temp()` via x86_pkg_temp, and a `_livecam()`
  dispatcher over the existing run_* service functions). The curses UI does not
  reference any of it.
- setup (Arch): registers camdash-gui.desktop and prepares the per-user config
  directory the GUI persists window geometry into, chowned to the invoking user
  (root-owned would be silently unwritable from the user's session).

### Notes
- GUI is Arch-only. PySide6 has no Debian bookworm packages (the split pyside6
  packages start at trixie) and the Debian node is headless, so `gui/` lives at
  the repo root rather than under `pkg/`, and the .deb payload is unchanged.

## [3.0.3] - 2026-05-06
### Fixed
- camdash: VIDEO STACK shows N/A for MSSG API, DARK, FPS, REPAIR when server is off ([o] toggle)
- camdash: CAM shows FOUND (not LIVE) when server is off but camera is present
- camdash: CAM shows LIVE only when server is on and camera is present
- setup (Arch): mediamtx restarted after config write to avoid "path not configured" on fresh installs
- setup (Arch): sudoers entries use `disable --now` / `enable --now` to match camdash [o] toggle


## [2.8.7] - 2026-05-01
### Fixed
- camstack: `getdata()` → `tobytes()` (Pillow deprecation, Python 3.14)
- Arch setup: move nginx default server from port 80 to 8080 so conf.d config wins
- Arch setup: add `include conf.d/*.conf;` to nginx.conf if missing
- Arch setup: create `/var/log/nginx/` if missing

## [2.8.6] - 2026-04-26
### Fixed
- Arch setup: `User=www-data` → `User=http` in broadcast-api.service
- Arch setup: sudoers entry updated from www-data to http
- deb: version bumped, ffmpeg-cam.service synced to pkg

## [2.8.5] - 2026-04-25
### Fixed
- Arch setup: pkg copy of hls-livecam-setup-arch had stale `hostname -I` — now matches installed fix from v2.8.4

## [2.8.4] - 2026-04-25
### Fixed
- Arch setup: IP address empty in completion message — replaced `hostname -I` with `ip route get` fallback

## [2.8.3] - 2026-04-25
### Fixed
- Arch setup: `hostname` command not found — replaced with `hostnamectl hostname` with `/etc/hostname` fallback

## [2.8.2] - 2026-04-25
### Added
- Feed mode controls: Show / Cloak / Hide replacing single Hide Feed toggle
- Cloak mode: client-side halfblock pixelation canvas overlay (color, live)
- Cloak bridges to Hide: grayscale pixelation shown immediately on Hide to prevent flash of raw video while snapshot generates
- confirm() dialog on Clear message button

### Changed
- Forced dark theme (no longer follows system preference)
- Sidebar sections styled as cards
- Button state logic: Save and Cancel blue only when changes pending; Clear blue when message exists; all always visible
- block_art COLS reduced to 80 to match Cloak pixelation density
- dark.png cache-busted on Hide with timestamp query string

### Notes
- Cloak is client-side only — a determined user can bypass via dev tools.
  Future goal: server-side pixelated HLS stream via ffmpeg-cam-dark.service.

## [2.8.1] - 2026-04-24
### Added
- camstack SYSTEM panel: CPU temperature display (coretemp sensor, falls back to "?" if unavailable)
- snap_interval config: `/var/lib/hls-livecam/snap_interval` sets widget refresh (1/2/5s), falls back to 2s default

### Changed
- SMART box: colon spacing normalized, TEMP renamed to DISK TEMP
- SYSTEM panel bottom row: equidistant thirds layout for RAM / USB / CPU TEMP

## [2.8.0] - 2026-04-24
### Added
- camstack MESSAGE box: live pixelated webcam widget using halfblock ▀ rendering with oceanic/earth-tone palette (color when feed live, grayscale when hidden)
- camstack broadcast editor: multiline support with Enter for newline, Ctrl+D to save & deliver, left/right cursor navigation, mid-text insert/delete
- camstack footer: dynamic word wrap at • boundaries, two-row layout
- Mute Buzzes button: now permanently blue (primary) for visual consistency
- Blinking • bullet on LIVE status in camstack header

### Changed
- snap_worker refresh interval: 5s (tuned from 2s for CPU stability)
- Widget capture size increased to 80×26 for terminal resize support

## [2.7.9] - 2026-04-24
### Fixed
- Repair completion status "OK" overriding header sys_status, causing "OK | feed hidden" to display in red instead of falling back to base status (LIVE/CONNECTING/DOWN)
- Removed dead color branch in `header_attr()` handling "OK" — unreachable after above fix

## [2.7.8] - 2026-04-24
### Fixed
- Packaging and setup audit: corrected dependency declarations, sudoers, service paths, and postinst to reach clean installable state on Debian and Arch

## [2.8.8] - 2026-05-02
- index.html: hostname now dynamic in title and header (works on any host)
- index.html: feed mode buttons inverted logic fixed (active=gray, inactive=blue)
- index.html: cancel button no longer lit on page load
- ffmpeg-cam.service template: User=root (was mediamtx, cross-contamination fix)
- camstack: version string updated to 2.8.8

## [2.8.9] - 2026-05-02
- index.html: feed mode button logic fixed (active=gray, inactive=blue)
- index.html: cancel button no longer lit on page load
- index.html: renamed CAM-01 to HLS Livecam

## [2.8.10] - 2026-05-04
- setup-arch: fix nginx log dir, http user, conf.d handling (Arch-specific)
- broadcast-api.service: revert DynamicUser, use www-data (setup substitutes http on Arch)

## [2.8.11] - 2026-05-04
- broadcast-api.service: revert DynamicUser, use www-data (setup substitutes http on Arch)

## [2.8.12] - 2026-05-04
- setup: use template for ffmpeg-cam.service (wrong file — patched hls-livecam-setup instead of hls-livecam-setup-arch, no effect)

## [2.8.13] - 2026-05-04
- setup-arch: use @PLACEHOLDER@ template for ffmpeg-cam.service ExecStart, eliminating ${VAR} word-splitting bug

## [2.8.14] - 2026-05-04
- index.html: remove hardcoded primary class from showBtn
- index.html: rename Cloak to Blur
