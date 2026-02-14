import streamlit as st
from streamlit_drawable_canvas import st_canvas
import uuid
import io
import math
import json
import hashlib
import ezdxf
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import cm
from datetime import datetime

# ========================
# Compatibilidade ezdxf
# ========================
try:
    from ezdxf.enums import TextEntityAlignment as TEA
except Exception:
    TEA = None


# ========================
# Funções Auxiliares
# ========================
def clamp(v, vmin, vmax):
    return max(vmin, min(v, vmax))


def snap(v, step):
    if not step or step <= 0:
        return v
    return round(v / step) * step


def get_hash(obj) -> str:
    """Hash estável para detectar mudanças reais"""
    return hashlib.md5(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def ensure_ids(comodos):
    for c in comodos:
        if "id" not in c:
            c["id"] = f"c_{uuid.uuid4().hex[:8]}"


def comodos_to_drawing(terreno_w_m, terreno_h_m, comodos, px_por_m):
    """Converte cômodos para formato Fabric.js"""
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


def sync_comodos_from_canvas(drawing, terreno_w_m, terreno_h_m, comodos, px_por_m, snap_m):
    """Sincroniza comodos a partir do drawing do canvas"""
    if not drawing or "objects" not in drawing:
        return

    objs = drawing.get("objects", [])
    if len(objs) <= 1:
        return

    terreno_w_px = float(terreno_w_m * px_por_m)
    terreno_h_px = float(terreno_h_m * px_por_m)
    snap_px = float(snap_m * px_por_m) if snap_m and snap_m > 0 else 0.0

    for i in range(1, len(objs)):
        if (i - 1) >= len(comodos):
            break

        obj = objs[i]
        if obj.get("type") != "rect":
            continue

        sx = float(obj.get("scaleX", 1.0) or 1.0)
        sy = float(obj.get("scaleY", 1.0) or 1.0)
        w_px = float(obj.get("width", 0.0) or 0.0) * sx
        h_px = float(obj.get("height", 0.0) or 0.0) * sy
        left_px = float(obj.get("left", 0.0) or 0.0)
        top_px = float(obj.get("top", 0.0) or 0.0)

        if snap_px > 0:
            left_px = snap(left_px, snap_px)
            top_px = snap(top_px, snap_px)
            w_px = max(1.0, snap(w_px, snap_px))
            h_px = max(1.0, snap(h_px, snap_px))

        max_left = max(0.0, terreno_w_px - w_px)
        max_top = max(0.0, terreno_h_px - h_px)
        left_px = clamp(left_px, 0.0, max_left)
        top_px = clamp(top_px, 0.0, max_top)

        w_m = w_px / px_por_m
        h_m = h_px / px_por_m
        x_m = left_px / px_por_m
        y_m = terreno_h_m - (top_px / px_por_m) - h_m

        x_m = clamp(x_m, 0.0, max(0.0, terreno_w_m - w_m))
        y_m = clamp(y_m, 0.0, max(0.0, terreno_h_m - h_m))

        comodos[i - 1]["x"] = float(x_m)
        comodos[i - 1]["y"] = float(y_m)
        comodos[i - 1]["largura"] = float(max(0.10, w_m))
        comodos[i - 1]["comprimento"] = float(max(0.10, h_m))


# ========================
# DXF com Paredes Duplas (CORRIGIDO)
# ========================
def gerar_dxf_paredes_duplas(larg_m, comp_m, comodos, esp_ext_m=0.20, esp_int_m=0.12):
    """Gera DXF com paredes duplas"""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    if "PAREDES" not in doc.layers:
        doc.layers.new(name="PAREDES", dxfattribs={"color": 7})
    if "TEXTOS" not in doc.layers:
        doc.layers.new(name="TEXTOS", dxfattribs={"color": 2})

    def q(v, nd=4):
        return round(float(v), nd)

    def seg_key(p1, p2):
        x1, y1 = q(p1[0]), q(p1[1])
        x2, y2 = q(p2[0]), q(p2[1])
        if (x2, y2) < (x1, y1):
            x1, y1, x2, y2 = x2, y2, x1, y1
        return (x1, y1, x2, y2)

    segs = {}
    textos = []

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

        if math.isclose(y1, y2, abs_tol=1e-9):
            y = y1
            msp.add_line((x1, y + off), (x2, y + off), dxfattribs={"layer": "PAREDES"})
            msp.add_line((x1, y - off), (x2, y - off), dxfattribs={"layer": "PAREDES"})
            return

        if math.isclose(x1, x2, abs_tol=1e-9):
            x = x1
            msp.add_line((x + off, y1), (x + off, y2), dxfattribs={"layer": "PAREDES"})
            msp.add_line((x - off, y1), (x - off, y2), dxfattribs={"layer": "PAREDES"})
            return

        msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "PAREDES"})

    for item in segs.values():
        thickness = esp_ext_m if item["count"] == 1 else esp_int_m
        draw_double_wall(item["p1"], item["p2"], thickness)

    for nome, cx, cy in textos:
        txt = msp.add_text(nome, dxfattribs={"layer": "TEXTOS", "height": 0.30})
        if TEA is not None:
            txt.set_placement((cx, cy), align=TEA.MIDDLE_CENTER)
        else:
            try:
                txt.set_pos((cx, cy), align="MIDDLE_CENTER")
            except Exception:
                txt.dxf.insert = (cx, cy)

    # CORRIGIDO: usar BytesIO em vez de StringIO
    buff = io.BytesIO()
    doc.write(buff)
    buff.seek(0)
    return buff.getvalue()


