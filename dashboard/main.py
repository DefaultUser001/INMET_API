import streamlit as st
import pandas as pd
import re
from pathlib import Path

st.set_page_config(page_title="Painel de Logs - INMET", layout="wide")

LOG_PATH = Path("../logs/access.log")

st.title("📊 Painel Admin - Web Scraper INMET")

if not LOG_PATH.exists():
    st.warning("Nenhum log encontrado ainda.")
    st.stop()

# Função para carregar e parsear logs
@st.cache_data
def carregar_logs():
    logs = []
    with open(LOG_PATH, "r") as f:
        for line in f.readlines():
            match = re.match(r"(.*?) - (.*?) - (.*?) - Status: (\d+)", line)
            if match:
                timestamp, level, ip_route, status = match.groups()
                ip, route = ip_route.split(" - ")
                logs.append({
                    "Data/Hora": timestamp,
                    "IP": ip,
                    "Rota": route,
                    "Status": int(status),
                    "Nível": level
                })
    return pd.DataFrame(logs)

df = carregar_logs()
st.dataframe(df.sort_values("Data/Hora", ascending=False), use_container_width=True)

st.markdown("---")
st.info(f"Total de requisições: **{len(df)}**")
st.bar_chart(df["Status"].value_counts())
