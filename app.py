import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import uuid

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Gerador de Galpão PRO", layout="wide")
st.title("🏭 Gerador de Layout Industrial - Modo General")

TIPOS = ["Escritório", "Banheiro", "Almoxarifado", "Produção", "Refeitório"]

# ----------------------------
# SESSION STATE
# ----------------------------
if "comodos" not in st.session_state:
    st.session_state["comodos"] = []

if "selected_id" not in st.session_state:
    st.session_state["selected_id"] = None


# ----------------------------
# HELPERS (regras geométricas)
# ----------------------------
def clamp(value, min_v, max_v):
    return max(min_v, min(value, max_v))

def dentro_do_galpao(x, y, w, h, larg_total, comp_total):
    """Retorna True se o retângulo estiver completamente dentro do galpão."""
    if x < 0 or y < 0:
        return False
    if x + w > larg_total:
        return False
    if y + h > comp_total:
        return False
    return True

def retangulos_colidem(a, b):
    """AABB collision (retângulos alinhados aos eixos)."""
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = a["x"] + a["largura"], a["y"] + a["comprimento"]

    bx1, by1 = b["x"], b["y"]
    bx2, by2 = b["x"] + b["largura"], b["y"] + b["comprimento"]

    # Se um está totalmente à esquerda/direita/acima/abaixo do outro, não colide
    if ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1:
        return False
    return True

def tem_colisao(lista, candidato, ignorar_id=None):
    for c in lista:
        if ignorar_id is not None and c["id"] == ignorar_id:
            continue
        if retangulos_colidem(c, candidato):
            return True
    return False

def get_comodo_by_id(cid):
    for c in st.session_state["comodos"]:
        if c["id"] == cid:
            return c
    return None

def update_comodo(cid, novos_campos):
    for i, c in enumerate(st.session_state["comodos"]):
        if c["id"] == cid:
            st.session_state["comodos"][i] = {**c, **novos_campos}
            return True
    return False

def delete_comodo(cid):
    st.session_state["comodos"] = [c for c in st.session_state["comodos"] if c["id"] != cid]
    if st.session_state["selected_id"] == cid:
        st.session_state["selected_id"] = None


# ----------------------------
# DXF
# ----------------------------
def gerar_dxf_completo(larg_total, comp_total, lista_comodos):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Camadas
    if "ESTRUTURA_EXTERNA" not in doc.layers:
        doc.layers.new(name="ESTRUTURA_EXTERNA", dxfattribs={"color": 7})
    if "PAREDES_INTERNAS" not in doc.layers:
        doc.layers.new(name="PAREDES_INTERNAS", dxfattribs={"color": 6})
    if "TEXTOS" not in doc.layers:
        doc.layers.new(name="TEXTOS", dxfattribs={"color": 2})

    # Galpão externo
    pontos_externos = [(0, 0), (larg_total, 0), (larg_total, comp_total), (0, comp_total), (0, 0)]
    msp.add_lwpolyline(pontos_externos, dxfattribs={"layer": "ESTRUTURA_EXTERNA"})

    # Cômodos
    for item in lista_comodos:
        x, y = item["x"], item["y"]
        l, c = item["largura"], item["comprimento"]
        nome = item["nome"]

        pontos_interno = [(x, y), (x + l, y), (x + l, y + c), (x, y + c), (x, y)]
        msp.add_lwpolyline(pontos_interno, dxfattribs={"layer": "PAREDES_INTERNAS"})

        msp.add_text(
            nome,
            dxfattribs={"layer": "TEXTOS", "height": 0.3},
        ).set_pos((x + l / 2, y + c / 2), align="MIDDLE_CENTER")

    output = io.StringIO()
    doc.write(output)
    return output.getvalue()


