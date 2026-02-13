import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import os

st.set_page_config(layout="wide", page_title="Planta Pro - CETESB")

ESCALA = 40 

# --- SISTEMA DE MEMÓRIA ANTI-AMNÉSIA ---
if 'dados_comodos' not in st.session_state:
    st.session_state.dados_comodos = []

if 'estado_atual' not in st.session_state:
    st.session_state.estado_atual = {
        "version": "4.4.0",
        "objects": [{
            "type": "rect", "left": 10, "top": 10, 
            "width": 20 * ESCALA, "height": 30 * ESCALA,
            "fill": "transparent", "stroke": "#333333", 
            "strokeWidth": 2, "strokeDashArray": [10, 5]
        }]
    }

# --- INTERFACE REFINADA ---
st.markdown("<h1 style='text-align: center; color: #2C3E50;'>🏗️ Gerador de Planta Baixa - Padrão CETESB</h1>", unsafe_allow_html=True)
st.divider()

col_canvas, col_painel = st.columns([3, 1], gap="large")

with col_painel:
    st.markdown("### 🛠️ Painel de Controle")
    
    with st.expander("➕ 1. Adicionar Setor/Cômodo", expanded=True):
        nome = st.text_input("Identificação", placeholder="Ex: Área de Produção")
        c1, c2 = st.columns(2)
        larg_m = c1.number_input("Largura (m)", min_value=1.0, value=5.0, step=0.5)
        comp_m = c2.number_input("Comprimento (m)", min_value=1.0, value=5.0, step=0.5)
        cor = st.color_picker("Cor de Destaque", "#D6EAF8")

        if st.button("Inserir Setor", use_container_width=True):
            if nome:
                st.session_state.dados_comodos.append({"Setor": nome, "Área (m²)": larg_m * comp_m})
                novo_bloco = {
                    "type": "rect", "left": 50, "top": 50, 
                    "width": larg_m * ESCALA, "height": comp_m * ESCALA,
                    "fill": cor, "stroke": "#2C3E50", "strokeWidth": 2, "opacity": 0.9
                }
                st.session_state.estado_atual["objects"].append(novo_bloco)
                st.rerun()

    with st.expander("🚪 2. Adicionar Porta"):
        larg_porta = st.number_input("Vão da Porta (m)", min_value=0.60, value=0.80, step=0.10)
        if st.button("Inserir Porta", use_container_width=True):
            w_px = larg_porta * ESCALA
            nova_porta = {
                "type": "path",
                "path": [["M", 0, 0], ["L", 0, -w_px], ["A", w_px, w_px, 0, 0, 1, w_px, 0]],
                "left": 100, "top": 100,
                "fill": "transparent", "stroke": "#A04000", "strokeWidth": 3, "opacity": 1.0
            }
            st.session_state.estado_atual["objects"].append(nova_porta)
            st.rerun()
            
    st.markdown("### 📋 Quadro de Áreas")
    df = pd.DataFrame(st.session_state.dados_comodos)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.success(f"**Área Total Construída:** {df['Área (m²)'].sum():.2f} m²")
    else:
        st.info("Nenhum setor adicionado.")

    if st.button("🗑️ Limpar Projeto", type="secondary", use_container_width=True):
        st.session_state.dados_comodos = []
        st.session_state.estado_atual["objects"] = [st.session_state.estado_atual["objects"][0]]
        st.rerun()

with col_canvas:
    st.caption("🖱️ Clique e arraste para posicionar. Use as bordas para ajustar. As alterações não serão perdidas.")
    
    # O Canvas
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=2,
        background_color="#F8F9F9",
        initial_drawing=st.session_state.estado_atual,
        drawing_mode="transform", 
        width=900, height=650,
        key="canvas",
    )
    
    # A TRAVA DE MEMÓRIA: Atualiza o estado silenciosamente sempre que você mexe o mouse
    if canvas_result.json_data is not None:
        st.session_state.estado_atual = canvas_result.json_data

st.divider()

# --- MÓDULO DE EXPORTAÇÃO PDF ---
st.markdown("### 🖨️ Exportação Oficial")
col_pdf, _ = st.columns([1, 3])
with col_pdf:
    if st.button("📄 Gerar PDF do Projeto", type="primary", use_container_width=True):
        if canvas_result.image_data is not None:
            # Converte o desenho da tela para imagem
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            img = img.convert('RGB')
            img.save("planta_temp.jpg")
            
            # Monta o PDF profissional
            pdf = FPDF(orientation="L", unit="mm", format="A4")
            pdf.add_page()
            
            # Cabeçalho
            pdf.set_font("helvetica", "B", 16)
            pdf.cell(0, 10, "PLANTA DE LAYOUT - LICENCIAMENTO AMBIENTAL (CETESB)", ln=True, align="C")
            pdf.set_font("helvetica", "", 12)
            pdf.cell(0, 8, "Proprietário(a): Priscila", ln=True, align="C")
            pdf.cell(0, 8, "Responsável Técnico: General", ln=True, align="C")
            pdf.line(10, 35, 287, 35) # Linha divisória
            
            # Insere a planta
            pdf.image("planta_temp.jpg", x=40, y=40, w=210)
            
            # Roda o arquivo pra download
            pdf.output("Planta_CETESB.pdf")
            
            with open("Planta_CETESB.pdf", "rb") as f:
                st.download_button("⬇️ Baixar Arquivo PDF", f, file_name="Planta_CETESB.pdf", mime="application/pdf")
