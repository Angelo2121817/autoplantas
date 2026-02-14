import streamlit as st
import ezdxf
import io
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="AutoPlantas", layout="wide")

# ---------- Estado ----------
if "comodos" not in st.session_state:
    st.session_state.comodos = []  # cada item: {id, nome, x, y, largura, comprimento}

if "px_por_m" not in st.session_state:
    st.session_state.px_por_m = 40  # escala base

# ---------- DXF ----------
def gerar_dxf(larg_m, comp_m, lista_comodos):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    doc.layers.new(name="ESTRUTURA_EXTERNA", dxfattribs={"color": 7})
    doc.layers.new(name="PAREDES_INTERNAS", dxfattribs={"color": 6})
    doc.layers.new(name="TEXTOS", dxfattribs={"color": 2})

    # contorno
    pts = [(0, 0), (larg_m, 0), (larg_m, comp_m), (0, comp_m), (0, 0)]
    msp.add_lwpolyline(pts, dxfattribs={"layer": "ESTRUTURA_EXTERNA"})

    for c in lista_comodos:
        x, y = c["x"], c["y"]
        w, h = c["largura"], c["comprimento"]
        nome = c["nome"]

        pts_i = [(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)]
        msp.add_lwpolyline(pts_i, dxfattribs={"layer": "PAREDES_INTERNAS"})

        txt = msp.add_text(nome, dxfattribs={"layer": "TEXTOS", "height": 0.30})
        txt.set_placement((x + w/2, y + h/2), align="MIDDLE_CENTER")

    buff = io.StringIO()
    doc.write(buff)
    return buff.getvalue()

# ---------- UI ----------
col_left, col_right = st.columns([1, 2])

with col_left:
    st.header("Terreno / Construção")

    largura_m = st.number_input("Largura (m)", 5.0, 200.0, 15.0)
    comprimento_m = st.number_input("Comprimento (m)", 5.0, 200.0, 30.0)
    st.session_state.px_por_m = st.slider("Escala (px por metro)", 10, 100, st.session_state.px_por_m)

    st.divider()
    st.header("Adicionar bloco")

    nome = st.selectbox("Tipo", ["Escritório", "Banheiro", "Almoxarifado", "Produção", "Refeitório"])
    c1, c2 = st.columns(2)
    w_m = c1.number_input("Largura (m)", 0.5, 50.0, 3.0, key="w_m")
    h_m = c2.number_input("Comprimento (m)", 0.5, 50.0, 3.0, key="h_m")

    if st.button("Adicionar"):
        st.session_state.comodos.append({
            "id": f"c{len(st.session_state.comodos)+1}",
            "nome": nome,
            "x": 0.0,
            "y": 0.0,
            "largura": float(w_m),
            "comprimento": float(h_m),
        })
        st.rerun()

    if st.button("Limpar tudo"):
        st.session_state.comodos = []
        st.rerun()

with col_right:
    st.subheader("Editor (arrastar / redimensionar)")

    px_por_m = st.session_state.px_por_m
    canvas_w = int(largura_m * px_por_m)
    canvas_h = int(comprimento_m * px_por_m)

    # Monte o "initial_drawing" com os retângulos existentes
    # Observação: Fabric usa top/left em px; aqui fazemos (x,y) em m -> px
    objects = []
    for c in st.session_state.comodos:
        objects.append({
            "type": "rect",
            "left": c["x"] * px_por_m,
            "top": (comprimento_m - (c["y"] + c["comprimento"])) * px_por_m,  # invertendo Y p/ ficar “planta”
            "width": c["largura"] * px_por_m,
            "height": c["comprimento"] * px_por_m,
            "fill": "rgba(160,203,232,0.5)",
            "stroke": "blue",
            "strokeWidth": 2,
            "objectCaching": False,
            "name": c["id"],  # vamos usar isso pra mapear de volta
        })

    initial_drawing = {"version": "4.4.0", "objects": objects}

    # Importante para parar o "pisca": key fixa + não recriar key com dimensões
    canvas_result = st_canvas(
        fill_color="rgba(0,0,0,0)",
        stroke_width=2,
        stroke_color="blue",
        background_color="#f0f0f0",
        width=canvas_w,
        height=canvas_h,
        drawing_mode="transform",   # mover/resize
        initial_drawing=initial_drawing,
        update_streamlit=True,
        key="planta_canvas",
    )

    # Sincronizar posições do canvas -> session_state
    if canvas_result.json_data and "objects" in canvas_result.json_data:
        # Atualiza com base nos objetos atuais
        by_id = {c["id"]: c for c in st.session_state.comodos}

        for obj in canvas_result.json_data["objects"]:
            cid = obj.get("name")
            if cid in by_id:
                left_px = float(obj.get("left", 0))
                top_px = float(obj.get("top", 0))
                w_px = float(obj.get("width", 0)) * float(obj.get("scaleX", 1))
                h_px = float(obj.get("height", 0)) * float(obj.get("scaleY", 1))

                # px -> m
                w_m_new = w_px / px_por_m
                h_m_new = h_px / px_por_m

                # desfaz inversão do Y
                x_m_new = left_px / px_por_m
                y_m_new = (comprimento_m * px_por_m - (top_px + h_px)) / px_por_m

                by_id[cid]["x"] = max(0.0, x_m_new)
                by_id[cid]["y"] = max(0.0, y_m_new)
                by_id[cid]["largura"] = max(0.1, w_m_new)
                by_id[cid]["comprimento"] = max(0.1, h_m_new)

    st.divider()

    dxf_text = gerar_dxf(largura_m, comprimento_m, st.session_state.comodos)
    st.download_button(
        "Baixar DXF",
        data=dxf_text,
        file_name="planta.dxf",
        mime="application/dxf",
    )
