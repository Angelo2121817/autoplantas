import streamlit as st
from streamlit_elements import elements, mui, dashboard
import pandas as pd

st.set_page_config(page_title="AutoPlanta CETESB", layout="wide")

if "layout" not in st.session_state:
    st.session_state.layout = [
        {"i": "construcao", "x": 0, "y": 0, "w": 6, "h": 4}
    ]
if "portas" not in st.session_state:
    st.session_state.portas = []

st.title("🏗️ Editor de Planta Baixa")

with st.sidebar:
    st.header("⚙️ Ferramentas")
    area_terreno = st.number_input("Área Total do Terreno (m²)", value=350.0)
    
    if st.button("🚪 Adicionar Portão"):
        id_p = f"Porta_{len(st.session_state.portas) + 1}"
        st.session_state.portas.append(id_p)
        st.session_state.layout.append({"i": id_p, "x": 0, "y": 0, "w": 2, "h": 1})
        st.rerun()

    if st.button("🗑️ Limpar Tudo"):
        st.session_state.portas = []
        st.session_state.layout = [{"i": "construcao", "x": 0, "y": 0, "w": 6, "h": 4}]
        st.rerun()

col_desenho, col_dados = st.columns([3, 1])

with col_desenho:
    st.write("👇 Arraste e redimensione os blocos abaixo:")
    
    with elements("dashboard"):
        with mui.Box(sx={"height": 500, "width": "100%", "border": "1px solid #ccc", "bgcolor": "#fafafa"}):
            with dashboard.Grid(
                st.session_state.layout, 
                onLayoutChange=lambda new_l: st.session_state.update({"layout": new_l}), 
                cols=12, 
                rowHeight=50
            ):
                mui.Paper(
                    "ÁREA CONSTRUÍDA",
                    key="construcao",
                    sx={
                        "display": "flex", 
                        "alignItems": "center", 
                        "justifyContent": "center", 
                        "bgcolor": "#d3d3d3", 
                        "border": "2px solid #000",
                        "boxShadow": 3
                    }
                )
                for p_id in st.session_state.portas:
                    mui.Paper(
                        "PORTÃO",
                        key=p_id,
                        sx={
                            "display": "flex", 
                            "alignItems": "center", 
                            "justifyContent": "center", 
                            "bgcolor": "#8B4513", 
                            "color": "white",
                            "border": "1px solid #333"
                        }
                    )

with col_dados:
    st.subheader("📋 Quadro de Áreas")
    
    info_c = next((item for item in st.session_state.layout if item["i"] == "construcao"), {"w": 0, "h": 0})
    
    area_c = (info_c["w"] * info_c["h"]) * 10 
    
    df = pd.DataFrame({
        "Descrição": ["Terreno", "Área Construída"],
        "Área (m²)": [f"{area_terreno:.2f}", f"{area_c:.2f}"]
    })
    st.table(df)
    
    st.write("**Responsável:** General")
    st.write("**Cônjuge:** Priscila")
