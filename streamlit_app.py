# -*- coding: utf-8 -*-
"""
極簡版：依網址參數顯示「單一文物」
- 參數：?csv=XXXX&id=YYYY  （csv 可為本機檔名或 http/https 連結）
- 未給參數：不載入資料，只顯示範例連結
- 僅用 pandas，無額外套件
"""

import os
import sys
import random
import pandas as pd
import streamlit as st
from urllib.parse import urlparse, unquote, quote, urlunparse
import ssl
import certifi
import urllib.request
import io

# 先給暫時標題，稍後以 JS 覆寫為「id + name」
st.set_page_config(page_title="文物檢視", layout="centered")
# 頁面不顯示固定大標題，改由後面依資料動態輸出

# -------------------- 共用：取得網址參數 --------------------
def get_params():
    try:
        qp = st.query_params if hasattr(st, "query_params") else st.experimental_get_query_params()
    except Exception:
        qp = {}
    def _one(v, default=None):
        if isinstance(v, list):
            return v[0] if v else default
        return v if v is not None else default
    csv_param = _one(qp.get("csv"), "")
    id_param  = _one(qp.get("id"), None)
    return csv_param, id_param

# -------------------- URL 正規化（處理中文路徑） --------------------
def normalize_url(u: str) -> str:
    try:
        if not isinstance(u, str) or not u.lower().startswith(("http://","https://")):
            return u
        pr = urlparse(u)
        path_decoded = unquote(pr.path)
        new_path = quote(path_decoded, safe="/.-_~")
        if new_path == pr.path:
            return u
        return urlunparse((pr.scheme, pr.netloc, new_path, pr.params, pr.query, pr.fragment))
    except Exception:
        return u

# -------------------- 範例清單（提供隨機預設與下方「快速範例」共用） --------------------
def _default_examples():
    return [
        {"title": "銅器範例",   "csv": "https://raw.githubusercontent.com/muse-101/npm-dataset/main/d01銅_s1.csv", "id": "中銅000651"},
        {"title": "玉器範例",   "csv": "https://raw.githubusercontent.com/muse-101/npm-dataset/main/d02玉_s1.csv", "id": "故玉002103"},
        {"title": "瓷器範例",   "csv": "https://raw.githubusercontent.com/muse-101/npm-dataset/main/d03瓷_s1.csv", "id": "故瓷014204"},
        {"title": "琺瑯範例",   "csv": "https://raw.githubusercontent.com/muse-101/npm-dataset/main/d04琺_s1.csv", "id": "故琺000844"},
        {"title": "雜項範例",   "csv": "https://raw.githubusercontent.com/muse-101/npm-dataset/main/d05雜_s1.csv", "id": "故雜001599"},
        {"title": "文具範例",   "csv": "https://raw.githubusercontent.com/muse-101/npm-dataset/main/d06文_s1.csv", "id": "故文000071"},
        {"title": "繪畫範例",   "csv": "https://raw.githubusercontent.com/muse-101/npm-dataset/main/d20畫_s1.csv", "id": "故畫00124400014"},
        {"title": "法書範例",   "csv": "https://raw.githubusercontent.com/muse-101/npm-dataset/main/d21書_s1.csv", "id": "故書00014100000"},
        {"title": "法帖範例",   "csv": "https://raw.githubusercontent.com/muse-101/npm-dataset/main/d22帖_s1.csv", "id": "故帖00000100000"},
        {"title": "成扇範例",   "csv": "https://raw.githubusercontent.com/muse-101/npm-dataset/main/d23扇_s1.csv", "id": "故扇001592"},
    ]

# -------------------- 讀取 CSV --------------------
@st.cache_data(show_spinner=False)
def load_csv(csv_hint: str) -> pd.DataFrame:
    """csv_hint 可為本機檔名或 http(s) 連結；回傳 DataFrame。
    增加 macOS 常見 SSL 憑證問題的處理：改用 certifi 憑證建立 SSL context 後再讀取。
    """
    def _read_url(url: str) -> pd.DataFrame:
        # 1) 直接用 pandas 嘗試
        try:
            return pd.read_csv(url)
        except Exception:
            pass
        # 2) 用 urllib + certifi context 取得 bytes 再交給 pandas
        try:
            import ssl, certifi, urllib.request, io
            ctx = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(url, context=ctx) as resp:
                data = resp.read()
            return pd.read_csv(io.BytesIO(data))
        except Exception:
            # 3) 再試一次用 utf-8-sig 讀取
            try:
                import ssl, certifi, urllib.request, io
                ctx = ssl.create_default_context(cafile=certifi.where())
                with urllib.request.urlopen(url, context=ctx) as resp:
                    data = resp.read()
                return pd.read_csv(io.BytesIO(data), encoding="utf-8-sig")
            except Exception as ee:
                raise ee

    if csv_hint and str(csv_hint).lower().startswith(("http://","https://")):
        url = normalize_url(csv_hint)
        return _read_url(url)
    else:
        # 視為檔案路徑（同層或絕對路徑）
        path = os.path.join(os.path.dirname(__file__), csv_hint) if not os.path.isabs(csv_hint) else csv_hint
        if not os.path.exists(path):
            # 若找不到同層檔案，直接當作給的是其他有效路徑
            path = csv_hint
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.read_csv(path, encoding="utf-8-sig")

