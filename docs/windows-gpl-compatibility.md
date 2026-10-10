# Original Windows installer: GPL compatibility review

Reviewed 2026-10-10. Scope: the maintainer-tested setup from
[run `37802965979`](https://github.com/chonnakanch/yomimado/actions/runs/37802965979),
source `c69eff996f7e85ea88ecb4f0407e05cf5d8ec8b5`, setup SHA-256
`51b0091103c10c03ecd3748039bd4db0631381fb43885fe7163b889821fba207`.
This is a distribution review of the original runtime, not installer approval
or a finding that the maintainer's internal tests infringed copyright.

## Decision and limits

**Do not publicly distribute this combination under its current permissions.**
The verified library calls and licence restrictions establish a GPL compatibility
conflict under the Free Software Foundation's published interpretation of combined
programs. No applicable additional permission was found in the reviewed detector
licence, README or inference/NMS files. This is the project's release review
decision; whether a particular combination is a derivative work is ultimately a
legal determination, not something a build or automated test can conclusively prove.

Intel's licence allows conditional binary redistribution. The concern is complying
with that licence **and** the GPL at the same time in this combined service. An
Intel term does not itself prove that the application violated Intel's licence.
This review does not clear the remaining Windows source, notices or installer gates.

## Verified combination

The Windows preparation recipe copies detector source at
[`440b978563c71b758e31aaa315d100faba1efa2f`](https://github.com/dmMaze/comic-text-detector/tree/440b978563c71b758e31aaa315d100faba1efa2f)
and applies the recorded training-only `wandb` import patch. The user installs
the ONNX weights separately; the installer still distributes GPL detector **code**.

The pinned detector's `LICENSE` is byte-identical to the unmodified GNU GPLv3
text, SHA-256 `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`.
Its recursive upstream tree lists only this licence file. The following pinned
files were retrieved independently and match the local detector export:

| Source file             | SHA-256                                                            |
| ----------------------- | ------------------------------------------------------------------ |
| `inference.py`          | `5173c4e98efa4db2e230c783341875d3a0a68aeb9d001a207b283ce49f1644f2` |
| `basemodel.py`          | `0795a8e3903751d7b8c4a2e62083a743ae56327c85c50f6119e6becea7ceff77` |
| `utils/yolov5_utils.py` | `62c72d7fa1529b8259cac5a21b93ba43a4c9fd32071f735678f8a95ee012571e` |

`app/pipeline/real_ocr.py` imports this detector inside the OCR service. Even
the ONNX path calls `cv2.dnn.readNetFromONNX`, `blobFromImage` and `forward`;
postprocessing converts output with `torch.from_numpy` and calls
`torchvision.ops.nms`. These are function calls sharing arrays/tensors in the
same Python process, not independent executables communicating through files.
The desktop-to-service HTTP boundary does not separate these internal libraries.

The installed smoke and inventory reports bind the following loaded files to
hash-identical members of the pinned original wheels:

| Installed file            | SHA-256                                                            |
| ------------------------- | ------------------------------------------------------------------ |
| `cv2/cv2.pyd`             | `d2e14633f0699469c37e43210ca9e167887ce4a162e01f1490be49fd8e45388f` |
| `torch/lib/torch_cpu.dll` | `9e2a771549e9acd8461d2c75a0a78f7fe3f1c062bb17bef339a0ecf0612746bd` |

The original environment reports IPP 2021.12.0 and MKL 2025.2. The later
`4639a6351eb8…` candidate retains these same two binary hashes; adding notices
does not change their compatibility. The exact setup bytes were not downloaded
again for this review; installed evidence and original wheel bytes were checked.

## Terms and exception checks

The exact OpenCV wheel's `LICENSE-3RD-PARTY.txt` expressly identifies statically
linked IPP and includes the Intel Simplified Software License, October 2022.
Full notice SHA-256:
`0b33c5be17819d10ecad11360c6f2bd5a7df7c0f80a3314a81e28070d93818e2`.
The MKL 2025.2 wheel's `LICENSE.txt` contains that same licence version,
SHA-256 `7721633d0ddff43fae25ebfd405f8166a0ce730cbcec44f2f3ad9d5eb8ac9a6f`.
It permits unchanged binary redistribution with notices, but forbids modification
and reverse engineering. Intel publishes the text on
[page 10 of its October 2022 overview](https://cdrdv2-public.intel.com/686502/oneapi-license-overview-10-05-22.pdf#page=10);
the original bundled texts control this review. IPP is directly identified in its
delivered notice. MKL identification additionally relies on Torch's exact build
report; a complete static vendor/link map remains separate work.

[GPLv3 sections 5, 6 and 10](https://www.gnu.org/licenses/gpl-3.0.html) require
GPL permissions and corresponding source for a covered combined work and prohibit
further restrictions on those permissions. GPLv3 also preserves separate works
in an aggregate and provides a system-library exception.

The [FSF's aggregation guidance](https://www.gnu.org/licenses/gpl-faq.en.html#MereAggregation)
treats designed shared-process library calls as evidence of a combined program.
Its [interpreter guidance](https://www.gnu.org/licenses/gpl-faq.en.html#IfInterpreterIsGPL)
also treats native bindings as linking. This inference matches the actual detector
calls above; sharing an installer alone would not establish it.

The system-library exception does not provide an established permission here:
IPP/MKL are separately added application libraries, not part of the normal Windows,
CPython or MSVC runtime package used by this app. A BLAS interface alone does not
satisfy all of GPLv3 section 1's system-library criteria. This finding does not
classify every Windows runtime DLL or Intel component as incompatible.

The [FSF's exception guidance](https://www.gnu.org/licenses/gpl-faq.en.html#GPLIncompatibleLibs)
requires permission from the relevant GPL copyright holders. The maintainer can
grant exceptions for code they own, but cannot grant one for the third-party
detector. No such grant is present in the reviewed pinned detector material.

## Available resolutions

1. Use verified compatible replacement libraries. The prepared IPP-free OpenCV
   and MKL-free Torch builds follow this route; their full installed runtime,
   corresponding sources and notices still need completion.
2. Obtain sufficient additional permission from the relevant rights holders for
   this exact combination. No request has been sent and no permission is claimed.
3. Establish another permitted distribution structure or compatible prebuilt
   runtime with actual separation, exact licences and source coverage. Relabelling
   the existing service as an aggregate, omitting weights, adding attribution or
   changing only YomiMado's own licence would not resolve the identified issue.

Rebuilding is therefore the selected resolution, not a universal requirement for
Windows software. A permitted prebuilt replacement could avoid compiling Torch.
Research downloads and full original notices remain in the ignored local directory
`services/ocr/build/windows-licence-review-20261010/`; no installer, model weights,
credentials or manga screenshots were added to the repository.
