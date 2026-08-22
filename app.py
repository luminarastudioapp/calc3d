import pandas as pd
from datetime import datetime
import streamlit as st
import base64
import json
import time
from supabase import create_client, Client

# A configuração da página DEVE ser a primeira coisa aqui no topo!
st.set_page_config(page_title="3D Calc Pro", page_icon="🎲", layout="wide")

# --- 🔒 BARREIRA DE SEGURANÇA (LOGIN) ---
def check_password():
    """Retorna True se o usuário tiver as credenciais corretas."""
    def password_entered():
        # Verifica se o usuário existe nos Secrets e se a senha bate
        if st.session_state["username"] in st.secrets["passwords"] and st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Apaga a senha da memória por segurança
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        # TELA DE LOGIN VISUAL (Removido o set_page_config duplicado daqui)
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style='background-color: #1e1e1e; padding: 30px; border-radius: 10px; border: 1px solid #333;'>
            """, unsafe_allow_html=True)
            
            with st.form("login_form"):
                st.text_input("E-mail de Acesso", key="username", placeholder="exemplo@email.com")
                st.text_input("Senha", type="password", key="password", placeholder="••••••••")
                st.form_submit_button("Entrar no Sistema", on_click=password_entered, use_container_width=True)
            
            if st.session_state.get("password_correct") == False:
                st.error("🚨 Acesso negado. Credenciais inválidas.")
                
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br><p style='text-align: center; font-size: 13px; color: gray;'>Solicitação de acesso à administração:<br><b>veronica.campos.pt@gmail.com</b></p>", unsafe_allow_html=True)
            
        return False
    return True

# Se a pessoa não logar, o sistema para de rodar exatamente aqui.
if not check_password():
    st.stop()

# --- 1. CONFIGURAÇÃO DO SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Função auxiliar blindada contra erros de API
def get_df(table_name):
    try:
        response = supabase.table(table_name).select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"🚨 Erro de comunicação com a tabela '{table_name}'. Verifique o banco de dados.")
        st.caption(f"Detalhe técnico: {e}")
        return pd.DataFrame() # Retorna vazio para o sistema não quebrar a tela

def converter_imagem(upload):
    if upload is not None:
        return base64.b64encode(upload.read()).decode()
    return None

# Inicializando variáveis de sessão (Memória do App)
if "lista_extras" not in st.session_state:
    st.session_state.lista_extras = []
if "markup" not in st.session_state:
    st.session_state.markup = 100
if "proj_base" not in st.session_state:
    st.session_state.proj_base = {}

def set_markup(val):
    st.session_state.markup = val

def carregar_projeto(df, nome_projeto):
    if nome_projeto != "-- Criar Novo Projeto do Zero --":
        row = df[df['nome_projeto'] == nome_projeto].iloc[0]
        st.session_state.proj_base = row.to_dict()
        try:
            st.session_state.lista_extras = json.loads(row['custos_extras'])
        except:
            st.session_state.lista_extras = []
    else:
        st.session_state.proj_base = {}
        st.session_state.lista_extras = []

# --- 2. ESTILOS VISUAIS E IMPRESSÃO ---
st.set_page_config(page_title="3D Calc Pro", page_icon="🎲", layout="wide")

st.markdown("""
    <style>
    @media print {
        @page { size: landscape; margin: 15mm; }
        section[data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .stButton, .stDownloadButton, .stFileUploader, .stSelectbox, .stRadio, .stSlider { display: none !important; }
        footer { display: none !important; }
        .print-container { width: 100%; border: 1px solid #ccc; padding: 20px; border-radius: 8px; page-break-inside: avoid; margin-bottom: 20px; }
        .print-header { font-size: 24px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 15px; }
        body { background-color: white !important; color: black !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. NAVEGAÇÃO DOS MÓDULOS ---
st.sidebar.title("🎲 3D Calc Pro")

# Criando a inteligência que permite mudar o menu via código
if "menu_selecionado" not in st.session_state:
    st.session_state.menu_selecionado = "⚙️ Módulo 1: CADASTROS"

menu = st.sidebar.radio(
    "Módulos do Sistema", 
    [
        "⚙️ Módulo 1: CADASTROS", 
        "🚀 Módulo 2: NOVO PROJETO", 
        "📜 Módulo 3: RELATÓRIO",
        "💰 Módulo 4: VENDAS",
        "💾 Módulo 5: BACKUP"
    ],
    key="menu_selecionado" # Essa é a chave que vamos hackear para pular de tela
)

# =====================================================================
# MÓDULO 1: CADASTROS 
# =====================================================================
if menu == "⚙️ Módulo 1: CADASTROS":
    st.title("⚙️ Cadastros e Custos da Gráfica")
    tab_cfg, tab_cat, tab_fil, tab_out, tab_imp, tab_pecas, tab_est = st.tabs(["💵 Custos Fixos", "🏷️ Categorias", "🧵 Filamentos", "📦 Outros", "🖨️ Impressoras", "🧩 Catálogo de Peças", "📦 Estoque"])
    
    # --- CONFIGURAÇÕES GERAIS ---
    with tab_cfg:
        cfg_df = get_df('configuracoes')
        if not cfg_df.empty:
            kwh_atual = float(cfg_df.iloc[0]['kwh'])
            mao_obra_atual = float(cfg_df.iloc[0]['mao_obra'])
            
            st.markdown("### Parâmetros Base da Sua Produção")
            with st.form("form_cfg"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    novo_kwh = st.number_input("Custo do kWh (R$)", value=kwh_atual, step=0.05)
                with col_c2:
                    nova_mao_obra = st.number_input("Seu Valor Hora - Mão de Obra (R$/h)", value=mao_obra_atual, step=5.0)
                if st.form_submit_button("Atualizar Custos Fixos"):
                    supabase.table('configuracoes').update({'kwh': novo_kwh, 'mao_obra': nova_mao_obra}).eq('id', 1).execute()
                    st.success("✅ Custos base atualizados!")
                    time.sleep(1)
                    st.rerun()

    # --- CRUD: CATEGORIAS ---
    with tab_cat:
        cat_df = get_df('categorias')
        if not cat_df.empty:
            display_cat = cat_df.copy()
            display_cat.rename(columns={'nome': 'Nome da Categoria', 'tipo_categoria': 'Tipo', 'descricao': 'Descrição'}, inplace=True)
            st.dataframe(display_cat[['id', 'Nome da Categoria', 'Tipo', 'Descrição']], use_container_width=True, hide_index=True)

        acao_cat = st.radio("Ação Categoria", ["Nova", "Editar / Excluir"], horizontal=True, label_visibility="collapsed")
        
        if acao_cat == "Nova":
            with st.form("form_cat", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1: nome_cat = st.text_input("Nome da Categoria")
                with col2: tipo_cat = st.selectbox("Aplica-se à:", ["Insumo", "Peça"])
                desc_cat = st.text_area("Descrição (Opcional)", placeholder="O que entra nesta categoria?")
                
                if st.form_submit_button("Salvar Categoria") and nome_cat:
                    try:
                        supabase.table('categorias').insert({'nome': nome_cat, 'tipo_categoria': tipo_cat, 'descricao': desc_cat}).execute()
                        st.success("✅ Categoria adicionada com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception:
                        st.error("Esta categoria já existe ou ocorreu um erro!")
        else:
            if not cat_df.empty:
                cat_ed = st.selectbox("Selecione a Categoria", cat_df['nome'].tolist())
                row_cat = cat_df[cat_df['nome'] == cat_ed].iloc[0]
                cat_id = int(row_cat['id'])
                
                col1, col2 = st.columns(2)
                with col1: novo_nome = st.text_input("Nome", value=row_cat['nome'])
                with col2: novo_tipo = st.selectbox("Tipo", ["Insumo", "Peça"], index=["Insumo", "Peça"].index(row_cat['tipo_categoria']))
                nova_desc = st.text_area("Descrição", value=row_cat['descricao'] if pd.notna(row_cat['descricao']) else "")
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("🔄 Atualizar Categoria", use_container_width=True):
                    supabase.table('categorias').update({'nome': novo_nome, 'tipo_categoria': novo_tipo, 'descricao': nova_desc}).eq('id', cat_id).execute()
                    st.success("✅ Categoria atualizada!")
                    time.sleep(1)
                    st.rerun()
                if col_btn2.button("🗑️ Excluir Categoria", use_container_width=True):
                    supabase.table('categorias').delete().eq('id', cat_id).execute()
                    st.success("✅ Categoria excluída!")
                    time.sleep(1)
                    st.rerun()

    # --- CRUD: FILAMENTOS ---
    # --- CRUD: FILAMENTOS ---
    with tab_fil:
        filamentos_df = get_df('filamentos')
        if not filamentos_df.empty:
            display_fil = filamentos_df.copy()
            # Garante a estabilidade da tabela caso as colunas estejam vazias
            if 'marca' not in display_fil.columns: display_fil['marca'] = 'S/N'
            if 'cor' not in display_fil.columns: display_fil['cor'] = 'S/N'
            
            display_fil.rename(columns={'marca': 'Marca', 'nome': 'Tipo', 'cor': 'Cor', 'preco_kg': 'Preço/KG (R$)'}, inplace=True)
            st.dataframe(display_fil[['id', 'Marca', 'Tipo', 'Cor', 'Preço/KG (R$)']], use_container_width=True, hide_index=True)

        acao_fil = st.radio("Ação Filamento", ["Novo", "Editar / Excluir"], horizontal=True, label_visibility="collapsed", key="rad_fil")
        
        if acao_fil == "Novo":
            with st.form("form_fil", clear_on_submit=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1: marca_fil = st.text_input("Marca / Fornecedor (Ex: Voolt3D)")
                with col_f2: nome_fil = st.text_input("Tipo (Ex: PLA, PETG)")
                with col_f3: cor_fil = st.text_input("Cor (Ex: Preto Silk)")
                
                preco_fil = st.number_input("Custo Unitário (R$/KG)", min_value=0.0, value=99.0)
                if st.form_submit_button("Salvar Filamento") and nome_fil:
                    supabase.table('filamentos').insert({'marca': marca_fil, 'nome': nome_fil, 'cor': cor_fil, 'preco_kg': preco_fil}).execute()
                    st.success("✅ Filamento cadastrado!")
                    time.sleep(1)
                    st.rerun()
        else:
            if not filamentos_df.empty:
                # Cria a lista compilada para a edição
                filamentos_df['display'] = filamentos_df.apply(lambda x: f"{x.get('marca', 'S/N')} - {x['nome']} - {x.get('cor', 'S/N')}", axis=1)
                fil_ed = st.selectbox("Selecione o Filamento", filamentos_df['display'].tolist())
                row_fil = filamentos_df[filamentos_df['display'] == fil_ed].iloc[0]
                fil_id = int(row_fil['id'])
                
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1: novo_marca_fil = st.text_input("Marca / Fornecedor", value=row_fil.get('marca', ''))
                with col_f2: novo_nome_fil = st.text_input("Tipo", value=row_fil['nome'])
                with col_f3: novo_cor_fil = st.text_input("Cor", value=row_fil.get('cor', ''))
                
                novo_preco_fil = st.number_input("Custo Unitário (R$/KG)", min_value=0.0, value=float(row_fil['preco_kg']))
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("🔄 Atualizar Filamento", use_container_width=True):
                    supabase.table('filamentos').update({'marca': novo_marca_fil, 'nome': novo_nome_fil, 'cor': novo_cor_fil, 'preco_kg': novo_preco_fil}).eq('id', fil_id).execute()
                    st.success("✅ Atualizado!")
                    time.sleep(1)
                    st.rerun()
                if col_btn2.button("🗑️ Excluir Filamento", use_container_width=True):
                    supabase.table('filamentos').delete().eq('id', fil_id).execute()
                    st.success("✅ Excluído!")
                    time.sleep(1)
                    st.rerun()

    # --- CRUD: OUTROS ---
    with tab_out:
        outros_df = get_df('outros')
        if not outros_df.empty:
            display_out = outros_df.copy()
            display_out.rename(columns={'categoria': 'Categoria', 'nome': 'Nome', 'marca': 'Marca/Modelo', 'valor_unit': 'Valor Unitário (R$)', 'especificacoes': 'Especificações'}, inplace=True)
            st.dataframe(display_out[['id', 'Categoria', 'Nome', 'Marca/Modelo', 'Valor Unitário (R$)', 'Especificações']], use_container_width=True, hide_index=True)

        cat_df_seguro = get_df('categorias')
        if not cat_df_seguro.empty:
            categorias_insumo = cat_df_seguro[cat_df_seguro['tipo_categoria'] == 'Insumo']['nome'].tolist()
            if not categorias_insumo: 
                categorias_insumo = ["Cadastre uma categoria primeiro"]
        else:
            categorias_insumo = ["Cadastre uma categoria primeiro"]

        acao_out = st.radio("Ação Outros", ["Novo", "Editar / Excluir"], horizontal=True, label_visibility="collapsed", key="rad_out")

        if acao_out == "Novo":
            with st.form("form_outros", clear_on_submit=True):
                col_o1, col_o2 = st.columns(2)
                with col_o1:
                    cat_outro = st.selectbox("Categoria", categorias_insumo)
                    nome_outro = st.text_input("Nome do Material (Ex: Ímã Neodímio)")
                    marca_outro = st.text_input("Marca | Modelo")
                with col_o2:
                    valor_outro = st.number_input("Valor Unitário (R$)", min_value=0.0, value=1.50)
                    espec_outro = st.text_area("Especificações")
                if st.form_submit_button("Salvar Material Extra") and nome_outro:
                    supabase.table('outros').insert({'categoria': cat_outro, 'nome': nome_outro, 'marca': marca_outro, 'valor_unit': valor_outro, 'especificacoes': espec_outro}).execute()
                    st.success("✅ Insumo cadastrado!")
                    time.sleep(1)
                    st.rerun()
        else:
            if not outros_df.empty:
                out_ed = st.selectbox("Selecione o Insumo", outros_df['nome'].tolist())
                row_out = outros_df[outros_df['nome'] == out_ed].iloc[0]
                out_id = int(row_out['id'])
                
                idx_cat = categorias_insumo.index(row_out['categoria']) if row_out['categoria'] in categorias_insumo else 0
                
                col_o1, col_o2 = st.columns(2)
                with col_o1:
                    n_cat = st.selectbox("Categoria", categorias_insumo, index=idx_cat)
                    n_nome = st.text_input("Nome", value=row_out['nome'])
                    n_marca = st.text_input("Marca | Modelo", value=row_out['marca'])
                with col_o2:
                    n_valor = st.number_input("Valor Unitário (R$)", min_value=0.0, value=float(row_out['valor_unit']))
                    n_espec = st.text_area("Especificações", value=row_out['especificacoes'])
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("🔄 Atualizar Insumo", use_container_width=True):
                    supabase.table('outros').update({'categoria': n_cat, 'nome': n_nome, 'marca': n_marca, 'valor_unit': n_valor, 'especificacoes': n_espec}).eq('id', out_id).execute()
                    st.success("✅ Atualizado!")
                    time.sleep(1)
                    st.rerun()
                if col_btn2.button("🗑️ Excluir Insumo", use_container_width=True):
                    supabase.table('outros').delete().eq('id', out_id).execute()
                    st.success("✅ Excluído!")
                    time.sleep(1)
                    st.rerun()

    # --- CRUD: IMPRESSORAS ---
    with tab_imp:
        imp_df = get_df('impressoras')
        if not imp_df.empty:
            imp_df['Consumo (kW)'] = imp_df['watts'] / 1000
            display_imp = imp_df.copy()
            display_imp.rename(columns={'nome': 'Modelo', 'preco_maquina': 'Valor (R$)', 'vida_util_h': 'Vida Útil (h)'}, inplace=True)
            st.dataframe(display_imp[['Modelo', 'Consumo (kW)', 'Valor (R$)', 'Vida Útil (h)']].style.format({
                "Consumo (kW)": "{:.2f} kW", "Valor (R$)": "R$ {:.2f}"
            }), use_container_width=True, hide_index=True)

        acao_imp = st.radio("Ação Impressora", ["Nova", "Editar / Excluir"], horizontal=True, label_visibility="collapsed", key="rad_imp")

        if acao_imp == "Nova":
            with st.form("form_imp", clear_on_submit=True):
                nome_imp = st.text_input("Marca | Modelo da Impressora")
                kw_imp = st.number_input("Consumo Máquina (kW) - Ex: 0.15", value=0.15, step=0.05)
                preco_imp = st.number_input("Valor da Impressora (R$)", value=5000.0)
                vida_imp = st.number_input("Vida Útil Estimada (Horas)", value=3000)
                if st.form_submit_button("Salvar Máquina") and nome_imp:
                    supabase.table('impressoras').insert({'nome': nome_imp, 'watts': kw_imp*1000, 'preco_maquina': preco_imp, 'vida_util_h': vida_imp}).execute()
                    st.success("✅ Impressora cadastrada!")
                    time.sleep(1)
                    st.rerun()
        else:
            if not imp_df.empty:
                imp_ed = st.selectbox("Selecione a Impressora", imp_df['nome'].tolist())
                row_imp = imp_df[imp_df['nome'] == imp_ed].iloc[0]
                imp_id = int(row_imp['id'])
                
                col1, col2 = st.columns(2)
                with col1:
                    n_nome_imp = st.text_input("Modelo", value=row_imp['nome'])
                    n_kw = st.number_input("Consumo (kW)", value=float(row_imp['watts'])/1000, step=0.05)
                with col2:
                    n_preco_imp = st.number_input("Valor (R$)", value=float(row_imp['preco_maquina']))
                    n_vida = st.number_input("Vida Útil (h)", value=float(row_imp['vida_util_h']))
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("🔄 Atualizar Impressora", use_container_width=True):
                    supabase.table('impressoras').update({'nome': n_nome_imp, 'watts': n_kw*1000, 'preco_maquina': n_preco_imp, 'vida_util_h': n_vida}).eq('id', imp_id).execute()
                    st.success("✅ Atualizado!")
                    time.sleep(1)
                    st.rerun()
                if col_btn2.button("🗑️ Excluir Impressora", use_container_width=True):
                    supabase.table('impressoras').delete().eq('id', imp_id).execute()
                    st.success("✅ Excluído!")
                    time.sleep(1)
                    st.rerun()

# --- CRUD: CATÁLOGO DE PEÇAS (VISUALIZAÇÃO E GESTÃO) ---
    with tab_pecas:
        pecas_df = get_df('historico')
        
        if not pecas_df.empty:
            # Preparando a tabela para uma visualização limpa e profissional
            display_pecas = pecas_df[['id', 'categoria_peca', 'nome_projeto', 'material', 'custo_total', 'preco_venda']].copy()
            display_pecas.rename(columns={
                'categoria_peca': 'Categoria', 
                'nome_projeto': 'Nome da Peça', 
                'material': 'Filamento', 
                'custo_total': 'Custo (R$)', 
                'preco_venda': 'Venda (R$)'
            }, inplace=True)
            
            st.dataframe(display_pecas.style.format({
                "Custo (R$)": "R$ {:.2f}", 
                "Venda (R$)": "R$ {:.2f}"
            }), use_container_width=True, hide_index=True)

            acao_peca = st.radio("Ação Peça", ["Excluir Peça", "Editar Peça"], horizontal=True, label_visibility="collapsed", key="rad_pecas")
            
            if acao_peca == "Excluir Peça":
                peca_del = st.selectbox("Selecione o projeto para remover do catálogo:", pecas_df['nome_projeto'].tolist())
                peca_id = int(pecas_df[pecas_df['nome_projeto'] == peca_del].iloc[0]['id'])
                
                if st.button("🗑️ Confirmar Exclusão", use_container_width=True):
                    supabase.table('historico').delete().eq('id', peca_id).execute()
                    st.success("✅ Peça excluída definitivamente do sistema!")
                    time.sleep(1)
                    st.rerun()
                    
            elif acao_peca == "Editar Peça":
                peca_edit = st.selectbox("Selecione o projeto para editar:", pecas_df['nome_projeto'].tolist(), key="sel_edit_peca")
                
                # Inteligência de Callback: executa nos bastidores antes da tela piscar
                def preparar_edicao():
                    carregar_projeto(pecas_df, peca_edit)
                    st.session_state.menu_selecionado = "🚀 Módulo 2: NOVO PROJETO"
                
                st.button("✏️ Enviar para Edição (Módulo 2)", type="primary", use_container_width=True, on_click=preparar_edicao)

# --- GESTÃO DE ESTOQUE (NOVO) ---
    # --- GESTÃO DE ESTOQUE ---
    # --- GESTÃO DE ESTOQUE ---
    with tab_est:
        st.subheader("📦 Visão Geral do Estoque")
        fil_df = get_df('filamentos')
        out_df = get_df('outros')
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.markdown("**🧵 Filamentos Disponíveis**")
            if not fil_df.empty:
                df_fil_vis = fil_df.copy()
                df_fil_vis['Filamento'] = df_fil_vis.apply(lambda x: f"{x.get('marca', '')} {x['nome']} {x.get('cor', '')}".strip(), axis=1)
                df_fil_vis.rename(columns={'peso_estoque_g': 'Estoque (g)'}, inplace=True)
                st.dataframe(df_fil_vis[['Filamento', 'Estoque (g)']], use_container_width=True, hide_index=True)
            else:
                st.info("Sem filamentos.")
                
        with col_v2:
            st.markdown("**📦 Insumos Extras**")
            if not out_df.empty:
                df_out_vis = out_df.copy()
                df_out_vis['Insumo'] = df_out_vis.apply(lambda x: f"{x.get('marca', '')} - {x['nome']}".strip(' -'), axis=1)
                df_out_vis.rename(columns={'qtd_estoque': 'Qtd (Un)'}, inplace=True)
                st.dataframe(df_out_vis[['Insumo', 'Qtd (Un)']], use_container_width=True, hide_index=True)
            else:
                st.info("Sem insumos.")
                
        st.divider()
        st.subheader("⚖️ Atualização Manual Inteligente")
        st.caption("Selecione o item na lista abaixo para habilitar o formulário de edição de estoque.")
        
        col_est1, col_est2 = st.columns(2, gap="large")
        
        with col_est1:
            st.markdown("**🧵 Ajuste de Filamentos**")
            if not fil_df.empty:
                # Cria a lista compilada e adiciona o texto indicativo no topo
                fil_df['display'] = fil_df.apply(lambda x: f"{x.get('marca', '')} {x['nome']} {x.get('cor', '')}".strip(), axis=1)
                opcoes_filamentos = ["-- Selecione o Filamento --"] + fil_df['display'].tolist()
                
                fil_edit_sel = st.selectbox("Ajuste de Filamentos", opcoes_filamentos, label_visibility="collapsed", key="sel_est_fil")
                
                # O formulário só aparece se for uma escolha válida (diferente da primeira opção)
                if fil_edit_sel != "-- Selecione o Filamento --":
                    row_fil = fil_df[fil_df['display'] == fil_edit_sel].iloc[0]
                    peso_atual = float(row_fil.get('peso_estoque_g', 0))
                    
                    ce1, ce2 = st.columns([3, 1])
                    with ce1: 
                        novo_peso = st.number_input("Estoque Físico (g)", value=peso_atual, step=50.0, key="inp_est_fil")
                    with ce2: 
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("💾 Salvar", key="btn_est_fil", use_container_width=True):
                            supabase.table('filamentos').update({'peso_estoque_g': novo_peso}).eq('id', int(row_fil['id'])).execute()
                            st.success("Atualizado!")
                            time.sleep(0.5)
                            st.rerun()
                            
        with col_est2:
            st.markdown("**📦 Ajuste de Insumos**")
            if not out_df.empty:
                # Cria a lista compilada e adiciona o texto indicativo no topo
                out_df['display'] = out_df.apply(lambda x: f"{x.get('marca', '')} - {x['nome']}".strip(' -'), axis=1)
                opcoes_insumos = ["-- Selecione o Insumo --"] + out_df['display'].tolist()
                
                out_edit_sel = st.selectbox("Ajuste de Insumos", opcoes_insumos, label_visibility="collapsed", key="sel_est_out")
                
                # O formulário só aparece se for uma escolha válida
                if out_edit_sel != "-- Selecione o Insumo --":
                    row_out = out_df[out_df['display'] == out_edit_sel].iloc[0]
                    qtd_atual = int(row_out.get('qtd_estoque', 0))
                    
                    ce1, ce2 = st.columns([3, 1])
                    with ce1: 
                        nova_qtd = st.number_input("Estoque Físico (Un)", value=qtd_atual, step=1, key="inp_est_out")
                    with ce2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("💾 Salvar", key="btn_est_out", use_container_width=True):
                            supabase.table('outros').update({'qtd_estoque': nova_qtd}).eq('id', int(row_out['id'])).execute()
                            st.success("Atualizado!")
                            time.sleep(0.5)
                            st.rerun()

# =====================================================================
# MÓDULO 2: NOVO PROJETO 
# =====================================================================
elif menu == "🚀 Módulo 2: NOVO PROJETO":
    st.title("🚀 Criação e Precificação de Projeto")
    
    filamentos_df = get_df('filamentos')
    impressoras_df = get_df('impressoras')
    
    cat_pecas_resp = supabase.table('categorias').select('nome').eq('tipo_categoria', 'Peça').execute()
    categorias_peca_df = pd.DataFrame(cat_pecas_resp.data)
    
    outros_df = get_df('outros')
    cfg_df = get_df('configuracoes')
    projetos_salvos = get_df('historico') # Puxando o histórico para servir de catálogo
    
    kwh_cost = float(cfg_df.iloc[0]['kwh']) if not cfg_df.empty else 0.95
    mao_obra_rate = float(cfg_df.iloc[0]['mao_obra']) if not cfg_df.empty else 35.0
    
    # --- NOVO: CATÁLOGO DE PROJETOS SALVOS NO TOPO ---
    st.markdown("### 🔍 Catálogo de Projetos (Templates)")
    if not projetos_salvos.empty:
        col_p1, col_p2 = st.columns([4, 1])
        with col_p1:
            lista_projs = ["-- Criar Novo Projeto do Zero --"] + projetos_salvos['nome_projeto'].tolist()
            proj_selecionado = st.selectbox("Selecione um projeto para carregar os dados base:", lista_projs, label_visibility="collapsed")
        with col_p2:
            if st.button("📥 Carregar Dados", use_container_width=True):
                carregar_projeto(projetos_salvos, proj_selecionado)
                st.rerun()
    else:
        st.info("Nenhum projeto salvo no histórico ainda. Crie o seu primeiro abaixo!")
        
    st.divider()
    
    # Atalho para os dados carregados na memória
    pb = st.session_state.proj_base
    
    col1, col2 = st.columns([1.2, 1], gap="large")

    with col1:
        st.subheader("📋 Identidade da Peça")
        
        opcoes_cat_peca = categorias_peca_df['nome'].tolist() if not categorias_peca_df.empty else ["Nenhuma categoria cadastrada"]
        idx_cat_peca = opcoes_cat_peca.index(pb.get('categoria_peca')) if pb.get('categoria_peca') in opcoes_cat_peca else 0
        cat_peca_selecionada = st.selectbox("Categoria da Peça", opcoes_cat_peca, index=idx_cat_peca)
        
        proj_name = st.text_input("Nome da Peça", value=pb.get('nome_projeto', ''), placeholder="Ex: Vaso Geométrico")
        
        foto_upload = st.file_uploader("📸 Anexar Nova Foto (Opcional)", type=["png", "jpg", "jpeg"])
        foto_b64 = converter_imagem(foto_upload)
        
        origem_idx = ["Autoral", "Fornecedor"].index(pb.get('origem', 'Autoral')) if pb.get('origem', 'Autoral') in ["Autoral", "Fornecedor"] else 0
        origem = st.radio("Origem do Design", ["Autoral", "Fornecedor"], index=origem_idx, horizontal=True)
        
        link_projeto = pb.get('link_projeto', '')
        arquivo_pago = pb.get('arquivo_pago', 'Não')
        preco_arquivo = float(pb.get('preco_arquivo', 0.0))
        
        if origem == "Fornecedor":
            link_projeto = st.text_input("🔗 Link do Projeto (Onde baixou/comprou)", value=link_projeto)
            arq_pago_idx = ["Não", "Sim"].index(arquivo_pago) if arquivo_pago in ["Não", "Sim"] else 0
            arquivo_pago = st.radio("O arquivo (STL/3MF) é pago?", ["Não", "Sim"], index=arq_pago_idx, horizontal=True)
            if arquivo_pago == "Sim":
                preco_arquivo = st.number_input("Preço do Arquivo (R$)", value=preco_arquivo, min_value=0.0, step=5.0)

        st.divider()
        st.subheader("⚙️ Parâmetros de Fabricação")
        
        descricao = st.text_area("Descrição / Observações", value=pb.get('descricao', ''), placeholder="Ex: Preenchimento giroide 15%.")
        
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1: cores = st.number_input("Qtd. de Cores", min_value=1, value=int(pb.get('cores', 1)), step=1)
        with col_c2:
            st.caption("Dimensões Finais (cm)")
            d1, d2, d3 = st.columns(3)
            with d1: dim_l = st.number_input("Largura", value=float(pb.get('dim_largura', 0.0)), min_value=0.0)
            with d2: dim_p = st.number_input("Profund.", value=float(pb.get('dim_profundidade', 0.0)), min_value=0.0)
            with d3: dim_a = st.number_input("Altura", value=float(pb.get('dim_altura', 0.0)), min_value=0.0)
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            printer_selected = st.selectbox("Impressora", impressoras_df['nome'].tolist() if not impressoras_df.empty else ["Nenhuma"])
            printer_info = impressoras_df[impressoras_df['nome'] == printer_selected].iloc[0] if not impressoras_df.empty else None
        with col_m2:
            printer_selected = st.selectbox("Impressora", impressoras_df['nome'].tolist() if not impressoras_df.empty else ["Nenhuma"])
            printer_info = impressoras_df[impressoras_df['nome'] == printer_selected].iloc[0] if not impressoras_df.empty else None
            
            # Nova lógica da lista compilada para Filamentos
            if not filamentos_df.empty:
                filamentos_df['display'] = filamentos_df.apply(lambda x: f"{x.get('marca', 'S/N')} - {x['nome']} - {x.get('cor', 'S/N')}", axis=1)
                fil_list = filamentos_df['display'].tolist()
            else:
                fil_list = ["Nenhum"]
                
            idx_fil = fil_list.index(pb.get('material')) if pb.get('material') in fil_list else 0
            fil_selected = st.selectbox("Filamento", fil_list, index=idx_fil)
            
            if not filamentos_df.empty:
                fil_info = filamentos_df[filamentos_df['display'] == fil_selected].iloc[0]
                mat_cost_per_kg = float(fil_info['preco_kg'])
            else:
                fil_info = None
                mat_cost_per_kg = 0.0

        # Lógica para separar horas e minutos salvos no banco
        total_h_banco = float(pb.get('tempo_h', 0.0))
        horas_calc = int(total_h_banco)
        minutos_calc = int(round((total_h_banco - horas_calc) * 60))
        
        col_w, col_t1, col_t2 = st.columns([1, 1, 1])
        with col_w: weight_g = st.number_input("Peso total (g)", value=float(pb.get('peso_g', 0.0)), min_value=0.0)
        with col_t1: hours = st.number_input("Tempo (h)", value=horas_calc, min_value=0)
        with col_t2: mins = st.number_input("Tempo (min)", value=minutos_calc, min_value=0, max_value=59)

        # Calculando mão de obra baseada no custo salvo vs taxa atual
        mo_salva_reais = float(pb.get('custo_mao_obra', 0.0))
        minutos_mo_calc = int((mo_salva_reais / mao_obra_rate) * 60) if mao_obra_rate > 0 else 15
        tempo_mao_obra_min = st.number_input("Sua Mão de Obra Dedicada (Minutos)", value=minutos_mo_calc if mo_salva_reais > 0 else 15, min_value=0, step=5)

        st.divider()
        st.subheader("📦 Custos Extras")
        st.caption("Adicione itens de montagem, imãs, elásticos ou embalagens à vontade.")
        
        if not outros_df.empty:
            outros_dict = {f"{row['nome']} ({row['marca']}) - R$ {row['valor_unit']:.2f}": row.to_dict() for _, row in outros_df.iterrows()}
            col_e1, col_e2, col_e3 = st.columns([5, 2, 2])
            with col_e1: 
                item_extra = st.selectbox("Selecione o Insumo", list(outros_dict.keys()), label_visibility="collapsed")
            with col_e2: 
                qtd_extra = st.number_input("Qtd", min_value=1, value=1, label_visibility="collapsed")
            with col_e3:
                if st.button("➕ Adicionar"):
                    item_dados = outros_dict[item_extra]
                    st.session_state.lista_extras.append({
                        "nome": item_dados['nome'],
                        "qtd": qtd_extra,
                        "valor_unit": item_dados['valor_unit'],
                        "subtotal": item_dados['valor_unit'] * qtd_extra
                    })
                    st.rerun()
            
            custo_extras_total = 0.0
            if st.session_state.lista_extras:
                st.markdown("**Itens Adicionados:**")
                for i, ex in enumerate(st.session_state.lista_extras):
                    col_l1, col_l2 = st.columns([8, 2])
                    col_l1.markdown(f"- **{ex['qtd']}x** {ex['nome']} (R$ {ex['subtotal']:.2f})")
                    if col_l2.button("❌", key=f"del_ex_{i}"):
                        st.session_state.lista_extras.pop(i)
                        st.rerun()
                    custo_extras_total += ex['subtotal']
        else:
            st.info("Cadastre insumos na aba 'Outros' do Módulo 1 para usá-los aqui.")
            custo_extras_total = 0.0

    # CÁLCULOS BASE
    total_hours = hours + (mins / 60)
    cost_mat = (weight_g / 1000) * mat_cost_per_kg
    cost_energy = (printer_info['watts'] / 1000) * total_hours * kwh_cost if printer_info is not None else 0
    cost_depr = (printer_info['preco_maquina'] / max(1, printer_info['vida_util_h'])) * total_hours if printer_info is not None else 0
    cost_mao_obra = (tempo_mao_obra_min / 60) * mao_obra_rate
    
    total_cost_prod = cost_mat + cost_energy + cost_depr + cost_mao_obra + custo_extras_total
    
    with col2:
        st.markdown("### 📈 Lucro Desejado")
        st.markdown("""
        <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0;'>
        """, unsafe_allow_html=True)
        
        st.session_state.markup = st.slider("Markup (%)", 0, 500, st.session_state.markup, key="markup_slider")
        
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
        btn_col1.button("50%", on_click=set_markup, args=(50,), use_container_width=True)
        btn_col2.button("100%", on_click=set_markup, args=(100,), use_container_width=True)
        btn_col3.button("150%", on_click=set_markup, args=(150,), use_container_width=True)
        btn_col4.button("200%", on_click=set_markup, args=(200,), use_container_width=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        preco_venda_final = total_cost_prod * (1 + (st.session_state.markup / 100))
        lucro_liquido = preco_venda_final - total_cost_prod

        st.divider()
        st.subheader("📊 Resumo e Precificação")
        
        if proj_name and weight_g > 0 and (total_hours > 0 or tempo_mao_obra_min > 0):
            st.metric(label="🛍️ PREÇO DE VENDA SUGERIDO", value=f"R$ {preco_venda_final:.2f}", delta=f"Lucro Limpo: R$ {lucro_liquido:.2f}")
            
            df_detalhes = pd.DataFrame({
                "Componente de Custo": ["Filamento", "Energia", "Depreciação Máquina", "Sua Mão de Obra", "Custos Extras (Insumos)"], 
                "Valor (R$)": [cost_mat, cost_energy, cost_depr, cost_mao_obra, custo_extras_total]
            })
            st.dataframe(df_detalhes.style.format({"Valor (R$)": "R$ {:.2f}"}), use_container_width=True, hide_index=True)

            memoria_calc_str = f"Mat: R${cost_mat:.2f} | Energ: R${cost_energy:.2f} | Deprec: R${cost_depr:.2f} | MO: R${cost_mao_obra:.2f} | Extras: R${custo_extras_total:.2f} | Markup: {st.session_state.markup}%"

            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- NOVA INTELIGÊNCIA: ATUALIZAR VS DUPLICAR ---
            id_projeto_atual = pb.get('id')
            
            if id_projeto_atual:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    btn_atualizar = st.button("🔄 Atualizar Peça Existente", type="primary", use_container_width=True)
                with col_b2:
                    btn_novo = st.button("📄 Salvar como Nova Peça (Cópia)", use_container_width=True)
            else:
                btn_atualizar = False
                btn_novo = st.button("💾 Salvar Precificação Completa", type="primary", use_container_width=True)

            if btn_atualizar or btn_novo:
                data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
                foto_final = foto_b64 if foto_b64 else pb.get('foto_principal')
                
                dados_salvar = {
                    'nome_projeto': proj_name, 'material': fil_selected, 'peso_g': weight_g, 
                    'tempo_h': total_hours, 'custo_total': total_cost_prod, 'preco_venda': preco_venda_final, 
                    'data': data_hoje, 'memoria_calculo': memoria_calc_str, 'foto_principal': foto_final, 
                    'origem': origem, 'link_projeto': link_projeto, 'custo_mao_obra': cost_mao_obra,
                    'arquivo_pago': arquivo_pago, 'preco_arquivo': preco_arquivo, 'descricao': descricao, 
                    'cores': cores, 'dim_largura': dim_l, 'dim_profundidade': dim_p, 'dim_altura': dim_a,
                    'categoria_peca': cat_peca_selecionada, 'custos_extras': json.dumps(st.session_state.lista_extras), 
                    'markup_aplicado': st.session_state.markup
                }
                
                if btn_atualizar:
                    supabase.table('historico').update(dados_salvar).eq('id', id_projeto_atual).execute()
                    st.success("✅ Peça atualizada com sucesso no catálogo!")
                else:
                    supabase.table('historico').insert(dados_salvar).execute()
                    st.success("✅ Novo projeto salvo com sucesso!")
                
                # Limpa a memória para o próximo projeto
                st.session_state.lista_extras = [] 
                st.session_state.proj_base = {}
                time.sleep(1.5)
                st.rerun()
        else:
            st.info("👈 Preencha os parâmetros e adicione o peso da peça para gerar o cálculo.")


# =====================================================================
# MÓDULO 3: RELATÓRIO 
# =====================================================================
elif menu == "📜 Módulo 3: RELATÓRIO":
    st.title("📜 Vitrine de Produção e Venda")
    
    st.markdown("""
        <button onclick="window.print()" style="background-color: #000; color: white; padding: 10px 24px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; margin-bottom: 20px;">
            🖨️ IMPRIMIR FICHA TÉCNICA (LANDSCAPE)
        </button>
    """, unsafe_allow_html=True)
    
    resp_hist = supabase.table('historico').select('*').order('id', desc=True).execute()
    df_hist = pd.DataFrame(resp_hist.data)

    if not df_hist.empty:
        for idx, row in df_hist.iterrows():
            st.markdown(f"""
            <div class="print-container">
                <div class="print-header">[{row.get('categoria_peca', 'S/Categoria')}] {row['nome_projeto']} <span style="float:right; font-size:16px; color:gray;">Data: {row['data']}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 1.5, 1.5])
            
            with c1:
                foto = row.get('foto_principal')
                if pd.notna(foto) and isinstance(foto, str) and foto.strip() != "" and foto.strip() != "None":
                    try:
                        st.image(base64.b64decode(foto), use_column_width=True)
                    except Exception:
                        st.warning("⚠️ Imagem corrompida.")
                else:
                    st.info("Nenhuma foto atrelada.")
            
            with c2:
                origem_lbl = row.get('origem', 'Não Informado')
                link_lbl = row.get('link_projeto', '')
                st.markdown(f"**Origem:** {origem_lbl}")
                if origem_lbl == "Fornecedor":
                    if row.get('arquivo_pago', 'Não') == "Sim":
                        st.caption(f"💳 Arquivo Comprado: R$ {row.get('preco_arquivo', 0.0):.2f}")
                    if pd.notna(link_lbl) and link_lbl:
                        st.markdown(f"🔗 [Link do Projeto]({link_lbl})")
                
                st.markdown(f"**Filamento:** {row['material']} | **Cores:** {row.get('cores', 1)}")
                st.markdown(f"**Peso:** {row['peso_g']} g | **Tempo:** {row['tempo_h']:.2f} h")
                st.markdown(f"**Dimensões:** {row.get('dim_largura', 0)} L x {row.get('dim_profundidade', 0)} P x {row.get('dim_altura', 0)} A (cm)")
                
                extras_json = row.get('custos_extras', '[]')
                if pd.notna(extras_json) and extras_json != '[]':
                    try:
                        lista_ex = json.loads(extras_json)
                        if lista_ex:
                            st.markdown("**📦 Insumos Extras:**")
                            for ex in lista_ex:
                                st.caption(f"- {ex['qtd']}x {ex['nome']}")
                    except: pass

            with c3:
                st.markdown(f"**Custo Total de Produção:** R$ {row['custo_total']:.2f}")
                st.markdown(f"**Markup Aplicado:** {row.get('markup_aplicado', 0):.0f}%")
                st.markdown(f"**PREÇO DE VENDA:** <span style='font-size:22px; color:#2e7d32; font-weight:bold;'>R$ {row['preco_venda']:.2f}</span>", unsafe_allow_html=True)
                
                memoria = row.get('memoria_calculo')
                if pd.notna(memoria) and memoria:
                    st.caption(memoria.replace(" | ", "<br>"))
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Excluir Ficha", key=f"del_proj_{row['id']}", use_container_width=True):
                    supabase.table('historico').delete().eq('id', row['id']).execute()
                    st.success("Ficha removida com sucesso!")
                    time.sleep(1)
                    st.rerun()
            
            st.divider()
    else:
        st.info("Nenhuma ficha de produção e venda salva.")

# =====================================================================
# MÓDULO 4: VENDAS E MARKETPLACES
# =====================================================================
elif menu == "💰 Módulo 4: VENDAS":
    st.title("💰 Gestão de Vendas e Marketplaces")
    st.markdown("Controle de pedidos, simulação de taxas de plataformas e funil de status.")

    tab_nova_venda, tab_painel = st.tabs(["🛒 Lançar Nova Venda", "📊 Painel de Pedidos"])

    with tab_nova_venda:
        projetos_df = get_df('historico')

        if not projetos_df.empty:
            col_v1, col_v2 = st.columns([1, 1.5])

            with col_v1:
                st.subheader("1. Dados do Cliente e Canal")
                nome_cliente = st.text_input("Nome do Cliente / Comprador")
                canal_venda = st.radio("Canal de Venda", ["Venda Direta (WhatsApp/Balcão)", "Shopee", "Mercado Livre"])
                status_pedido = st.selectbox("Status Atual", ["Aguardando Pagamento", "Em Produção", "Pronto / Enviado", "Concluído"])

            with col_v2:
                st.subheader("2. Produto e Precificação Dinâmica")
                proj_selecionado = st.selectbox("Selecione a Peça", projetos_df['nome_projeto'].tolist())
                peca_dados = projetos_df[projetos_df['nome_projeto'] == proj_selecionado].iloc[0]
                
                custo_fabrica = float(peca_dados['custo_total'])
                preco_sugerido_original = float(peca_dados['preco_venda'])

                st.markdown(f"**Custo de Produção (Fábrica):** R$ {custo_fabrica:.2f}")

                # Dinâmica de Taxas
                taxa_percentual = 0.0
                taxa_fixa = 0.0

                if canal_venda == "Shopee":
                    st.caption("Ajuste as taxas conforme o seu programa (Ex: 14% ou 20% + R$ 3,00 ou R$ 4,00)")
                    c_tx1, c_tx2 = st.columns(2)
                    with c_tx1: taxa_percentual = st.number_input("Comissão Shopee (%)", value=20.0, step=1.0)
                    with c_tx2: taxa_fixa = st.number_input("Taxa Fixa (R$)", value=4.0, step=0.5)
                elif canal_venda == "Mercado Livre":
                    st.caption("Ajuste as taxas conforme o anúncio (Clássico/Premium)")
                    c_tx1, c_tx2 = st.columns(2)
                    with c_tx1: taxa_percentual = st.number_input("Comissão ML (%)", value=14.0, step=1.0)
                    with c_tx2: taxa_fixa = st.number_input("Custo Fixo ML (R$)", value=6.0, step=0.5)

                preco_final_venda = st.number_input(
                    "Preço Final Cobrado do Cliente (R$)", 
                    value=preco_sugerido_original, 
                    step=5.0,
                    help="Aumente este valor para repassar as taxas da plataforma para o cliente e proteger seu lucro."
                )

                # Cálculos do Lucro Real
                valor_descontado_taxas = (preco_final_venda * (taxa_percentual / 100)) + taxa_fixa
                receita_liquida = preco_final_venda - valor_descontado_taxas
                lucro_real = receita_liquida - custo_fabrica
                margem_real = (lucro_real / preco_final_venda) * 100 if preco_final_venda > 0 else 0

                st.markdown("---")
                res_col1, res_col2, res_col3 = st.columns(3)
                res_col1.metric("Você Recebe (Líquido)", f"R$ {receita_liquida:.2f}", f"- R$ {valor_descontado_taxas:.2f} (Taxas)", delta_color="inverse")
                res_col2.metric("Lucro Limpo Real", f"R$ {lucro_real:.2f}", f"{margem_real:.1f}% Margem")
                res_col3.metric("Custo da Peça", f"R$ {custo_fabrica:.2f}")

                if st.button("✅ Registrar Venda", type="primary", use_container_width=True):
                    if nome_cliente:
                        supabase.table('vendas').insert({
                            'cliente': nome_cliente,
                            'nome_projeto': proj_selecionado,
                            'canal': canal_venda,
                            'valor_venda': preco_final_venda,
                            'taxa_plataforma': valor_descontado_taxas,
                            'custo_producao': custo_fabrica,
                            'lucro_liquido': lucro_real,
                            'status': status_pedido
                        }).execute()
                        st.success("✅ Venda registrada com sucesso no funil!")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("🚨 Informe o nome do cliente/comprador antes de salvar.")
        else:
            st.info("Você precisa ter projetos salvos no Histórico (Módulo 2) para poder vender.")

    with tab_painel:
        vendas_df = get_df('vendas')
        if not vendas_df.empty:
            st.subheader("Funil de Pedidos Abertos e Concluídos")
            
            # Exibição limpa
            disp_vendas = vendas_df[['id', 'status', 'cliente', 'nome_projeto', 'canal', 'lucro_liquido', 'created_at']].copy()
            disp_vendas.rename(columns={'status': 'Status', 'cliente': 'Cliente', 'nome_projeto': 'Peça', 'canal': 'Canal', 'lucro_liquido': 'Lucro (R$)'}, inplace=True)
            
            # Limpa o formato da data visualmente
            disp_vendas['Data'] = pd.to_datetime(disp_vendas['created_at']).dt.strftime('%d/%m/%Y')
            disp_vendas = disp_vendas.drop(columns=['created_at'])

            # Move a coluna de Data para o início
            cols = ['id', 'Data'] + [col for col in disp_vendas.columns if col not in ['id', 'Data']]
            disp_vendas = disp_vendas[cols]

            st.dataframe(disp_vendas.style.format({"Lucro (R$)": "R$ {:.2f}"}), use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("**Atualizar Status do Pedido:**")
            col_a1, col_a2, col_a3 = st.columns([2, 2, 1])
            with col_a1:
                venda_id_atualizar = st.selectbox("Selecione o ID do Pedido", disp_vendas['id'].tolist())
            with col_a2:
                novo_status = st.selectbox("Mover para:", ["Aguardando Pagamento", "Em Produção", "Pronto / Enviado", "Concluído"], key="st_update")
            with col_a3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔄 Atualizar", use_container_width=True):
                    # Puxa o status antigo para saber se já estava concluído
                    venda_antiga = vendas_df[vendas_df['id'] == venda_id_atualizar].iloc[0]
                    status_antigo = venda_antiga['status']
                    
                    # Atualiza o status no banco
                    supabase.table('vendas').update({'status': novo_status}).eq('id', venda_id_atualizar).execute()
                    
                    # A MÁGICA: Se mudou para "Concluído", dispara o robô de baixa de estoque!
                    if novo_status == "Concluído" and status_antigo != "Concluído":
                        nome_peca = venda_antiga['nome_projeto']
                        historico_df = get_df('historico')
                        
                        if not historico_df.empty:
                            peca_info = historico_df[historico_df['nome_projeto'] == nome_peca]
                            if not peca_info.empty:
                                peca_dados = peca_info.iloc[0]
                                
                                # 1. Baixa do Filamento (Gramas)
                                material_usado = peca_dados['material']
                                peso_usado = float(peca_dados['peso_g'])
                                
                                # O robô agora busca na lista compilada
                                fil_df_robo = get_df('filamentos')
                                if not fil_df_robo.empty:
                                    fil_df_robo['display'] = fil_df_robo.apply(lambda x: f"{x.get('marca', 'S/N')} - {x['nome']} - {x.get('cor', 'S/N')}", axis=1)
                                    fil_encontrado = fil_df_robo[fil_df_robo['display'] == material_usado]
                                    
                                    if not fil_encontrado.empty:
                                        fil_id = fil_encontrado.iloc[0]['id']
                                        peso_atual = float(fil_encontrado.iloc[0]['peso_estoque_g'] or 0)
                                        novo_peso = peso_atual - peso_usado
                                        supabase.table('filamentos').update({'peso_estoque_g': novo_peso}).eq('id', int(fil_id)).execute()
                                
                                # 2. Baixa dos Insumos Extras (Unidades)
                                extras_json = peca_dados.get('custos_extras', '[]')
                                try:
                                    lista_extras = json.loads(extras_json)
                                    for ex in lista_extras:
                                        nome_insumo = ex['nome']
                                        qtd_usada = int(ex['qtd'])
                                        
                                        out_info = supabase.table('outros').select('id, qtd_estoque').eq('nome', nome_insumo).execute()
                                        if out_info.data:
                                            out_id = out_info.data[0]['id']
                                            qtd_atual = int(out_info.data[0]['qtd_estoque'] or 0)
                                            nova_qtd = qtd_atual - qtd_usada
                                            supabase.table('outros').update({'qtd_estoque': nova_qtd}).eq('id', out_id).execute()
                                except:
                                    pass # Blindagem caso a peça não tenha extras
                                    
                        st.success("✅ Venda Concluída! Materiais baixados do estoque automaticamente.")
                    else:
                        st.success("✅ Status do pedido atualizado!")
                        
                    time.sleep(2)
                    st.rerun()
        else:
            st.info("Nenhuma venda registrada ainda. O seu painel de controle aparecerá aqui.")

# =====================================================================
# MÓDULO 5: BACKUP E EXPORTAÇÃO
# =====================================================================
elif menu == "💾 Módulo 5: BACKUP":
    st.title("💾 Backup de Segurança do Sistema")
    st.markdown("A sua base de dados principal está **blindada e operando na nuvem** pelo Supabase. Mas ter uma cópia física local é a regra de ouro da gestão industrial.")
    
    st.divider()
    
    st.subheader("📦 Exportar Histórico de Projetos")
    st.caption("Baixe toda a sua inteligência de precificação para abrir no Excel.")
    
    # Busca os dados no banco
    df_backup_historico = get_df('historico')
    
    if not df_backup_historico.empty:
        # Converte para CSV
        csv = df_backup_historico.to_csv(index=False).encode('utf-8')
        
        data_hoje_arquivo = datetime.now().strftime("%Y-%m-%d")
        nome_arquivo = f"backup_3dcalcpro_historico_{data_hoje_arquivo}.csv"
        
        st.download_button(
            label="⬇️ Baixar Backup do Histórico (CSV)",
            data=csv,
            file_name=nome_arquivo,
            mime="text/csv",
            type="primary"
        )
        st.success("Tudo pronto! Clique no botão acima para salvar a cópia no seu HD.")
    else:
        st.warning("O seu histórico ainda está vazio. Cadastre e precifique peças para gerar um backup.")
