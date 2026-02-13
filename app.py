import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

st.set_page_config(page_title="Planta CETESB - General", layout="wide")

st.title("🏗️ Gerador de Planta - Modo Raiz")

# --- Controles na Lateral ---
with st.sidebar:
    st.header("📍 Terreno")
    larg_t = st.slider("Largura Terreno (m)", 1.0, 100.0, 20.0)
    comp_t = st.slider("Comprimento Terreno (m)", 1.0, 100.0, 30.0)
    
    st.header("🏢 Área Construída")
    larg_c = st.slider("Largura da Construção (m)", 1.0, larg_t, 10.0)
    comp_c = st.slider("Comprimento da Construção (m)", 1.0, comp_t, 15.0)
    pos_x = st.slider("Distância da Esquerda (m)", 0.0, larg_t - larg_c, 2.0)
    pos_y = st.slider("Distância do Fundo (m)", 0.0, comp_t - comp_c, 5.0)

    st.header("🚪 Portão")
    tem_portao = st.checkbox("Adicionar Portão na fachada")
    if tem_portao:
        larg_p = st.slider("Largura do Portão (m)", 1.0, larg_c, 4.0)
        pos_p = st.slider("Posição do Portão na Parede (m)", 0.0, larg_c - larg_p, 0.0)

# --- Cálculos ---
area_t = larg_t * comp_t
area_c_calc = larg_c * comp_c

# --- Layout da Tela ---
col1, col2 = st.columns([3, 1])

with col1:
    fig, ax = plt.subplots(figsize=(8, 10))
    
    # Desenha o Terreno (linha tracejada)
    ax.add_patch(patches.Rectangle((0, 0), larg_t, comp_t, fill=False, edgecolor='black', lw=2, linestyle='--'))
    
    # Desenha a Construção (cinza)
    ax.add_patch(patches.Rectangle((pos_x, pos_y), larg_c, comp_c, facecolor='#d3d3d3', edgecolor='black', lw=2))
    ax.text(pos_x + larg_c/2, pos_y + comp_c/2, "ÁREA CONSTRUÍDA", ha='center', va='center', fontweight='bold')
    
    # Desenha o Portão (marrom)
    if tem_portao:
        ax.add_patch(patches.Rectangle((pos_x + pos_p, pos_y), larg_p, 0.5, facecolor='#8B4513', edgecolor='black'))
        ax.text(pos_x + pos_p + larg_p/2, pos_y + 0.25, "PORTÃO", ha='center', va='center', color='white', fontsize=8)

    # Ajusta o zoom da imagem
    ax.set_xlim(-2, larg_t + 2)
    ax.set_ylim(-2, comp_t + 2)
    ax.set_aspect('equal')
    plt.axis('off')
    
    st.pyplot(fig)

with col2:
    st.subheader("📋 Quadro de Áreas")
    df = pd.DataFrame({
        "Descrição": ["Terreno", "Área Construída"],
        "Área (m²)": [f"{area_t:.2f}", f"{area_c_calc:.2f}"]
    })
    st.table(df)
