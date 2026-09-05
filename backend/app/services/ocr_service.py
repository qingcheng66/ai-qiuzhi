"""OCR 服务：PaddleOCR（Python 3.12 独立进程）→ MinerU → 百度 OCR → 腾讯 OCR → 降级

PaddleOCR 通过 ocr_worker/.venv （Python 3.12）中的 worker.py 子进程调用。
"""
import base64
import io
import json
import os
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Protocol

import httpx

from app.config import settings

OCR_TIMEOUT = 180
POLL_INTERVAL = 3

WORKER_PY = str(Path(__file__).resolve().parent.parent.parent / "ocr_worker" / "worker.py")
WORKER_VENV_PYTHON = str(Path(__file__).resolve().parent.parent.parent / "ocr_worker" / ".venv" / "bin" / "python")


class OCRUnavailable(Exception):
    pass


class OCRProvider(Protocol):
    name: str

    def recognize(self, image_b64: str) -> str:
        ...


# ---------- PaddleOCR（Python 3.12 独立进程）----------


class PaddleOCRProvider:
    name = "paddleocr"

    def recognize(self, image_b64: str) -> str:
        if not os.path.exists(WORKER_VENV_PYTHON):
            raise OCRUnavailable("PaddleOCR 环境未初始化")
        proc = subprocess.run(
            [WORKER_VENV_PYTHON, WORKER_PY, image_b64],
            capture_output=True, text=True, timeout=OCR_TIMEOUT,
        )
        if proc.returncode != 0:
            raise OCRUnavailable(f"PaddleOCR 识别失败: {proc.stderr[:200]}")
        data = json.loads(proc.stdout)
        if "error" in data:
            raise OCRUnavailable(f"PaddleOCR 错误: {data['error']}")
        text = data.get("text", "").strip()
        if not text:
            raise OCRUnavailable("PaddleOCR 未识别到文字")
        return text


# ---------- MinerU（精准 API，限 PDF 文档）----------


class MinerUProvider:
    name = "mineru"

    def __init__(self):
        self._token = settings.mineru_ocr_token
        self._base = "https://mineru.net"
        # 禁用系统代理（防止 SOCKS 环境变量干扰）
        self._client = httpx.Client(timeout=30, transport=httpx.HTTPTransport(proxy=None))

    def recognize(self, image_b64: str) -> str:
        # 图片转 PDF → 上传 MinerU
        pdf_bytes = self._img_to_pdf(image_b64)
        return self._parse_pdf(pdf_bytes)

    def _img_to_pdf(self, image_b64: str) -> bytes:
        """把 base64 图片转为扫描 PDF"""
        import pymupdf

        img_bytes = base64.b64decode(image_b64)
        img = pymupdf.open(stream=img_bytes, filetype="jpeg")
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        # 保持比例居中
        iw, ih = img[0].rect.width, img[0].rect.height
        scale = min(595 / iw, 842 / ih) * 0.95
        pw, ph = iw * scale, ih * scale
        x0, y0 = (595 - pw) / 2, (842 - ph) / 2
        page.insert_image(pymupdf.Rect(x0, y0, x0 + pw, y0 + ph), stream=img_bytes)
        pdf = doc.write(garbage=4, deflate=True)
        doc.close()
        img.close()
        return pdf

    def _parse_pdf(self, pdf_bytes: bytes) -> str:
        """上传 PDF 到 MinerU 并返回 Markdown 文本"""
        batch_id, file_url = self._apply_upload()
        self._upload_file(file_url, pdf_bytes)
        return self._poll_result(batch_id)

    def _apply_upload(self) -> tuple[str, str]:
        resp = self._client.post(
            f"{self._base}/api/v4/file-urls/batch",
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
            json={
                "files": [{"name": "doc.pdf", "is_ocr": True}],
                "model_version": settings.mineru_ocr_model or "pipeline",
                "language": "ch",
                "no_cache": True,
            },
        )
        data = resp.json()
        if data.get("code") != 0:
            raise OCRUnavailable(f"MinerU 申请上传失败: {data.get('msg', 'unknown')}")
        return data["data"]["batch_id"], data["data"]["file_urls"][0]

    def _upload_file(self, url: str, data: bytes):
        resp = self._client.put(url, content=data)
        if resp.status_code not in (200, 201):
            raise OCRUnavailable(f"MinerU 文件上传失败 HTTP {resp.status_code}")

    def _poll_result(self, batch_id: str) -> str:
        deadline = time.time() + OCR_TIMEOUT
        while time.time() < deadline:
            time.sleep(POLL_INTERVAL)
            resp = self._client.get(
                f"{self._base}/api/v4/extract-results/batch/{batch_id}",
                headers={"Authorization": f"Bearer {self._token}"},
            )
            d = resp.json()
            result = d["data"]["extract_result"][0]
            state = result["state"]
            if state == "done":
                zip_url = result["full_zip_url"]
                return self._extract_md(zip_url)
            if state == "failed":
                raise OCRUnavailable(f"MinerU 解析失败: {result.get('err_msg', 'unknown')}")
        raise OCRUnavailable(f"MinerU 解析超时 ({OCR_TIMEOUT}s)")

    def _extract_md(self, zip_url: str) -> str:
        zip_resp = self._client.get(zip_url)
        z = zipfile.ZipFile(io.BytesIO(zip_resp.content))
        # 优先读 full.md（MinerU 标准输出）
        if "full.md" in z.namelist():
            md = z.read("full.md").decode("utf-8")
            # 去除纯图片引用行
            lines = [l for l in md.splitlines() if not l.strip().startswith("![](")]
            text = "\n".join(lines).strip()
            if text:
                return text
        # 尝试从 content_list 提取文本
        for name in z.namelist():
            if "content_list" in name and "v2" not in name:
                cl = json.loads(z.read(name))
                texts = []
                for item in cl if isinstance(cl, list) else [cl]:
                    t = item.get("type", "")
                    txt = item.get("text", "") or item.get("content", {}).get("text", "") if isinstance(item.get("content"), dict) else ""
                    if t == "text" and txt:
                        texts.append(txt)
                if texts:
                    return "\n".join(texts)
        raise OCRUnavailable("MinerU 未提取到文本内容")


