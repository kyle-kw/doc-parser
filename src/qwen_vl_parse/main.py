import base64
import io
import re
from io import BytesIO

from bs4 import BeautifulSoup, Tag
from openai import OpenAI
from PIL import Image
from qwen_vl_utils import smart_resize
from utils.config import config

API_KEY = config.API_KEY
BASE_URL = config.BASE_URL
MODEL_NAME = config.MODEL_NAME

system_prompt = "You are an AI specialized in recognizing and extracting text from images. Your mission is to analyze the image document and generate the result in QwenVL Document Parser HTML format using specified tags while data integrity."

prompt = "QwenVL HTML "
min_pixels = config.min_pixels
max_pixels = config.max_pixels


client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


# Function to draw bounding boxes and text on images based on HTML content
def save_images(image, resized_width, resized_height, full_predict):
    original_width = image.width
    original_height = image.height

    # Parse the provided HTML content
    soup = BeautifulSoup(full_predict, "html.parser")

    # Draw bounding boxes and text for each element
    image_number = 1
    image_path_list = {}
    for element in soup.find_all("img", attrs={"data-bbox": True}):
        parent_bbox_str = element.parent["data-bbox"]
        bbox_str = element["data-bbox"]
        if parent_bbox_str == bbox_str and element.parent.find_all("div"):
            element.decompose()
            continue

        x1, y1, x2, y2 = map(int, bbox_str.split())

        # Calculate scaling factors
        scale_x = resized_width / original_width
        scale_y = resized_height / original_height

        # Scale coordinates accordingly
        x1_resized = int(x1 / scale_x)
        y1_resized = int(y1 / scale_y)
        x2_resized = int(x2 / scale_x)
        y2_resized = int(y2 / scale_y)

        if x1_resized > x2_resized:
            x1_resized, x2_resized = x2_resized, x1_resized
        if y1_resized > y2_resized:
            y1_resized, y2_resized = y2_resized, y1_resized

        cropped_image = image.crop((x1_resized, y1_resized, x2_resized, y2_resized))
        image_path = f"img-{image_number}.jpg"
        # cropped_image.save(image_path)

        buffer = io.BytesIO()
        cropped_image.save(buffer, format=format)
        image_path_list[image_path] = encode_image(buffer.getvalue())
        buffer.close()

        element["src"] = image_path

        image_number += 1

    return soup, image_path_list


# Function to clean and format HTML content
def clean_and_format_html(soup: BeautifulSoup):
    # soup = BeautifulSoup(full_predict, "html.parser")

    # Regular expression pattern to match 'color' styles in style attributes
    color_pattern = re.compile(r"\bcolor:[^;]+;?")

    # Find all tags with style attributes and remove 'color' styles
    for tag in soup.find_all(style=True):
        original_style = tag.get("style", "")
        new_style = color_pattern.sub("", original_style)
        if not new_style.strip():
            del tag["style"]
        else:
            new_style = new_style.rstrip(";")
            tag["style"] = new_style

    # Remove 'data-bbox' and 'data-polygon' attributes from all tags
    for attr in ["data-bbox", "data-polygon"]:
        for tag in soup.find_all(attrs={attr: True}):
            del tag[attr]

    classes_to_update = ["formula.machine_printed", "formula.handwritten"]
    # Update specific class names in div tags
    for tag in soup.find_all(class_=True):
        if isinstance(tag, Tag) and "class" in tag.attrs:
            new_classes = [
                cls if cls not in classes_to_update else "formula"
                for cls in tag.get("class", [])
            ]
            tag["class"] = list(
                dict.fromkeys(new_classes)
            )  # Deduplicate and update class names

    # Clear contents of divs with specific class names and rename their classes
    for div in soup.find_all("div", class_="image caption"):
        div.clear()
        div["class"] = ["image"]

    classes_to_clean = ["music sheet", "chemical formula", "chart"]
    # Clear contents and remove 'format' attributes of tags with specific class names
    for class_name in classes_to_clean:
        for tag in soup.find_all(class_=class_name):
            if isinstance(tag, Tag):
                tag.clear()
                if "format" in tag.attrs:
                    del tag["format"]

    # Manually build the output string
    output = []
    for child in soup.body.children:
        if isinstance(child, Tag):
            output.append(str(child))
            output.append("\n")  # Add newline after each top-level element
        elif isinstance(child, str) and not child.strip():
            continue  # Ignore whitespace text nodes
    complete_html = f"""```html\n<html><body>\n{" ".join(output)}</body></html>\n```"""
    return complete_html


