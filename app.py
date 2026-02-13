import streamlit as st
from streamlit_elements import elements, mui, dashboard
import pandas as pd
import json
import uuid
from datetime import datetime

# ============================================================================
# CONFIGURAÇÃO INICIAL E ESTILO
# ============================================================================

st.set_page_config(page_title="AutoPlanta CETESB Pro+", layout="wide", page_icon="🏗️")

# Estilo CSS customizado para melhorar a UI
st.markdown("""
<style>
    /* Melhora a aparência dos botões na sidebar */
    .stButton>button {
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #4A5568; /* Cor mais escura no hover */
        color: white;
        border-color: #A0AEC0;
    }
    /* Remove padding excessivo do topo */
    .main .block-container {
        padding-top: 2rem;
    }
    /* Estilo para o cabeçalho do painel de dados */
    .st-emotion-cache-1r4qj8v {
        border-bottom: 2px solid #4A5568;
        padding-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def calcular_area(elemento):
    """Calcula a área real de um elemento em m²."""
    return elemento["w"] * elemento["h"]

def criar_elemento(tipo, x=0, y=0, w=2, h=2):
    """Cria um novo elemento com propriedades padrão."""
    cores = {
        "construcao": "#d3d3d3", "porta": "#8B4513", "janela": "#4682B4",
        "parede": "#696969", "portao": "#654321"
    }
    elemento_id = str(uuid.uuid4())[:8]
    return {
        "i": elemento_id, "x": x, "y": y, "w": w, "h": h, "tipo": tipo,
        "cor": cores.get(tipo, "#cccccc"), "rotacao": 0, "rotulo": f"{tipo.title()} {elemento_id}"
    }

def validar_layout(layout, largura_terreno, altura_terreno):
    """Valida o layout e retorna uma lista de avisos."""
    avisos = []
    for elem in layout:
        if elem["x"] + elem["w"] > largura_terreno:
            avisos.append(f"⚠️ {elem.get('rotulo', elem['i'])} fora dos limites (largura).")
        if elem["y"] + elem["h"] > altura_terreno:
            avisos.append(f"⚠️ {elem.get('rotulo', elem['i'])} fora dos limites (altura).")
    
    for i, elem1 in enumerate(layout):
        for elem2 in layout[i+1:]:
            if (elem1["x"] < elem2["x"] + elem2["w"] and elem1["x"] + elem1["w"] > elem2["x"] and
                elem1["y"] < elem2["y"] + elem2["h"] and elem1["y"] + elem1["h"] > elem2["y"]):
                avisos.append(f"⚠️ Sobreposição: {elem1.get('rotulo', elem1['i'])} e {elem2.get('rotulo', elem2['i'])}.")
    return avisos

def exportar_para_json():
    """Exporta o estado atual do projeto para uma string JSON."""
    projeto = {
        "versao_app": "2.1",
        "data_exportacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "terreno": {
            "largura": st.session_state.largura_terreno,
            "altura": st.session_state.altura_terreno,
            "area": st.session_state.largura_terreno * st.session_state.altura_terreno
        },
        "layout": st.session_state.layout,
        "metadados": {
            "responsavel": st.session_state.get("responsavel", ""),
            "notas": st.session_state.get("notas", "")
        }
    }
    return json.dumps(projeto, indent=2, ensure_ascii=False)

def importar_de_json(json_str):
    """Carrega um projeto a partir de uma string JSON, atualizando o session_state."""
    try:
        projeto = json.loads(json_str)
        st.session_state.layout = projeto["layout"]
        st.session_state.largura_terreno = projeto["terreno"]["largura"]
        st.session_state.altura_terreno = projeto["terreno"]["altura"]
        st.session_state.responsavel = projeto.get("metadados", {}).get("responsavel", "")
        st.session_state.notas = projeto.get("metadados", {}).get("notas", "")
        st.session_state.elemento_selecionado = None # Limpa seleção após importação
        st.toast("✅ Projeto importado com sucesso!", icon="📥")
        return True
    except Exception as e:
        st.error(f"❌ Erro ao importar o arquivo: {e}")
        return False

def atualizar_elemento_selecionado(elem_id):
    """Callback para definir o elemento selecionado."""
    st.session_state.elemento_selecionado = elem_id

def desmarcar_elemento():
    """Callback para limpar a seleção (usado no duplo clique)."""
    st.session_state.elemento_selecionado = None

# ============================================================================
# INICIALIZAÇÃO DO SESSION STATE
# ============================================================================

# Usar um dicionário para agrupar estados relacionados ao projeto
if "projeto" not in st.session_state:
    st.session_state.projeto = {
        "layout": [criar_elemento("construcao", x=2, y=2, w=8, h=6)],
        "largura_terreno": 20,
        "altura_terreno": 15,
        "responsavel": "Eng. Responsável",
        "notas": "Projeto inicial."
    }
if "elemento_selecionado" not in st.session_state:
    st.session_state.elemento_selecionado = None

# Atalhos para facilitar o acesso
layout = st.session_state.projeto["layout"]
largura_terreno = st.session_state.projeto["largura_terreno"]
altura_terreno = st.session_state.projeto["altura_terreno"]

# ============================================================================
# INTERFACE PRINCIPAL
# ============================================================================

st.title("🏗️ AutoPlanta CETESB Pro+")
st.markdown("---")

# ============================================================================
# SIDEBAR - FERRAMENTAS E CONFIGURAÇÕES
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configurações do Terreno")
    
    col1, col2 = st.columns(2)
    st.session_state.projeto["largura_terreno"] = col1.number_input("Largura (m)", min_value=5, max_value=100, value=largura_terreno, step=1)
    st.session_state.projeto["altura_terreno"] = col2.number_input("Altura (m)", min_value=5, max_value=100, value=altura_terreno, step=1)
    
    area_terreno = st.session_state.projeto["largura_terreno"] * st.session_state.projeto["altura_terreno"]
    st.info(f"📐 Área Total: **{area_terreno:.2f} m²**")
    
    st.markdown("---")
    
    st.header("📚 Biblioteca de Elementos")
    elementos_disponiveis = [
        {"tipo": "construcao", "icone": "🏠", "nome": "Construção", "w": 6, "h": 4},
        {"tipo": "porta", "icone": "🚪", "nome": "Porta", "w": 1, "h": 0.2}, # Portas são finas
        {"tipo": "janela", "icone": "🪟", "nome": "Janela", "w": 2, "h": 0.2}, # Janelas são finas
        {"tipo": "parede", "icone": "🧱", "nome": "Parede", "w": 0.2, "h": 4}, # Paredes são finas
        {"tipo": "portao", "icone": "🚧", "nome": "Portão", "w": 3, "h": 0.3}
    ]
    for elem in elementos_disponiveis:
        if st.button(f"{elem['icone']} Adicionar {elem['nome']}", key=f"add_{elem['tipo']}", use_container_width=True):
            novo_elem = criar_elemento(elem['tipo'], w=elem['w'], h=elem['h'])
            st.session_state.projeto["layout"].append(novo_elem)
            st.rerun()
            
    st.markdown("---")
    
    st.header("✏️ Editor de Propriedades")
    if st.session_state.elemento_selecionado:
        try:
            elem_idx = next(i for i, e in enumerate(layout) if e["i"] == st.session_state.elemento_selecionado)
            elem = layout[elem_idx]
            
            st.write(f"**Editando:** {elem.get('rotulo', elem['i'])}")
            elem['rotulo'] = st.text_input("Rótulo", value=elem.get('rotulo', ''), key=f"edit_rotulo_{elem['i']}")
            
            col1, col2 = st.columns(2)
            elem["w"] = col1.number_input("Largura (m)", min_value=0.1, max_value=50.0, value=elem["w"], step=0.1, key=f"edit_w_{elem['i']}")
            elem["h"] = col2.number_input("Altura (m)", min_value=0.1, max_value=50.0, value=elem["h"], step=0.1, key=f"edit_h_{elem['i']}")
            
            elem['cor'] = st.color_picker("Cor", value=elem.get('cor', '#cccccc'), key=f"edit_cor_{elem['i']}")
            elem['rotacao'] = st.slider("Rotação (°)", 0, 360, elem.get('rotacao', 0), key=f"edit_rot_{elem['i']}")
            
            st.info(f"📐 Área do Elemento: **{calcular_area(elem):.2f} m²**")
            
            if st.button("🗑️ Remover Elemento", use_container_width=True, type="primary"):
                st.session_state.projeto["layout"].pop(elem_idx)
                desmarcar_elemento()
                st.rerun()
        except StopIteration:
            st.warning("Elemento selecionado não encontrado. Recarregando...")
            desmarcar_elemento()
            st.rerun()
    else:
        st.info("👆 Clique em um elemento para editar suas propriedades. Dê um duplo clique para desmarcar.")

    st.markdown("---")
    
    st.header("🔧 Ações do Projeto")
    if st.button("🗑️ Limpar Desenho", use_container_width=True):
        st.session_state.projeto["layout"] = []
        desmarcar_elemento()
        st.rerun()

    with st.expander("💾 Exportar/Importar"):
        json_export = exportar_para_json()
        st.download_button("📥 Download JSON", json_export, f"planta_{datetime.now().strftime('%Y%m%d')}.json", "application/json", use_container_width=True)
        
        arquivo_upload = st.file_uploader("Carregar arquivo JSON", type=["json"])
        if arquivo_upload:
            json_str = arquivo_upload.read().decode()
            importar_de_json(json_str)
            st.rerun()

# ============================================================================
# ÁREA PRINCIPAL - GRID E PAINEL DE DADOS
# ============================================================================

col_desenho, col_dados = st.columns([3, 1])

with col_desenho:
    st.subheader("🗺️ Área de Desenho")
    st.caption(f"Dimensões do terreno: {largura_terreno}m × {altura_terreno}m. Grid: {largura_terreno} colunas.")
    
    with elements("dashboard_main"):
        # O onLayoutChange é o segredo para sincronizar o grid com o session_state
        def handle_layout_change(new_layout):
            st.session_state.projeto["layout"] = new_layout

        with mui.Box(sx={"height": 650, "width": "100%", "border": "2px dashed #718096", "bgcolor": "#f0f2f6", "borderRadius": "8px"}):
            with dashboard.Grid(
                layout,
                onLayoutChange=handle_layout_change,
                cols=largura_terreno,
                rowHeight=20, # Ajuste para melhor granularidade
                isDraggable=True,
                isResizable=True,
                compactType=None,
                preventCollision=False,
            ):
                for elem in layout:
                    is_selected = st.session_state.elemento_selecionado == elem["i"]
                    mui.Paper(
                        elem.get('rotulo', elem['tipo'].upper()),
                        key=elem["i"],
                        sx={
                            "display": "flex", "alignItems": "center", "justifyContent": "center",
                            "bgcolor": elem.get('cor', '#cccccc'),
                            "border": f"3px solid {'#ff4757' if is_selected else 'rgba(0,0,0,0.6)'}",
                            "boxShadow": "0 6px 10px rgba(0,0,0,0.2)" if is_selected else "0 2px 4px rgba(0,0,0,0.1)",
                            "transform": f"rotate({elem.get('rotacao', 0)}deg) scale({1.05 if is_selected else 1})",
                            "transition": "all 0.2s ease-in-out",
                            "cursor": "pointer", "fontWeight": "bold", "fontSize": "12px", "color": "#fff",
                            "textShadow": "1px 1px 3px rgba(0,0,0,0.7)",
                        },
                        onClick=lambda e, elem_id=elem["i"]: atualizar_elemento_selecionado(elem_id),
                        onDoubleClick=lambda: desmarcar_elemento(),
                    )

with col_dados:
    st.subheader("📋 Dados do Projeto")
    
    with st.expander("👤 Informações", expanded=True):
        st.session_state.projeto["responsavel"] = st.text_input("Responsável", value=st.session_state.projeto["responsavel"])
        st.session_state.projeto["notas"] = st.text_area("Notas", value=st.session_state.projeto["notas"], height=80)
    
    with st.expander("📊 Tabela de Elementos", expanded=True):
        if layout:
            df = pd.DataFrame([{
                "Elemento": e.get('rotulo', e['tipo']), "Tipo": e['tipo'].title(),
                "Largura (m)": e['w'], "Altura (m)": e['h'], "Área (m²)": f"{calcular_area(e):.2f}"
            } for e in layout])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum elemento no desenho.")
    
    with st.expander("📐 Totalizadores", expanded=True):
        area_construida = sum(calcular_area(e) for e in layout if e['tipo'] == 'construcao')
        taxa_ocupacao = (area_construida / area_terreno * 100) if area_terreno > 0 else 0
        
        st.metric("Área do Terreno", f"{area_terreno:.2f} m²")
        st.metric("Área Construída Total", f"{area_construida:.2f} m²")
        st.metric("Taxa de Ocupação", f"{taxa_ocupacao:.1f}%")
        
        if taxa_ocupacao > 100:
            st.error("⚠️ Área construída excede a área do terreno!")
    
    with st.expander("✅ Validações", expanded=True):
        avisos = validar_layout(layout, largura_terreno, altura_terreno)
        if avisos:
            for aviso in avisos:
                st.warning(aviso)
        else:
            st.success("✅ Tudo certo! Nenhum problema detectado.")

st.markdown("---")
st.caption("🏗️ AutoPlanta CETESB Pro+ | Criado com Streamlit e a ajuda de Manus | v2.1")
