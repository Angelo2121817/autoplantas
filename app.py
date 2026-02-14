import math
import ezdxf
import io

def gerar_dxf(larg_m, comp_m, lista_comodos, esp_ext_m=0.20, esp_int_m=0.12):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Layers
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

    segs = {}   # key -> {"p1","p2","count"}
    textos = [] # (nome,cx,cy)

    for c in lista_comodos:
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

        # fallback (não deveria ocorrer com retângulos)
        msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "PAREDES"})

    # Desenhar segmentos: count==1 => perímetro => esp_ext; count>=2 => interna => esp_int
    for item in segs.values():
        thickness = esp_ext_m if item["count"] == 1 else esp_int_m
        draw_double_wall(item["p1"], item["p2"], thickness)

    # Textos
    for nome, cx, cy in textos:
        txt = msp.add_text(nome, dxfattribs={"layer": "TEXTOS", "height": 0.30})
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
