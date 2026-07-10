import unittest
from pathlib import Path
from types import SimpleNamespace

from app.utils.import_paths import get_import_upload_dir


class ImportPathTests(unittest.TestCase):
    def test_default_upload_dir_uses_backend_tmp_imports(self):
        settings = SimpleNamespace(IMPORT_UPLOAD_DIR="", BACKEND_DIR=Path("C:/project/backend"))

        self.assertEqual(
            get_import_upload_dir(settings),
            Path("C:/project/backend") / "tmp" / "imports",
        )

    def test_configured_upload_dir_overrides_default(self):
        settings = SimpleNamespace(IMPORT_UPLOAD_DIR="C:/shared/imports", BACKEND_DIR=Path("C:/project/backend"))

        self.assertEqual(get_import_upload_dir(settings), Path("C:/shared/imports"))


if __name__ == "__main__":
    unittest.main()
