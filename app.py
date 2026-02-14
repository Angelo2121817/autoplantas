import streamlit as st
from streamlit_drawable_canvas import st_canvas
import uuid
import inspect
import io
import ezdxf

# =========================
# Compat ezdxf (alinhamento do texto)
# =========================
try:
    from ezdxf.enums import TextEntityAlignment as TEA
except Exception:
    TEA = None  # fallback para versões antigas


# =========================
# Utilitários
# =========================
def clamp(v, vmin, vmax):
    return max(vmin, min(v, vmax))


def snap(v, step):
    if step <= 0:
        return v
    return round(v / step) * step


def garantir_ids(comodos):
    for c in comodos:
        if "id" not in c:
            c["id"] = f"c_{uuid.uuid4().hex[:8]}"


def comodos_para_drawing(largura_m, comprimento_m, comodos, px_por_m):
    """
    objects[0] = terreno (não selecionável)
    objects[1:] = comodos (mapeado por índice com comodos[i])
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
        # Observação: estamos usando Y invertido para ter y=0 embaixo (planta)
        top_px = (comprimento_m - (c["y"] + c["comprimento"])) * px_por_m
        objects.append({
            "type": "rect",
            "left": float(c["x"] * px_por_m),
            "top": float(top_px),
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
    Lê objects[1:] do canvas (pula terreno) e escreve em comodos[i] (por índice).
    Aplica snap e clamp para manter dentro do terreno.
    """
    objs = (drawing or {}).get("objects", [])
    if len(objs) <= 1:
        return

    for i, obj in enumerate(objs[1:]):
        if i >= len(comodos):
            break

        left_px = float(obj.get("left", 0.0))
        top_px = float(obj.get("top", 0.0))
        w_px = float(obj.get("width", 0.0)) * float(obj.get("scaleX", 1.0))
        h_px = float(obj.get("height", 0.0)) * float(obj.get("scaleY", 1.0))

        w_m_new = max(0.10, w_px / px_por_m)
        h_m_new = max(0.10, h_px / px_por_m)

        x_m_new = left_px / px_por_m
        # desfaz inversão do Y: top = (comp - (y+h)) * px
        y_m_new = float(comprimento_m) - (top_px / px_por_m) - h_m_new

        # snap (posição e tamanho)
        x_m_new = snap(x_m_new, snap_m)
        y_m_new = snap(y_m_new, snap_m)
        if snap_m > 0:
            w_m_new = max(0.10, snap(w_m_new, snap_m))
            h_m_new = max(0.10, snap(h_m_new, snap_m))

        # clamp (para manter dentro do terreno)
        x_m_new = clamp(x_m_new, 0.0, max(0.0, float(largura_m) - w_m_new))
        y_m_new = clamp(y_m_new, 0.0, max(0.0, float(comprimento_m) - h_m_new))

        comodos[i]["x"] = float(x_m_new)
        comodos[i]["y"] = float(y_m_new)
        comodos[i]["largura"] = float(w_m_new)
        comodos[i]["comprimento"] = float(h_m_new)


# =========================
# DXF (exportação)
# =========================
import math
import ezdxf
import io

