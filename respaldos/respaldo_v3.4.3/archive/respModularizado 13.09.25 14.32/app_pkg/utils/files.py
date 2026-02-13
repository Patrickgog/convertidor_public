import io
from pathlib import Path
import zipfile


def zip_directory(path: str) -> bytes:
    """Zip a directory recursively and return the bytes."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for file_path in Path(path).glob('**/*'):
            if file_path.is_file():
                zip_file.write(file_path, file_path.relative_to(path))
    return zip_buffer.getvalue()


__all__ = ["zip_directory"]
