import streamlit as st
from streamlit_drawable_canvas import st_canvas
import ezdxf
import io
import uuid

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="Planta por Blocos", layout="wide")
st.title("Planta Baixa por Blocos (arrastar e soltar)")

# ---------------------------
# STATE
# ---------------------------
if "blocos" not in st.session_state:
    # Cada bloco tem um id estável (para sincronizar com objetos do canvas)
    st.session_state["blocos"] = []

if "canvas_key" not in st.session_state:
    st.session_state["canvas_key"] = 0  # para forçar reset do canvas quando necessário

# ---------------------------
# FUNÇÕES
# ---------------------------
def m_to_px(m, escala_px_por_m):
    return m * escala_px_por_m

def px_to_m(px, escala_px_por_m):
    return px / escala_px_por_m

def gerar_dxf(larg_m, comp_m, objetos_canvas, escala_px_por_m):
    """
    objetos_canvas: lista de shapes do canvas (retângulos), em pixels
    converte px -> m e escreve DXF
    """
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # layers
    if "ESTRUTURA_EXTERNA" not in doc.layers:
        doc.layers.new(name="ESTRUTURA_EXTERNA", dxfattribs={"color": 7})
    if "PAREDES_INTERNAS" not in doc.layers:
        doc.layers.new(name="PAREDES_INTERNAS", dxfattribs={"color": 6})
    if "TEXTOS" not in doc.layers:
        doc.layers.new(name="TEXTOS", dxfattribs={"color": 2})

    # contorno do terreno/galpão (em metros)
    pontos_externos = [(0, 0), (larg_m, 0), (larg_m, comp_m), (0, comp_m), (0, 0)]
    msp.add_lwpolyline(pontos_externos, dxfattribs={"layer": "ESTRUTURA_EXTERNA"})

    # objetos (retângulos) do canvas
    for obj in objetos_canvas:
        if obj.get("type") != "rect":
            continue

        # No fabric.js (base do canvas), retângulo tem left/top/width/height e scaleX/scaleY
        left_px = obj.get("left", 0)
        top_px = obj.get("top", 0)
        w_px = obj.get("width", 0) * obj.get("scaleX", 1)
        h_px = obj.get("height", 0) * obj.get("scaleY", 1)

        # Conversão px -> m
        x_m = px_to_m(left_px, escala_px_por_m)
        y_m = px_to_m(top_px, escala_px_por_m)
        w_m = px_to_m(w_px, escala_px_por_m)
        h_m = px_to_m(h_px, escala_px_por_m)

        # IMPORTANTE: origem do canvas (0,0) é topo-esquerda.
        # Em planta/DXF normalmente você quer origem em baixo-esquerda.
        # Então convertemos Y invertendo:
        # y_canvas_top = top_px -> y_m_top
        # y_dxf = comp_m - (y_m_top + h_m)
        y_dxf = comp_m - (y_m + h_m)
        x_dxf = x_m

        nome = obj.get("name", "Bloco")

        pontos = [
            (x_dxf, y_dxf),
            (x_dxf + w_m, y_dxf),
            (x_dxf + w_m, y_dxf + h_m),
            (x_dxf, y_dxf + h_m),
            (x_dxf, y_dxf),
        ]
        msp.add_lwpolyline(pontos, dxfattribs={"layer": "PAREDES_INTERNAS"})
        msp.add_text(nome, dxfattribs={"layer": "TEXTOS", "height": 0.3}).set_pos(
            (x_dxf + w_m / 2, y_dxf + h_m / 2), align="MIDDLE_CENTER"
        )

    output = io.StringIO()
    doc.write(output)
    return output.getvalue()

def montar_drawing_inicial(blocos, escala_px_por_m):
    """
    Retorna a lista de objetos do fabric.js para o canvas.
    Vamos desenhar como retângulos movíveis.
    """
    objs = []
    for b in blocos:
        objs.append({
            "type": "rect",
            "left": m_to_px(b["x_m"], escala_px_por_m),
            "top": m_to_px(b["y_m"], escala_px_por_m),
            "width": m_to_px(b["w_m"], escala_px_por_m),
            "height": m_to_px(b["h_m"], escala_px_por_m),
            "fill": "rgba(160,203,232,0.45)",
            "stroke": "blue",
            "strokeWidth": 2,
            "name": b["nome"],     # campo extra (vai no JSON)
            "bloc_id": b["id"],    # id estável (vai no JSON)
        })
    return {"version": "4.4.0", "objects": objs}

# ---------------------------
# UI
# ---------------------------
col_config, col_canvas = st.columns([1, 2])

with col_config:
    st.header("1) Área (m)")
    largura_m = st.number_input("Largura total (m)", 5.0, 200.0, 15.0)
    comprimento_m = st.number_input("Comprimento total (m)", 5.0, 300.0, 30.0)

    st.divider()

    st.header("2) Escala do canvas")
    escala_px_por_m = st.slider("Pixels por metro", 10, 80, 30)
    canvas_w = int(m_to_px(largura_m, escala_px_por_m))
    canvas_h = int(m_to_px(comprimento_m, escala_px_por_m))

    st.divider()

    st.header("3) Adicionar bloco")
    tipo = st.selectbox("Tipo", ["Escritório", "Banheiro", "Almoxarifado", "Produção", "Refeitório"])
    c1, c2 = st.columns(2)
    w_m = c1.number_input("Largura (m)", 1.0, 50.0, 3.0)
    h_m = c2.number_input("Comprimento (m)", 1.0, 50.0, 3.0)

    # posição inicial (em metros) só para “nascer” no canvas; depois o usuário arrasta
    st.caption("Posição inicial é só para nascer no canvas (depois arrasta).")
    c3, c4 = st.columns(2)
    x_m = c3.number_input("X inicial (m)", 0.0, largura_m, 0.5)
    y_m = c4.number_input("Y inicial (m) (a partir do topo do canvas)", 0.0, comprimento_m, 0.5)

    if st.button("➕ Inserir bloco"):
        st.session_state["blocos"].append({
            "id": str(uuid.uuid4())[:8],
            "nome": tipo,
            "w_m": float(w_m),
            "h_m": float(h_m),
            "x_m": float(x_m),
            "y_m": float(y_m),
        })
        # força o canvas recarregar com o novo bloco
        st.session_state["canvas_key"] += 1
        st.rerun()

    if st.button("🗑️ Limpar tudo"):
        st.session_state["blocos"] = []
        st.session_state["canvas_key"] += 1
        st.rerun()

with col_canvas:
    st.subheader("Arraste e redimensione os blocos")

    drawing_data = montar_drawing_inicial(st.session_state["blocos"], escala_px_por_m)

    canvas_result = st_canvas(
        fill_color="rgba(160,203,232,0.35)",
        stroke_width=2,
        stroke_color="blue",
        background_color="#f2f2f2",
        width=canvas_w,
        height=canvas_h,
        drawing_mode="transform",  # move/resize/rotate
        initial_drawing=drawing_data,
        key=f"canvas_{st.session_state['canvas_key']}",
        update_streamlit=True,
    )

    objetos = []
    if canvas_result.json_data and "objects" in canvas_result.json_data:
        objetos = canvas_result.json_data["objects"]

    st.divider()

    # Exportar DXF (usa o que está no canvas AGORA)
    dxf_text = gerar_dxf(largura_m, comprimento_m, objetos, escala_px_por_m)
    st.download_button(
        "📥 Baixar DXF",
        data=dxf_text,
        file_name="planta_blocos.dxf",
        mime="application/dxf",
    )