# -------------------- 主流程 --------------------
csv_param, id_param = get_params()

# 不自動寫入任何網址參數；若未提供參數，顯示查詢表單 + 範例清單，方便除錯
if not (csv_param and id_param):
    st.markdown("_未帶參數，可直接查詢或從下方範例挑選。_")

    # --- 互動查詢區（即使沒有參數也可使用） ---
    st.markdown("---")
    st.subheader("查詢其他文物")
    with st.form("lookup_form_landing", clear_on_submit=False):
        in_csv = st.text_input("CSV URL 或路徑", value="")
        in_id  = st.text_input("ID / caseId / url", value="")
        submitted = st.form_submit_button("查詢", type="primary")

    if 'lookup_feedback_landing' not in st.session_state:
        st.session_state['lookup_feedback_landing'] = ''

    if submitted:
        if not in_csv.strip() or not in_id.strip():
            st.session_state['lookup_feedback_landing'] = "請同時填入 CSV 與 ID。"
        else:
            try:
                _df_test = load_csv(in_csv.strip())
                if _df_test.empty:
                    st.session_state['lookup_feedback_landing'] = "讀到的 CSV 為空，請確認連結或檔案內容。"
                else:
                    _key_order = ["id","ID","Id","caseId","caseID","CaseId","url","URL","Url"]
                    key_col = next((k for k in _key_order if k in _df_test.columns), None)
                    if not key_col:
                        st.session_state['lookup_feedback_landing'] = "此 CSV 缺少可當主鍵的欄位（id/caseId/url）。"
                    else:
                        hit = _df_test[_df_test[key_col].astype(str) == str(in_id.strip())]
                        if hit.empty:
                            st.session_state['lookup_feedback_landing'] = f"找不到此 ID：{in_id.strip()}。"
                        else:
                            try:
                                st.query_params.update({"csv": in_csv.strip(), "id": in_id.strip()})
                            except Exception:
                                st.experimental_set_query_params(csv=in_csv.strip(), id=in_id.strip())
                            st.rerun()
            except Exception as e:
                st.session_state['lookup_feedback_landing'] = f"讀取失敗：{e}"

    if st.session_state.get('lookup_feedback_landing'):
        st.error(st.session_state['lookup_feedback_landing'])

    # --- 範例清單（本頁開啟，另開新分頁） ---
    st.markdown("---")
    st.subheader("快速範例（本頁開啟）")
    examples = _default_examples()
    for i, ex in enumerate(examples, start=1):
        title_ex = str(ex.get("title", f"範例 {i}"))
        csv_ex   = str(ex.get("csv", "")).strip()
        id_ex    = str(ex.get("id", "")).strip()
        if csv_ex and id_ex:
            rel = f"?csv={quote(csv_ex)}&id={quote(id_ex)}"
            html = (
                f"<div style='margin:6px 0;'>[ {title_ex}<br>"
                f"<a href='{rel}' target='_blank' rel='noopener noreferrer'>{rel}</a><br>]" 
                f"</div>"
            )
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown(f"[ {title_ex}（請補 csv 與 id） ]")
    st.stop()

# -------------- 這裡開始是「有帶參數」的顯示邏輯 --------------
# 讀取 CSV -> 依 id 選取單一列 -> 顯示標題 + 小圖（150px）
try:
    df = load_csv(csv_param)
except Exception as e:
    st.error(f"讀取 CSV 失敗：{e}")
    st.stop()

if df.empty:
    st.warning("CSV 為空，無資料可顯示。")
    st.stop()

# 偏好欄位名稱（最小集合）
PREFS = {
    # ★ id 欄位的優先順序：id → caseId → url（再補其它大小寫變體）
    "id": [
        "id", "ID", "Id",
        "caseId", "caseID", "CaseId",
        "url", "URL", "Url"
    ],
    # ★ name/標題 欄位：加入 caseName 作為候選
    "name": ["name", "名稱", "title", "caseName"],
    # ★ 縮圖欄位：加入 representImage.transform.c
    "image": [
        "imageUrl_s", "image", "thumbnail", "image_url", "imageurl", "img", "thumb", "thumbnail_s",
        "representImage.transform.c"
    ],
}

