import streamlit as st
import plotly.graph_objects as go
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

def gerar_visualizacao_planta():
    """Gera a visualização da planta usando Plotly"""
    fig = go.Figure()
    
    # Adicionar retângulo do terreno
    fig.add_shape(
        type="rect",
        x0=0, y0=0,
        x1=st.session_state.largura_terreno,
        y1=st.session_state.altura_terreno,
        line=dict(color="black", width=3),
        fillcolor="lightgray",
        opacity=0.2
    )
    
    # Adicionar elementos
    for elem in st.session_state.layout:
        # Determinar se está selecionado
        borda_largura = 4 if st.session_state.elemento_selecionado == elem["i"] else 2
        borda_cor = "red" if st.session_state.elemento_selecionado == elem["i"] else "black"
        
        fig.add_shape(
            type="rect",
            x0=elem["x"],
            y0=elem["y"],
            x1=elem["x"] + elem["w"],
            y1=elem["y"] + elem["h"],
            line=dict(color=borda_cor, width=borda_largura),
            fillcolor=elem.get("cor", "#cccccc"),
            opacity=0.8
        )
        
        # Adicionar texto (rótulo)
        fig.add_annotation(
            x=elem["x"] + elem["w"]/2,
            y=elem["y"] + elem["h"]/2,
            text=elem.get("rotulo", elem["tipo"].upper()),
            showarrow=False,
            font=dict(size=12, color="white", family="Arial Black"),
            bgcolor="rgba(0,0,0,0.5)",
            borderpad=4
        )
        
        # Adicionar dimensões
        fig.add_annotation(
            x=elem["x"] + elem["w"]/2,
            y=elem["y"] + elem["h"] + 0.3,
            text=f"{elem['w']}m",
            showarrow=False,
            font=dict(size=9, color="blue")
        )
        fig.add_annotation(
            x=elem["x"] - 0.3,
            y=elem["y"] + elem["h"]/2,
            text=f"{elem['h']}m",
            showarrow=False,
            font=dict(size=9, color="blue"),
            textangle=-90
        )
    
    # Configurar layout
    fig.update_layout(
        width=900,
        height=600,
        xaxis=dict(
            range=[-1, st.session_state.largura_terreno + 1],
            showgrid=True,
            gridwidth=1,
            gridcolor="lightblue",
            title="Largura (metros)",
            dtick=1
        ),
        yaxis=dict(
            range=[-1, st.session_state.altura_terreno + 1],
            showgrid=True,
            gridwidth=1,
            gridcolor="lightblue",
            title="Altura (metros)",
            dtick=1,
            scaleanchor="x",
            scaleratio=1
        ),
        plot_bgcolor="white",
        margin=dict(l=50, r=50, t=50, b=50),
        title=dict(
            text=f"Planta Baixa - Terreno {st.session_state.largura_terreno}m × {st.session_state.altura_terreno}m",
            x=0.5,
            xanchor="center"
        )
    )
    
    return fig

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
                avisos.append(f"⚠️ Sobreposição: {elem1.get('rotulo', elem1['i'])} e {elem2.get('rotulo', elem2['i'])}")
    
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
    st.session_state.layout = [criar_elemento("construcao", x=5, y=5, w=8, h=6)]

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
        largura = st.number_input(
            "Largura (m)", 
            min_value=5, 
            max_value=100, 
            value=st.session_state.largura_terreno,
            step=1,
            key="input_largura"
        )
        if largura != st.session_state.largura_terreno:
            st.session_state.largura_terreno = largura
            st.rerun()
    
    with col2:
        altura = st.number_input(
            "Altura (m)", 
            min_value=5, 
            max_value=100, 
            value=st.session_state.altura_terreno,
            step=1,
            key="input_altura"
        )
        if altura != st.session_state.altura_terreno:
            st.session_state.altura_terreno = altura
            st.rerun()
    
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
            novo_elem = criar_elemento(elem['tipo'], x=1, y=1, w=elem['w'], h=elem['h'])
            st.session_state.layout.append(novo_elem)
            st.session_state.elemento_selecionado = novo_elem["i"]
            st.rerun()
    
    st.markdown("---")
    
    # ========================================================================
    # SELETOR DE ELEMENTOS
    # ========================================================================
    
    st.header("🎯 Selecionar Elemento")
    
    if st.session_state.layout:
        opcoes = ["Nenhum"] + [f"{e.get('rotulo', e['tipo'])} ({e['i']})" for e in st.session_state.layout]
        indices = [None] + [e["i"] for e in st.session_state.layout]
        
        selecao_atual = None
        if st.session_state.elemento_selecionado:
            try:
                selecao_atual = indices.index(st.session_state.elemento_selecionado)
            except:
                selecao_atual = 0
        else:
            selecao_atual = 0
        
        escolha = st.selectbox(
            "Escolha um elemento para editar:",
            range(len(opcoes)),
            format_func=lambda x: opcoes[x],
            index=selecao_atual,
            key="selector_elemento"
        )
        
        st.session_state.elemento_selecionado = indices[escolha]
    
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
            
            st.write(f"**Editando:** {elem.get('rotulo', elem['i'])}")
            
            # Editar rótulo
            novo_rotulo = st.text_input("Rótulo", value=elem.get('rotulo', ''), key="edit_rotulo")
            if novo_rotulo != elem.get('rotulo', ''):
                elem['rotulo'] = novo_rotulo
                st.rerun()
            
            # Editar posição
            st.subheader("📍 Posição")
            col1, col2 = st.columns(2)
            with col1:
                nova_x = st.number_input("X (m)", min_value=0, max_value=st.session_state.largura_terreno, value=elem["x"], key="edit_x")
                if nova_x != elem["x"]:
                    elem["x"] = nova_x
                    st.rerun()
            with col2:
                nova_y = st.number_input("Y (m)", min_value=0, max_value=st.session_state.altura_terreno, value=elem["y"], key="edit_y")
                if nova_y != elem["y"]:
                    elem["y"] = nova_y
                    st.rerun()
            
            # Editar dimensões
            st.subheader("📏 Dimensões")
            col1, col2 = st.columns(2)
            with col1:
                nova_largura = st.number_input("Largura (m)", min_value=1, max_value=50, value=elem["w"], key="edit_w")
                if nova_largura != elem["w"]:
                    elem["w"] = nova_largura
                    st.rerun()
            with col2:
                nova_altura = st.number_input("Altura (m)", min_value=1, max_value=50, value=elem["h"], key="edit_h")
                if nova_altura != elem["h"]:
                    elem["h"] = nova_altura
                    st.rerun()
            
            # Editar cor
            nova_cor = st.color_picker("🎨 Cor", value=elem.get('cor', '#cccccc'), key="edit_cor")
            if nova_cor != elem.get('cor', '#cccccc'):
                elem['cor'] = nova_cor
                st.rerun()
            
            st.info(f"📐 Área: **{calcular_area(elem):.2f} m²**")
            
            if st.button("🗑️ Remover Elemento", use_container_width=True, type="primary"):
                st.session_state.layout.pop(elem_idx)
                st.session_state.elemento_selecionado = None
                st.rerun()
        else:
            st.warning("Elemento não encontrado")
            st.session_state.elemento_selecionado = None
    else:
        st.info("👆 Selecione um elemento acima para editar")
    
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
    
    # Importar
    with st.expander("📥 Importar Projeto"):
        arquivo_upload = st.file_uploader("Escolha um arquivo JSON", type=["json"], key="uploader")
        if arquivo_upload is not None:
            json_str = arquivo_upload.read().decode()
            if st.button("Carregar Projeto", key="btn_carregar"):
                if importar_de_json(json_str):
                    st.success("✅ Projeto carregado!")
                    st.rerun()

