import streamlit as st
from streamlit_drawable_canvas import st_canvas

import uuid
import io
import math
import json
import inspect

import ezdxf

# -------------------------
# Compat: alinhamento texto ezdxf (novos exigem enum)
# -------------------------
try:
    from ezdxf.enums import TextEntityAlignment as TEA
except Exception:
    TEA = None


# =========================
# Helpers
# =========================
def clamp(v, vmin, vmax):
    return max(vmin, min(v, vmax))


def snap(v, step):
    if not step or step <= 0:
        return v
    return round(v / step) * step


def stable_hash(obj) -> str:
    # hash estável para comparar JSON sem ficar rerodando à toa
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def ensure_ids(comodos):
    for c in comodos:
        if "id" not in c:
            c["id"] = f"c_{uuid.uuid4().hex[:8]}"


def comodos_to_drawing(terreno_w_m, terreno_h_m, comodos, px_por_m):
    """
    objects[0] = terreno (não selecionável)
    objects[1:] = comodos (mapeado por índice: comodos[i] <-> objects[i+1])
    """
    objects = [{
        "type": "rect",
        "left": 0,
        "top": 0,
        "width": float(terreno_w_m * px_por_m),
        "height": float(terreno_h_m * px_por_m),
        "fill": "rgba(240,240,240,1)",
        "stroke": "black",
        "strokeWidth": 2,
        "selectable": False,
        "evented": False,
        "objectCaching": False,
    }]

    for c in comodos:
        # y=0 embaixo (planta). No canvas, top=0 é em cima, então invertimos.
        top_px = (terreno_h_m - (c["y"] + c["comprimento"])) * px_por_m
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


def sanitize_transform_rect(obj):
    """
    Aplica scaleX/scaleY no width/height e reseta scale para 1.
    Isso evita acumular escala e mantém medidas coerentes.
    """
    sx = float(obj.get("scaleX", 1.0) or 1.0)
    sy = float(obj.get("scaleY", 1.0) or 1.0)
    w = float(obj.get("width", 0.0) or 0.0) * sx
    h = float(obj.get("height", 0.0) or 0.0) * sy
    obj["width"] = w
    obj["height"] = h
    obj["scaleX"] = 1.0
    obj["scaleY"] = 1.0
    return obj


def apply_constraints_and_sync(drawing, terreno_w_m, terreno_h_m, comodos, px_por_m, snap_m):
    """
    - sanitiza scale (width/height reais)
    - aplica snap/clamp em pixels
    - sincroniza comodos (metros) a partir do desenho (objects[1:])
    - retorna drawing atualizado (sem rebuild completo -> menos “pisca”)
    """
    if not drawing or "objects" not in drawing:
        return drawing

    objs = drawing.get("objects", [])
    if len(objs) <= 1:
        return drawing

    terreno_w_px = float(terreno_w_m * px_por_m)
    terreno_h_px = float(terreno_h_m * px_por_m)
    snap_px = float(snap_m * px_por_m) if snap_m and snap_m > 0 else 0.0

    for i in range(1, len(objs)):
        if (i - 1) >= len(comodos):
            break

        obj = objs[i]
        if obj.get("type") != "rect":
            continue

        obj = sanitize_transform_rect(obj)

        left_px = float(obj.get("left", 0.0) or 0.0)
        top_px = float(obj.get("top", 0.0) or 0.0)
        w_px = float(obj.get("width", 0.0) or 0.0)
        h_px = float(obj.get("height", 0.0) or 0.0)

        # clamp em px (mantém dentro do terreno)
        max_left = max(0.0, terreno_w_px - w_px)
        max_top = max(0.0, terreno_h_px - h_px)

        # snap em px
        if snap_px > 0:
            left_px = snap(left_px, snap_px)
            top_px = snap(top_px, snap_px)
            w_px = max(1.0, snap(w_px, snap_px))
            h_px = max(1.0, snap(h_px, snap_px))

        left_px = clamp(left_px, 0.0, max_left)
        top_px = clamp(top_px, 0.0, max_top)

        # escreve de volta no desenho
        obj["left"] = float(left_px)
        obj["top"] = float(top_px)
        obj["width"] = float(w_px)
        obj["height"] = float(h_px)

        # sincroniza comodos (px -> m)
        w_m = w_px / px_por_m
        h_m = h_px / px_por_m
        x_m = left_px / px_por_m
        # desfaz inversão do Y: top = (H - (y+h)) * px
        y_m = terreno_h_m - (top_px / px_por_m) - h_m

        # clamp final em metros (segurança)
        x_m = clamp(x_m, 0.0, max(0.0, terreno_w_m - w_m))
        y_m = clamp(y_m, 0.0, max(0.0, terreno_h_m - h_m))

        comodos[i - 1]["x"] = float(x_m)
        comodos[i - 1]["y"] = float(y_m)
        comodos[i - 1]["largura"] = float(max(0.10, w_m))
        comodos[i - 1]["comprimento"] = float(max(0.10, h_m))

    drawing["objects"] = objs
    return drawing