def gerar_dxf(larg_m, comp_m, lista_comodos, esp_parede_m=0.15):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Layers
    if "ESTRUTURA_EXTERNA" not in doc.layers:
        doc.layers.new(name="ESTRUTURA_EXTERNA", dxfattribs={"color": 7})
    if "PAREDES" not in doc.layers:
        doc.layers.new(name="PAREDES", dxfattribs={"color": 6})
    if "TEXTOS" not in doc.layers:
        doc.layers.new(name="TEXTOS", dxfattribs={"color": 2})

    # Contorno do terreno/galpão
    pts = [(0, 0), (larg_m, 0), (larg_m, comp_m), (0, comp_m), (0, 0)]
    msp.add_lwpolyline(pts, dxfattribs={"layer": "ESTRUTURA_EXTERNA"})

    # --- util: normalizar segmento (evita problemas de float) ---
    def q(v, nd=4):
        # arredonda em metros: nd=4 -> 0,1 mm
        return round(float(v), nd)

    def seg_key(p1, p2):
        x1, y1 = q(p1[0]), q(p1[1])
        x2, y2 = q(p2[0]), q(p2[1])
        # ordena para a mesma parede ter a mesma chave independentemente do sentido
        if (x2, y2) < (x1, y1):
            x1, y1, x2, y2 = x2, y2, x1, y1
        return (x1, y1, x2, y2)

    # --- coletar segmentos das paredes (retângulos dos cômodos) ---
    # count==2 -> parede compartilhada; vamos desenhar só uma vez
    segs = {}  # key -> {"p1":(x1,y1),"p2":(x2,y2),"count":n}
    textos = []  # para texto central

    for c in lista_comodos:
        x, y = float(c["x"]), float(c["y"])
        w, h = float(c["largura"]), float(c["comprimento"])
        nome = c.get("nome", "Bloco")

        pA = (x, y)
        pB = (x + w, y)
        pC = (x + w, y + h)
        pD = (x, y + h)

        lados = [(pA, pB), (pB, pC), (pC, pD), (pD, pA)]
        for p1, p2 in lados:
            k = seg_key(p1, p2)
            if k not in segs:
                segs[k] = {"p1": (k[0], k[1]), "p2": (k[2], k[3]), "count": 1}
            else:
                segs[k]["count"] += 1

        textos.append((nome, x + w/2, y + h/2))

    # --- desenhar parede dupla para cada segmento único ---
    t = float(esp_parede_m)
    off = t / 2.0

    def draw_double_wall(p1, p2):
        x1, y1 = p1
        x2, y2 = p2

        # segmento horizontal
        if math.isclose(y1, y2, abs_tol=1e-9):
            y = y1
            msp.add_line((x1, y + off), (x2, y + off), dxfattribs={"layer": "PAREDES"})
            msp.add_line((x1, y - off), (x2, y - off), dxfattribs={"layer": "PAREDES"})
            return

        # segmento vertical
        if math.isclose(x1, x2, abs_tol=1e-9):
            x = x1
            msp.add_line((x + off, y1), (x + off, y2), dxfattribs={"layer": "PAREDES"})
            msp.add_line((x - off, y1), (x - off, y2), dxfattribs={"layer": "PAREDES"})
            return

        # se aparecer diagonal (não deveria com seus retângulos), fallback: desenha linha simples
        msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "PAREDES"})

    # desenha cada parede apenas uma vez (mesmo que compartilhada)
    for item in segs.values():
        draw_double_wall(item["p1"], item["p2"])

    # textos (opcional)
    for nome, cx, cy in textos:
        txt = msp.add_text(nome, dxfattribs={"layer": "TEXTOS", "height": 0.30})
        # compat com versões novas (enum) e antigas (string)
        try:
            from ezdxf.enums import TextEntityAlignment as TEA
            txt.set_placement((cx, cy), align=TEA.MIDDLE_CENTER)
        except Exception:
            try:
                txt.set_pos((cx, cy), align="MIDDLE_CENTER")
            except Exception:
                txt.dxf.insert = (cx, cy)

    buff = io.StringIO()
    doc.write(buff)
    return buff.getvalue()


# =========================
# App
# =========================
st.set_page_config(page_title="AutoPlantas", layout="wide")
st.title("AutoPlantas — Editor por Blocos (protótipo)")

# Estado
if "comodos" not in st.session_state:
    st.session_state["comodos"] = []
if "px_por_m" not in st.session_state:
    st.session_state["px_por_m"] = 40
if "drawing" not in st.session_state:
    st.session_state["drawing"] = None
if "canvas_ver" not in st.session_state:
    st.session_state["canvas_ver"] = 0
if "last_canvas_json" not in st.session_state:
    st.session_state["last_canvas_json"] = None

garantir_ids(st.session_state["comodos"])

col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.header("Terreno / Construção")

    largura_m = st.number_input("Largura (m)", 5.0, 200.0, 15.0, step=1.0)
    comprimento_m = st.number_input("Comprimento (m)", 5.0, 200.0, 30.0, step=1.0)
    st.session_state["px_por_m"] = st.slider("Escala (px por metro)", 10, 100, st.session_state["px_por_m"])
    px_por_m = st.session_state["px_por_m"]

    st.divider()
    st.header("Grade / Snap")

    snap_m = st.selectbox("Snap (m)", [0.0, 0.05, 0.10, 0.20, 0.50], index=2)
    st.caption("0 desliga o snap. 0,10 m costuma ficar bem usável.")

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
        # recria o desenho e reseta o componente
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

    # se não existe drawing persistido, cria
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
        # importante para não rerodar a cada micro-movimento (reduz piscar)
        canvas_kwargs["realtime_update"] = False

    canvas_result = st_canvas(**canvas_kwargs)

    # Sincroniza canvas -> comodos (só quando muda)
    if canvas_result.json_data and canvas_result.json_data != st.session_state["last_canvas_json"]:
        drawing_para_comodos(
            canvas_result.json_data,
            largura_m,
            comprimento_m,
            st.session_state["comodos"],
            px_por_m,
            snap_m=snap_m,
        )

        # Reconstrói um drawing “limpo” (evita scaleX/scaleY acumulando)
        st.session_state["drawing"] = comodos_para_drawing(largura_m, comprimento_m, st.session_state["comodos"], px_por_m)
        st.session_state["last_canvas_json"] = canvas_result.json_data

    st.caption("Clique no bloco para selecionar, arraste para mover, use as alças para redimensionar.")

    with st.expander("Blocos (debug)"):
        st.json(st.session_state["comodos"])
