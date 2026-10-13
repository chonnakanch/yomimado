# Security review — 2026-10-13

Reviewed the loopback API, upload/decoder boundaries, frontend configuration,
Tauri release CSP/capabilities, native model import, persistence queries and
release download/archive/publisher protections. The starting checkout was clean
on `develop` at `973c721`. This is a focused source and dependency review, not a
penetration test or certification of the published installers.

## Confirmed issues addressed

| Priority | Finding                                                                                                                                                                                                    | Remediation                                                                                                                                                                                                                                                                                                                           |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1       | CORS alone did not reject hostile-origin requests before handlers ran. A cross-origin multipart upload could invoke expensive OCR; missing Host validation also left the service exposed to DNS rebinding. | Add an exact loopback Host allowlist, reject unexpected browser origins, and require `X-YomiMado-Client: desktop` on all `/api/` requests. The header forces preflight for uploads and saved-data reads. Tests prove rejection before recognition, allow the existing Tauri/Vite origins and reject untrusted Host values.            |
| P2       | OCR read complete uploads without an application byte limit, and model inference/decoding had no application pixel budget.                                                                                 | Bound the received stream before JSON/multipart parsing: 32 MiB for OCR and 1 MiB otherwise, including absent/underdeclared Content-Length. Reject captures above 40 million pixels or 16,384 pixels per side before loading models. Restrict Pillow decoding to PNG and verify decoder dimensions before RGB conversion.             |
| P2       | npm audit returned four affected dependency entries, including critical-rated transitive development-tool alerts.                                                                                          | Pin Vitest to patched `4.1.11`, removing the old Tinypool dependency, and update `source-map-js` to `1.2.2`. A fresh `npm ci --ignore-scripts` and npm audit succeed with zero reported advisories. These dependencies belong to development/build tooling; the findings do not establish remote code execution in the installed app. |
| P3       | Vite's environment prefix allowed every `TAURI_` variable to become available to frontend code, including potential signing/build secrets.                                                                 | Expose only explicitly public `VITE_` variables. This removes unnecessary configuration exposure; no actual secret leak was established by this review.                                                                                                                                                                               |

The request marker is deliberately documented as a browser guard, not
authentication. The frontend adds it to JSON, multipart, GET and DELETE requests;
both platform smoke helpers were updated. Normal HTTP 413/403 errors surface
through the existing service error handling.

