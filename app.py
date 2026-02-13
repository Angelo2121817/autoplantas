import streamlit as st
from streamlit_elements import elements, mui, dashboard
import pandas as pd

st.set_page_config(page_title="AutoPlanta CETESB", layout="wide")

# Inicializa o estado se não existir
if "layout" not in st.session_state:
    st.session_state.layout = [
        {"i": "construcao", "x": 0, "y": 0, "w": 6, "h": 4}
    ]
if "portas" not in st.session_state:
    st.session_state.portas = []

st.title("🏗️ Editor de Planta - General")

with st.sidebar:
    st.header("⚙️ Ferramentas")
    area_terreno = st.number_input("Área Total do Terreno (m²)", value=350.0) # Baseado na planta exemplo [cite: 72]
    
    if st.button("🚪 Adicionar Portão"):
        id_p = f"Porta_{len(st.session_state.portas) + 1}"
        st.session_state.portas.append(id_p)
        st.session_state.layout.append({"i": id_p, "x": 0, "y": 0, "w": 1, "h": 1})
        st.rerun()

    if st.button("🗑️ Limpar Tudo"):
        st.session_state.portas = []
        st.session_state.layout = [{"i": "construcao", "x": 0, "y": 0, "w": 6, "h": 4}]
        st.rerun()

col_desenho, col_dados = st.columns([3, 1])

with col_desenho:
    # Função para atualizar o layout quando o usuário arrasta
    def handle_layout_change(new_layout):
        st.session_state.layout = new_layout

    with elements("dashboard"):
        with dashboard.Grid(st.session_state.layout, onLayoutChange=handle_layout_change, cols=12, rowHeight=50):
            # Galpão Principal
            mui.Paper(
                "ÁREA CONSTRUÍDA",
                key="construcao",
                sx={"display": "flex", "alignItems": "center", "justifyContent": "center", "bgcolor": "#e0e0e0", "border": "2px solid #000"}
            )
            # Portões
            for p_id in st.session_state.portas:
                mui.Paper(
                    "PORTÃO",
                    key=p_id,
                    sx={"display": "flex", "alignItems": "center", "justifyContent": "center", "bgcolor": "#8B4513", "color": "white"}
                )

with col_dados:
    st.subheader("📋 Quadro de Áreas") # 
    
    # Busca os dados atuais da construção no layout
    info_c = next(item for item in st.session_state.layout if item["i"] == "construcao")
    
    # Cálculo: Cada unidade do grid equivale a 5 metros (ajustável)
    area_c = (info_c["w"] * 5) * (info_c["h"] * 5)
    
    df = pd.DataFrame({
        "Descrição": ["Terreno", "Área Construída"], # [cite: 71, 72]
        "Área (m²)": [f"{area_terreno:.2f}", f"{area_c:.2f}"]
    })
    st.table(df)
    
    st.info(f"Proprietário: Priscila\n\nStatus: Planta Baixa simplificada para CETESB.")
