import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gerador de Galpão PRO", layout="wide")
st.title("🏭 Gerador de Layout Industrial - Modo General")

# --- INICIALIZAR MEMÓRIA (SESSION STATE) ---
# É aqui que a mágica acontece: o site "lembra" o que você adicionou
if 'comodos' not in st.session_state:
    st.session_state['comodos'] = []

# --- FUNÇÕES DE DESENHO ---
def gerar_dxf_completo(larg_total, comp_total, lista_comodos):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Criar Camadas (Layers)
    doc.layers.new(name='ESTRUTURA_EXTERNA', dxfattribs={'color': 7}) # Branco
    doc.layers.new(name='PAREDES_INTERNAS', dxfattribs={'color': 6}) # Magenta
    doc.layers.new(name='TEXTOS', dxfattribs={'color': 2}) # Amarelo

    # 1. Desenha o Galpão Principal
    pontos_externos = [(0, 0), (larg_total, 0), (larg_total, comp_total), (0, comp_total), (0, 0)]
    msp.add_lwpolyline(pontos_externos, dxfattribs={'layer': 'ESTRUTURA_EXTERNA'})

    # 2. Desenha os Cômodos (A MÁGICA)
    for item in lista_comodos:
        x, y = item['x'], item['y']
        l, c = item['largura'], item['comprimento']
        nome = item['nome']
        
        # Desenha as paredes do cômodo
        pontos_interno = [(x, y), (x+l, y), (x+l, y+c), (x, y+c), (x, y)]
        msp.add_lwpolyline(pontos_interno, dxfattribs={'layer': 'PAREDES_INTERNAS'})
        
        # Escreve o nome no meio do cômodo automaticamente
        msp.add_text(nome, dxfattribs={'layer': 'TEXTOS', 'height': 0.3}).set_pos((x + l/2, y + c/2), align='MIDDLE_CENTER')

    # Retorna o arquivo
    output = io.StringIO()
    doc.write(output)
    return output.getvalue()

def plotar_preview_interativo(larg_total, comp_total, lista_comodos):
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Galpão Principal (Cinza Claro)
    rect_main = patches.Rectangle((0, 0), larg_total, comp_total, linewidth=3, edgecolor='black', facecolor='#f0f0f0')
    ax.add_patch(rect_main)
    
    # Desenha os Cômodos
    for item in lista_comodos:
        rect = patches.Rectangle((item['x'], item['y']), item['largura'], item['comprimento'], 
                                 linewidth=2, edgecolor='blue', facecolor='#a0cbe8', alpha=0.5)
        ax.add_patch(rect)
        # Texto no centro
        ax.text(item['x'] + item['largura']/2, item['y'] + item['comprimento']/2, item['nome'], 
                ha='center', va='center', fontsize=9, color='darkblue', weight='bold')

    ax.set_xlim(-2, larg_total + 2)
    ax.set_ylim(-2, comp_total + 2)
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.3)
    return fig

# --- INTERFACE DO USUÁRIO ---
col_config, col_preview = st.columns([1, 2])

with col_config:
    st.header("1. O Galpão")
    largura = st.number_input("Largura Total (m)", 10.0, 100.0, 15.0)
    comprimento = st.number_input("Comprimento Total (m)", 10.0, 100.0, 30.0)
    
    st.divider()
    
    st.header("2. Adicionar Blocos")
    tipo_comodo = st.selectbox("O que vamos construir?", ["Escritório", "Banheiro", "Almoxarifado", "Produção", "Refeitório"])
    
    c1, c2 = st.columns(2)
    w_comodo = c1.number_input("Largura Cômodo", 1.0, 20.0, 3.0)
    h_comodo = c2.number_input("Comp. Cômodo", 1.0, 20.0, 3.0)
    
    st.info("Onde vai ficar? (Canto inferior esquerdo é o 0,0)")
    c3, c4 = st.columns(2)
    pos_x = c3.number_input("Posição X", 0.0, largura, 0.0)
    pos_y = c4.number_input("Posição Y", 0.0, comprimento, 0.0)
    
    if st.button("➕ Adicionar Bloco na Planta"):
        novo_comodo = {
            'nome': tipo_comodo,
            'largura': w_comodo,
            'comprimento': h_comodo,
            'x': pos_x,
            'y': pos_y
        }
        st.session_state['comodos'].append(novo_comodo)
        st.success(f"{tipo_comodo} adicionado!")

    if st.button("🗑️ Limpar Tudo (Resetar)"):
        st.session_state['comodos'] = []
        st.rerun()

with col_preview:
    st.subheader("👀 Planta Baixa em Tempo Real")
    fig = plotar_preview_interativo(largura, comprimento, st.session_state['comodos'])
    st.pyplot(fig)
    
    st.divider()
    
    # Botão de Download
    dxf_bytes = gerar_dxf_completo(largura, comprimento, st.session_state['comodos'])
    st.download_button(
        label="📥 BAIXAR PROJETO PARA COREL (.DXF)",
        data=dxf_bytes,
        file_name="planta_industrial_general.dxf",
        mime="application/dxf"
    )
