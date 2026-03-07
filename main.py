import os
import urllib.request
import streamlit as st

@st.cache_resource # 使用缓存，防止每次刷新页面都去检查/下载
def download_large_files():
    files_to_download = {
        "extract.pyz": "https://github.com/qqinzhihao847-cell/shuiyin/releases/download/v1.0/extract.pyz",
        "embed.pyz": https://github.com/qqinzhihao847-cell/shuiyin/releases/download/v1.0/embed.pyz" # 如果需要的话
    }
    
    for filename, url in files_to_download.items():
        if not os.path.exists(filename):
            with st.spinner(f"首次启动，正在下载核心组件 {filename}，请稍候..."):
                try:
                    urllib.request.urlretrieve(url, filename)
                except Exception as e:
                    st.error(f"下载 {filename} 失败: {e}")

# 在程序一开始调用这个函数
download_large_files()

# ... 下面继续写你原来的工作目录定义和功能代码 ...
import zipfile
import io
import shutil
import random
import datetime
import subprocess
from pathlib import Path
from PIL import Image
import hashlib
import base64
import streamlit as st
import streamlit.components.v1 as components

# --------------------------
# 固定工作目录（每次覆盖，不保留历史）
# --------------------------
EMBED_UPLOAD_DIR   = Path("./workspace/embed_upload")
EMBED_OUTPUT_DIR   = Path("./workspace/embed_output")
EXTRACT_UPLOAD_DIR = Path("./workspace/extract_upload")

# --------------------------
# 工具函数
# --------------------------

def clear_dir(p: Path):
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)

def run_cmd(cmd: str):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def list_images(folder: Path):
    if not folder.exists():
        return []
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts]
    files.sort(key=lambda x: x.name)
    return files

def make_zip_bytes(file_paths):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in file_paths:
            zf.write(p, arcname=p.name)
    buf.seek(0)
    return buf.read()

def calculate_uploaded_hash(uploaded_files):
    h = hashlib.md5()
    for f in uploaded_files:
        h.update(f.name.encode())
        h.update(str(f.size).encode())
    return h.hexdigest()

def random_msg() -> str:
    return "".join(random.choice("01") for _ in range(64))

def validate_msg(msg: str):
    if not msg:
        return False, ""
    bad = sorted(set(c for c in msg if c not in ("0", "1")))
    if bad:
        display = "".join(f'"{c}"' for c in bad)
        return False, f"包含非法字符 {display}，水印信息只允许输入 0 或 1"
    if len(msg) != 64:
        return False, f"当前长度为 {len(msg)} 位，水印信息须恰好为 64 位"
    return True, ""

def check_image_size(path: Path):
    with Image.open(path) as img:
        w, h = img.size
    return (w >= 512 and h >= 512), w, h

def read_text_auto(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8", "gbk", "gb2312", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1")

def save_uploaded_images(uploaded_files, target_dir: Path):
    valid_exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    saved, skipped = [], []
    for f in uploaded_files:
        raw = f.read()
        if f.name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                    for member in zf.namelist():
                        mp = Path(member)
                        if member.startswith("__MACOSX") or member.endswith("/"):
                            continue
                        if mp.name.startswith("."):
                            continue
                        if mp.suffix.lower() not in valid_exts:
                            continue
                        file_data = zf.read(member)
                        dest = target_dir / mp.name
                        if dest.exists():
                            idx = 1
                            while dest.exists():
                                dest = target_dir / f"{mp.stem}_{idx}{mp.suffix}"
                                idx += 1
                        dest.write_bytes(file_data)
                        ok, w, h = check_image_size(dest)
                        if not ok:
                            dest.unlink()
                            skipped.append(f"{mp.name}（{w}x{h}，小于 512x512）")
                        else:
                            saved.append(dest)
            except Exception as e:
                skipped.append(f"{f.name}（ZIP 解压失败：{e}）")
        else:
            dest = target_dir / f.name
            dest.write_bytes(raw)
            ok, w, h = check_image_size(dest)
            if not ok:
                dest.unlink()
                skipped.append(f"{f.name}（{w}x{h}，小于 512x512）")
            else:
                saved.append(dest)
    return saved, skipped