# 對應實際欄位
actual = {}
for key, cand in PREFS.items():
    for c in cand:
        if c in df.columns:
            actual[key] = c
            break

# 取目標列
row = None
if id_param and actual.get("id"):
    try:
        row_df = df[df[actual["id"]].astype(str) == str(id_param)]
        if not row_df.empty:
            row = row_df.iloc[0]
    except Exception:
        row = None

# 若找不到該 id，退回第一筆
if row is None:
    row = df.iloc[0]

# 顯示標題（頁面抬頭：id + name）
def _to_text(x):
    try:
        if x is None:
            return ""
        # pandas 的 NaN / NA
        if isinstance(x, float) and pd.isna(x):
            return ""
        return str(x)
    except Exception:
        return ""

name_val_raw = row.get(actual.get("name", ""), "") if isinstance(row, pd.Series) else ""
id_val_raw   = row.get(actual.get("id", ""), "") if isinstance(row, pd.Series) else ""
name_val = _to_text(name_val_raw)
id_val   = _to_text(id_val_raw)

page_title = (id_val + (" " if id_val and name_val else "") + (name_val or "（未命名）")).strip()
st.header(page_title)

# 動態設定瀏覽器標題（Streamlit 的 set_page_config 已在最上方呼叫，這裡用 JS 覆寫）
try:
    from streamlit.components.v1 import html as _html
    _html(f"<script>document.title = {page_title!r};</script>", height=0)
except Exception:
    pass

# 小圖（150px 寬）
img_col = actual.get("image")
if img_col:
    try:
        img_url = str(row.get(img_col, "")).strip()
        if img_url:
            st.image(img_url, width=150)
    except Exception:
        pass

# === 顯示所有欄位 ===
st.subheader("欄位資料")
cols = list(df.columns)

def _is_url(s: str) -> bool:
    try:
        return isinstance(s, str) and s.lower().startswith(("http://", "https://"))
    except Exception:
        return False

for c in cols:
    val = row.get(c, "") if isinstance(row, pd.Series) else ""
    if pd.isna(val):
        val = ""
    sval = str(val)
    if _is_url(sval):
        st.markdown(f"**{c}**：<a href='{sval}' target='_blank' rel='noopener noreferrer'>{sval}</a>", unsafe_allow_html=True)
    else:
        st.write(f"**{c}**：{sval}")

# === 查詢區（CSV URL + ID） ===
st.markdown("---")
st.subheader("查詢其他文物")
with st.form("lookup_form", clear_on_submit=False):
    in_csv = st.text_input("CSV URL 或路徑", value=str(csv_param or ""))
    in_id  = st.text_input("ID / caseId / url", value=str(id_param or ""))
    submitted = st.form_submit_button("查詢", type="primary")

if 'lookup_feedback' not in st.session_state:
    st.session_state['lookup_feedback'] = ''

if submitted:
    if not in_csv.strip() or not in_id.strip():
        st.session_state['lookup_feedback'] = "請同時填入 CSV 與 ID。"
    else:
        # 嘗試讀取；失敗則停留本頁並顯示錯誤
        try:
            _df_test = load_csv(in_csv.strip())
            if _df_test.empty:
                st.session_state['lookup_feedback'] = "讀到的 CSV 為空，請確認連結或檔案內容。"
            else:
                # 找主鍵欄位（沿用 PREFS 設定）
                key_col = None
                for k in PREFS['id']:
                    if k in _df_test.columns:
                        key_col = k
                        break
                if not key_col:
                    st.session_state['lookup_feedback'] = "此 CSV 缺少可當主鍵的欄位（id/caseId/url）。"
                else:
                    hit = _df_test[_df_test[key_col].astype(str) == str(in_id.strip())]
                    if hit.empty:
                        st.session_state['lookup_feedback'] = f"找不到此 ID：{in_id.strip()}。"
                    else:
                        # 一切 OK → 寫入網址參數並重載同頁
                        try:
                            st.query_params.update({"csv": in_csv.strip(), "id": in_id.strip()})
                        except Exception:
                            st.experimental_set_query_params(csv=in_csv.strip(), id=in_id.strip())
                        st.rerun()
        except Exception as e:
            st.session_state['lookup_feedback'] = f"讀取失敗：{e}"

if st.session_state.get('lookup_feedback'):
    st.error(st.session_state['lookup_feedback'])