# ----------------------------
# PREVIEW
# ----------------------------
def plotar_preview_interativo(larg_total, comp_total, lista_comodos, selected_id=None):
    fig, ax = plt.subplots(figsize=(10, 8))

    rect_main = patches.Rectangle(
        (0, 0),
        larg_total,
        comp_total,
        linewidth=3,
        edgecolor="black",
        facecolor="#f0f0f0",
    )
    ax.add_patch(rect_main)

    for item in lista_comodos:
        is_sel = (selected_id is not None and item["id"] == selected_id)
        edge = "red" if is_sel else "blue"
        lw = 3 if is_sel else 2
        face = "#ffb3b3" if is_sel else "#a0cbe8"
        alpha = 0.65 if is_sel else 0.5

        rect = patches.Rectangle(
            (item["x"], item["y"]),
            item["largura"],
            item["comprimento"],
            linewidth=lw,
            edgecolor=edge,
            facecolor=face,
            alpha=alpha,
        )
        ax.add_patch(rect)

        ax.text(
            item["x"] + item["largura"] / 2,
            item["y"] + item["comprimento"] / 2,
            item["nome"],
            ha="center",
            va="center",
            fontsize=9,
            color="darkred" if is_sel else "darkblue",
            weight="bold",
        )

    ax.set_xlim(-1, larg_total + 1)
    ax.set_ylim(-1, comp_total + 1)
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.3)
    return fig


# ----------------------------
# UI
# ----------------------------
col_config, col_preview = st.columns([1, 2])

