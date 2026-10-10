# Actions history cleanup — 2026-10-10

The maintainer explicitly requested clearing workflow history and confirmed
**Delete all 58 runs**, including permanent removal of their GitHub logs and
artifacts. A one-time job at commit `bf36fe0` preflighted the exact IDs, completed
state, repository and source SHA before deletion, then verified HTTP 404 for each.
[Cleanup run 38044773930](https://github.com/chonnakanch/yomimado/actions/runs/38044773930)
passed. A subsequent public API listing contained only this new cleanup run.
The temporary Actions-write workflow has been removed. No private release draft,
release asset, branch, tag, source/human approval or installer was changed.

Earlier documents intentionally retain historical run identities and evidence
hashes. Their Actions links no longer resolve. Previously downloaded evidence
remains in ignored local `services/ocr/build/windows-*-run-*` and
`services/ocr/build/windows-run-*` directories; this is not a claim that every
historical log or artifact was downloaded. GitHub's deleted artifacts cannot be
recovered from Actions. The original listing snapshot is retained locally at
`services/ocr/build/onnx-prototype/workflow-history.json`.

| Deleted run | Workflow                                                                   | Conclusion | Source SHA                                 |
| ----------- | -------------------------------------------------------------------------- | ---------- | ------------------------------------------ |
| 38040678348 | Windows Torch source audit                                                 | cancelled  | `dfa7ad289368cec9724e67fc4f153efb5caee4b0` |
| 38031623655 | Windows Torch source audit                                                 | failure    | `85d0766354eef528cd3317d1e487f17206836773` |
| 38024770382 | Windows Torch source audit                                                 | failure    | `0a7cbe84a40414d91b9d876cd101e3ddf02bba84` |
| 38022182370 | Windows private candidate                                                  | success    | `65ac794370fe2b0f60d7ed968ac0be2c04ca4d51` |
| 38021809403 | GEOS private setup 51b0091103c1 — 6be7046c222372ad2b7d3278303444e4a2ecc328 | success    | `6be7046c222372ad2b7d3278303444e4a2ecc328` |
| 38020734345 | Windows Torch source audit                                                 | failure    | `d2b52dde989c91cbbbf548a198e7be3d03ec2102` |
| 38020734338 | GEOS private setup 51b0091103c1 — d2b52dde989c91cbbbf548a198e7be3d03ec2102 | failure    | `d2b52dde989c91cbbbf548a198e7be3d03ec2102` |
| 38020734334 | Windows private candidate                                                  | success    | `d2b52dde989c91cbbbf548a198e7be3d03ec2102` |
| 38019354851 | Windows private candidate                                                  | success    | `87731d65c50499a67ec7683e889402638ba557ca` |
| 38017337839 | GEOS private setup 51b0091103c1 — 220bd0bf2d9e4fce616cb8f70b7059e107451a01 | failure    | `220bd0bf2d9e4fce616cb8f70b7059e107451a01` |
| 38016752910 | GEOS private setup 51b0091103c1 — 485c672e63befc3f2718cd6dc64decd7b4c8fcca | failure    | `485c672e63befc3f2718cd6dc64decd7b4c8fcca` |
| 38016673211 | Windows private candidate                                                  | failure    | `902bcf6d3446fbeab65128cfa62ac93f5549a051` |
| 38016054660 | Windows private candidate                                                  | failure    | `09c4caaea69993cda765efb23dae0d966452f113` |
| 38015437061 | Windows Torch source audit                                                 | failure    | `3f2866d8dac6d82cb08f59cc6f8dde8735616ece` |
| 38015229208 | Windows Torch source audit                                                 | cancelled  | `e47f25dc18162118b9f186c90a4a6ebf1594611f` |
| 37943467439 | Windows Torch source audit                                                 | failure    | `bba93e491f1d6198285917a3cec9bacf3840cd1c` |
| 37941928033 | Windows Torch source audit                                                 | failure    | `64ab5de2d18f77c27e324c95ac9c7a5ef84d593f` |
| 37941502143 | Windows Torch source audit                                                 | failure    | `572cd7dc5ae376e37ebf38182e8b7cee195c4d93` |
| 37941035678 | Windows Torch source audit                                                 | failure    | `9e08202bc782114227612c13ccf14f1996271f37` |
| 37940832130 | Windows GEOS source audit                                                  | failure    | `ded468145c562e4843a8d887e56d9b97516d33e9` |
| 37939801320 | Windows Torch source audit                                                 | failure    | `61143751c5c79238acfcb57df15c37f9cc8492bc` |
| 37938465690 | Windows GEOS source audit                                                  | failure    | `f252ed7d1af767866af54a18a78e08c1b5e31d00` |
| 37938195277 | Windows OpenCV source audit                                                | success    | `23ad7f119cf99881aa634855f4394e6b45deac02` |
| 37936508507 | Windows OpenCV source audit                                                | failure    | `1ea0b33b932b5ef1f8beb7c8e13758cb9b3f699b` |
| 37935912253 | Windows GEOS source audit                                                  | failure    | `082b241d6b24f127bbfd632b8b37f969e951b039` |
| 37934320710 | Windows OpenCV source audit                                                | success    | `3be03080dc59cbd16868da35e51a65b3697a9eb6` |
| 37933246289 | Windows OpenCV source audit                                                | failure    | `81988bb07121e9bb08c2cdaee4b8ee649a8dc685` |
| 37877467511 | Windows GEOS source audit                                                  | success    | `a10db77ec91d5e1e0f96f444b0a98376c641774a` |
| 37876379469 | Windows GEOS source audit                                                  | failure    | `ac10c48f41a8546d0dfe1c09a83bfd875ff81ffa` |
| 37802965979 | Windows private candidate                                                  | success    | `c69eff996f7e85ea88ecb4f0407e05cf5d8ec8b5` |
| 37798943690 | Windows private candidate                                                  | failure    | `7a8c4d82a9f10461c02ba7e94399c206bf9648a8` |
| 37794271949 | Windows private candidate                                                  | failure    | `80be890535305c2e3b349fc118561d850a0dfa02` |
| 37787583634 | Windows private candidate                                                  | failure    | `10b8aba894fe83d08fd7f02fb83771ad68413984` |
| 37782181350 | Windows private candidate                                                  | failure    | `f5c157d6f9a4b0efdb39908e5054fbd061a37956` |
| 37780854704 | Windows private candidate                                                  | cancelled  | `4fe9a54dd77e5fda26e080503da181ed7d8213f7` |
| 37780050429 | Windows private candidate                                                  | failure    | `2f41b64630ba5e33812069469b344a23de282432` |
| 37721943728 | Windows private candidate                                                  | success    | `79065df7ba34a3aaa4ddb3a1ebb30e164405742a` |
| 37720960120 | Windows private candidate                                                  | failure    | `3be715b2c52923707f2512cf3889d06e4fd819cc` |
| 37720331486 | Windows private candidate                                                  | failure    | `b6b4702044e6e3b1f70cfa6307dabf540f2079f7` |
| 37720144182 | Windows private candidate                                                  | cancelled  | `bbc4e2b8e4f7eb8daa80add8a3389622e95ac09f` |
| 37719537003 | Windows private candidate                                                  | cancelled  | `473f2c67da72ab4905974b01e109f8a15c3bbe28` |
| 37718330039 | Windows private candidate                                                  | cancelled  | `7d665de6b0a5b1b67826f0d4f32fc96123830d2c` |
| 37718102058 | Windows private candidate                                                  | cancelled  | `a7106ddfde6b7d0362602209afc753ed715c07f3` |
| 37717190035 | Windows private candidate                                                  | failure    | `c048616e023988e7fcafd9fbacfd2d4d79789b00` |
| 37589437962 | Windows private candidate                                                  | failure    | `9dd6e6f0d73c247d08ee771ad5cdbd4f9a9dd894` |
| 37589073792 | Windows private candidate                                                  | cancelled  | `cec78fd282c3d26fc23923d52da192527a4b8c09` |
| 37586829449 | Windows private candidate                                                  | failure    | `8c38e7581359c717acdbe0ca0c56155dc7c41fb8` |
| 37585224570 | Windows private candidate                                                  | cancelled  | `6795535d9e922bb2b7c0e8b94d4effdcd57de47f` |
| 37584983920 | Windows private candidate                                                  | failure    | `ae5b2acb18cd670b127ed34f9cc8ba9843df43db` |
| 37584643118 | Windows private candidate                                                  | cancelled  | `585c70e839a4730bacaf4da90dd191fa5b2f28e3` |
| 37584122748 | Windows private candidate                                                  | cancelled  | `b4700224237a5842bebd6b124e1a9cdd9ca4d169` |
| 37583697067 | Windows private candidate                                                  | failure    | `5cda1f479ba9dcc14b73fc0dd0cbbed00add81af` |
| 37582948931 | Windows private candidate                                                  | failure    | `c7110b46e2e4fef3e632d43b7c13e6a0f84c18c6` |
| 37581451301 | Windows private candidate                                                  | failure    | `84f93402b7df9952a52885de4a8c0cb06f69ee72` |
| 37580840075 | Windows private candidate                                                  | failure    | `705fe582f78e4b5b864f93b6ba3941876b2c7838` |
| 37580415474 | Windows private candidate                                                  | failure    | `25538b9da501d2b18351304447a3311d95ebdd5f` |
| 37580037955 | Windows private candidate                                                  | failure    | `dcfafad7f5edd4e1ec2c86bf8d1a7fc0708f2947` |
| 37579195580 | Windows private candidate                                                  | failure    | `5e619cfcb68d705a1abdee5cf0f2188b82db561e` |
