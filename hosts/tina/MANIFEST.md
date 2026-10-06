# Tina: the live livecam install, captured 2026-10-05

Tina (Ubuntu, i3-2330M, 3 GB) runs hls-livecam-server, deployed over the 6.0.7 .deb, with
the same code files as Tanzania (see ../tanzania/MANIFEST.md). The viewer page (Video panel
above Audio), broadcast-api, the nginx conf, cv_detect.py, cv_processor.py and
vendor/hls.min.js were copied from Tanzania's live install on 2026-10-05; the other cv_*.py
files were already identical. Before that Tina ran 8e17f08 (2026-09-01) with local edits; the
snapshot is in the operator's backups (tina-livecam-20261006-0313.tar.gz).

Tina-specific:
- Its CV tuning is configuration, not code: CV_TEMPORAL_W_CUR=0.60 and CV_TEMPORAL_W_PREV=0.20
  in etc/hls-livecam/device.env (upstream defaults 0.44 and 0.28).
- The map renderer add-on is the separate laptop-livecam-lite repo (hls-lightcv-server); it
  does not import these files.
- The camera (USB 0c45:6366) drops off the bus and needs a physical reseat. Without /cam there
  is no roomaudio either, so a call's room-to-caller leg comes up only with the camera.
- notches.json (empty) and audio.json were created for www-data (root:www-data 664).
