"""
Everything the OCR scripts need from HunyuanOCR, in one place: finding a Python that can load the model, loading it,
running one image through it, and parsing its ``word(x1,y1),(x2,y2)`` output. No other project is imported.

Which transformers and which checkpoint
--------------------------------------
* transformers >= 5.13 (pip release) ships ``HunYuanVLForConditionalGeneration``. That is the normal install:
  ``pip install -r requirements.txt`` into a venv. The 4.57.1.dev0 HunYuanVL pull-request build on the original
  workstation works too.
* The Hub checkpoint is pinned to PINNED_REVISION, the last commit before tencent/HunyuanOCR was reformatted on
  2026-09-10. Tested 2026-09-15 on the Vancouver tile: the reformatted ``main`` checkpoint (under transformers 5.17)
  answered "not answerable" on one tile and looped to the cap on another where the pinned revision reads normally in
  both transformers builds. ``HUNYUAN_REVISION=main`` (or ``--revision main``) tries the current checkpoint instead.

Which Python runs the OCR scripts
---------------------------------
``ensure_hunyuan_python()`` is called first thing by fim_tile_ocr.py / fim_hunyuan.py / fim_rotation_probe.py. If the
current interpreter has HunYuanVL it returns; otherwise it re-executes the script under the first of
``$HUNYUAN_PY``, ``<repo>/.venv/bin/python``, ``~/projects/hunyuan/hunyuanocr/bin/python`` that does. So
``python3 scripts/fim_tile_ocr.py ...`` works from any shell once a venv exists.
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PINNED_REVISION = "f6af82ee007fe6091b29fb3bb287b491ead41c82"  # last pre-reformat checkpoint; reads better than main (see module doc)
MIN_NATIVE_TRANSFORMERS = (5, 13)  # first pip release with HunYuanVL


def _transformers_version() -> tuple[int, ...] | None:
    try:
        import transformers
    except ImportError:
        return None
    return tuple(int(x) for x in re.findall(r"\d+", transformers.__version__)[:2])


def has_hunyuan() -> bool:
    try:
        from transformers import HunYuanVLForConditionalGeneration  # noqa: F401
        return True
    except ImportError:
        return False


def default_revision() -> str | None:
    """Hub revision to load: HUNYUAN_REVISION if set ('main' = the current checkpoint), else the pinned known-good commit."""
    env = os.environ.get("HUNYUAN_REVISION")
    if env:
        return None if env.lower() in ("main", "none") else env
    return PINNED_REVISION


DEFAULT_REVISION = default_revision()


def candidate_pythons() -> list[Path]:
    c = []
    if os.environ.get("HUNYUAN_PY"):
        c.append(Path(os.environ["HUNYUAN_PY"]).expanduser())
    c.append(PROJECT_ROOT / ".venv" / "bin" / "python")
    c.append(Path(os.environ.get("HUNYUAN_SRC", "~/projects/hunyuan")).expanduser() / "hunyuanocr" / "bin" / "python")
    return c


def ensure_hunyuan_python() -> None:
    """Re-exec the running script under a Python that has HunYuanVL, unless this one does."""
    if has_hunyuan():
        return
    if os.environ.get("FIM_HUNYUAN_REEXEC") == "1":
        sys.exit("error: re-executed under a Python that still has no HunYuanVLForConditionalGeneration; "
                 "install transformers>=5.13 there (pip install -r requirements.txt)")
    for py in candidate_pythons():
        if py.is_file():
            os.environ["FIM_HUNYUAN_REEXEC"] = "1"
            os.execv(str(py), [str(py), *sys.argv])
    sys.exit("error: this Python's transformers has no HunYuanVLForConditionalGeneration and no venv was found.\n"
             "  Create one:   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
             "  or point HUNYUAN_PY at a python that has transformers>=5.13 (see README, Setup).")


def load_hunyuan(model_name: str, attn: str = "sdpa", revision: str | None = DEFAULT_REVISION) -> tuple[Any, Any]:
    import torch
    from transformers import AutoProcessor, HunYuanVLForConditionalGeneration

    rev = {"revision": revision} if revision else {}
    fast = os.environ.get("HUNYUAN_FAST_PROCESSOR", "0") == "1"
    processor = AutoProcessor.from_pretrained(model_name, use_fast=fast, **rev)

    if torch.cuda.is_available():
        device_map = "auto"
    elif torch.backends.mps.is_available():
        device_map = {"": "mps"}
    else:
        device_map = "auto"  # CPU fallback

    model = HunYuanVLForConditionalGeneration.from_pretrained(
        model_name, attn_implementation=attn, dtype=torch.bfloat16, device_map=device_map, **rev
    ).eval()
    # Vision blocks can be left with config._attn_implementation = None -> KeyError: None in generate.
    for module in model.modules():
        mc = getattr(module, "config", None)
        if mc is not None and getattr(mc, "_attn_implementation", "unset") is None:
            mc._attn_implementation = attn
    return model, processor


# ------------------------------------------------------------------------------------------------ images
def load_pil(path: Path) -> Image.Image:
    """Open an image (or the first page of a PDF, if pdf2image is installed) as RGB."""
    Image.MAX_IMAGE_PIXELS = None
    if path.suffix.lower() == ".pdf":
        from pdf2image import convert_from_path
        pages = convert_from_path(str(path))
        if not pages:
            raise ValueError(f"No pages from PDF: {path}")
        return pages[0].convert("RGB")
    return Image.open(path).convert("RGB")


def resize_max_edge(img: Image.Image, max_edge: int) -> tuple[Image.Image, tuple[int, int]]:
    w, h = img.size
    if max(w, h) <= max_edge:
        return img, (w, h)
    r = max_edge / max(w, h)
    return img.resize((int(w * r), int(h * r)), Image.Resampling.LANCZOS), (w, h)


# ------------------------------------------------------------------------------------------------ inference
def clean_repeated_substrings(text: str) -> str:
    """Trim pathological repetition at the end of long generations (the model loops when it hits the cap)."""
    n = len(text)
    if n < 8000:
        return text
    for length in range(2, n // 10 + 1):
        candidate = text[-length:]
        count, i = 0, n - length
        while i >= 0 and text[i: i + length] == candidate:
            count += 1
            i -= length
        if count >= 10:
            return text[: n - length * (count - 1)]
    return text


def _cuda_snapshot() -> dict[str, Any] | None:
    import torch
    if not torch.cuda.is_available():
        return None
    devs = []
    for i in range(torch.cuda.device_count()):
        devs.append({"index": i, "name": torch.cuda.get_device_name(i), "allocated_bytes": torch.cuda.memory_allocated(i),
                     "reserved_bytes": torch.cuda.memory_reserved(i), "max_allocated_bytes": torch.cuda.max_memory_allocated(i)})
    return {"device_count": len(devs), "devices": devs}


def hunyuan_infer_one(*, model, processor, image_pil: Image.Image, image_path: Path, user_prompt: str,
                      max_new_tokens: int) -> tuple[str, dict[str, Any]]:
    """One image + prompt -> (model text, metadata). Greedy decoding. Metadata keys are what the fim_* scripts record."""
    import torch

    messages = [{"role": "system", "content": ""},
                {"role": "user", "content": [{"type": "image", "image": str(Path(image_path).resolve())},
                                             {"type": "text", "text": user_prompt}]}]
    t0 = time.perf_counter()
    text_in = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text_in], images=image_pil, padding=True, return_tensors="pt")
    w, h = image_pil.size
    pw = ph = None
    pv = getattr(inputs, "pixel_values", None)
    if pv is not None and hasattr(pv, "shape") and len(pv.shape) >= 4 and 8 <= pv.shape[-2] <= 8192 and 8 <= pv.shape[-1] <= 8192:
        ph, pw = int(pv.shape[-2]), int(pv.shape[-1])
    if pw is None:
        pw, ph = w, h
    inputs = inputs.to(next(model.parameters()).device)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    t1 = time.perf_counter()
    n_in = int(inputs["input_ids"].shape[-1])
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, use_cache=True,
                             pad_token_id=processor.tokenizer.eos_token_id)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    t2 = time.perf_counter()
    cuda = _cuda_snapshot()
    trimmed = [o[len(i):] for i, o in zip(inputs["input_ids"], out)]
    raw = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    t3 = time.perf_counter()
    text = clean_repeated_substrings(raw[0] if raw else "")
    n_total = int(out.shape[-1])
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    meta = {
        "processed_width": pw, "processed_height": ph, "image_width_pixels": w, "image_height_pixels": h,
        "scale_x": w / pw if pw else None, "scale_y": h / ph if ph else None,
        "input_tokens": n_in, "output_tokens": n_total - n_in, "total_tokens": n_total,
        "compute": {"prepare_elapsed_seconds": round(t1 - t0, 6), "generate_elapsed_seconds": round(t2 - t1, 6),
                    "decode_elapsed_seconds": round(t3 - t2, 6), "cuda": {"during_and_after_generate": cuda}},
        "generation": {"do_sample": False, "max_new_tokens": max_new_tokens},
    }
    return text, meta


# ------------------------------------------------------------------------------------------------ output parsing
# HunyuanOCR text spotting: each region is ``label(x1,y1),(x2,y2)`` in 0-1000 coordinates of the fed image.
SPOTTING_BOX_PATTERN = re.compile(r"([^(]*?)\((\d+),(\d+)\),\((\d+),(\d+)\)", re.DOTALL)


def extract_elements(content: str, scale_x: float = 1.0, scale_y: float = 1.0) -> tuple[list[tuple[int, int, int, int]], list[str]]:
    """Parse the model string -> ([(x1,y1,x2,y2), ...], [text, ...]); boxes are normalised so x1<=x2, y1<=y2."""
    coords, texts = [], []
    for m in SPOTTING_BOX_PATTERN.findall(content):
        x1, y1, x2, y2 = (int(m[1]) * scale_x, int(m[2]) * scale_y, int(m[3]) * scale_x, int(m[4]) * scale_y)
        coords.append((int(min(x1, x2)), int(min(y1, y2)), int(max(x1, x2)), int(max(y1, y2))))
        texts.append(m[0].strip())
    return coords, texts