# ========================
# PDF com ReportLab
# ========================
def gerar_pdf_paredes_duplas(larg_m, comp_m, comodos, esp_ext_m=0.20, esp_int_m=0.12):
    """Gera PDF com planta baixa em A4 paisagem"""
    buffer = io.BytesIO()
    page_width, page_height = landscape(A4)
    c = pdf_canvas.Canvas(buffer, pagesize=landscape(A4))
    
    margin = 1 * cm
    disponivel_w = page_width - 2 * margin
    disponivel_h = page_height - 3 * cm
    
    # Escala para caber na página
    escala_w = disponivel_w / larg_m
    escala_h = disponivel_h / comp_m
    escala = min(escala_w, escala_h)
    
    # Posição inicial
    x_inicio = margin + (disponivel_w - larg_m * escala) / 2
    y_inicio = margin + (disponivel_h - comp_m * escala) / 2
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, page_height - 1 * cm, "PLANTA BAIXA")
    
    # Data e escala
    c.setFont("Helvetica", 10)
    data_str = datetime.now().strftime("%d/%m/%Y")
    c.drawString(margin, page_height - 1.5 * cm, f"Data: {data_str}")
    c.drawString(margin + 8 * cm, page_height - 1.5 * cm, f"Escala: 1:{int(1/escala*100)}")
    
    # Função auxiliar para desenhar parede dupla
    def desenhar_parede_dupla(p1, p2, thickness):
        off = thickness * escala / 2.0
        x1, y1 = p1
        x2, y2 = p2
        
        x1_px = x_inicio + x1 * escala
        y1_px = y_inicio + y1 * escala
        x2_px = x_inicio + x2 * escala
        y2_px = y_inicio + y2 * escala
        
        if math.isclose(y1, y2, abs_tol=1e-9):
            y = y1_px
            c.line(x1_px, y + off, x2_px, y + off)
            c.line(x1_px, y - off, x2_px, y - off)
        elif math.isclose(x1, x2, abs_tol=1e-9):
            x = x1_px
            c.line(x + off, y1_px, x + off, y2_px)
            c.line(x - off, y1_px, x - off, y2_px)
    
    # Coletar segmentos
    def q(v, nd=4):
        return round(float(v), nd)
    
    def seg_key(p1, p2):
        x1, y1 = q(p1[0]), q(p1[1])
        x2, y2 = q(p2[0]), q(p2[1])
        if (x2, y2) < (x1, y1):
            x1, y1, x2, y2 = x2, y2, x1, y1
        return (x1, y1, x2, y2)
    
    segs = {}
    textos = []
    
    for com in comodos:
        x, y = float(com["x"]), float(com["y"])
        w, h = float(com["largura"]), float(com["comprimento"])
        nome = com.get("nome", "Bloco")
        
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
    
    # Desenhar paredes
    c.setLineWidth(0.5)
    for item in segs.values():
        thickness = esp_ext_m if item["count"] == 1 else esp_int_m
        desenhar_parede_dupla(item["p1"], item["p2"], thickness)
    
    # Desenhar textos
    c.setFont("Helvetica", 8)
    for nome, cx, cy in textos:
        cx_px = x_inicio + cx * escala
        cy_px = y_inicio + cy * escala
        c.drawCentredString(cx_px, cy_px, nome)
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ========================
# SVG/CDR com paredes duplas
# ========================
def gerar_svg_paredes_duplas(larg_m, comp_m, comodos, esp_ext_m=0.20, esp_int_m=0.12):
    """Gera SVG compatível com CorelDRAW"""
    escala = 100  # 1m = 100 unidades SVG
    
    svg_lines = [
        f'<svg width="{larg_m * escala}" height="{comp_m * escala}" xmlns="http://www.w3.org/2000/svg">',
        '<defs><style>text { font-family: Arial; font-size: 12px; }</style></defs>',
    ]
    
    # Função auxiliar
    def q(v, nd=4):
        return round(float(v), nd)
    
    def seg_key(p1, p2):
        x1, y1 = q(p1[0]), q(p1[1])
        x2, y2 = q(p2[0]), q(p2[1])
        if (x2, y2) < (x1, y1):
            x1, y1, x2, y2 = x2, y2, x1, y1
        return (x1, y1, x2, y2)
    
    segs = {}
    textos = []
    
    for com in comodos:
        x, y = float(com["x"]), float(com["y"])
        w, h = float(com["largura"]), float(com["comprimento"])
        nome = com.get("nome", "Bloco")
        
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
    
    # Desenhar paredes
    for item in segs.values():
        thickness = esp_ext_m if item["count"] == 1 else esp_int_m
        off = thickness * escala / 2.0
        x1, y1 = item["p1"]
        x2, y2 = item["p2"]
        
        x1_px = x1 * escala
        y1_px = y1 * escala
        x2_px = x2 * escala
        y2_px = y2 * escala
        
        if math.isclose(y1, y2, abs_tol=1e-9):
            y = y1_px
            svg_lines.append(f'<line x1="{x1_px}" y1="{y + off}" x2="{x2_px}" y2="{y + off}" stroke="black" stroke-width="1"/>')
            svg_lines.append(f'<line x1="{x1_px}" y1="{y - off}" x2="{x2_px}" y2="{y - off}" stroke="black" stroke-width="1"/>')
        elif math.isclose(x1, x2, abs_tol=1e-9):
            x = x1_px
            svg_lines.append(f'<line x1="{x + off}" y1="{y1_px}" x2="{x + off}" y2="{y2_px}" stroke="black" stroke-width="1"/>')
            svg_lines.append(f'<line x1="{x - off}" y1="{y1_px}" x2="{x - off}" y2="{y2_px}" stroke="black" stroke-width="1"/>')
    
    # Desenhar textos
    for nome, cx, cy in textos:
        cx_px = cx * escala
        cy_px = cy * escala
        svg_lines.append(f'<text x="{cx_px}" y="{cy_px}" text-anchor="middle" dominant-baseline="middle">{nome}</text>')
    
    svg_lines.append('</svg>')
    return '\n'.join(svg_lines)


