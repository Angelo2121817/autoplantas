import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import io

# Configuração da página pra não ficar com cara de site amador
st.set_page_config(page_title="Gerador de Galpão do General", layout="wide")

st.title("🏭 Gerador de Barracão Industrial - Padrão General")
st.markdown("Bota as medidas aí e para de perder tempo desenhando linha por linha.")

# --- BARRA LATERAL (ENTRADA DE DADOS) ---
with st.sidebar:
    st.header("Dimensões do Monstro")
    largura = st.number_input("Largura (m)", min_value=5.0, value=15.0, step=0.5)
    comprimento = st.number_input("Comprimento (m)", min_value=5.0, value=30.0, step=0.5)
    
    st.header("Estrutura")
    distancia_pilares = st.number_input("Distância entre Pilares (m)", min_value=3.0, value=5.0, step=0.5)
    
    nome_arquivo = st.text_input("Nome do Arquivo", value="Projeto_Barracao.dxf")

# --- FUNÇÃO QUE GERA O DXF ---
def gerar_dxf(larg, comp, dist_pilares):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Camadas
    doc.layers.new(name='PAREDES', dxfattribs={'color': 7})
    doc.layers.new(name='PILARES', dxfattribs={'color': 1}) # Vermelho

    # 1. Desenha o Retângulo Externo (Paredes)
    pontos_parede = [(0, 0), (larg, 0), (larg, comp), (0, comp), (0, 0)]
    msp.add_lwpolyline(pontos_parede, dxfattribs={'layer': 'PAREDES'})

    # 2. Desenha os Pilares (Calcula quantos cabem)
    num_pilares_lado = int(comp / dist_pilares) + 1
    tamanho_pilar = 0.40 # 40cm de pilar, padrãozão
    
    # Pilares da esquerda e direita
    for i in range(num_pilares_lado):
        y = i * dist_pilares
        if y > comp: break # Proteção pra não desenhar fora
        
        # Pilar Esquerda
        msp.add_lwpolyline([(0, y), (tamanho_pilar, y), (tamanho_pilar, y+tamanho_pilar), (0, y+tamanho_pilar), (0, y)], dxfattribs={'layer': 'PILARES'})
        
        # Pilar Direita
        msp.add_lwpolyline([(larg-tamanho_pilar, y), (larg, y), (larg, y+tamanho_pilar), (larg-tamanho_pilar, y+tamanho_pilar), (larg-tamanho_pilar, y)], dxfattribs={'layer': 'PILARES'})

    # Retorna o arquivo na memória (buffer)
    output = io.StringIO()
    doc.write(output)
    return output.getvalue()

# --- FUNÇÃO DO PREVIEW (VISUALIZAÇÃO NA TELA) ---
def plotar_preview(larg, comp):
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Desenha o retângulo
    rect = plt.Rectangle((0, 0), larg, comp, fill=False, color='black', linewidth=2)
    ax.add_patch(rect)
    
    # Ajusta os limites do gráfico pra ficar proporcional
    ax.set_xlim(-5, larg + 5)
    ax.set_ylim(-5, comp + 5)
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_title(f"Preview: {larg}m x {comp}m")
    
    return fig

# --- A MÁGICA ACONTECE AQUI ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("👀 Olhada Rápida")
    fig = plotar_preview(largura, comprimento)
    st.pyplot(fig)

with col2:
    st.subheader("💾 Baixar Planta")
    st.write("Se gostou do desenho, baixa logo essa porcaria.")
    
    # Gera o DXF na memória
    dxf_data = gerar_dxf(largura, comprimento, distancia_pilares)
    
    # Botão de Download
    st.download_button(
        label="BAIXAR ARQUIVO .DXF",
        data=dxf_data,
        file_name=nome_arquivo if nome_arquivo.endswith('.dxf') else f"{nome_arquivo}.dxf",
        mime="application/dxf"
    )
