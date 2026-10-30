# art/

Base artwork for this product, at source resolution. **Nothing here is
shipped as-is** — 1254x1254 at ~1.5 MB has no business in a page header or an
app bundle. Derivatives (header mark, favicon, app icon) get generated from
this and committed or built alongside; see task #115.

`hls-livecam-server.png` is this project's. The fork keeps its own in
`hls-lightcv-server`, deliberately: a node signs its licence notice and wears
its mark under its own name, and one shared art directory across two products
is how a fork ends up branded as the thing it forked from.

Source images are RGB with no alpha. The viewer header sits on a dark
housing, so a derivative needs a transparent or matched background rather
than the white one that comes out of a naive resize.

---

## macOS derivatives

The switch has happened: every macOS derivative is now generated from
`hls-livecam-server.png`, not downscaled from a previous icon.

- `web/brand.png` / `web/brand@2x.png` — 40px/80px header mark
  `scripts/make-brand-mark.py --product livecam --full-tile --size 40|80 --out <path>`
- `gui/assets/icon_1024.png` — the 1024 master
  `scripts/make-app-icon.py --art art/hls-livecam-server.png --shape <previous icon> --out <path>`
- `gui/assets/AppIcon.iconset/` then `iconutil -c icns` — the bundle icon,
  copied on to `packaging/` and `camdash-gui.app/Contents/Resources/`

Two things that are easy to get wrong and were:

**The corner is a superellipse, not a rounded rectangle.** `make-app-icon.py`
clones the silhouette's alpha from an existing icon rather than drawing one,
because a circular-arc radius looks subtly wrong beside every other icon in
the Dock. A hand-rolled `rounded_rectangle` mask is the wrong curve.

**The source is full-bleed, and its corners are field colour.** The tile
shape belongs to the mask, not to the artwork. An earlier revision painted
its own rounded corners in black, which survived just inside the arc when the
squircle was cut and fringed all four corners — and, in the mirror-image
failure, made the Windows generator read black as the background and pad with
it. The corners are now `#012463` like the rest of the field, so no consumer
has to know about it. Keep it that way: if a future source arrives with
painted corners, flood-fill them to the field colour before committing it.

The generators need numpy and Pillow — `.venv/bin/python` has both, the system
interpreters do not.

Heed the alpha warning above: this source is RGB with no alpha, and the
header sits on dark housing, so a naive `sips -Z` leaves a white square.

The LightCV artwork for **amira** is deliberately NOT here — it lives in the
`hls-lightcv-server` fork, so a fork does not end up wearing the mark of the
thing it forked from. Fetch it from that repo when amira is set up.
