import streamlit as st
from streamlit_elements import elements, mui, html, dashboard

# Configuração de estado para salvar a posição dos objetos
if "layout" not in st.session_state:
    st.session_state.layout = [
        # x, y, largura, altura
        dashboard.Item("construcao", 0, 0, 4, 3), 
    ]
if "portas" not in st.session_state:
    st.session_state.portas = []

st.title("🏗️ Editor Interativo - General")

with st.sidebar:
    st.header("Ferramentas")
    if st.button("🚪 Adicionar Porta"):
        nova_porta_id = f"porta_{len(st.session_state.portas) + 1}"
        st.session_state.portas.append(nova_porta_id)
        # Adiciona a porta ao layout do dashboard para ser arrastável
        st.session_state.layout.append(dashboard.Item(nova_porta_id, 1, 1, 1, 1))

# Área de desenho interativa
with elements("planta_interativa"):
    # Define a grade onde os objetos podem ser movidos
    with dashboard.Grid(st.session_state.layout):
        # O bloco da construção
        mui.Paper(
            "ÁREA CONSTRUÍDA",
            key="construcao",
            sx={"display": "flex", "alignItems": "center", "justifyContent": "center", "bgcolor": "#f0f0f0", "border": "2px solid black"}
        )
        
        # As portas adicionadas
        for porta_id in st.session_state.portas:
            mui.Paper(
                "PORTA",
                key=porta_id,
                sx={"display": "flex", "alignItems": "center", "justifyContent": "center", "bgcolor": "brown", "color": "white"}
            )

st.info("💡 Arraste os cantos para redimensionar e o centro para mover.")