# ========================
# App Principal
# ========================
st.set_page_config(page_title="AutoPlantas", layout="wide")
st.title("🏭 AutoPlantas — Editor de Plantas Baixas")

# Estado
if "comodos" not in st.session_state:
    st.session_state["comodos"] = []
ensure_ids(st.session_state["comodos"])

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
if "drawing" not in st.session_state:
    st.session_state["drawing"] = None
if "last_canvas_hash" not in st.session_state:
    st.session_state["last_canvas_hash"] = None

col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.header("⚙️ Configurações")

    with st.form("form_terreno"):
        w_new = st.number_input("Largura do terreno (m)", 5.0, 200.0, float(st.session_state["terreno_w_m"]), step=1.0)
        h_new = st.number_input("Comprimento do terreno (m)", 5.0, 200.0, float(st.session_state["terreno_h_m"]), step=1.0)
        px_new = st.slider("Escala (px por metro)", 10, 120, int(st.session_state["px_por_m"]))
        snap_new = st.selectbox("Snap (m)", [0.0, 0.05, 0.10, 0.20, 0.50], index=[0.0, 0.05, 0.10, 0.20, 0.50].index(float(st.session_state["snap_m"])))
        esp_ext_new = st.number_input("Parede externa (m)", 0.08, 0.60, float(st.session_state["esp_ext_m"]), step=0.01)
        esp_int_new = st.number_input("Parede interna (m)", 0.05, 0.40, float(st.session_state["esp_int_m"]), step=0.01)
        aplicar = st.form_submit_button("✅ Aplicar")

    if aplicar:
        st.session_state["terreno_w_m"] = float(w_new)
        st.session_state["terreno_h_m"] = float(h_new)
        st.session_state["px_por_m"] = int(px_new)
        st.session_state["snap_m"] = float(snap_new)
        st.session_state["esp_ext_m"] = float(esp_ext_new)
        st.session_state["esp_int_m"] = float(esp_int_new)
        st.session_state["drawing"] = None
        st.rerun()

    st.divider()
    st.header("➕ Adicionar Bloco")

    nome = st.selectbox("Tipo", ["Escritório", "Banheiro", "Almoxarifado", "Produção", "Refeitório"])
    c1, c2 = st.columns(2)
    w_m = c1.number_input("Largura (m)", 0.5, 50.0, 3.0, step=0.5)
    h_m = c2.number_input("Comprimento (m)", 0.5, 50.0, 3.0, step=0.5)

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
        st.session_state["drawing"] = None
        st.rerun()

    if b2.button("Limpar tudo", use_container_width=True):
        st.session_state["comodos"] = []
        st.session_state["drawing"] = None
        st.rerun()

    st.divider()
    if st.button("🔄 Recriar desenho", use_container_width=True):
        st.session_state["drawing"] = None
        st.rerun()

    st.divider()
    st.header("📥 Exportar")

    # Gerar arquivos
    dxf_data = gerar_dxf_paredes_duplas(
        st.session_state["terreno_w_m"],
        st.session_state["terreno_h_m"],
        st.session_state["comodos"],
        esp_ext_m=st.session_state["esp_ext_m"],
        esp_int_m=st.session_state["esp_int_m"],
    )
    
    pdf_data = gerar_pdf_paredes_duplas(
        st.session_state["terreno_w_m"],
        st.session_state["terreno_h_m"],
        st.session_state["comodos"],
        esp_ext_m=st.session_state["esp_ext_m"],
        esp_int_m=st.session_state["esp_int_m"],
    )
    
    svg_data = gerar_svg_paredes_duplas(
        st.session_state["terreno_w_m"],
        st.session_state["terreno_h_m"],
        st.session_state["comodos"],
        esp_ext_m=st.session_state["esp_ext_m"],
        esp_int_m=st.session_state["esp_int_m"],
    )

    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        st.download_button(
            "📄 Baixar PDF",
            data=pdf_data,
            file_name="planta.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with col_exp2:
        st.download_button(
            "🎨 Baixar SVG/CDR",
            data=svg_data,
            file_name="planta.svg",
            mime="image/svg+xml",
            use_container_width=True,
        )

    with col_exp3:
        st.download_button(
            "📐 Baixar DXF",
            data=dxf_data,
            file_name="planta.dxf",
            mime="application/dxf",
            use_container_width=True,
        )

with col_right:
    st.subheader("🎨 Editor (arrastar / redimensionar)")

    terreno_w_m = float(st.session_state["terreno_w_m"])
    terreno_h_m = float(st.session_state["terreno_h_m"])
    px_por_m = int(st.session_state["px_por_m"])
    snap_m = float(st.session_state["snap_m"])

    canvas_w = int(terreno_w_m * px_por_m)
    canvas_h = int(terreno_h_m * px_por_m)

    if st.session_state["drawing"] is None:
        st.session_state["drawing"] = comodos_to_drawing(terreno_w_m, terreno_h_m, st.session_state["comodos"], px_por_m)

    canvas_result = st_canvas(
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
        key="planta_canvas_fixed",
    )

    if canvas_result.json_data:
        current_hash = get_hash(canvas_result.json_data)
        if current_hash != st.session_state["last_canvas_hash"]:
            sync_comodos_from_canvas(
                canvas_result.json_data,
                terreno_w_m,
                terreno_h_m,
                st.session_state["comodos"],
                px_por_m,
                snap_m=snap_m,
            )
            st.session_state["last_canvas_hash"] = current_hash

    st.caption("💡 Clique no bloco para selecionar, arraste para mover e use as alças para redimensionar.")

    with st.expander("📋 Blocos (debug)"):
        st.json(st.session_state["comodos"])
