from pathlib import Path


def get_import_upload_dir(settings, backend_dir: Path | str | None = None) -> Path:
    configured_dir = getattr(settings, "IMPORT_UPLOAD_DIR", "")
    if configured_dir:
        return Path(configured_dir).expanduser()
    if backend_dir is None:
        backend_dir = getattr(settings, "BACKEND_DIR", None)
    if backend_dir is None:
        from app.core.config import BACKEND_DIR
        backend_dir = BACKEND_DIR
    return Path(backend_dir) / "tmp" / "imports"
