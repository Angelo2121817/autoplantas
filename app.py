import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io

from streamlit_drawable_canvas import st_canvas
from ezdxf.enums import TextEntityAlignment

# ---------------------------
# DXF (corrigido)
# ---------------------------
def gerar_dxf_completo(larg_total, comp_total, lista_comodos):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    doc.layers.new(name="ESTRUTURA_EXTERNA", dxfattribs={"color": 7})
    doc.layers.new(name="PAREDES_INTERNAS", dxfattribs={"color": 6})
    doc.layers.new(name="TEXTOS", dxfattribs={"color": 2})

    pontos_externos = [(0, 0), (larg_total, 0), (larg_total, comp_total), (0, comp_total), (0, 0)]
    msp.add_lwpolyline(pontos_externos, dxfattribs={"layer": "ESTRUTURA_EXTERNA"})

    for item in lista_comodos:
        x, y = item["x"], item["y"]
        l, c = item["largura"], item["comprimento"]
        nome = item["nome"]

        pontos_interno = [(x, y), (x + l, y), (x + l, y + c), (x, y + c), (x, y)]
        msp.add_lwpolyline(pontos_interno, dxfattribs={"layer": "PAREDES_INTERNAS"})

       txt = msp.add_text(nome, dxfattribs={'layer': 'TEXTOS', 'height': 0.3})
txt.set_placement((x + l/2, y + c/2), align="MIDDLE_CENTER")

    output = io.StringIO()
    doc.write(output)
    return output.getvalue()

# ---------------------------
# Conversões px <-> m
# ---------------------------
def m_para_px(valor_m, escala_px_por_m):
    return valor_m * escala_px_por_m

def px_para_m(valor_px, escala_px_por_m):
    return valor_px / escala_px_por_m

# ---------------------------
# Streamlit
# ---------------------------
st.set_page_config(page_title="AutoPlantas", layout="wide")
st.title("AutoPlantas — blocos arrastáveis")

if "comodos" not in st.session_state:
    st.session_state["comodos"] = []

col_config, col_canvas = st.columns([1, 2])

with col_config:
    st.header("Terreno / Galpão")
    largura_m = st.number_input("Largura total (m)", 10.0, 200.0, 15.0)
    comprimento_m = st.number_input("Comprimento total (m)", 10.0, 200.0, 30.0)

    st.divider()
    st.header("Escala")
    escala_px_por_m = st.slider("px por metro", 10, 200, 50)

    st.divider()
    st.header("Adicionar bloco (entra no canvas)")
    tipo = st.selectbox("Tipo", ["Escritório", "Banheiro", "Almoxarifado", "Produção", "Refeitório"])
    c1, c2 = st.columns(2)
    w_m = c1.number_input("Largura (m)", 1.0, 50.0, 3.0)
    h_m = c2.number_input("Comprimento (m)", 1.0, 50.0, 3.0)

    if st.button("➕ Adicionar bloco"):
        st.session_state["comodos"].append({
            "nome": tipo,
            "largura": w_m,
            "comprimento": h_m,
            "x": 0.0,
            "y": 0.0
        })
        st.rerun()

    if st.button("🗑️ Limpar tudo"):
        st.session_state["comodos"] = []
        st.rerun()

with col_canvas:
    st.subheader("Arraste os blocos no canvas")

    # tamanho do canvas em px baseado no galpão em metros
    canvas_w = int(m_para_px(largura_m, escala_px_por_m))
    canvas_h = int(m_para_px(comprimento_m, escala_px_por_m))

    # monta objetos iniciais para o canvas
    initial_objects = []
    for i, c in enumerate(st.session_state["comodos"]):
        initial_objects.append({
            "type": "rect",
            "left": m_para_px(c["x"], escala_px_por_m),
            "top": m_para_px(c["y"], escala_px_por_m),
            "width": m_para_px(c["largura"], escala_px_por_m),
            "height": m_para_px(c["comprimento"], escala_px_por_m),
            "fill": "rgba(160,203,232,0.5)",
            "stroke": "blue",
            "strokeWidth": 2,
            "name": c["nome"],  # metadado
            "object_id": i      # id pra mapear de volta
        })

    # desenha o canvas
    canvas_result = st_canvas(
        fill_color="rgba(0, 0, 0, 0)",
        stroke_width=2,
        stroke_color="blue",
        background_color="#f0f0f0",
        width=canvas_w,
        height=canvas_h,
        drawing_mode="transform",  # permite mover/redimensionar
        initial_drawing={"version": "4.4.0", "objects": initial_objects},
        key="canvas_planta",
        update_streamlit=True,
    )

    # Atualiza session_state com base no JSON do canvas (posições em px)
    if canvas_result.json_data and "objects" in canvas_result.json_data:
        objs = canvas_result.json_data["objects"]
        # reconstrói comodos mantendo larg/comp e atualizando x,y
        novos = []
        for obj in objs:
            if obj.get("type") != "rect":
                continue
            nome = obj.get("name", "Bloco")
            x_m = px_para_m(obj.get("left", 0), escala_px_por_m)
            y_m = px_para_m(obj.get("top", 0), escala_px_por_m)
            w_m2 = px_para_m(obj.get("width", 0) * obj.get("scaleX", 1), escala_px_por_m)
            h_m2 = px_para_m(obj.get("height", 0) * obj.get("scaleY", 1), escala_px_por_m)

            # opcional: clamp dentro do terreno
            x_m = max(0.0, min(x_m, largura_m - w_m2))
            y_m = max(0.0, min(y_m, comprimento_m - h_m2))

            novos.append({
                "nome": nome,
                "x": x_m,
                "y": y_m,
                "largura": w_m2,
                "comprimento": h_m2,
            })

        st.session_state["comodos"] = novos

    st.divider()

    # download DXF com os blocos arrastados
    dxf_text = gerar_dxf_completo(largura_m, comprimento_m, st.session_state["comodos"])
    st.download_button(
        "📥 Baixar DXF",
        data=dxf_text,
        file_name="planta.dxf",
        mime="application/dxf"
    )
