# First macOS pre-release notes — draft

Publication is pending source-delivery clearance, exact-candidate verification
and installed-app sign-off. Attach the final DMG/source/notices download links,
source commit and SHA-256 values before publishing these notes.

YomiMado (読み窓) helps you read Japanese text on your screen: select a region,
run local OCR, then click the overlay to explore readings, dictionary meanings,
kanji and on-demand translation. Screenshots stay local. This pre-release
supports Apple Silicon Macs running macOS 14 or later.

## Installation

This is a hobby build **without Developer ID signing or Apple notarization**.
It requires explicit macOS Gatekeeper approval. Download the release DMG,
check its published SHA-256, open it, drag YomiMado to Applications and eject
it. Launch from Applications. After the initial macOS block, follow Apple's
[per-app Open Anyway instructions](https://support.apple.com/en-us/102445)
in System Settings → Privacy & Security. Investigate damaged or malware
warnings; do not disable Gatekeeper globally.

The detector weights are not included. Download `comictextdetector.pt.onnx`
from the [original publisher's beta-0.2.1 release](https://github.com/zyddnys/manga-image-translator/releases/tag/beta-0.2.1),
then choose **Select detector model file** in YomiMado. Expected SHA-256:
`1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f`.
YomiMado verifies and copies it to local Application Support; the original
file remains intact. Scanning is unavailable until import succeeds.

Grant YomiMado Screen Recording in System Settings → Privacy & Security and
follow macOS's quit/reopen instruction. Use Cmd+Shift+O to select text. OCR,
tokenization, dictionaries and the bundled on-demand translation run locally.
Model import requires your own downloaded file; the app does not download it.

## Data and limitations

JMdict and KANJIDIC2 headers are dated **2026-09-27**. Dictionary data is
copyright James William Breen and EDRDG, under CC BY-SA 4.0; see the
[EDRDG licence](https://www.edrdg.org/edrdg/licence.html). Software, model and
data credits are available through **Sources and licenses** and the bundled
notices. The Release must supply matching project/dependency sources,
rebuild instructions and licence texts alongside the installer.

OCR and translation can be inaccurate, particularly stylized text and complex
layouts. This release does not reconstruct complete page reading order or
replace manga artwork with translations. Fresh-macOS installation was not
tested because no clean Mac was available. Intel Macs and Windows installers
are outside this release's verified target. Record any additional untested
installed-app cases in the final notes.
