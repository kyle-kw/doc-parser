import gradio as gr
import base64
from pathlib import Path

from utils.utils import convert_to_markdown_main, detect_file_type
# from pandoc_convert.main import convert_markdown_to_new

def process_file(file_obj, use_llm=False):
    """处理上传的文件并转换为Markdown"""
    if file_obj is None:
        return "请上传文件", None
    
    # 读取文件内容
    file_path = Path(file_obj)
    file_bytes = file_path.read_bytes()
    file_name = file_path.name

    file_type = detect_file_type(file_bytes, file_name)
    if file_type is None or file_type == "markdown":
        raise gr.Error("不支持的文件类型")
    
    # 调用您已经实现的函数
    markdown_text = convert_to_markdown_main(
        file_bytes=file_bytes,
        file_name=file_name,
        use_llm=use_llm,
        return_images=True
    )
    
    return markdown_text, markdown_text

def create_download_link(markdown_text):
    """创建Markdown文件的下载链接"""
    if not markdown_text:
        return None
    
    # 将Markdown文本转换为字节
    markdown_bytes = markdown_text.encode('utf-8')
    
    # 创建base64编码的下载链接
    b64 = base64.b64encode(markdown_bytes).decode()
    href = f"data:text/markdown;base64,{b64}"
    
    return href

# 创建Gradio界面
with gr.Blocks() as app:
    gr.Markdown("# 文件转Markdown转换器")
    gr.Markdown("上传文件，将自动转换为Markdown格式。支持PDF、PNG、JPG、JPEG、DOC、DOCX、PPTX、XLSX等格式。")
    
    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="上传文件")
            use_llm_checkbox = gr.Checkbox(label="使用LLM解析", value=False)
            convert_btn = gr.Button("转换为Markdown", variant="primary")
        
        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.TabItem("预览"):
                    markdown_output = gr.Markdown(label="Markdown预览", min_height="600px")
                with gr.TabItem("源码"):
                    text_output = gr.Textbox(label="Markdown源码", lines=20)
            
            with gr.Row():
                copy_btn = gr.Button("复制Markdown", variant="secondary")
                download_btn = gr.Button("下载Markdown文件", variant="secondary")
    
    # 处理转换逻辑
    convert_btn.click(
        fn=process_file,
        inputs=[file_input, use_llm_checkbox],
        outputs=[markdown_output, text_output]
    )
    
    # 复制按钮逻辑
    copy_btn.click(
        fn=lambda x: x,
        inputs=[text_output],
        outputs=[],
        js="""
        function(text) {
            if (!text) {
                alert("没有可复制的内容！");
                return;
            }
            navigator.clipboard.writeText(text);
            alert("已复制到剪贴板！");
            return text;
        }
        """
    )
    
    # 下载按钮逻辑
    download_btn.click(
        fn=create_download_link,
        inputs=[text_output],
        outputs=[],
        js="""
        function(href) {
            if (!href) {
                alert("没有可下载的内容！");
                return;
            }
            const a = document.createElement('a');
            a.href = href;
            a.download = 'converted_markdown.md';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
        """
    )

# 启动应用
if __name__ == "__main__":
    app.launch()