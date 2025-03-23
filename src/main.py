from io import BytesIO
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse

from utils.utils import convert_to_markdown_main, get_mime_type
from pandoc_convert.main import convert_markdown_to_new

app = FastAPI()


@app.get("/")
@app.get("/ping")
def ping():
    return "pong"


@app.post("/v1/convert")
def convert(
    file: UploadFile = File(...),
    return_images: bool = Form(False),
    use_llm: bool = Form(False),
):
    file_bytes = file.file.read()
    file_name = file.filename

    try:
        res = convert_to_markdown_main(file_bytes, file_name, use_llm, return_images)

        return JSONResponse(content={"code": 200, "data": res})

    except Exception as e:
        return JSONResponse(content={"code": 400, "error": str(e)}, status_code=400)


@app.post("/v1/markdown")
def convert_to_new(
    file: UploadFile = File(...),
    convert_to: str = Form("docx"),
):
    file_bytes = file.file.read()
    file_name = file.filename
    return_name = Path(file_name).with_suffix(f".{convert_to}")

    try:
        res = convert_markdown_to_new(file_bytes, convert_to)
        return StreamingResponse(
            content=BytesIO(res),
            media_type=get_mime_type(res),
            headers={"Content-Disposition": f'attachment; filename="{return_name}"'},
        )
    except Exception as e:
        return JSONResponse(content={"code": 400, "error": str(e)}, status_code=400)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
