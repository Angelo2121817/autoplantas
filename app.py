import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Gerador de Plantas - General v1.0", layout="wide")

st.title("🏗️ Automatizador de Plantas - Padrão CETESB")
st.write("Insira as medidas e gere sua planta profissional em segundos.")

# Sidebar para Dados do Terreno
with st.sidebar:
    st.header("📍 Dados do Terreno")
    largura_t = st.number_input("Largura do Terreno (m)", value=20.0)
    comprimento_t = st.number_input("Comprimento do Terreno (m)", value=35.0)
    
    st.divider()
    st.header("🏢 Adicionar Áreas")
    nome_setor = st.text_input("Nome do Setor (Ex: Galpão, Escritório)")
    larg_s = st.number_input("Largura do Setor (m)", value=5.0)
    comp_s = st.number_input("Comprimento do Setor (m)", value=5.0)
    pos_x = st.number_input("Posição X (distância da esquerda)", value=0.0)
    pos_y = st.number_input("Posição Y (distância do fundo)", value=0.0)

    if 'setores' not in st.session_state:
        st.session_state.setores = []

    if st.button("Adicionar Setor"):
        st.session_state.setores.append({
            "Setor": nome_setor,
            "L": larg_s,
            "C": comp_s,
            "X": pos_x,
            "Y": pos_y,
            "Area": larg_s * comp_s
        })

# Layout das Colunas
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📐 Representação Visual")
    fig, ax = plt.subplots(figsize=(10, 12))
    
    # Desenha o Terreno (Linha grossa)
    terreno = patches.Rectangle((0, 0), largura_t, comprimento_t, linewidth=2, edgecolor='black', facecolor='none', linestyle='--')
    ax.add_patch(terreno)
    
    # Desenha cada setor adicionado
    for s in st.session_state.setores:
        rect = patches.Rectangle((s['X'], s['Y']), s['L'], s['C'], linewidth=1.5, edgecolor='blue', facecolor='#e6f3ff')
        ax.add_patch(rect)
        # Label no centro do retângulo
        ax.text(s['X'] + s['L']/2, s['Y'] + s['C']/2, f"{s['Setor']}\n{s['Area']:.2f}m²", 
                ha='center', va='center', fontsize=8, fontweight='bold')

    # Ajustes do Gráfico
    ax.set_xlim(-2, largura_t + 2)
    ax.set_ylim(-2, comprimento_t + 2)
    ax.set_aspect('equal', adjustable='box')
    plt.axis('off')
    st.pyplot(fig)

with col2:
    st.subheader("📋 Quadro de Áreas")
    if st.session_state.setores:
        df = pd.DataFrame(st.session_state.setores)
        # Exibe a tabela no padrão da Planta 2026
        st.table(df[['Setor', 'Area']])
        
        total_area = df['Area'].sum()
        st.metric("ÁREA TOTAL CONSTRUÍDA", f"{total_area:.2f} m²")
        
        if st.button("Limpar Tudo"):
            st.session_state.setores = []
            st.rerun()

# Botão para salvar
st.download_button("Baixar Planta (PDF)", "Funcionalidade em desenvolvimento...", file_name="planta_baixa.pdf")
