import streamlit as st
import ezdxf
import io
import uuid
import inspect
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="AutoPlantas", layout="wide")
st.title("AutoPlantas — Editor por Blocos (protótipo)")

# =========================
# Estado (Session State)
# =========================
if "comodos" not in st.session_state:
    st.session_state["comodos"] = []  # cada item: {id, nome, x, y, largura, comprimento}

if "px_por_m" not in st.session_state:
    st.session_state["px_por_m"] = 40

if "drawing" not in st.session_state:
    st.session_state["drawing"] = None  # JSON do canvas (dict)

if "canvas_ver" not in st.session_state:
    st.session_state["canvas_ver"] = 0  # incrementa quando queremos resetar o componente

if "last_canvas_json" not in st.session_state:
    st.session_state["last_canvas_json"] = None

# garantir ID em itens antigos
for c in st.session_state["comodos"]:
    if "id" not in c:
        c["id"] = f"c_{uuid.uuid4().hex[:8]}"


# =========================
# Utilitários
# =========================
def clamp(v, vmin, vmax):
    return max(vmin, min(v, vmax))


def snap(v, step):
    if step <= 0:
        return v
    return round(v / step) * step


def comodos_para_drawing(largura_m, comprimento_m, comodos, px_por_m):
    """
    Objects[0] = terreno (não selecionável)
    Objects[1:] = comodos (index i ↔ comodos[i])
    """
    objects = [{
        "type": "rect",
        "left": 0,
        "top": 0,
        "width": float(largura_m * px_por_m),
        "height": float(comprimento_m * px_por_m),
        "fill": "rgba(240,240,240,1)",
        "stroke": "black",
        "strokeWidth": 2,
        "selectable": False,
        "evented": False,
        "objectCaching": False,
    }]

    for c in comodos:
        objects.append({
            "type": "rect",
            "left": float(c["x"] * px_por_m),
            # invertendo Y para ficar “planta”: y=0 embaixo
            "top": float((comprimento_m - (c["y"] + c["comprimento"])) * px_por_m),
            "width": float(c["largura"] * px_por_m),
            "height": float(c["comprimento"] * px_por_m),
            "fill": "rgba(160,203,232,0.5)",
            "stroke": "blue",
            "strokeWidth": 2,
            "objectCaching": False,
        })

    return {"version": "4.4.0", "objects": objects}


def drawing_para_comodos(drawing, largura_m, comprimento_m, comodos, px_por_m, snap_m=0.0):
    """
    Lê objects[1:] e escreve de volta em comodos (por índice).
    Aplica snap e clamp para manter dentro do terreno.
    """
    objs = (drawing or {}).get("objects", [])
    if len(objs) <= 1:
        return

    for i, obj in enumerate(objs[1:]):  # pula terreno
        if i >= len(comodos):
            break

        left_px = float(obj.get("left", 0.0))
        top_px = float(obj.get("top", 0.0))
        w_px = float(obj.get("width", 0.0)) * float(obj.get("scaleX", 1.0))
        h_px = float(obj.get("height", 0.0)) * float(obj.get("scaleY", 1.0))

        w_m_new = w_px / px_por_m
        h_m_new = h_px / px_por_m

        x_m_new = left_px / px_por_m
        # desfaz inversão do Y
        y_m_new = float(comprimento_m) - (top_px / px_por_m) - h_m_new

        # snap
        x_m_new = snap(x_m_new, snap_m)
        y_m_new = snap(y_m_new, snap_m)
        w_m_new = max(0.10, snap(w_m_new, snap_m) if snap_m > 0 else w_m_new)
        h_m_new = max(0.10, snap(h_m_new, snap_m) if snap_m > 0 else h_m_new)

        # clamp (manter dentro do terreno)
        x_m_new = clamp(x_m_new, 0.0, max(0.0, float(largura_m) - w_m_new))
        y_m_new = clamp(y_m_new, 0.0, max(0.0, float(comprimento_m) - h_m_new))

        comodos[i]["x"] = float(x_m_new)
        comodos[i]["y"] = float(y_m_new)
        comodos[i]["largura"] = float(w_m_new)
        comodos[i]["comprimento"] = float(h_m_new)


# =========================
# DXF
# =========================
def gerar_dxf(larg_m, comp_m, lista_comodos):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # layers
    if "ESTRUTURA_EXTERNA" not in doc.layers:
        doc.layers.new(name="ESTRUTURA_EXTERNA", dxfattribs={"color": 7})
    if "PAREDES_INTERNAS" not in doc.layers:
        doc.layers.new(name="PAREDES_INTERNAS", dxfattribs={"color": 6})
    if "TEXTOS" not in doc.layers:
        doc.layers.new(name="TEXTOS", dxfattribs={"color": 2})

    # contorno externo
    pts = [(0, 0), (larg_m, 0), (larg_m, comp_m), (0, comp_m), (0, 0)]
    msp.add_lwpolyline(pts, dxfattribs={"layer": "ESTRUTURA_EXTERNA"})

    for c in lista_comodos:
        x, y = c["x"], c["y"]
        w, h = c["largura"], c["comprimento"]
        nome = c["nome"]

        pts_i = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
        msp.add_lwpolyline(pts_i, dxfattribs={"layer": "PAREDES_INTERNAS"})

        txt = msp.add_text(nome, dxfattribs={"layer": "TEXTOS", "height": 0.30})
        txt.set_placement((x + w / 2, y + h / 2), align="MIDDLE_CENTER")

    buff = io.StringIO()
    doc.write(buff)
    return buff.getvalue()


