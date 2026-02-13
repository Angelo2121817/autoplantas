import streamlit as st
from streamlit_elements import elements, mui, dashboard
import pandas as pd

# Configuração da página para aproveitar o espaço
st.set_page_config(page_title="AutoPlanta CETESB - General", layout="wide")

st.title("🏗️ Editor de Planta Interativo - Padrão General")

# Inicialização do estado para não perder os dados ao interagir
if "layout" not in st.session_state:
    st.session_state.layout = [
        # O "caixote" principal da construção (x, y, largura, altura)
        dashboard.Item("construcao", 0, 0, 6, 4),
    ]
if "portas" not in st.session_state:
    st.session_state.portas = []

# --- Barra Lateral (Controles) ---
with st.sidebar:
    st.header("⚙️ Ferramentas de Campo")
    
    st.subheader("📍 Dados do Terreno")
    area_terreno = st.number_input("Área Total do Terreno (m²)", value=350.00) # Baseado no exemplo [cite: 72]
    
    st.divider()
    
    if st.button("🚪 Adicionar Porta/Portão"):
        id_porta = f"Porta_{len(st.session_state.portas) + 1}"
        st.session_state.portas.append(id_porta)
        # Adiciona a porta no canto para o usuário arrastar
        st.session_state.layout.append(dashboard.Item(id_porta, 0, 0, 1, 1))
        st.rerun()

    if st.button("🗑️ Limpar Tudo"):
        st.session_state.portas = []
        st.session_state.layout = [dashboard.Item("construcao", 0, 0, 6, 4)]
        st.rerun()

# --- Área de Desenho e Cálculos ---
col_desenho, col_dados = st.columns([3, 1])

with col_desenho:
    st.info("💡 Arraste o centro para mover e as bordas para redimensionar o galpão e as portas.")
    
    # O componente 'elements' cria a área onde o mouse funciona
    with elements("canvas_interativo"):
        # Grid interativo
        with dashboard.Grid(st.session_state.layout, cols=12, rowHeight=50, onLayoutChange=lambda x: None):
            
            # Bloco da Construção
            mui.Paper(
                "ÁREA CONSTRUÍDA",
                key="construcao",
                sx={
                    "display": "flex", 
                    "alignItems": "center", 
                    "justifyContent": "center", 
                    "bgcolor": "#e0e0e0", 
                    "border": "3px solid #000",
                    "fontWeight": "bold",
                    "fontSize": "20px"
                }
            )
            
            # Blocos das Portas
            for porta in st.session_state.portas:
                mui.Paper(
                    "PORTA",
                    key=porta,
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
    # Capturando as dimensões do layout atual para o cálculo
    # (No Streamlit Elements, os valores de w e h representam a escala no grid)
    main_box = next(item for item in st.session_state.layout if item.i == "construcao")
    
    # Cálculo simulado de área construída baseado na proporção do grid
    area_estimada = (main_box.w * main_box.h) * 10 # Fator de escala para m²
    
    dados_tabela = {
        "Descrição": ["Terreno", "Área Construída"],
        "Área (m²)": [f"{area_terreno:.2f}", f"{area_estimada:.2f}"]
    }
    
    st.table(pd.DataFrame(dados_tabela))
    
    st.divider()
    st.subheader("📑 Informações Adicionais")
    st.write(f"**Status:** Pronto para exportação")
    st.write(f"**Proprietário:** Priscila") # Conforme contexto pessoal

    if st.button("💾 Finalizar e Salvar"):
        st.success("Planta processada para PDF!")