# ---------- 百度 OCR ----------


class BaiduOCR:
    name = "baidu"

    def _token(self) -> str:
        resp = httpx.post(
            "https://aip.baidubce.com/oauth/2.0/token",
            params={"grant_type": "client_credentials", "client_id": settings.baidu_ocr_api_key, "client_secret": settings.baidu_ocr_secret_key},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def recognize(self, image_b64: str) -> str:
        token = self._token()
        resp = httpx.post(
            "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic",
            params={"access_token": token},
            data={"image": image_b64},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return "\n".join(w["words"] for w in data.get("words_result", []))


# ---------- 腾讯 OCR ----------


class TencentOCR:
    name = "tencent"

    def recognize(self, image_b64: str) -> str:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.ocr.v20181119 import ocr_client, models

        cred = credential.Credential(settings.tencent_ocr_secret_id, settings.tencent_ocr_secret_key)
        cp = ClientProfile(httpProfile=HttpProfile(endpoint="ocr.tencentcloudapi.com"))
        client = ocr_client.OcrClient(cred, "", cp)
        req = models.GeneralBasicOCRRequest()
        req.ImageBase64 = image_b64
        resp = client.GeneralBasicOCR(req)
        return "\n".join(i.Text.strip() for i in resp.TextDetections)


# ---------- Mock ----------


class MockOCR:
    name = "none"

    def recognize(self, image_b64: str) -> str:
        raise OCRUnavailable("OCR 未配置：请在设置中填写 MinerU Token 或百度/腾讯 OCR 的 API Key")


# ---------- 工厂 ----------


def get_ocr_provider() -> OCRProvider:
    """返回当前可用的 OCR provider（用于前端显示 provider 名）"""
    if os.path.exists(WORKER_VENV_PYTHON):
        return PaddleOCRProvider()
    if settings.mineru_ocr_token:
        return MinerUProvider()
    if settings.baidu_ocr_api_key and settings.baidu_ocr_secret_key:
        return BaiduOCR()
    if settings.tencent_ocr_secret_id and settings.tencent_ocr_secret_key:
        return TencentOCR()
    return MockOCR()


def ocr_image_bytes(image_bytes: bytes) -> str:
    """识别图片文字。

    优先级：PaddleOCR(本地) > MinerU(PDF) > 百度OCR > 腾讯OCR > Mock
    """
    image_b64 = base64.b64encode(image_bytes).decode()

    # 1) PaddleOCR（本地 Python 3.12 独立进程）
    if os.path.exists(WORKER_VENV_PYTHON):
        try:
            return PaddleOCRProvider().recognize(image_b64)
        except OCRUnavailable:
            pass

    # 2) MinerU（优先处理 PDF）
    if settings.mineru_ocr_token:
        try:
            return MinerUProvider().recognize(image_b64)
        except OCRUnavailable:
            pass

    # 3) 百度 OCR
    if settings.baidu_ocr_api_key and settings.baidu_ocr_secret_key:
        return BaiduOCR().recognize(image_b64)

    # 4) 腾讯 OCR
    if settings.tencent_ocr_secret_id and settings.tencent_ocr_secret_key:
        return TencentOCR().recognize(image_b64)

    # 5) 全部未配置
    raise OCRUnavailable("OCR 未配置：请安装 PaddleOCR 或配置百度/腾讯 OCR 的 API Key")