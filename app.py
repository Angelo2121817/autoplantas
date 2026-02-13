import streamlit as st
from streamlit_drawable_canvas import st_canvas
import ezdxf
import pandas as pd
import io

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Layout Industrial Visual", layout="wide")
st.title("🏭 General CAD: O Arrasta-e-Solta")

# --- BARRA LATERAL: CONFIGURAÇÕES DO GALPÃO ---
st.sidebar.header("1. Tamanho do Galpão (Metros)")
largura_real = st.sidebar.number_input("Largura (m)", 10.0, 100.0, 20.0)
comprimento_real = st.sidebar.number_input("Comprimento (m)", 10.0, 100.0, 30.0)

st.sidebar.markdown("---")
st.sidebar.header("2. Ferramentas")
# O segredo tá aqui: Transform permite mover os quadrados
modo_ferramenta = st.sidebar.radio("O que você quer fazer?", 
    ("Desenhar Quadrado (rect)", "Mover/Editar (transform)", "Apagar (delete)"))

# Mapeando o nome bonito pro nome técnico da lib
mode_map = {
    "Desenhar Quadrado (rect)": "rect",
    "Mover/Editar (transform)": "transform",
    "Apagar (delete)": "freedraw" # Delete funciona selecionando e apertando Del no teclado na vdd
}
tool = mode_map[modo_ferramenta]

# Cor do preenchimento pra facilitar a visão
fill_color = st.sidebar.color_picker("Cor do Bloco", "#00FFAA")

# --- ÁREA DE DESENHO (CANVAS) ---
st.subheader("Área de Projeto")
st.info("💡 Dica: Selecione 'Desenhar' para criar salas. Depois mude para 'Mover' para arrastar elas.")

# Definindo a escala: Vamos fixar a largura da tela em 800 pixels
LARGURA_CANVAS_PX = 800
# Calcula a altura proporcional pra não distorcer o galpão
escala_px_por_metro = LARGURA_CANVAS_PX / largura_real
ALTURA_CANVAS_PX = int(comprimento_real * escala_px_por_metro)

# O Canvas Mágico
canvas_result = st_canvas(
    fill_color=fill_color,
    stroke_width=2,
    stroke_color="#000000",
    background_color="#eeeeee", # Cinza claro pra simular o chão
    height=ALTURA_CANVAS_PX,
    width=LARGURA_CANVAS_PX,
    drawing_mode=tool,
    key="canvas_galpao",
    display_toolbar=True, # Mostra barra de ferramentas extra
)

# --- PROCESSAMENTO DOS DADOS ---
if canvas_result.json_data is not None:
    objetos = canvas_result.json_data["objects"]
    df = pd.json_normalize(objetos) # Transforma o JSON em tabela pra gente ler

    # Se tiver algum desenho lá dentro...
    if not df.empty:
        st.write("📋 **Lista de Blocos Detectados:**")
        
        # Filtra só o que interessa
        blocos = []
        for index, row in df.iterrows():
            if row['type'] == 'rect':
                # CONVERSÃO CRÍTICA: PIXEL -> METROS
                # O Y no Canvas cresce pra baixo, no CAD cresce pra cima. Tem que inverter.
                
                x_metros = row['left'] / escala_px_por_metro
                # Invertendo o eixo Y
                y_canvas_invertido = ALTURA_CANVAS_PX - (row['top'] + row['height'])
                y_metros = y_canvas_invertido / escala_px_por_metro
                
                w_metros = row['width'] / escala_px_por_metro
                h_metros = row['height'] / escala_px_por_metro
                
                blocos.append({
                    'x': x_metros, 'y': y_metros, 
                    'l': w_metros, 'h': h_metros
                })
                
        st.dataframe(pd.DataFrame(blocos)) # Mostra a tabelinha pro General conferir

        # --- BOTÃO DE EXPORTAR DXF ---
        def gerar_dxf_visual():
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            
            # Layer do Galpão
            doc.layers.new(name='GALPAO', dxfattribs={'color': 7})
            doc.layers.new(name='COMODOS', dxfattribs={'color': 4}) # Ciano

            # Desenha o contorno do galpão
            msp.add_lwpolyline([(0, 0), (largura_real, 0), (largura_real, comprimento_real), (0, comprimento_real), (0, 0)], dxfattribs={'layer': 'GALPAO'})

            # Desenha os blocos que você arrastou
            for b in blocos:
                # ezdxf desenha polilinha fechada
                pontos = [
                    (b['x'], b['y']),
                    (b['x'] + b['l'], b['y']),
                    (b['x'] + b['l'], b['y'] + b['h']),
                    (b['x'], b['y'] + b['h']),
                    (b['x'], b['y'])
                ]
                msp.add_lwpolyline(pontos, dxfattribs={'layer': 'COMODOS'})
                
                # Texto de cota
                texto = f"{b['l']:.1f}x{b['h']:.1f}m"
                msp.add_text(texto, dxfattribs={'height': 0.3, 'layer': 'COMODOS'}).set_pos((b['x'], b['y']+b['h']+0.1))

            output = io.StringIO()
            doc.write(output)
            return output.getvalue()

        dxf_data = gerar_dxf_visual()
        
        st.download_button(
            label="💾 Baixar DXF do Layout Atual",
            data=dxf_data,
            file_name="layout_visual.dxf",
            mime="application/dxf"
        )
