import subprocess
import tempfile
from pathlib import Path
from loguru import logger


def convert_markdown_to_docx(file_bytes: bytes) -> bytes:
    # 使用 pandoc 将 markdown 转换为 docx
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建临时文件
        input_file = Path(temp_dir) / "input.md"
        input_file.write_bytes(file_bytes)
        temp_file = Path(temp_dir) / "temp.docx"
        cmd = [
            "pandoc",
            "--from=markdown",
            "--to=docx",
            "-V", "CJKmainfont=Microsoft YaHei",
            "-o", temp_file,
            input_file
        ]
        try:
            # 执行命令
            subprocess.run(cmd, check=True)
            return temp_file.read_bytes()
        
        except Exception as e:
            logger.error(f"无法将 markdown 文件转换为 DOCX 格式: {e}")
            raise e


def convert_markdown_to_pdf(file_bytes: bytes) -> bytes:
    # 使用 pandoc 将 markdown 转换为 pdf
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建临时文件
        input_file = Path(temp_dir) / "input.md"
        input_file.write_bytes(file_bytes)
        temp_file = Path(temp_dir) / "temp.pdf"
        cmd = [
            "pandoc",
            "--from=markdown",
            "--to=pdf",
            "--pdf-engine=typst",
            "-V", "CJKmainfont=Microsoft YaHei",
            "-V", "fontsize=14pt",
            "-o", temp_file,
            input_file
        ]
        try:
            # 执行命令
            subprocess.run(cmd, check=True)
            return temp_file.read_bytes()
        
        except Exception as e:
            logger.error(f"无法将 markdown 文件转换为 PDF 格式: {e}")
            raise e


def convert_markdown_to_new(file_bytes: bytes, convert_to: str) -> bytes:
    # 将 markdown 文件转换为指定格式
    if convert_to == "docx":
        return convert_markdown_to_docx(file_bytes)
    elif convert_to == "pdf":
        return convert_markdown_to_pdf(file_bytes)
    else:
        raise ValueError(f"不支持的转换格式: {convert_to}")