# =========================
# UI
# =========================
col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.header("Terreno / Configurações")

    largura_m = st.number_input("Largura (m)", 5.0, 200.0, 15.0, step=1.0)
    comprimento_m = st.number_input("Comprimento (m)", 5.0, 200.0, 30.0, step=1.0)

    st.session_state["px_por_m"] = st.slider("Escala (px por metro)", 10, 100, st.session_state["px_por_m"])
    px_por_m = st.session_state["px_por_m"]

    st.divider()
    st.header("Grade / Snap")

    snap_m = st.selectbox("Snap (m)", [0.0, 0.05, 0.10, 0.20, 0.50], index=2)
    st.caption("Dica: `0,10 m` deixa bem usável. `0` desliga snap.")

    st.divider()
    st.header("Adicionar bloco")

    nome = st.selectbox("Tipo", ["Escritório", "Banheiro", "Almoxarifado", "Produção", "Refeitório"])
    c1, c2 = st.columns(2)
    w_m = c1.number_input("Largura do bloco (m)", 0.5, 50.0, 3.0, step=0.5)
    h_m = c2.number_input("Comprimento do bloco (m)", 0.5, 50.0, 3.0, step=0.5)

    b1, b2 = st.columns(2)
    if b1.button("Adicionar", use_container_width=True):
        st.session_state["comodos"].append({
            "id": f"c_{uuid.uuid4().hex[:8]}",
            "nome": nome,
            "x": 0.0,
            "y": 0.0,
            "largura": float(w_m),
            "comprimento": float(h_m),
        })
        st.session_state["drawing"] = comodos_para_drawing(largura_m, comprimento_m, st.session_state["comodos"], px_por_m)
        st.session_state["canvas_ver"] += 1
        st.rerun()

    if b2.button("Limpar tudo", use_container_width=True):
        st.session_state["comodos"] = []
        st.session_state["drawing"] = comodos_para_drawing(largura_m, comprimento_m, [], px_por_m)
        st.session_state["canvas_ver"] += 1
        st.rerun()

    st.divider()
    if st.button("Recriar desenho (se travar)", use_container_width=True):
        st.session_state["drawing"] = comodos_para_drawing(largura_m, comprimento_m, st.session_state["comodos"], px_por_m)
        st.session_state["canvas_ver"] += 1
        st.rerun()

    st.divider()
    st.subheader("Exportar")
    dxf_text = gerar_dxf(largura_m, comprimento_m, st.session_state["comodos"])
    st.download_button(
        "Baixar DXF",
        data=dxf_text,
        file_name="planta.dxf",
        mime="application/dxf",
        use_container_width=True,
    )


with col_right:
    st.subheader("Editor (arrastar / redimensionar)")

    canvas_w = int(largura_m * px_por_m)
    canvas_h = int(comprimento_m * px_por_m)

    # Se não existe drawing persistido, cria uma vez
    if st.session_state["drawing"] is None:
        st.session_state["drawing"] = comodos_para_drawing(largura_m, comprimento_m, st.session_state["comodos"], px_por_m)

    # Detecta se st_canvas suporta realtime_update
    sig = inspect.signature(st_canvas)
    canvas_kwargs = dict(
        fill_color="rgba(0,0,0,0)",
        stroke_width=2,
        stroke_color="blue",
        background_color="#ffffff",
        width=canvas_w,
        height=canvas_h,
        drawing_mode="transform",
        display_toolbar=False,
        initial_drawing=st.session_state["drawing"],
        update_streamlit=True,
        key=f"planta_canvas_{st.session_state['canvas_ver']}",
    )
    if "realtime_update" in sig.parameters:
        canvas_kwargs["realtime_update"] = False

    canvas_result = st_canvas(**canvas_kwargs)

    # Sincroniza canvas -> comodos, e persiste o próprio JSON do canvas
    if canvas_result.json_data and canvas_result.json_data != st.session_state["last_canvas_json"]:
        drawing_para_comodos(
            canvas_result.json_data,
            largura_m,
            comprimento_m,
            st.session_state["comodos"],
            px_por_m,
            snap_m=snap_m,
        )

        # Após aplicar snap/clamp nos comodos, reconstrói o drawing “limpo”
        # (isso mantém a geometria coerente e evita scaleX/scaleY acumulando)
        st.session_state["drawing"] = comodos_para_drawing(largura_m, comprimento_m, st.session_state["comodos"], px_por_m)
        st.session_state["last_canvas_json"] = canvas_result.json_data

    st.caption(
        "Como usar: clique no bloco para selecionar, arraste para mover, use as alças para redimensionar."
    )

    with st.expander("Lista de blocos (debug)"):
        st.json(st.session_state["comodos"])