Starlette documents that simple CORS requests are passed through to the
application, and that trusted-host checks address Host-header attacks.
[Middleware documentation](https://starlette.dev/middleware/).

Patched development-tool details:
[Vitest advisory](https://github.com/advisories/GHSA-82fw-gwwq-j7x9),
[Tinypool advisory](https://github.com/advisories/GHSA-85c8-ppgw-ccpr),
[source-map-js advisory](https://github.com/advisories/GHSA-68fv-2mgg-jv7q).
The exact licenses and original texts for all 16 new/updated development packages
are retained under
`THIRD_PARTY_LICENSES/development/security-update-2026-10-13/`.

## Open findings and exposure limits

### P1 — Refresh the frozen Python runtime before a future release

OSV matched advisories for **13 distinct PyPI package names** in the checked-in
macOS/Windows inventories: AnyIO, Filelock, fsspec, Pillow, pytest, python-dotenv,
python-multipart, Requests, setuptools, Starlette, Torch, Transformers and urllib3.
The [advisory snapshot](security-advisory-snapshot-2026-10-13.json) records exact
input hashes, matched versions, identifiers, aliases, upstream summaries and
reported fix versions. It contains 733 package/version queries: 84 macOS,
80 Windows and 569 Rust entries. Duplicate GHSA/PYSEC aliases are not separate
vulnerabilities.

Prioritize the HTTP parsing path: Starlette `0.49.3` and python-multipart `0.0.20`
match request/form parsing advisories. Byte/origin guards reduce exposure but
do not patch vulnerable parsers or eliminate CPU denial of service within an
accepted request. The affected Starlette form-limits behavior is documented in
the [upstream advisory](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq).

Other matches require application-specific triage. The API accepts PNG captures;
the Pillow alerts include PSD, font, PDF and other paths the OCR handler does not
use. Translation uses local Marian models and disables downloads; Trainer,
LightGlue, source-saving and other reported Transformers paths are not exposed by
these handlers. These observations reduce reachability; they do not establish
that an entire dependency is safe. pytest/setuptools are inventory/build tooling.
Windows requirements include export/reference Torch inputs even though the
installed ONNX runtime's existing delivery checks exclude Torch binaries.

Do not rewrite the historical v0.1.0 locks/manifests to claim a patched installed
runtime. Prepare updated exact dependency inputs, review licenses/native notices,
rebuild both runtimes and verify the new installers for the next authorized
release. macOS must use a newly reviewed seed; its reuse gate remains intact.

### P2 — Other local processes are not authenticated

Any native process that can reach loopback can supply the public client header
and read or modify saved study data. This includes another logged-in OS user
on a shared computer. Host/origin checks primarily protect against browser
attacks. A future per-launch secret shared privately between Tauri and its child
service should protect sensitive endpoints; keep it out of frontend build
variables, URLs, logs and readiness files. Concurrent expensive requests also
need an inference admission/concurrency limit if local callers are outside the
trust boundary. These protections are not implemented by this patch.

### P3 — Rust maintenance advisories

The all-platform Cargo lock matches seven Rust entries. `glib 0.18.5` has an
iterator soundness advisory, but target-filtered `cargo tree` shows no dependency
path on macOS Apple Silicon or Windows x64; it is not evidence of an affected
supported-platform binary. `proc-macro-error` and five `unic-*` crates have
unmaintained-package advisories. The latter remain in Tauri's dependency graph;
track upstream replacement/update work. Do not treat maintenance notices as
confirmed exploitable defects.

## Existing protections retained

- Packaged macOS and Windows configs enforce CSP, restricting connections to
  Tauri IPC and `127.0.0.1:8766`. The null CSP in the base config serves development.
- Tauri capabilities name the four application windows and grant no remote URL
  access or frontend filesystem/shell execution permissions. Custom app commands
  are registered for app windows; the capability list alone does not constrain
  those commands to individual windows. See
  [Tauri capabilities](https://v2.tauri.app/security/capabilities/).
- OCR/dictionary text is rendered through React text nodes. The reviewed UI uses
  no production `dangerouslySetInnerHTML`/`eval` path. SQLite study/cache lookups use
  bound parameters. Screenshots remain local and translation is explicit.
- Detector import checks exact SHA-256 before installing the staged ONNX file.
  Models and developer source checkouts remain trusted local inputs; the service
  is not a sandbox for arbitrary model packages or Python repositories.
- Release jobs retain pinned actions, read-only builders, protected owner
  publication, exact candidate/upload digests and archive-member checks. Signed
  asset redirects strip authorization on cross-origin hops. No release protection
  was weakened for this patch.
- A limited tracked-source scan for GitHub token, AWS access-key and private-key
  header formats found no matches. It excludes Git history, ignored files and
  files over 2 MB; it is not a complete secret audit.

## Verification and release scope

- 20 focused browser/body/pixel security regression tests pass, including streamed
  bodies without trustworthy Content-Length and preservation of normal payloads.
- Frontend: production build and TypeScript checks pass; 100 tests pass on
  Vitest 4.1.11. Formatting checks pass. A normal clean npm install succeeds.
- Service: 77 tests pass under Python 3.9.6; the Windows graph-checksum test passes
  separately under Python 3.13.15 because it requires `hashlib.file_digest`.
  All 78 service tests are exercised. Changed Python lint/format checks pass.
- Native: 36 Rust tests and the macOS debug build pass. The build retains an
  Xcode SDK/cache discovery warning, with no errors. No Windows installer was
  built or exercised.
- Release tools: 51 required fake-API/version tests pass on Python 3.13.15;
  32 Windows input/smoke-helper tests pass using the bundled Python runtime.
  These are source/fixture tests and do not claim installed Windows acceptance.
- Changed Python lint/format, desktop/document formatting and application diff
  whitespace checks pass. Original license texts remain byte-for-byte copies;
  the std-env license retains an upstream trailing blank line.

No installer is published, no existing candidate hash or platform acceptance
record changes, and no claim is made that this patch has reached v0.1.0 users.
The Python/source/build changes require fresh reviewed runtime inputs and future
exact-installer acceptance before an authorized publication.
