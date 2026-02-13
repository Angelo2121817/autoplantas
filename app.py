import streamlit as st
from streamlit_elements import elements, mui, dashboard
import pandas as pd
import json
import uuid
from datetime import datetime

# ============================================================================
# CONFIGURAÇÃO INICIAL
# ============================================================================

st.set_page_config(page_title="AutoPlanta CETESB Pro", layout="wide", page_icon="🏗️")

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def calcular_area(elemento):
    """Calcula a área real de um elemento em m²"""
    return elemento["w"] * elemento["h"]

def criar_elemento(tipo, x=0, y=0, w=2, h=2):
    """Cria um novo elemento com propriedades padrão"""
    cores = {
        "construcao": "#d3d3d3",
        "porta": "#8B4513",
        "janela": "#4682B4",
        "parede": "#696969",
        "portao": "#654321"
    }
    
    elemento_id = str(uuid.uuid4())[:8]
    
    return {
        "i": elemento_id,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "tipo": tipo,
        "cor": cores.get(tipo, "#cccccc"),
        "rotacao": 0,
        "rotulo": tipo.upper()
    }

def validar_layout(layout, largura_terreno, altura_terreno):
    """Valida o layout e retorna avisos"""
    avisos = []
    
    # Verificar limites
    for elem in layout:
        if elem["x"] + elem["w"] > largura_terreno:
            avisos.append(f"⚠️ {elem.get('rotulo', elem['i'])} está fora dos limites (largura)")
        if elem["y"] + elem["h"] > altura_terreno:
            avisos.append(f"⚠️ {elem.get('rotulo', elem['i'])} está fora dos limites (altura)")
    
    # Verificar sobreposições
    for i, elem1 in enumerate(layout):
        for elem2 in layout[i+1:]:
            if (elem1["x"] < elem2["x"] + elem2["w"] and
                elem1["x"] + elem1["w"] > elem2["x"] and
                elem1["y"] < elem2["y"] + elem2["h"] and
                elem1["y"] + elem1["h"] > elem2["y"]):
                avisos.append(f"⚠️ Sobreposição detectada: {elem1.get('rotulo', elem1['i'])} e {elem2.get('rotulo', elem2['i'])}")
    
    return avisos

def exportar_para_json():
    """Exporta o layout atual para JSON"""
    projeto = {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "terreno": {
            "largura": st.session_state.largura_terreno,
            "altura": st.session_state.altura_terreno,
            "area": st.session_state.largura_terreno * st.session_state.altura_terreno
        },
        "layout": st.session_state.layout,
        "responsavel": st.session_state.get("responsavel", ""),
        "notas": st.session_state.get("notas", "")
    }
    return json.dumps(projeto, indent=2, ensure_ascii=False)

def importar_de_json(json_str):
    """Importa um layout de JSON"""
    try:
        projeto = json.loads(json_str)
        st.session_state.layout = projeto["layout"]
        st.session_state.largura_terreno = projeto["terreno"]["largura"]
        st.session_state.altura_terreno = projeto["terreno"]["altura"]
        st.session_state.responsavel = projeto.get("responsavel", "")
        st.session_state.notas = projeto.get("notas", "")
        return True
    except Exception as e:
        st.error(f"Erro ao importar: {e}")
        return False

# ============================================================================
# INICIALIZAÇÃO DO SESSION STATE
# ============================================================================

if "layout" not in st.session_state:
    st.session_state.layout = [criar_elemento("construcao", x=2, y=2, w=8, h=6)]

if "largura_terreno" not in st.session_state:
    st.session_state.largura_terreno = 20

if "altura_terreno" not in st.session_state:
    st.session_state.altura_terreno = 15

if "elemento_selecionado" not in st.session_state:
    st.session_state.elemento_selecionado = None

if "responsavel" not in st.session_state:
    st.session_state.responsavel = "General"

if "notas" not in st.session_state:
    st.session_state.notas = ""

# ============================================================================
# INTERFACE PRINCIPAL
# ============================================================================

st.title("🏗️ Editor de Planta Baixa Profissional")
st.markdown("---")

