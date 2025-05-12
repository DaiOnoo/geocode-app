# geocode_full_app.py

import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- ローカルAPI使用回数ログ機能 ---
LOG_FILE = "api_usage_log.json"

def get_month_key():
    return datetime.now().strftime("%Y-%m")

def load_api_usage():
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_api_usage(log_data):
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f)

def update_api_usage(api_calls_this_session):
    usage = load_api_usage()
    key = get_month_key()
    usage[key] = usage.get(key, 0) + api_calls_this_session
    save_api_usage(usage)
    return usage[key], 10000 - usage[key]

# --- Geocoding API 呼び出し ---
def get_coordinates(query, api_key):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": query, "key": api_key, "language": "ja"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        result = response.json()
        if result["status"] == "OK":
            location = result["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"], True
    return None, None, False

# --- メイン処理 ---
def main():
    st.title("📍 XY座標補完（Google Maps API）＋ 月間使用記録付き")
    st.markdown("欠損している緯度・経度のみ補完し、月ごとのAPI使用数をローカルに記録します。")

    api_key = st.text_input("🔑 Google Maps APIキーを入力", type="password")
    uploaded_file = st.file_uploader("📄 CSVファイルをアップロード（施設名 / 住所 / 緯度 / 経度が必要）", type="csv")

    if uploaded_file and api_key:
        df = pd.read_csv(uploaded_file)

        required = {"施設名", "住所", "緯度", "経度"}
        if not required.issubset(df.columns):
            st.error("以下の列が必要です：施設名 / 住所 / 緯度 / 経度")
            return

        df["検索キー"] = df["施設名"].astype(str) + " " + df["住所"].astype(str)

        success_log, fail_log = [], []
        api_calls = 0

        with st.spinner("座標取得中..."):
            for i, row in df.iterrows():
                if pd.isna(row["緯度"]) or pd.isna(row["経度"]):
                    lat, lng, success = get_coordinates(row["検索キー"], api_key)
                    api_calls += 1
                    if success:
                        df.at[i, "緯度"] = lat
                        df.at[i, "経度"] = lng
                        success_log.append(row["検索キー"])
                    else:
                        fail_log.append(row["検索キー"])

        # 使用数の記録と表示
        total_used, remaining = update_api_usage(api_calls)

        st.success(f"✅ 実行完了：今回 {api_calls} 件 ／ 今月累計 {total_used} 件（残り {remaining} 件）")
        st.write(f"🔵 成功：{len(success_log)} ／ 🔴 失敗：{len(fail_log)}")
        st.dataframe(df)

        csv_result = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📥 補完済CSVをダウンロード", csv_result, "geocoded_result.csv", "text/csv")

        if fail_log:
            fail_df = pd.DataFrame({"失敗した検索キー": fail_log})
            fail_csv = fail_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("⚠ 失敗ログCSVをダウンロード", fail_csv, "geocode_failed.csv", "text/csv")

if __name__ == "__main__":
    main()