# =========================
# DXF com paredes duplas (externa x interna)
# =========================
def gerar_dxf_paredes_duplas(larg_m, comp_m, comodos, esp_ext_m=0.20, esp_int_m=0.12):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    if "PAREDES" not in doc.layers:
        doc.layers.new(name="PAREDES", dxfattribs={"color": 7})
    if "TEXTOS" not in doc.layers:
        doc.layers.new(name="TEXTOS", dxfattribs={"color": 2})

    # normalização para evitar problemas de float
    def q(v, nd=4):
        return round(float(v), nd)

    def seg_key(p1, p2):
        x1, y1 = q(p1[0]), q(p1[1])
        x2, y2 = q(p2[0]), q(p2[1])
        if (x2, y2) < (x1, y1):
            x1, y1, x2, y2 = x2, y2, x1, y1
        return (x1, y1, x2, y2)

    segs = {}   # key -> {"p1","p2","count"}
    textos = [] # (nome,cx,cy)

    # coletar segmentos dos retângulos
    for c in comodos:
        x, y = float(c["x"]), float(c["y"])
        w, h = float(c["largura"]), float(c["comprimento"])
        nome = c.get("nome", "Bloco")

        pA = (x, y)
        pB = (x + w, y)
        pC = (x + w, y + h)
        pD = (x, y + h)

        for p1, p2 in [(pA, pB), (pB, pC), (pC, pD), (pD, pA)]:
            k = seg_key(p1, p2)
            if k not in segs:
                segs[k] = {"p1": (k[0], k[1]), "p2": (k[2], k[3]), "count": 1}
            else:
                segs[k]["count"] += 1

        textos.append((nome, x + w / 2, y + h / 2))

    def draw_double_wall(p1, p2, thickness):
        off = float(thickness) / 2.0
        x1, y1 = p1
        x2, y2 = p2

        # horizontal
        if math.isclose(y1, y2, abs_tol=1e-9):
            y = y1
            msp.add_line((x1, y + off), (x2, y + off), dxfattribs={"layer": "PAREDES"})
            msp.add_line((x1, y - off), (x2, y - off), dxfattribs={"layer": "PAREDES"})
            return

        # vertical
        if math.isclose(x1, x2, abs_tol=1e-9):
            x = x1
            msp.add_line((x + off, y1), (x + off, y2), dxfattribs={"layer": "PAREDES"})
            msp.add_line((x - off, y1), (x - off, y2), dxfattribs={"layer": "PAREDES"})
            return

        # fallback (não esperado)
        msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "PAREDES"})

    # desenhar segmentos: count==1 -> perímetro (externa); count>=2 -> divisória (interna)
    for item in segs.values():
        thickness = esp_ext_m if item["count"] == 1 else esp_int_m
        draw_double_wall(item["p1"], item["p2"], thickness)

    # textos
    for nome, cx, cy in textos:
        txt = msp.add_text(nome, dxfattribs={"layer": "TEXTOS", "height": 0.30})
        if TEA is not None:
            txt.set_placement((cx, cy), align=TEA.MIDDLE_CENTER)
        else:
            # versões antigas (fallback)
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
st.title("AutoPlantas — Editor por Blocos")

# Estado principal
if "comodos" not in st.session_state:
    st.session_state["comodos"] = []
ensure_ids(st.session_state["comodos"])

# Config do terreno (persistente)
if "terreno_w_m" not in st.session_state:
    st.session_state["terreno_w_m"] = 15.0
if "terreno_h_m" not in st.session_state:
    st.session_state["terreno_h_m"] = 30.0

if "px_por_m" not in st.session_state:
    st.session_state["px_por_m"] = 40

if "snap_m" not in st.session_state:
    st.session_state["snap_m"] = 0.10

if "esp_ext_m" not in st.session_state:
    st.session_state["esp_ext_m"] = 0.20
if "esp_int_m" not in st.session_state:
    st.session_state["esp_int_m"] = 0.12

# Canvas persistido (para não piscar)
if "drawing" not in st.session_state:
    st.session_state["drawing"] = None
if "canvas_ver" not in st.session_state:
    st.session_state["canvas_ver"] = 0
if "last_canvas_hash" not in st.session_state:
    st.session_state["last_canvas_hash"] = None

