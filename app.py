import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="Planta Interativa")

st.title("🏗️ Planta Baixa - Clica, Arrasta e Gira (Modo Ampliado)")

# --- O SEGREDO DO TAMANHO ESTÁ AQUI ---
# Antes era 15. Agora 1 metro = 40 pixels na tela (Tudo fica quase 3x maior)
ESCALA = 40 

if 'dados_comodos' not in st.session_state:
    st.session_state.dados_comodos = []

if 'objetos_canvas' not in st.session_state:
    st.session_state.objetos_canvas = [{
        "type": "rect", "left": 10, "top": 10, 
        "width": 20 * ESCALA, "height": 30 * ESCALA,
        "fill": "transparent", "stroke": "black", 
        "strokeWidth": 3, "strokeDashArray": [10, 10]
    }]

with st.sidebar:
    st.header("1. Inserir Cômodo")
    nome = st.text_input("Nome do Setor", placeholder="Ex: Produção")
    larg_m = st.number_input("Largura (m)", min_value=1.0, value=5.0)
    comp_m = st.number_input("Comprimento (m)", min_value=1.0, value=5.0)
    cor = st.color_picker("Cor do Cômodo", "#A9Cce3")

    if st.button("➕ Adicionar Cômodo"):
        if nome:
            area = larg_m * comp_m
            st.session_state.dados_comodos.append({"Nome": nome, "Área (m²)": area})
            
            novo_bloco = {
                "type": "rect",
                "left": 50, "top": 50, 
                "width": larg_m * ESCALA,
                "height": comp_m * ESCALA,
                "fill": cor,
                "stroke": "black",
                "strokeWidth": 2,
                "opacity": 0.8
            }
            st.session_state.objetos_canvas.append(novo_bloco)
            st.rerun()

    st.divider()
    
    st.header("2. Inserir Porta")
    larg_porta = st.number_input("Largura da Porta (m)", min_value=0.60, max_value=6.0, value=0.80, step=0.10)
    
    if st.button("🚪 Adicionar Porta"):
        w_px = larg_porta * ESCALA
        nova_porta = {
            "type": "path",
            "path": [
                ["M", 0, 0], 
                ["L", 0, -w_px], 
                ["A", w_px, w_px, 0, 0, 1, w_px, 0]
            ],
            "left": 150, 
            "top": 150,
            "fill": "transparent",
            "stroke": "#8B4513", 
            "strokeWidth": 4, # Deixei a linha da porta mais grossa pra enxergar bem
            "opacity": 1.0
        }
        st.session_state.objetos_canvas.append(nova_porta)
        st.rerun()

    st.divider()
    
    if st.button("🗑️ Resetar Tudo"):
        st.session_state.dados_comodos = []
        st.session_state.objetos_canvas = st.session_state.objetos_canvas[:1] 
        st.rerun()

# --- TELA PRINCIPAL ---
col1, col2 = st.columns([3, 1])

with col1:
    st.info("🖱️ **Instruções:** Selecione um objeto e arraste. Tudo está em escala maior agora.")
    
    estado_inicial = {
        "version": "4.4.0",
        "objects": st.session_state.objetos_canvas
    }

    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=2,
        background_color="#e8e8e8",
        initial_drawing=estado_inicial,
        drawing_mode="transform", 
        width=1000,   # AUMENTEI A LARGURA DA PRANCHETA
        height=800,   # AUMENTEI A ALTURA DA PRANCHETA
        key="canvas",
    )

with col2:
    st.subheader("📋 Quadro de Áreas")
    if st.session_state.dados_comodos:
        df = pd.DataFrame(st.session_state.dados_comodos)
        st.table(df)
        st.metric("Total Construído", f"{df['Área (m²)'].sum():.2f} m²")
    else:
        st.write("Adicione um cômodo na lateral.")
