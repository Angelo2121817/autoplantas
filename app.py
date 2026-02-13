import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="Planta Interativa")

st.title("🏗️ Planta Baixa - Modo Clica e Arrasta")

# Escala: 1 metro = 15 pixels na tela para ficar visível
ESCALA = 15 

# Guarda as informações reais dos cômodos para a tabela
if 'dados_comodos' not in st.session_state:
    st.session_state.dados_comodos = []

# Guarda os objetos visuais do Canvas
if 'objetos_canvas' not in st.session_state:
    # Já começamos com o Terreno (uma caixa grande transparente com borda tracejada)
    st.session_state.objetos_canvas = [{
        "type": "rect", "left": 10, "top": 10, 
        "width": 20 * ESCALA, "height": 30 * ESCALA, # Terreno base de 20x30m
        "fill": "transparent", "stroke": "black", 
        "strokeWidth": 2, "strokeDashArray": [5, 5]
    }]

with st.sidebar:
    st.header("1. Inserir Cômodo")
    nome = st.text_input("Nome do Setor", placeholder="Ex: Produção")
    larg_m = st.number_input("Largura (m)", min_value=1.0, value=5.0)
    comp_m = st.number_input("Comprimento (m)", min_value=1.0, value=5.0)
    cor = st.color_picker("Cor do Cômodo", "#A9Cce3")

    if st.button("➕ Adicionar à Planta"):
        if nome:
            # Salva pra tabela
            area = larg_m * comp_m
            st.session_state.dados_comodos.append({"Nome": nome, "Área (m²)": area})
            
            # Cria a caixa visual para arrastar
            novo_bloco = {
                "type": "rect",
                "left": 50, "top": 50, # Nasce no canto
                "width": larg_m * ESCALA,
                "height": comp_m * ESCALA,
                "fill": cor,
                "stroke": "black",
                "strokeWidth": 2,
                "opacity": 0.8
            }
            st.session_state.objetos_canvas.append(novo_bloco)
            st.rerun()

    if st.button("🗑️ Resetar Tudo"):
        st.session_state.dados_comodos = []
        st.session_state.objetos_canvas.append(novo_bloco)
            st.rerun()

    # <<< É AQUI QUE VAMOS INJETAR O MÓDULO DA PORTA >>>

    if st.button("🗑️ Resetar Tudo"):
col1, col2 = st.columns([3, 1])

with col1:
    st.info("🖱️ **Instruções:** Selecione um bloco colorido e arraste para posicionar. Puxe nas pontas se quiser distorcer.")
    
    # O dicionário que o Canvas lê
    estado_inicial = {
        "version": "4.4.0",
        "objects": st.session_state.objetos_canvas
    }

    # O Canvas Interativo
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=2,
        background_color="#f0f0f0",
        initial_drawing=estado_inicial,
        drawing_mode="transform", # MODO DE ARRASTAR E REDIMENSIONAR
        width=700,
        height=600,
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