def try_extract_embedded_msg_from_zips(uploaded_files, target_dir: Path):
    for f in uploaded_files:
        if not f.name.lower().endswith(".zip"):
            continue
        f.seek(0)
        raw = f.read()
        try:
            with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                if "embedded_msg.txt" in zf.namelist():
                    (target_dir / "embedded_msg.txt").write_bytes(zf.read("embedded_msg.txt"))
                    return
        except Exception:
            pass

def img_to_thumb_b64(path: Path, thumb_size: int = 150) -> str:
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((thumb_size, thumb_size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return base64.b64encode(buf.getvalue()).decode()

def render_image_slider(image_paths: list, thumb_size: int = 150, box_height: int = 210):
    if not image_paths:
        return
    items_html = ""
    for p in image_paths:
        p = Path(p)
        try:
            b64 = img_to_thumb_b64(p, thumb_size)
        except Exception:
            continue
        name = p.name
        short = name if len(name) <= 14 else name[:11] + "..."
        items_html += (
            f'<div class="item">'
            f'<img src="data:image/jpeg;base64,{b64}" title="{name}"/>'
            f'<span class="name">{short}</span>'
            f'</div>'
        )
    html = (
        f'<style>'
        f'.sb{{display:flex;flex-direction:row;align-items:flex-start;'
        f'gap:10px;overflow-x:auto;overflow-y:hidden;'
        f'padding:10px 12px 14px;background:#fff;'
        f'border:1px solid #ddd;border-radius:10px;'
        f'box-sizing:border-box;width:100%;min-height:{box_height}px;'
        f'scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;}}'
        f'.sb::-webkit-scrollbar{{height:6px;}}'
        f'.sb::-webkit-scrollbar-track{{background:#eee;border-radius:3px;}}'
        f'.sb::-webkit-scrollbar-thumb{{background:#aaa;border-radius:3px;}}'
        f'.item{{flex:0 0 auto;display:flex;flex-direction:column;'
        f'align-items:center;gap:5px;scroll-snap-align:start;}}'
        f'.item img{{width:{thumb_size}px;height:{thumb_size}px;object-fit:contain;'
        f'border-radius:6px;border:1px solid #ddd;background:#f5f5f5;}}'
        f'.name{{font-size:10px;color:#666;max-width:{thumb_size}px;'
        f'text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}'
        f'</style>'
        f'<div class="sb">{items_html}</div>'
    )
    components.html(html, height=box_height + 30, scrolling=False)

# ---- 溯源准确率相关 ----

def parse_msg_txt(text: str) -> dict:
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        name_part, _, bits_part = line.partition(":")
        name = name_part.strip()
        bits = bits_part.strip()
        if len(bits) == 64 and all(c in "01" for c in bits):
            result[name] = bits
    return result

def calc_bit_accuracy(ref: str, ext: str) -> float:
    if len(ref) != 64 or len(ext) != 64:
        return 0.0
    return sum(r == e for r, e in zip(ref, ext)) / 64

def render_accuracy_table(parsed: dict, ref_msg: str):
    if not parsed:
        st.warning("未能从提取结果中解析出有效水印数据，请检查 msg.txt 格式。")
        return

    rows = []
    for name, bits in parsed.items():
        acc = calc_bit_accuracy(ref_msg, bits)
        rows.append({"name": name, "bits": bits, "acc": acc})

    avg_acc = sum(r["acc"] for r in rows) / len(rows)

    def bar_color(v):
        if v >= 0.9:
            return "#27ae60"
        if v >= 0.7:
            return "#e67e22"
        return "#e74c3c"

    rows_html = ""
    for r in rows:
        pct = r["acc"] * 100
        color = bar_color(r["acc"])
        rows_html += (
            f'<tr>'
            f'<td style="padding:6px 10px;font-size:12px;word-break:break-all;'
            f'max-width:260px;color:#333;">{r["name"]}</td>'
            f'<td style="padding:6px 10px;font-family:monospace;font-size:11px;'
            f'color:#555;word-break:break-all;">{r["bits"]}</td>'
            f'<td style="padding:6px 14px;white-space:nowrap;">'
            f'<div style="display:flex;align-items:center;gap:6px;">'
            f'<div style="flex:1;background:#eee;border-radius:4px;height:8px;min-width:60px;">'
            f'<div style="width:{pct:.1f}%;background:{color};border-radius:4px;height:8px;"></div>'
            f'</div>'
            f'<span style="font-size:13px;font-weight:600;color:{color};min-width:46px;">{pct:.1f}%</span>'
            f'</div></td></tr>'
        )

    avg_pct = avg_acc * 100
    avg_color = bar_color(avg_acc)

    html = (
        f'<style>'
        f'.at{{width:100%;border-collapse:collapse;background:#fff;'
        f'border:1px solid #ddd;border-radius:10px;overflow:hidden;}}'
        f'.at th{{background:#f5f5f5;padding:8px 10px;font-size:12px;color:#555;'
        f'font-weight:600;text-align:left;border-bottom:2px solid #ddd;}}'
        f'.at tr:nth-child(even){{background:#fafafa;}}'
        f'.at tr:hover{{background:#f0f7ff;}}'
        f'.avgr td{{padding:8px 10px;font-weight:700;font-size:13px;'
        f'border-top:2px solid #ddd;background:#fff8e1;}}'
        f'</style>'
        f'<table class="at"><thead><tr>'
        f'<th>图像名称</th><th>提取水印位串</th><th>逐位准确率</th>'
        f'</tr></thead><tbody>'
        f'{rows_html}'
        f'<tr class="avgr">'
        f'<td colspan="2">平均溯源准确率（共 {len(rows)} 张图像）</td>'
        f'<td><div style="display:flex;align-items:center;gap:6px;">'
        f'<div style="flex:1;background:#eee;border-radius:4px;height:10px;min-width:60px;">'
        f'<div style="width:{avg_pct:.1f}%;background:{avg_color};border-radius:4px;height:10px;"></div>'
        f'</div>'
        f'<span style="font-size:15px;font-weight:700;color:{avg_color};min-width:52px;">{avg_pct:.1f}%</span>'
        f'</div></td></tr>'
        f'</tbody></table>'
    )
    components.html(html, height=min(80 + len(rows) * 44 + 60, 600), scrolling=True)


# --------------------------
# Session State 初始化
# --------------------------
_defaults = {
    "embed_files_hash":   None,
    "embedded_files":     [],
    "embed_zip_ts":       None,
    "extract_files_hash": None,
    "extracted_text":     None,
    "txt_file_path":      None,
    "watermark_msg":      random_msg(),
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---- 弹窗（统一用一个，传入标题和内容） ----

@st.dialog("操作提示")
def _show_error_dialog(title: str, body: str):
    st.markdown(
        f'<div style="text-align:center;padding:8px 0 16px;">'
        f'<div style="font-size:48px;margin-bottom:12px;">&#x1F6AB;</div>'
        f'<div style="font-size:15px;color:#c0392b;font-weight:600;margin-bottom:8px;">{title}</div>'
        f'<div style="font-size:14px;color:#555;line-height:1.7;'
        f'background:#fff5f5;border-radius:8px;padding:12px 16px;border:1px solid #fcc;">'
        f'{body}</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("知道了", type="primary", use_container_width=True):
        st.rerun()

# --------------------------
# 页面
# --------------------------
st.title("水印嵌入与提取工具（批量）")

# ══════════════════════════
#  1. 嵌入水印
# ══════════════════════════
st.header("1. 嵌入水印")

embed_files = st.file_uploader(
    "选择图片或压缩包（PNG / JPG / JPEG / ZIP，数量不限；图片须 >= 512x512）",
    type=["zip", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="embed_uploader",
)

if embed_files:
    cur_hash = calculate_uploaded_hash(embed_files)
    if st.session_state.embed_files_hash != cur_hash:
        st.session_state.embed_files_hash = cur_hash
        st.session_state.embedded_files = []
        st.session_state.embed_zip_ts = None
        clear_dir(EMBED_UPLOAD_DIR)
        clear_dir(EMBED_OUTPUT_DIR)
        saved, skipped = save_uploaded_images(embed_files, EMBED_UPLOAD_DIR)
        if skipped:
            st.warning(
                "以下文件因尺寸不足 512x512 或解压失败已跳过：\n"
                + "\n".join(f"  - {s}" for s in skipped)
            )
    imgs = list_images(EMBED_UPLOAD_DIR)
    if imgs:
        st.success(f"文件上传成功，共获取到 {len(imgs)} 张有效图片。")
        st.caption("图片预览（可左右滑动）")
        render_image_slider(imgs)
    else:
        st.warning("未检测到有效图片，请确认上传内容的格式及尺寸是否符合要求。")

elif not embed_files and st.session_state.embed_files_hash is not None:
    st.session_state.embed_files_hash = None
    st.session_state.embedded_files = []
    st.session_state.embed_zip_ts = None

# ---- 水印信息 ----
st.markdown("#### 水印信息")
st.caption("以下为系统随机生成的 64 位 0/1 水印序列，可直接使用，也可手动修改或重新生成。")

col_input, col_btn = st.columns([5, 1], vertical_alignment="bottom")
with col_input:
    typed = st.text_input(
        "水印信息输入框",
        value=st.session_state.watermark_msg,
        label_visibility="collapsed",
        placeholder="请输入 64 位 0/1 序列...",
        max_chars=64,
    )
    st.session_state.watermark_msg = typed
with col_btn:
    if st.button("随机生成", use_container_width=True):
        st.session_state.watermark_msg = random_msg()
        st.rerun()

cur_msg = typed
msg_ok, msg_err = validate_msg(cur_msg)
if cur_msg and not msg_ok:
    st.error(f"水印信息格式错误：{msg_err}")
elif msg_ok:
    st.success("水印信息验证通过，共 64 位，格式符合要求。")

# ---- 嵌入按钮 ----
# 在按钮渲染前，将本帧输入框的值快照，确保后续命令用的值与界面显示完全一致
embed_msg_snapshot = typed

if st.button("开始嵌入水印", type="primary", key="btn_embed"):
    # 检查当前上传控件是否有文件（不能用文件夹，文件夹是上次留下的）
    if not embed_files:
        _show_error_dialog(
            "尚未上传图片",
            "请先上传待嵌入水印的图片，再执行嵌入操作。"
        )
        st.stop()

    # 校验水印信息
    final_msg = embed_msg_snapshot
    final_ok, final_err = validate_msg(final_msg)
    if not final_ok:
        _show_error_dialog(
            "水印信息不合规",
            final_err if final_err else "请输入合法的 64 位 0/1 水印序列。"
        )
        st.stop()

    # 将本次确认使用的水印值写入 session_state，后续不再读取输入框
    st.session_state.watermark_msg = final_msg

    with st.spinner("正在嵌入水印，请稍候..."):
        # embed.pyz 对整个文件夹批量处理，只调用一次，所有图片使用同一个水印
        cmd = (
            f'python embed.pyz '
            f'--img_path "{EMBED_UPLOAD_DIR}" '
            f'--out_path "{EMBED_OUTPUT_DIR}" '
            f'--msg "{final_msg}"'
        )
        res = run_cmd(cmd)

    result_imgs = list_images(EMBED_OUTPUT_DIR)
    st.session_state.embedded_files = [str(p) for p in result_imgs]

    if res.returncode == 0 and result_imgs:
        st.session_state.embed_zip_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        (EMBED_OUTPUT_DIR / "embedded_msg.txt").write_text(final_msg, encoding="utf-8")
        st.success(f"水印嵌入完成，共处理 {len(result_imgs)} 张图片，嵌入水印：{final_msg}")
    else:
        st.error("水印嵌入失败，请检查图片格式或联系管理员。")

# ---- 嵌入结果预览与下载 ----
if st.session_state.embedded_files:
    st.subheader("嵌入结果预览与下载")
    ep = [Path(p) for p in st.session_state.embedded_files if Path(p).exists()]
    if ep:
        st.caption(f"共 {len(ep)} 张，可左右滑动预览")
        render_image_slider(ep)

        pick = st.selectbox("选择一张进行大图预览", [p.name for p in ep])
        pick_path = ep[[p.name for p in ep].index(pick)]
        st.image(Image.open(pick_path), caption=pick, width=400)

        zip_ts = st.session_state.embed_zip_ts or datetime.datetime.now().strftime("%Y%m%d_%H%M")
        extra = EMBED_OUTPUT_DIR / "embedded_msg.txt"
        zip_paths = ep + ([extra] if extra.exists() else [])
        st.download_button(
            label="下载全部（zip）",
            data=make_zip_bytes(zip_paths),
            file_name=f"watermarked_{zip_ts}.zip",
            mime="application/zip",
        )


# ══════════════════════════
#  2. 提取水印
# ══════════════════════════
st.header("2. 提取水印")

extract_files = st.file_uploader(
    "选择含水印图像（PNG / JPG / JPEG / ZIP，数量不限；图片须 >= 512x512）",
    type=["zip", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="extract_uploader",
)

if extract_files:
    cur_hash = calculate_uploaded_hash(extract_files)
    if st.session_state.extract_files_hash != cur_hash:
        st.session_state.extract_files_hash = cur_hash
        st.session_state.extracted_text = None
        st.session_state.txt_file_path = None
        clear_dir(EXTRACT_UPLOAD_DIR)
        saved, skipped = save_uploaded_images(extract_files, EXTRACT_UPLOAD_DIR)
        try_extract_embedded_msg_from_zips(extract_files, EXTRACT_UPLOAD_DIR)
        if skipped:
            st.warning(
                "以下文件因尺寸不足 512x512 或解压失败已跳过：\n"
                + "\n".join(f"  - {s}" for s in skipped)
            )
    imgs = list_images(EXTRACT_UPLOAD_DIR)
    if imgs:
        st.success(f"文件上传成功，共获取到 {len(imgs)} 张有效图片。")
        st.caption(f"共 {len(imgs)} 张，可左右滑动预览")
        render_image_slider(imgs)
    else:
        st.warning("未检测到有效图片，请确认上传内容的格式及尺寸是否符合要求。")

elif not extract_files and st.session_state.extract_files_hash is not None:
    st.session_state.extract_files_hash = None
    st.session_state.extracted_text = None
    st.session_state.txt_file_path = None

if st.button("提取水印", type="primary", key="btn_extract"):
    # 检查当前上传控件，而非文件夹
    if not extract_files:
        _show_error_dialog(
            "尚未上传图片",
            "请先上传含水印的图片，再执行提取操作。"
        )
        st.stop()

    with st.spinner("正在提取水印，请稍候..."):
        cmd = (
            f'python extract.pyz '
            f'--ori_path "{EXTRACT_UPLOAD_DIR}" '
            f'--out_path "{EXTRACT_UPLOAD_DIR}"'
        )
        result = run_cmd(cmd)

    if result.returncode == 0:
        txt = EXTRACT_UPLOAD_DIR / "msg.txt"
        if txt.exists():
            st.session_state.extracted_text = read_text_auto(txt)
            st.session_state.txt_file_path = str(txt)
            st.success("水印提取完成。")
        else:
            st.error("提取命令执行完毕，但未找到输出文件 msg.txt，请检查脚本配置。")
    else:
        st.error("水印提取失败，请检查图片格式或联系管理员。")

if st.session_state.extracted_text:
    st.text_area("提取的水印文本：", st.session_state.extracted_text, height=200)
    with open(st.session_state.txt_file_path, "rb") as f:
        st.download_button(
            label="下载提取的水印文本",
            data=f,
            file_name="msg.txt",
            mime="text/plain",
        )

    # ---- 溯源准确率 ----
    st.subheader("溯源准确率")

    auto_ref = ""
    ref_file = EXTRACT_UPLOAD_DIR / "embedded_msg.txt"
    if ref_file.exists():
        auto_ref = read_text_auto(ref_file).strip()

    ref_msg_input = st.text_input(
        "原始嵌入水印信息（64 位 0/1，用于逐位准确率对比）",
        value=auto_ref,
        placeholder="上传含 embedded_msg.txt 的压缩包可自动填入，也可手动粘贴...",
        max_chars=64,
        key="ref_msg_input",
    )

    ref_ok, ref_err = validate_msg(ref_msg_input)
    if ref_msg_input and not ref_ok:
        st.warning(f"原始水印信息格式错误：{ref_err}")
    elif ref_ok:
        parsed = parse_msg_txt(st.session_state.extracted_text)
        if parsed:
            render_accuracy_table(parsed, ref_msg_input)
        else:
            st.warning("无法从提取结果中解析出有效水印数据，请确认 msg.txt 的格式是否正确。")