#  base 64 编码格式
def encode_image(image):
    if isinstance(image, str):
        with open(image, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    elif isinstance(image, bytes):
        return base64.b64encode(image).decode("utf-8")


def inference_with_api(
    image_url,
    prompt=prompt,
    sys_prompt=system_prompt,
    model_id=MODEL_NAME,
    min_pixels=512 * 28 * 28,
    max_pixels=2048 * 28 * 28,
):
    messages = [
        {"role": "system", "content": [{"type": "text", "text": sys_prompt}]},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "min_pixels": min_pixels,
                    "max_pixels": max_pixels,
                    "image_url": {"url": image_url},
                },
                {"type": "text", "text": prompt},
            ],
        },
    ]
    completion = client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=8192,
        # temperature=0.6,
        timeout=3600,
    )
    return completion.choices[0].message.content


def html_to_markdown(html_content):
    """
    将 HTML 转换为 Markdown

    参数:
        html_content (str): HTML 内容

    返回:
        str: 转换后的 Markdown 内容
    """
    # 创建 BeautifulSoup 对象
    soup = BeautifulSoup(html_content, "html.parser")

    # 移除 script 和 style 标签
    for script in soup(["script", "style"]):
        script.extract()

    # 初始化 Markdown 内容
    markdown_content = ""

    # 递归处理 HTML 元素
    def process_element(element):
        nonlocal markdown_content

        # 如果是字符串，直接添加
        if isinstance(element, str):
            markdown_content += element
            return

        # 处理不同类型的标签
        tag_name = element.name

        if tag_name is None:
            # 处理纯文本
            text = element.string
            if text:
                markdown_content += text

        elif tag_name == "h1":
            markdown_content += f"# {element.get_text().strip()}\n\n"

        elif tag_name == "h2":
            markdown_content += f"## {element.get_text().strip()}\n\n"

        elif tag_name == "h3":
            markdown_content += f"### {element.get_text().strip()}\n\n"

        elif tag_name == "h4":
            markdown_content += f"#### {element.get_text().strip()}\n\n"

        elif tag_name == "h5":
            markdown_content += f"##### {element.get_text().strip()}\n\n"

        elif tag_name == "h6":
            markdown_content += f"###### {element.get_text().strip()}\n\n"

        elif tag_name == "p":
            markdown_content += f"{element.get_text().strip()}\n\n"

        elif tag_name == "a":
            href = element.get("href", "")
            text = element.get_text().strip()
            markdown_content += f"[{text}]({href})"

        elif tag_name == "img":
            alt = element.get("alt", "")
            src = element.get("src", "")
            markdown_content += f"![{alt}]({src})"

        elif tag_name == "div":
            # 处理 div 内的内容
            for child in element.children:
                process_element(child)
            markdown_content += "\n"

        elif tag_name == "table":
            # 处理表格头部
            headers = []
            header_row = element.find("thead")
            if header_row:
                for th in header_row.find_all("th"):
                    headers.append(th.get_text().strip())
            else:
                # 如果没有 thead，尝试从第一行获取标题
                first_row = element.find("tr")
                if first_row:
                    for th in first_row.find_all(["th", "td"]):
                        headers.append(th.get_text().strip())

            if headers:
                markdown_content += "| " + " | ".join(headers) + " |\n"
                markdown_content += "| " + " | ".join(["---"] * len(headers)) + " |\n"

            # 处理表格内容
            tbody = element.find("tbody") or element
            rows = tbody.find_all("tr")

            # 如果我们已经处理了第一行作为标题，并且没有 thead，跳过第一行
            start_idx = 1 if not element.find("thead") and headers else 0

            for row in rows[start_idx:]:
                cells = []
                for cell in row.find_all(["td", "th"]):
                    cells.append(cell.get_text().strip())
                if cells:
                    markdown_content += "| " + " | ".join(cells) + " |\n"

            markdown_content += "\n"

        elif tag_name == "ul":
            for li in element.find_all("li", recursive=False):
                markdown_content += f"* {li.get_text().strip()}\n"
            markdown_content += "\n"

        elif tag_name == "ol":
            for i, li in enumerate(element.find_all("li", recursive=False), 1):
                markdown_content += f"{i}. {li.get_text().strip()}\n"
            markdown_content += "\n"

        elif tag_name == "blockquote":
            lines = element.get_text().strip().split("\n")
            for line in lines:
                markdown_content += f"> {line}\n"
            markdown_content += "\n"

        elif tag_name == "pre":
            code = element.get_text().strip()
            markdown_content += f"```\n{code}\n```\n\n"

        elif tag_name == "code":
            code = element.get_text().strip()
            markdown_content += f"`{code}`"

        elif tag_name == "br":
            markdown_content += "\n"

        elif tag_name == "hr":
            markdown_content += "---\n\n"

        elif tag_name == "strong" or tag_name == "b":
            markdown_content += f"**{element.get_text().strip()}**"

        elif tag_name == "em" or tag_name == "i":
            markdown_content += f"*{element.get_text().strip()}*"

        elif tag_name == "address":
            address_text = element.get_text().strip()
            markdown_content += f"*{address_text}*\n\n"

        else:
            # 递归处理其他标签的子元素
            for child in element.children:
                process_element(child)

    # 处理整个文档
    for element in soup.body.children:
        process_element(element)

    # 清理多余的空行
    markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

    return markdown_content.strip()


