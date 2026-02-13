import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
from fpdf import FPDF
import io

st.set_page_config(layout="wide", page_title="Planta Lego - CETESB")

# Memória dos Blocos (Lego)
if 'blocos' not in st.session_state:
    st.session_state.blocos = []

st.markdown("<h1 style='text-align: center;'>🏗️ Montador de Planta - Padrão CETESB</h1>", unsafe_allow_html=True)
st.divider()

col_painel, col_tela = st.columns([1, 3], gap="large")

with col_painel:
    st.markdown("### 🧱 Peças do Lego")
    
    with st.form("form_bloco"):
        nome = st.text_input("Nome do Cômodo", placeholder="Ex: Sala Amarração [cite: 113]")
        c1, c2 = st.columns(2)
        larg = c1.number_input("Largura (m) [X]", min_value=0.5, value=5.0, step=0.5)
        comp = c2.number_input("Comprimento (m) [Y]", min_value=0.5, value=5.0, step=0.5)
        
        st.markdown("**Posição no Terreno (Onde encaixar):**")
        p1, p2 = st.columns(2)
        pos_x = p1.number_input("Distância da Esquerda", value=0.0, step=0.5)
        pos_y = p2.number_input("Distância do Fundo", value=0.0, step=0.5)
        
        add_btn = st.form_submit_button("➕ Encaixar Bloco")
        
        if add_btn and nome:
            st.session_state.blocos.append({
                "Nome": nome, "W": larg, "H": comp, "X": pos_x, "Y": pos_y, "Area": larg * comp
            })
            st.rerun()

    st.markdown("### 📋 Quadro de Áreas: $m^{2}$ [cite: 134]")
    if st.session_state.blocos:
        df = pd.DataFrame(st.session_state.blocos)[["Nome", "Area"]]
        st.dataframe(df, hide_index=True, use_container_width=True)
        area_total = df["Area"].sum()
        st.success(f"**CONSTRUÍDA {area_total:.2f} [cite: 137]**")
    else:
        st.info("Nenhum bloco encaixado.")
        area_total = 0

    if st.button("🗑️ Demolir Tudo", use_container_width=True):
        st.session_state.blocos = []
        st.rerun()

with col_tela:
    # A Mágica do Acabamento Automático
    fig, ax = plt.subplots(figsize=(10, 14)) # Proporção retrato parecida com seu PDF
    
    # Se não tiver blocos, desenha um grid vazio de referência
    if not st.session_state.blocos:
        ax.set_xlim(0, 20)
        ax.set_ylim(0, 30)
        ax.text(10, 15, "Adicione blocos na lateral...", ha='center', color='gray')
    else:
        # Pega os limites máximos pra ajustar a câmera automaticamente
        max_x = max([b["X"] + b["W"] for b in st.session_state.blocos]) + 2
        max_y = max([b["Y"] + b["H"] for b in st.session_state.blocos]) + 2
        ax.set_xlim(-1, max_x)
        ax.set_ylim(-1, max_y)
        
        # Desenha cada bloco de Lego
        for b in st.session_state.blocos:
            # Retângulo com linha grossa (imita parede)
            rect = patches.Rectangle(
                (b["X"], b["Y"]), b["W"], b["H"], 
                linewidth=2.5, edgecolor='black', facecolor='white', zorder=2
            )
            ax.add_patch(rect)
            
            # Texto no meio exato do bloco igual no seu PDF
            texto = f"{b['Nome']}\nArea {b['Area']:.2f}m2"
            ax.text(
                b["X"] + b["W"]/2, b["Y"] + b["H"]/2, texto, 
                ha='center', va='center', fontsize=10, 
                fontweight='bold', color='black', zorder=3
            )

    ax.set_aspect('equal')
    plt.axis('off') # Tira as bordas feias do gráfico
    st.pyplot(fig)

st.divider()

# --- Módulo PDF Faca na Caveira ---
if st.session_state.blocos:
    # Salva o gráfico em memória pra jogar no PDF
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "PLANTA BAIXA - LAYOUT CETESB", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Proprietária: Priscila", ln=True, align="C")
    pdf.cell(0, 6, "Resp. Técnico: General", ln=True, align="C")
    pdf.line(10, 30, 200, 30)
    
    # Cola a imagem do gráfico no PDF
    # Tratando arquivo em memória com arquivo temporário seguro
    with open("planta_temp.png", "wb") as f:
        f.write(buf.getvalue())
    
    pdf.image("planta_temp.png", x=15, y=35, w=180)
    
    # Roda o PDF
    pdf.output("Planta_CETESB_Final.pdf")
    
    with open("Planta_CETESB_Final.pdf", "rb") as f:
        st.download_button(
            label="📄 Gerar e Baixar PDF Oficial", 
            data=f, 
            file_name="Planta_CETESB_Final.pdf", 
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
