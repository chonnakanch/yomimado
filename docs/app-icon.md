# YomiMado app icon

The initial icon uses a copper capture window around an ivory manga page. Two
vertical marks suggest Japanese reading; an offset page edge suggests reading
beyond the page. The charcoal tile follows the desktop UI palette and leaves
transparent padding around its rounded corners.

The master artwork is `apps/desktop/src-tauri/icons/source-v1.png`, generated
with the built-in imagegen tool on 2026-10-04. No font, third-party logo, manga
image, or model asset was used as an input. `placeholder.svg` preserves the
previous bootstrap icon and is not the source for the current exports.

Tauri's existing CLI generated the PNG sizes, Windows ICO/Store assets, and
macOS ICNS. The main Tauri configuration references the desktop icons; the
macOS release configuration inherits them. No mobile assets were added or
updated. Windows shell appearance still needs a native Windows check.

To regenerate the desktop exports from the master, run from `apps/desktop`:

```sh
npm run tauri -- icon src-tauri/icons/source-v1.png --output /tmp/yomimado-icons-v1
```

Copy only the top-level desktop files from that output into
`src-tauri/icons/`; the CLI also produces mobile subdirectories, which are
outside YomiMado's scope. Keep the master at its original resolution and
preserve its alpha channel. Review the 32px export after any design change.

## Generation prompt

```text
Use case: logo-brand
Asset type: production desktop app icon for YomiMado (読み窓), a Japanese manga reading assistant.
Primary request: create one polished, distinctive app icon expressing a reading window onto a manga page. Keep the existing app palette: warm charcoal #25211e, copper #df8259, and warm ivory #f8f6f1.
Subject: a bold copper rounded window frame surrounding a warm ivory manga page. Two distinct vertical charcoal pill-shaped marks on the page suggest vertical Japanese reading. A subtle offset page edge adds the idea of reading beyond the page. The frame should have an elegant small opening or layered corner that evokes the capture/overlay function. Simple cohesive symbol, not a collection of objects.
Style: precise geometric vector-like shapes, crisp edges, flat colors, exceptionally restrained depth. Friendly, calm, professional macOS and Windows application icon.
Composition: single centered icon on a warm charcoal rounded-square tile. Tile occupies about 84% of a square 1024x1024 transparent canvas with consistent transparent padding, generous inset around the central symbol. Strong silhouette, thick frame, legible at 32px. Straight-on view.
Constraints: one icon only, no mockup, no lettering, no Japanese glyphs, no labels, no watermark, no external shadow, no photographs, no characters or faces, no extra decorative sparkles, no gradients. Outside the rounded-square tile must be truly transparent.
```
