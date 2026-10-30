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

## Derivatives, and how they are built

Everything below comes from `hls-livecam-server.png`. Nothing is retouched
by hand, and nothing is downscaled from another derivative.

    scripts/make-app-icon.py --art art/hls-livecam-server.png \
        --shape <previous icon> --out gui/assets/icon_1024.png
    scripts/make-brand-mark.py --product livecam --full-tile --size 128

On macOS the icon set and `.icns` are then built with `sips` and
`iconutil -c icns`, and copied on to `packaging/` and the app bundle.

Two traps worth keeping written down:

**The corner is a continuous superellipse, not a circular-arc rounded
rectangle.** `make-app-icon.py` clones the silhouette's alpha from the icon
it replaces rather than drawing one, because a radius-based mask is the wrong
curve and looks subtly wrong beside other icons in a dock or launcher.

**The source is full-bleed, and its corners are field colour.** The tile
shape belongs to the mask, not to the artwork. An earlier revision painted its
own rounded corners in black, which survived just inside the arc when the tile
was cut and fringed all four corners -- and, in the mirror-image failure, made
the Windows generator read black as the background and pad with it. The
corners are now `#012463` like the rest of the field. Keep it that way: if a
future source arrives with painted corners, flood-fill them to the field
colour before committing it.

The generators need Pillow and numpy. On ariana `.venv/bin/python` has both
and the system interpreters do not.