def replace_image_with_base64(markdown_text, image_map):
    # 匹配Markdown中的图片标签
    pattern = r"\!\[(?:[^\]]*)\]\(([^)]+)\)"

    # 替换图片链接
    def replace(match):
        relative_path = match.group(1)
        base64_image = image_map.get(relative_path, "")
        return f"![{relative_path}](data:image/jpeg;base64,{base64_image})"

    # 应用替换
    return re.sub(pattern, replace, markdown_text)


def parse_image(
    image_bytes: bytes, image_name: str = None, return_images: bool = False
):
    image = Image.open(BytesIO(image_bytes))
    width, height = image.size
    input_height, input_width = smart_resize(
        height, width, min_pixels=min_pixels, max_pixels=max_pixels
    )
    image_url = build_image_url(image_bytes, image_name)
    output = inference_with_api(
        image_url,
        prompt,
        sys_prompt=system_prompt,
        min_pixels=min_pixels,
        max_pixels=max_pixels,
    )

    # print(output)
    soup, image_map = save_images(image, input_width, input_height, output)
    ordinary_html = clean_and_format_html(soup)
    markdown_result = html_to_markdown(ordinary_html)
    if return_images:
        return replace_image_with_base64(markdown_result, image_map).strip()

    return markdown_result.strip()


def build_image_url(image_bytes: bytes, image_name: str = None):
    base64_image = encode_image(image_bytes)
    if image_name is not None:
        if image_name.endswith("png"):
            image_format = "png"
        elif image_name.endswith("jpeg"):
            image_format = "jpeg"
        elif image_name.endswith("jpg"):
            image_format = "jpeg"
        elif image_name.endswith("webp"):
            image_format = "webp"
    else:
        image_format = "jpeg"

    return f"data:image/{image_format};base64,{base64_image}"


def demo():
    image_path = "/root/projects/py-lab/qwen2.5-vl-gradio/image_test/test2.png"
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    markdown_result, image_path_list = parse_image(image_bytes)
    print(markdown_result)
    print(image_path_list)


if __name__ == "__main__":
    demo()
