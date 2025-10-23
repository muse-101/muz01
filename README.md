# muz-01 Streamlit App

極簡版「單一文物檢視」：用網址參數 `?csv=...&id=...` 讀取遠端或本機 CSV，顯示目標列（小圖 + 所有欄位）。

## 使用方式

- 沒帶參數：會顯示查詢表單與 10 組範例連結（另開新分頁）。  
- 指定某一筆：

```
https://<your-app>.streamlit.app/?csv=https%3A//raw.githubusercontent.com/muse-101/npm-dataset/main/d01%E9%8A%85_s1.csv&id=%E4%B8%AD%E9%8A%85000651
```

## 本機開發

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 部署（Streamlit Community Cloud）

- Repo root：放 `streamlit_app.py`, `requirements.txt`, `runtime.txt`（可選）
- New app → repo / branch → **Main file path**：`streamlit_app.py` → Deploy
