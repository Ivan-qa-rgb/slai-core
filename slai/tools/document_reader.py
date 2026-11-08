from __future__ import annotations

from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCUMENT_ROOT = PROJECT_ROOT / "uploads"

ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
}

MAX_DOCUMENT_CHARS = 20_000
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024

def _validate_max_chars(max_chars: int) -> None:
    """Проверяет ограничение размера текста."""
    if isinstance(max_chars, bool) or not isinstance(max_chars, int):
        raise TypeError(
            "max_chars должен быть целым числом"
        )

    if max_chars <= 0:
        raise ValueError(
            "max_chars должен быть больше нуля"
        )

def _resolve_safe_path(
    file_path: str | Path,
    base_dir: str | Path,
) -> Path:
    """
    Возвращает безопасный путь внутри base_dir.

    Запрещает:
    - пустые пути;
    - null-байты;
    - выход за пределы base_dir;
    - отсутствующие файлы;
    - директории вместо файлов.
    """
    if not isinstance(file_path, (str, Path)):
        raise TypeError(
            "file_path должен быть строкой или Path"
        )

    raw_path = str(file_path)

    if not raw_path.strip():
        raise ValueError(
            "file_path не может быть пустым"
        )

    if "\x00" in raw_path:
        raise ValueError(
            "file_path содержит недопустимый null-байт"
        )

    root = Path(base_dir).expanduser().resolve()

    candidate = Path(raw_path).expanduser()

    if not candidate.is_absolute():
        candidate = root / candidate

    try:
        resolved_path = candidate.resolve(strict=True)
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Файл не найден: {file_path}"
        ) from error

    try:
        resolved_path.relative_to(root)
    except ValueError as error:
        raise PermissionError(
            "Доступ к файлам за пределами каталога документов запрещён"
        ) from error

    if not resolved_path.is_file():
        raise ValueError(
            f"Путь не является файлом: {file_path}"
        )

    return resolved_path

def read_text_file(
    path: str | Path,
    max_chars: int = MAX_DOCUMENT_CHARS,
    *,
    base_dir: str | Path = DEFAULT_DOCUMENT_ROOT,
) -> str:
    """
    Читает текстовый файл из разрешённого каталога.

    Текст ограничивается параметром max_chars.
    """
    _validate_max_chars(max_chars)

    resolved_path = _resolve_safe_path(
        file_path=path,
        base_dir=base_dir,
    )

    if resolved_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Формат '{resolved_path.suffix}' "
            "не поддерживается"
        )

    file_size = resolved_path.stat().st_size

    if file_size > MAX_DOCUMENT_BYTES:
        raise ValueError(
            "Размер файла превышает допустимый лимит"
        )

    with resolved_path.open(
        mode="r",
        encoding="utf-8",
        errors="replace",
    ) as file:
        text = file.read(max_chars + 1)

    return text[:max_chars]

def read_document(
    document: dict[str, Any],
    max_chars: int = MAX_DOCUMENT_CHARS,
    *,
    base_dir: str | Path = DEFAULT_DOCUMENT_ROOT,
) -> str:
    """
    Возвращает текст документа.

    Если в документе есть непустое поле extracted_text,
    файл с диска не читается.
    Иначе текст загружается из file_path.
    """
    if not isinstance(document, dict):
        raise TypeError(
            "document должен быть словарём"
        )

    _validate_max_chars(max_chars)

    if "extracted_text" in document:
        extracted_text = document["extracted_text"]

        if extracted_text is not None and not isinstance(
            extracted_text,
            str,
        ):
            raise TypeError(
                "Поле 'extracted_text' должно быть строкой"
            )

        if isinstance(extracted_text, str):
            if extracted_text.strip():
                return extracted_text[:max_chars]

    file_path = document.get("file_path")

    if not file_path:
        raise ValueError(
            "У документа нет extracted_text или file_path"
        )

    return read_text_file(
        path=file_path,
        max_chars=max_chars,
        base_dir=base_dir,
    )
