import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏗️ Planta Baixa - Modo Precisão")

# Memória para guardar os cômodos
if 'comodos' not in st.session_state:
    st.session_state.comodos = []

with st.sidebar:
    st.header("1. O Terreno")
    larg_t = st.number_input("Largura Terreno (eixo X)", value=20.0)
    comp_t = st.number_input("Comprimento Terreno (eixo Y)", value=30.0)

    st.divider()
    
    st.header("2. Adicionar Cômodo/Setor")
    nome = st.text_input("Nome (ex: Produção, Depósito)")
    larg_c = st.number_input("Largura (m)", value=5.0)
    comp_c = st.number_input("Comprimento (m)", value=5.0)
    
    st.markdown("**Posição no Terreno:**")
    pos_x = st.number_input("Distância da Esquerda (X)", value=0.0)
    pos_y = st.number_input("Distância do Fundo (Y)", value=0.0)

    if st.button("➕ Inserir Cômodo"):
        if nome:
            st.session_state.comodos.append({
                "Nome": nome, "W": larg_c, "H": comp_c, "X": pos_x, "Y": pos_y, "Area": larg_c * comp_c
            })
        else:
            st.error("Dê um nome pro cômodo!")
    
    if st.button("🗑️ Limpar Tudo"):
        st.session_state.comodos = []
        st.rerun()

# --- Desenho da Planta ---
col1, col2 = st.columns([3, 1])

with col1:
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Terreno (Tracejado)
    ax.add_patch(patches.Rectangle((0, 0), larg_t, comp_t, fill=False, edgecolor='black', lw=2, linestyle='--'))
    
    # Renderiza os cômodos que você adicionou
    for c in st.session_state.comodos:
        ax.add_patch(patches.Rectangle((c['X'], c['Y']), c['W'], c['H'], facecolor='#d3d3d3', edgecolor='black', lw=1.5))
        # Escreve o nome e a área no meio do bloco
        ax.text(c['X'] + c['W']/2, c['Y'] + c['H']/2, f"{c['Nome']}\n{c['Area']:.2f}m²", ha='center', va='center', fontsize=9, fontweight='bold')

    # Ajusta câmera
    ax.set_xlim(-1, larg_t + 1)
    ax.set_ylim(-1, comp_t + 1)
    ax.set_aspect('equal')
    plt.axis('off')
    st.pyplot(fig)

with col2:
    st.subheader("📋 Quadro de Áreas")
    if st.session_state.comodos:
        df = pd.DataFrame(st.session_state.comodos)[["Nome", "Area"]]
        st.table(df)
        st.metric("Área Total Construída", f"{df['Area'].sum():.2f} m²")
    else:
        st.write("Nenhum cômodo adicionado ainda.")