# ============================================================================
# SIDEBAR - FERRAMENTAS E CONFIGURAÇÕES
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configurações do Terreno")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.largura_terreno = st.number_input(
            "Largura (m)", 
            min_value=5, 
            max_value=100, 
            value=st.session_state.largura_terreno,
            step=1
        )
    with col2:
        st.session_state.altura_terreno = st.number_input(
            "Altura (m)", 
            min_value=5, 
            max_value=100, 
            value=st.session_state.altura_terreno,
            step=1
        )
    
    area_terreno = st.session_state.largura_terreno * st.session_state.altura_terreno
    st.info(f"📐 Área Total: **{area_terreno:.2f} m²**")
    
    st.markdown("---")
    
    # ========================================================================
    # BIBLIOTECA DE ELEMENTOS
    # ========================================================================
    
    st.header("📚 Biblioteca de Elementos")
    
    elementos_disponiveis = [
        {"tipo": "construcao", "icone": "🏠", "nome": "Construção", "w": 6, "h": 4},
        {"tipo": "porta", "icone": "🚪", "nome": "Porta", "w": 1, "h": 2},
        {"tipo": "janela", "icone": "🪟", "nome": "Janela", "w": 2, "h": 1},
        {"tipo": "parede", "icone": "🧱", "nome": "Parede", "w": 1, "h": 4},
        {"tipo": "portao", "icone": "🚧", "nome": "Portão", "w": 3, "h": 1}
    ]
    
    for elem in elementos_disponiveis:
        if st.button(f"{elem['icone']} Adicionar {elem['nome']}", key=f"add_{elem['tipo']}", use_container_width=True):
            novo_elem = criar_elemento(elem['tipo'], x=0, y=0, w=elem['w'], h=elem['h'])
            st.session_state.layout.append(novo_elem)
            st.rerun()
    
    st.markdown("---")
    
    # ========================================================================
    # EDITOR DE PROPRIEDADES
    # ========================================================================
    
    st.header("✏️ Editor de Propriedades")
    
    if st.session_state.elemento_selecionado:
        elem_idx = next((i for i, e in enumerate(st.session_state.layout) 
                        if e["i"] == st.session_state.elemento_selecionado), None)
        
        if elem_idx is not None:
            elem = st.session_state.layout[elem_idx]
            
            st.write(f"**Elemento:** {elem.get('rotulo', elem['i'])}")
            
            # Editar rótulo
            novo_rotulo = st.text_input("Rótulo", value=elem.get('rotulo', ''), key="edit_rotulo")
            elem['rotulo'] = novo_rotulo
            
            # Editar dimensões
            col1, col2 = st.columns(2)
            with col1:
                nova_largura = st.number_input("Largura (m)", min_value=1, max_value=50, value=elem["w"], key="edit_w")
                elem["w"] = nova_largura
            with col2:
                nova_altura = st.number_input("Altura (m)", min_value=1, max_value=50, value=elem["h"], key="edit_h")
                elem["h"] = nova_altura
            
            # Editar cor
            nova_cor = st.color_picker("Cor", value=elem.get('cor', '#cccccc'), key="edit_cor")
            elem['cor'] = nova_cor
            
            # Editar rotação
            nova_rotacao = st.slider("Rotação (°)", 0, 360, elem.get('rotacao', 0), key="edit_rot")
            elem['rotacao'] = nova_rotacao
            
            st.info(f"📐 Área: **{calcular_area(elem):.2f} m²**")
            
            if st.button("🗑️ Remover Elemento", use_container_width=True):
                st.session_state.layout.pop(elem_idx)
                st.session_state.elemento_selecionado = None
                st.rerun()
        else:
            st.warning("Elemento não encontrado")
            st.session_state.elemento_selecionado = None
    else:
        st.info("👆 Clique em um elemento no grid para editar")
    
    st.markdown("---")
    
    # ========================================================================
    # AÇÕES
    # ========================================================================
    
    st.header("🔧 Ações")
    
    if st.button("🗑️ Limpar Tudo", use_container_width=True):
        st.session_state.layout = []
        st.session_state.elemento_selecionado = None
        st.rerun()
    
    # Exportar
    with st.expander("💾 Exportar Projeto"):
        json_export = exportar_para_json()
        st.download_button(
            label="📥 Download JSON",
            data=json_export,
            file_name=f"planta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
        st.code(json_export, language="json")
    
    # Importar
    with st.expander("📥 Importar Projeto"):
        arquivo_upload = st.file_uploader("Escolha um arquivo JSON", type=["json"])
        if arquivo_upload is not None:
            json_str = arquivo_upload.read().decode()
            if st.button("Carregar Projeto"):
                if importar_de_json(json_str):
                    st.success("✅ Projeto carregado!")
                    st.rerun()

# ============================================================================
# ÁREA PRINCIPAL - GRID E PAINEL DE DADOS
# ============================================================================

col_desenho, col_dados = st.columns([3, 1])

# ============================================================================
# GRID INTERATIVO
# ============================================================================

with col_desenho:
    st.subheader("🗺️ Área de Desenho")
    st.caption(f"Dimensões do terreno: {st.session_state.largura_terreno}m × {st.session_state.altura_terreno}m")
    
    with elements("dashboard_main"):
        with mui.Box(sx={
            "height": 600, 
            "width": "100%", 
            "border": "3px solid #333", 
            "bgcolor": "#f5f5f5",
            "borderRadius": "8px",
            "boxShadow": "0 4px 6px rgba(0,0,0,0.1)"
        }):
            with dashboard.Grid(
                st.session_state.layout,
                onLayoutChange=lambda new_layout: st.session_state.update({"layout": new_layout}),
                cols=st.session_state.largura_terreno,
                rowHeight=30,
                isDraggable=True,
                isResizable=True,
                compactType=None,
                preventCollision=False
            ):
                for elem in st.session_state.layout:
                    # Destacar elemento selecionado
                    borda_cor = "#ff0000" if st.session_state.elemento_selecionado == elem["i"] else "#000"
                    borda_largura = "3px" if st.session_state.elemento_selecionado == elem["i"] else "2px"
                    
                    mui.Paper(
                        elem.get('rotulo', elem['tipo'].upper()),
                        key=elem["i"],
                        sx={
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "bgcolor": elem.get('cor', '#cccccc'),
                            "border": f"{borda_largura} solid {borda_cor}",
                            "boxShadow": 3,
                            "cursor": "pointer",
                            "fontWeight": "bold",
                            "fontSize": "14px",
                            "color": "#fff",
                            "textShadow": "1px 1px 2px rgba(0,0,0,0.5)",
                            "transform": f"rotate({elem.get('rotacao', 0)}deg)",
                            "transition": "all 0.3s ease"
                        },
                        onClick=lambda e, elem_id=elem["i"]: st.session_state.update({"elemento_selecionado": elem_id})
                    )

# ============================================================================
# PAINEL DE DADOS
# ============================================================================

with col_dados:
    st.subheader("📋 Dados do Projeto")
    
    # Informações do responsável
    with st.expander("👤 Informações", expanded=True):
        st.session_state.responsavel = st.text_input("Responsável", value=st.session_state.responsavel)
        st.session_state.notas = st.text_area("Notas", value=st.session_state.notas, height=80)
    
    # Tabela de elementos
    with st.expander("📊 Tabela de Elementos", expanded=True):
        if st.session_state.layout:
            dados_tabela = []
            for elem in st.session_state.layout:
                dados_tabela.append({
                    "Elemento": elem.get('rotulo', elem['tipo']),
                    "Tipo": elem['tipo'].title(),
                    "Largura (m)": elem['w'],
                    "Altura (m)": elem['h'],
                    "Área (m²)": f"{calcular_area(elem):.2f}"
                })
            df = pd.DataFrame(dados_tabela)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum elemento adicionado")
    
    # Totalizadores
    with st.expander("📐 Totalizadores", expanded=True):
        area_total_construida = sum(calcular_area(e) for e in st.session_state.layout if e['tipo'] == 'construcao')
        area_outras = sum(calcular_area(e) for e in st.session_state.layout if e['tipo'] != 'construcao')
        percentual_ocupado = (area_total_construida / area_terreno * 100) if area_terreno > 0 else 0
        
        st.metric("Área do Terreno", f"{area_terreno:.2f} m²")
        st.metric("Área Construída", f"{area_total_construida:.2f} m²")
        st.metric("Outras Áreas", f"{area_outras:.2f} m²")
        st.metric("% Lote Ocupado", f"{percentual_ocupado:.1f}%")
        
        if percentual_ocupado > 100:
            st.error("⚠️ Área construída excede o terreno!")
    
    # Validações
    with st.expander("✅ Validações", expanded=False):
        avisos = validar_layout(st.session_state.layout, st.session_state.largura_terreno, st.session_state.altura_terreno)
        if avisos:
            for aviso in avisos:
                st.warning(aviso)
        else:
            st.success("✅ Tudo OK! Nenhum problema encontrado.")

# ============================================================================
# RODAPÉ
# ============================================================================

st.markdown("---")
st.caption("🏗️ AutoPlanta CETESB Pro | Editor de Plantas Baixas Profissional | v2.0")
