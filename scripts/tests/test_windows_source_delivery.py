"""Keep export-only manga example artwork out of the source bundle."""

import tarfile
import tempfile
import unittest
from pathlib import Path

from windows_release import onnx_source_delivery_filter


class SourceDeliveryTests(unittest.TestCase):
    def test_only_the_replaced_raw_manga_sdist_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            retained = sources / "windows-native"
            retained.mkdir(parents=True)
            (sources / "manga_ocr-0.1.16.tar.gz").write_bytes(b"raw example artwork")
            code = b"unchanged preferred code and original licence"
            (retained / "manga-ocr-0.1.16.tar.gz").write_bytes(code)
            (retained / "source-preparation.json").write_bytes(b"exclusion record")
            archive_path = root / "delivery.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                archive.add(
                    sources, arcname="sources", filter=onnx_source_delivery_filter
                )
            with tarfile.open(archive_path) as archive:
                self.assertNotIn("sources/manga_ocr-0.1.16.tar.gz", archive.getnames())
                self.assertEqual(
                    archive.extractfile(
                        "sources/windows-native/manga-ocr-0.1.16.tar.gz"
                    ).read(),
                    code,
                )
                self.assertEqual(
                    archive.extractfile(
                        "sources/windows-native/source-preparation.json"
                    ).read(),
                    b"exclusion record",
                )


if __name__ == "__main__":
    unittest.main()