# ============================================================================
# ÁREA PRINCIPAL - VISUALIZAÇÃO E PAINEL DE DADOS
# ============================================================================

col_desenho, col_dados = st.columns([3, 1])

# ============================================================================
# VISUALIZAÇÃO DA PLANTA
# ============================================================================

with col_desenho:
    st.subheader("🗺️ Visualização da Planta")
    
    if st.session_state.layout:
        fig = gerar_visualizacao_planta()
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("👈 Adicione elementos usando a sidebar")
        # Mostrar terreno vazio
        fig = gerar_visualizacao_planta()
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# PAINEL DE DADOS
# ============================================================================

with col_dados:
    st.subheader("📋 Dados do Projeto")
    
    # Informações do responsável
    with st.expander("👤 Informações", expanded=True):
        st.session_state.responsavel = st.text_input("Responsável", value=st.session_state.responsavel, key="resp")
        st.session_state.notas = st.text_area("Notas", value=st.session_state.notas, height=80, key="notas")
    
    # Tabela de elementos
    with st.expander("📊 Elementos", expanded=True):
        if st.session_state.layout:
            dados_tabela = []
            for elem in st.session_state.layout:
                dados_tabela.append({
                    "Elemento": elem.get('rotulo', elem['tipo']),
                    "Tipo": elem['tipo'].title(),
                    "L×A": f"{elem['w']}×{elem['h']}",
                    "Área": f"{calcular_area(elem):.1f}m²"
                })
            df = pd.DataFrame(dados_tabela)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Sem elementos")
    
    # Totalizadores
    with st.expander("📐 Totais", expanded=True):
        area_total_construida = sum(calcular_area(e) for e in st.session_state.layout if e['tipo'] == 'construcao')
        percentual_ocupado = (area_total_construida / area_terreno * 100) if area_terreno > 0 else 0
        
        st.metric("Terreno", f"{area_terreno:.0f} m²")
        st.metric("Construída", f"{area_total_construida:.1f} m²")
        st.metric("% Ocupado", f"{percentual_ocupado:.1f}%")
        
        if percentual_ocupado > 100:
            st.error("⚠️ Excede terreno!")
    
    # Validações
    with st.expander("✅ Validações"):
        avisos = validar_layout(st.session_state.layout, st.session_state.largura_terreno, st.session_state.altura_terreno)
        if avisos:
            for aviso in avisos:
                st.warning(aviso)
        else:
            st.success("✅ Tudo OK!")

# ============================================================================
# RODAPÉ
# ============================================================================

st.markdown("---")
st.caption("🏗️ AutoPlanta CETESB Pro | Editor de Plantas Baixas | v2.1")