col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.header("Tamanho do terreno (aplicar)")

    # FORM evita rerun contínuo enquanto você está arrastando no canvas
    with st.form("form_terreno"):
        w_new = st.number_input("Largura do terreno (m)", 5.0, 200.0, float(st.session_state["terreno_w_m"]), step=1.0)
        h_new = st.number_input("Comprimento do terreno (m)", 5.0, 200.0, float(st.session_state["terreno_h_m"]), step=1.0)
        px_new = st.slider("Escala (px por metro)", 10, 120, int(st.session_state["px_por_m"]))
        snap_new = st.selectbox("Snap (m)", [0.0, 0.05, 0.10, 0.20, 0.50], index=[0.0, 0.05, 0.10, 0.20, 0.50].index(float(st.session_state["snap_m"])))

        esp_ext_new = st.number_input("Parede externa (m)", 0.08, 0.60, float(st.session_state["esp_ext_m"]), step=0.01)
        esp_int_new = st.number_input("Parede interna (m)", 0.05, 0.40, float(st.session_state["esp_int_m"]), step=0.01)

        aplicar = st.form_submit_button("Aplicar tamanho/escala")

    if aplicar:
        st.session_state["terreno_w_m"] = float(w_new)
        st.session_state["terreno_h_m"] = float(h_new)
        st.session_state["px_por_m"] = int(px_new)
        st.session_state["snap_m"] = float(snap_new)
        st.session_state["esp_ext_m"] = float(esp_ext_new)
        st.session_state["esp_int_m"] = float(esp_int_new)

        # ao mudar terreno/escala, recria o desenho e reseta o componente
        st.session_state["drawing"] = comodos_to_drawing(
            st.session_state["terreno_w_m"],
            st.session_state["terreno_h_m"],
            st.session_state["comodos"],
            st.session_state["px_por_m"],
        )
        st.session_state["canvas_ver"] += 1
        st.session_state["last_canvas_hash"] = None
        st.rerun()

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

        # recria o desenho e reseta canvas
        st.session_state["drawing"] = comodos_to_drawing(
            st.session_state["terreno_w_m"],
            st.session_state["terreno_h_m"],
            st.session_state["comodos"],
            st.session_state["px_por_m"],
        )
        st.session_state["canvas_ver"] += 1
        st.session_state["last_canvas_hash"] = None
        st.rerun()

    if b2.button("Limpar tudo", use_container_width=True):
        st.session_state["comodos"] = []
        st.session_state["drawing"] = comodos_to_drawing(
            st.session_state["terreno_w_m"],
            st.session_state["terreno_h_m"],
            [],
            st.session_state["px_por_m"],
        )
        st.session_state["canvas_ver"] += 1
        st.session_state["last_canvas_hash"] = None
        st.rerun()

    st.divider()
    if st.button("Recriar desenho (se travar)", use_container_width=True):
        st.session_state["drawing"] = comodos_to_drawing(
            st.session_state["terreno_w_m"],
            st.session_state["terreno_h_m"],
            st.session_state["comodos"],
            st.session_state["px_por_m"],
        )
        st.session_state["canvas_ver"] += 1
        st.session_state["last_canvas_hash"] = None
        st.rerun()

    st.divider()
    st.subheader("Exportar")

    dxf_text = gerar_dxf_paredes_duplas(
        st.session_state["terreno_w_m"],
        st.session_state["terreno_h_m"],
        st.session_state["comodos"],
        esp_ext_m=st.session_state["esp_ext_m"],
        esp_int_m=st.session_state["esp_int_m"],
    )
    st.download_button(
        "Baixar DXF (paredes duplas)",
        data=dxf_text,
        file_name="planta.dxf",
        mime="application/dxf",
        use_container_width=True,
    )

with col_right:
    st.subheader("Editor (arrastar / redimensionar)")

    terreno_w_m = float(st.session_state["terreno_w_m"])
    terreno_h_m = float(st.session_state["terreno_h_m"])
    px_por_m = int(st.session_state["px_por_m"])
    snap_m = float(st.session_state["snap_m"])

    canvas_w = int(terreno_w_m * px_por_m)
    canvas_h = int(terreno_h_m * px_por_m)

    # cria drawing uma vez, e depois preserva (para não piscar)
    if st.session_state["drawing"] is None:
        st.session_state["drawing"] = comodos_to_drawing(terreno_w_m, terreno_h_m, st.session_state["comodos"], px_por_m)

    # compat: realtime_update existe em algumas versões
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
        # importante: evita rerun a cada micro-movimento
        canvas_kwargs["realtime_update"] = False

    canvas_result = st_canvas(**canvas_kwargs)

    if canvas_result.json_data:
        current_hash = stable_hash(canvas_result.json_data)
        if current_hash != st.session_state["last_canvas_hash"]:
            # aplica snap/clamp e sincroniza comodos sem rebuild completo (menos flicker)
            st.session_state["drawing"] = apply_constraints_and_sync(
                canvas_result.json_data,
                terreno_w_m,
                terreno_h_m,
                st.session_state["comodos"],
                px_por_m,
                snap_m=snap_m,
            )
            st.session_state["last_canvas_hash"] = current_hash

    st.caption(
        "Dica: clique no bloco para selecionar, arraste para mover e use as alças para redimensionar."
    )

    with st.expander("Blocos (debug)"):
        st.json(st.session_state["comodos"])
