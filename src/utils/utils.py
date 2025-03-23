import io
import re
import httpx
import magic
import fitz
import tempfile
import subprocess
from pathlib import Path
from typing import List
from loguru import logger
from PIL import Image
from pdf2image import convert_from_bytes
from markitdown_parse.main import convert_office_to_markdown
from qwen_vl_parse.main import parse_image
from utils.config import config

mineru_url_base = config.MINERU_API_URL
mineru_timeout = config.MINERU_API_TIMEOUT

pdf_file_types = [
    "pdf",
]

image_file_types = [
    "png",
    "jpg",
    "jpeg",
]

office_file_types = ["doc", "docx", "pptx", "xlsx"]

magic_file_type_map = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpeg",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}

output_file_types = [
    "markdown",
    "pdf",
    "docx",
]


def detect_file_type(file_bytes, file_name):
    # 使用magic库检测文件类型
    if file_name.endswith(".md") or file_name.endswith(".markdown"):
        return "markdown"

    file_type = magic.Magic(mime=True).from_buffer(file_bytes)
    return magic_file_type_map.get(file_type, None)


def fetch_mineru_api(file_bytes: bytes, file_name: str, return_images: bool):
    url = mineru_url_base + "/pdf_parse"
    headers = {"Content-Type": "application/octet-stream"}
    files = {"pdf_file": (file_name, file_bytes)}
    data = {"return_images": return_images}

    res = httpx.post(url, headers=headers, files=files, data=data, timeout=mineru_timeout)

    res = res.json()
    if return_images:
        return replace_image_with_base64(res["md_content"], res["images"])
    
    return res["md_content"]


def replace_image_with_base64(markdown_text, image_map):
    # 匹配Markdown中的图片标签
    pattern = r'\!\[(?:[^\]]*)\]\(([^)]+)\)'

    # 替换图片链接
    def replace(match):
        relative_path = match.group(1)
        base64_image = image_map.get(relative_path, "")
        return f'![{relative_path}](data:image/jpeg;base64,{base64_image})'

    # 应用替换
    return re.sub(pattern, replace, markdown_text)

def convert_pdf_to_markdown(file_bytes: bytes, file_name: str, use_llm: bool = False, return_images: bool = False):
    # 使用markitdown_parse库将pdf转换为markdown
    if not use_llm:
        return fetch_mineru_api(file_bytes, file_name, return_images)
    else:
        images_bytes = convert_pdf_to_image(file_bytes)
        result_list = []
        for image_bytes in images_bytes:
            result_list.append(parse_image(image_bytes, file_name, return_images))
        return "\n\n".join(result_list)


def convert_image_to_pdf(file_bytes: bytes, file_type: str):
    # 使用fitz库将图片转换为pdf
    pdf_bytes = fitz.open(stream=file_bytes, filetype=file_type).convert_to_pdf()

    return pdf_bytes


def images_to_bytes_readable(
    images: List[Image.Image], format: str = "JPEG"
) -> List[bytes]:
    result = []
    for img in images:
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        result.append(buffer.getvalue())
        buffer.close()
    return result


def convert_pdf_to_image(file_bytes: bytes) -> List[bytes]:
    # 使用fitz库将pdf转换为图片
    image_bytes = convert_from_bytes(file_bytes, dpi=300)
    image_bytes = images_to_bytes_readable(image_bytes)

    return image_bytes

def convert_doc_to_docx(file_bytes: bytes):
    # 使用 LibreOffice 将 DOC 文件转换为 DOCX 格式
    with tempfile.TemporaryDirectory() as temp_dir:
        doc_file = Path(temp_dir) / "temp.doc"
        docx_file = Path(temp_dir) / "temp.docx"
         # 构建命令
        cmd = [
            "soffice",
            '--headless',
            '--convert-to', 'docx',
            '--outdir', doc_file,
            docx_file
        ]
        try:
            # 执行命令
            subprocess.run(cmd, check=True)
            
            return docx_file.read_bytes()
        
        except Exception as e:
            logger.error(f"无法将 DOC 文件转换为 DOCX 格式: {e}")
            raise e


def convert_to_markdown_main(
    file_bytes: bytes,
    file_name: str,
    use_llm: bool = False,
    return_images: bool = False,
):
    # 检测文件类型
    file_type = detect_file_type(file_bytes, file_name)
    if file_type is None:
        raise Exception("Unsupported file type")

    if file_type in pdf_file_types:
        return convert_pdf_to_markdown(file_bytes, file_name, use_llm, return_images=return_images)

    elif file_type in image_file_types:
        if use_llm:
            return parse_image(file_bytes)

        pdf_bytes = convert_image_to_pdf(file_bytes, file_type)
        new_file_name = Path(file_name).with_suffix(".pdf")
        return convert_pdf_to_markdown(pdf_bytes, new_file_name, return_images=return_images)

    else:
        if file_type == "doc":
            file_bytes = convert_doc_to_docx(file_bytes)
            file_type = "docx"

        return convert_office_to_markdown(file_bytes)


def get_mime_type(file_bytes: bytes):
    return magic.Magic(mime=True).from_buffer(file_bytes)
