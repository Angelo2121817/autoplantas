import streamlit as st
from streamlit_elements import elements, mui, dashboard
import pandas as pd
import json
import uuid
from datetime import datetime

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira chamada do Streamlit)
# ============================================================================
st.set_page_config(page_title="AutoPlanta CETESB Pro+", layout="wide", page_icon="🏗️")

# ============================================================================
# ESTILO CSS
# ============================================================================
st.markdown("""
<style>
    /* Remove padding excessivo do topo no Streamlit Cloud */
    .main .block-container { padding-top: 2rem; }
    /* Estilo para botões na sidebar */
    .stButton>button { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNÇÕES AUXILIARES E DE CALLBACK
# ============================================================================

def criar_elemento(tipo, x=0, y=0, w=2, h=2):
    """Cria um novo dicionário de elemento com um ID único."""
    cores = {
        "construcao": "#B0B0B0", "porta": "#8B4513", "janela": "#4682B4",
        "parede": "#696969", "portao": "#654321"
    }
    elemento_id = str(uuid.uuid4())[:8]
    return {
        "i": elemento_id, "x": x, "y": y, "w": w, "h": h, "tipo": tipo,
        "cor": cores.get(tipo, "#cccccc"), "rotacao": 0, "rotulo": f"{tipo.title()} {elemento_id}"
    }

# --- Callbacks para manipulação do layout (essencial para streamlit-elements) ---

def adicionar_elemento_callback(tipo, w, h):
    """Adiciona um novo elemento ao layout no session_state."""
    novo_elem = criar_elemento(tipo, w=w, h=h)
    st.session_state.layout.append(novo_elem)
    st.toast(f"✅ {tipo.title()} adicionado!", icon="🎉")

def remover_elemento_callback():
    """Remove o elemento atualmente selecionado."""
    if st.session_state.elemento_selecionado:
        elem_idx = next((i for i, e in enumerate(st.session_state.layout) if e["i"] == st.session_state.elemento_selecionado), None)
        if elem_idx is not None:
            removido = st.session_state.layout.pop(elem_idx)
            st.session_state.elemento_selecionado = None
            st.toast(f"🗑️ '{removido['rotulo']}' removido.", icon="♻️")

def limpar_tudo_callback():
    """Limpa todos os elementos do desenho."""
    if st.session_state.layout:
        st.session_state.layout = []
        st.session_state.elemento_selecionado = None
        st.toast("✨ Desenho limpo!", icon="🗑️")

# --- Outras funções ---

def exportar_para_json():
    """Gera uma string JSON do projeto atual."""
    projeto = {
        "versao_app": "2.3-cloud", "data_exportacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "terreno": {"largura": st.session_state.largura_terreno, "altura": st.session_state.altura_terreno},
        "layout": st.session_state.layout,
        "metadados": {"responsavel": st.session_state.responsavel, "notas": st.session_state.notas}
    }
    return json.dumps(projeto, indent=2, ensure_ascii=False)

def importar_de_json(json_str):
    """Carrega um projeto a partir de uma string JSON."""
    try:
        projeto = json.loads(json_str)
        st.session_state.layout = projeto["layout"]
        st.session_state.largura_terreno = projeto["terreno"]["largura"]
        st.session_state.altura_terreno = projeto["terreno"]["altura"]
        st.session_state.responsavel = projeto.get("metadados", {}).get("responsavel", "")
        st.session_state.notas = projeto.get("metadados", {}).get("notas", "")
        st.session_state.elemento_selecionado = None
        st.toast("✅ Projeto importado com sucesso!", icon="📥")
        # st.rerun() é seguro aqui, pois estamos recarregando todo o estado de uma vez.
        st.rerun()
    except Exception as e:
        st.error(f"❌ Erro ao importar o arquivo: {e}")

# ============================================================================
# INICIALIZAÇÃO DO SESSION STATE
# ============================================================================

if "layout" not in st.session_state:
    st.session_state.layout = [criar_elemento("construcao", x=2, y=2, w=8, h=6)]
if "largura_terreno" not in st.session_state: st.session_state.largura_terreno = 20
if "altura_terreno" not in st.session_state: st.session_state.altura_terreno = 15
if "responsavel" not in st.session_state: st.session_state.responsavel = "Eng. Responsável"
if "notas" not in st.session_state: st.session_state.notas = "Projeto inicial."
if "elemento_selecionado" not in st.session_state: st.session_state.elemento_selecionado = None

# ============================================================================
# LAYOUT DA INTERFACE (Sidebar e Área Principal)
# ============================================================================

st.title("🏗️ AutoPlanta CETESB Pro+")
st.markdown("---")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Terreno")
    st.session_state.largura_terreno = st.number_input("Largura (m)", min_value=5, max_value=100, value=st.session_state.largura_terreno, step=1)
    st.session_state.altura_terreno = st.number_input("Altura (m)", min_value=5, max_value=100, value=st.session_state.altura_terreno, step=1)
    
    st.markdown("---")
    
    st.header("📚 Biblioteca")
    elementos_disponiveis = [
        {"tipo": "construcao", "icone": "🏠", "nome": "Construção", "w": 6, "h": 4},
        {"tipo": "porta", "icone": "🚪", "nome": "Porta", "w": 1, "h": 0.2},
        {"tipo": "janela", "icone": "🪟", "nome": "Janela", "w": 2, "h": 0.2},
        {"tipo": "parede", "icone": "🧱", "nome": "Parede", "w": 0.2, "h": 4},
        {"tipo": "portao", "icone": "🚧", "nome": "Portão", "w": 3, "h": 0.3}
    ]
    for elem_lib in elementos_disponiveis:
        st.button(
            f"{elem_lib['icone']} Adicionar {elem_lib['nome']}",
            key=f"add_{elem_lib['tipo']}",
            use_container_width=True,
            on_click=adicionar_elemento_callback,
            args=(elem_lib['tipo'], elem_lib['w'], elem_lib['h'])
        )
            
    st.markdown("---")
    
    st.header("✏️ Propriedades")
    if st.session_state.elemento_selecionado:
        try:
            elem_idx = next(i for i, e in enumerate(st.session_state.layout) if e["i"] == st.session_state.elemento_selecionado)
            elem = st.session_state.layout[elem_idx]
            
            st.write(f"**Editando:** {elem.get('rotulo', elem['i'])}")
            elem['rotulo'] = st.text_input("Rótulo", value=elem.get('rotulo', ''), key=f"edit_rotulo_{elem['i']}")
            
            col1, col2 = st.columns(2)
            elem["w"] = col1.number_input("Largura (m)", min_value=0.1, value=elem["w"], step=0.1, key=f"edit_w_{elem['i']}")
            elem["h"] = col2.number_input("Altura (m)", min_value=0.1, value=elem["h"], step=0.1, key=f"edit_h_{elem['i']}")
            
            elem['cor'] = st.color_picker("Cor", value=elem.get('cor', '#cccccc'), key=f"edit_cor_{elem['i']}")
            elem['rotacao'] = st.slider("Rotação (°)", 0, 360, elem.get('rotacao', 0), key=f"edit_rot_{elem['i']}")
            
            st.button("🗑️ Remover Elemento", use_container_width=True, type="primary", on_click=remover_elemento_callback)
        except StopIteration:
            st.session_state.elemento_selecionado = None
            st.rerun()
    else:
        st.info("Clique em um item para editar.")

    st.markdown("---")
    
    st.header("🔧 Ações")
    st.button("🗑️ Limpar Desenho", use_container_width=True, on_click=limpar_tudo_callback)

    with st.expander("💾 Exportar/Importar"):
        st.download_button("📥 Download JSON", exportar_para_json(), f"planta_{datetime.now().strftime('%Y%m%d')}.json", "application/json", use_container_width=True)
        
        arquivo_upload = st.file_uploader("Carregar arquivo JSON", type=["json"])
        if arquivo_upload:
            json_str = arquivo_upload.read().decode()
            importar_de_json(json_str)

# --- ÁREA PRINCIPAL ---
col_desenho, col_dados = st.columns([3, 1])

with col_desenho:
    st.subheader("🗺️ Área de Desenho")
    
    with elements("dashboard_main"):
        def handle_layout_change(new_layout):
            st.session_state.layout = new_layout

        with mui.Box(sx={"height": 650, "width": "100%", "border": "2px dashed #718096", "bgcolor": "#f0f2f6", "borderRadius": "8px"}):
            with dashboard.Grid(
                st.session_state.layout,
                onLayoutChange=handle_layout_change,
                cols=st.session_state.largura_terreno,
                rowHeight=20,
                isDraggable=True, isResizable=True, compactType=None, preventCollision=False,
            ):
                for elem in st.session_state.layout:
                    is_selected = st.session_state.elemento_selecionado == elem["i"]
                    mui.Paper(
                        elem.get('rotulo', elem['tipo'].upper()),
                        key=elem["i"],
                        sx={
                            "display": "flex", "alignItems": "center", "justifyContent": "center",
                            "backgroundColor": elem.get('cor', '#cccccc'),
                            "border": f"3px solid {'#ff4757' if is_selected else 'rgba(0,0,0,0.6)'}",
                            "transform": f"rotate({elem.get('rotacao', 0)}deg)",
                            "cursor": "pointer", "fontWeight": "bold", "fontSize": "12px", "color": "#fff",
                            "textShadow": "1px 1px 3px rgba(0,0,0,0.7)",
                        },
                        onClick=lambda e, elem_id=elem["i"]: st.session_state.update(elemento_selecionado=elem_id),
                        onDoubleClick=lambda: st.session_state.update(elemento_selecionado=None),
                    )

with col_dados:
    st.subheader("📋 Dados do Projeto")
    # (O restante do painel de dados pode continuar o mesmo, pois ele apenas lê o estado)
    # ...