with col_config:
    st.header("1. O Galpão")
    largura = st.number_input("Largura Total (m)", 10.0, 300.0, 15.0, step=1.0)
    comprimento = st.number_input("Comprimento Total (m)", 10.0, 300.0, 30.0, step=1.0)

    st.divider()

    st.header("2. Adicionar Blocos")
    tipo_comodo = st.selectbox("Tipo", TIPOS)

    c1, c2 = st.columns(2)
    w_comodo = c1.number_input("Largura", 0.5, 200.0, 3.0, step=0.5)
    h_comodo = c2.number_input("Comprimento", 0.5, 200.0, 3.0, step=0.5)

    st.info("Posição (canto inferior esquerdo).")
    c3, c4 = st.columns(2)
    pos_x = c3.number_input("X", 0.0, largura, 0.0, step=0.5)
    pos_y = c4.number_input("Y", 0.0, comprimento, 0.0, step=0.5)

    validar_colisao = st.checkbox("Evitar sobreposição (colisão)", value=False)

    if st.button("➕ Adicionar Bloco"):
        novo = {
            "id": str(uuid.uuid4()),
            "nome": tipo_comodo,
            "largura": float(w_comodo),
            "comprimento": float(h_comodo),
            "x": float(pos_x),
            "y": float(pos_y),
        }

        ok = True
        if not dentro_do_galpao(novo["x"], novo["y"], novo["largura"], novo["comprimento"], largura, comprimento):
            st.error("Esse bloco sai para fora do galpão. Ajuste posição ou tamanho.")
            ok = False

        if validar_colisao and tem_colisao(st.session_state["comodos"], novo):
            st.error("Esse bloco colide com outro. Ajuste posição.")
            ok = False

        if ok:
            st.session_state["comodos"].append(novo)
            st.session_state["selected_id"] = novo["id"]
            st.success(f"{tipo_comodo} adicionado!")

    if st.button("🗑️ Limpar Tudo (Resetar)"):
        st.session_state["comodos"] = []
        st.session_state["selected_id"] = None
        st.rerun()

    st.divider()

    st.header("3. Editar Bloco Existente")

    if len(st.session_state["comodos"]) == 0:
        st.caption("Ainda não há blocos para editar.")
    else:
        # Lista para seleção
        options = []
        for c in st.session_state["comodos"]:
            label = f"{c['nome']} | id:{c['id'][:8]} | ({c['x']:.1f},{c['y']:.1f}) {c['largura']:.1f}x{c['comprimento']:.1f}"
            options.append((label, c["id"]))

        # Define seleção padrão
        default_index = 0
        if st.session_state["selected_id"] is not None:
            for i, (_, cid) in enumerate(options):
                if cid == st.session_state["selected_id"]:
                    default_index = i
                    break

        selected_label = st.selectbox(
            "Selecione um bloco",
            [o[0] for o in options],
            index=default_index,
        )
        selected_id = dict(options).get(selected_label)
        st.session_state["selected_id"] = selected_id

        comodo = get_comodo_by_id(selected_id)

        if comodo is not None:
            novo_nome = st.selectbox("Tipo/Nome", TIPOS, index=TIPOS.index(comodo["nome"]) if comodo["nome"] in TIPOS else 0)

            e1, e2 = st.columns(2)
            novo_w = e1.number_input("Nova largura", 0.5, 200.0, float(comodo["largura"]), step=0.5, key="edit_w")
            novo_h = e2.number_input("Novo comprimento", 0.5, 200.0, float(comodo["comprimento"]), step=0.5, key="edit_h")

            e3, e4 = st.columns(2)
            novo_x = e3.number_input("Novo X", 0.0, largura, float(comodo["x"]), step=0.5, key="edit_x")
            novo_y = e4.number_input("Novo Y", 0.0, comprimento, float(comodo["y"]), step=0.5, key="edit_y")

            # Ajuste automático opcional (clamp)
            auto_ajustar = st.checkbox("Auto-ajustar para caber no galpão", value=True)

            candidato = {
                "id": comodo["id"],
                "nome": novo_nome,
                "largura": float(novo_w),
                "comprimento": float(novo_h),
                "x": float(novo_x),
                "y": float(novo_y),
            }

            if auto_ajustar:
                candidato["x"] = clamp(candidato["x"], 0.0, max(0.0, largura - candidato["largura"]))
                candidato["y"] = clamp(candidato["y"], 0.0, max(0.0, comprimento - candidato["comprimento"]))

            b1, b2, b3 = st.columns(3)

            if b1.button("💾 Aplicar alterações"):
                ok = True
                if not dentro_do_galpao(candidato["x"], candidato["y"], candidato["largura"], candidato["comprimento"], largura, comprimento):
                    st.error("Alteração inválida: bloco sai do galpão.")
                    ok = False

                if validar_colisao and tem_colisao(st.session_state["comodos"], candidato, ignorar_id=comodo["id"]):
                    st.error("Alteração inválida: bloco colide com outro.")
                    ok = False

                if ok:
                    update_comodo(comodo["id"], candidato)
                    st.success("Bloco atualizado!")

            if b2.button("📄 Duplicar"):
                dup = {**comodo, "id": str(uuid.uuid4())}
                # desloca um pouco para não ficar exatamente em cima
                dup["x"] = clamp(dup["x"] + 0.5, 0.0, max(0.0, largura - dup["largura"]))
                dup["y"] = clamp(dup["y"] + 0.5, 0.0, max(0.0, comprimento - dup["comprimento"]))
                if (not validar_colisao) or (not tem_colisao(st.session_state["comodos"], dup)):
                    st.session_state["comodos"].append(dup)
                    st.session_state["selected_id"] = dup["id"]
                    st.success("Duplicado!")
                else:
                    st.error("Não foi possível duplicar (colisão). Desative colisão ou ajuste depois.")

            if b3.button("🧨 Excluir"):
                delete_comodo(comodo["id"])
                st.success("Bloco removido.")
                st.rerun()

    st.divider()

    st.header("4. Lista de Blocos")
    if len(st.session_state["comodos"]) > 0:
        # visão rápida
        st.dataframe(
            [
                {
                    "id": c["id"][:8],
                    "tipo": c["nome"],
                    "x": c["x"],
                    "y": c["y"],
                    "largura": c["largura"],
                    "comprimento": c["comprimento"],
                }
                for c in st.session_state["comodos"]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("Sem blocos.")

with col_preview:
    st.subheader("👀 Planta Baixa em Tempo Real")
    fig = plotar_preview_interativo(largura, comprimento, st.session_state["comodos"], st.session_state["selected_id"])
    st.pyplot(fig)

    st.divider()

    dxf_texto = gerar_dxf_completo(largura, comprimento, st.session_state["comodos"])
    st.download_button(
        label="📥 BAIXAR PROJETO (.DXF)",
        data=dxf_texto,
        file_name="planta_industrial_general.dxf",
        mime="application/dxf",
    )
