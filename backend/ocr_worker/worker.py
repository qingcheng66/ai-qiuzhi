"""OCR Worker — 用 Python 3.12 独立环境运行 PaddleOCR

FastAPI 主进程（Python 3.14）通过 subprocess 调用此脚本。
传入 base64 图片数据，返回 JSON 识别结果。

用法：
  .venv/bin/python ocr_worker/worker.py <base64_string>
"""
import json
import sys
import base64

from PIL import Image
from paddleocr import PaddleOCR

# 全局初始化一次（模型加载缓存）
_ocr = PaddleOCR(
    text_det_limit_side_len=960,
    text_det_thresh=0.2,
    text_det_box_thresh=0.2,
    text_det_unclip_ratio=1.5,
    text_rec_score_thresh=0.3,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
)


def recognize(image_b64: str) -> str:
    img_bytes = base64.b64decode(image_b64)
    # 保存到临时文件供 PaddleOCR 读取
    tmp = "/tmp/ocr_input.jpg"
    with open(tmp, "wb") as f:
        f.write(img_bytes)

    result = _ocr.predict(tmp)
    lines = []
    for res in result:
        texts = res.get("rec_texts", [])
        scores = res.get("rec_scores", [])
        for t, s in zip(texts, scores):
            if s >= 0.3 and t.strip():
                lines.append(t.strip())
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "需要 base64 参数"}))
        sys.exit(1)
    try:
        text = recognize(sys.argv[1])
        print(json.dumps({"text": text}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)