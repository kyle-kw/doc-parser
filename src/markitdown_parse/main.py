from io import BytesIO

from markitdown import MarkItDown


def convert_office_to_markdown(file: bytes) -> str:
    md = MarkItDown(enable_plugins=False)
    result = md.convert(BytesIO(file))
    return result.markdown


