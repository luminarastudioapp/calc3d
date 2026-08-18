import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
import base64
import json
import time

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS (SQLite) ---
DB_NAME = "3d_calc_pro.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # --- RENAME MATERIAIS PARA FILAMENTOS (Migração segura) ---
    try:
        cursor.execute("ALTER TABLE materiais RENAME TO filamentos")
    except sqlite3.OperationalError:
        pass # Se já foi renomeada ou não existe, segue em frente

    # --- TABELAS BASE ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS filamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, preco_kg REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS impressoras (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, watts REAL, preco_maquina REAL, vida_util_h REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, kwh REAL, mao_obra REAL)''')
    
    # --- NOVAS TABELAS: CATEGORIAS E OUTROS INSUMOS ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS categorias (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, tipo_categoria TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS outros (id INTEGER PRIMARY KEY AUTOINCREMENT, categoria TEXT, nome TEXT, marca TEXT, valor_unit REAL, especificacoes TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nome_projeto TEXT, material TEXT, peso_g REAL, tempo_h REAL, 
        custo_total REAL, preco_venda REAL, data TEXT
    )''')
    
    # --- SCRIPT DE MIGRAÇÃO (Colunas do Histórico) ---
    colunas_novas = [
        ("memoria_calculo", "TEXT"), ("foto_principal", "TEXT"), 
        ("origem", "TEXT"), ("link_projeto", "TEXT"), ("custo_mao_obra", "REAL"),
        ("arquivo_pago", "TEXT"), ("preco_arquivo", "REAL"), ("descricao", "TEXT"),
        ("cores", "INTEGER"), ("dim_largura", "REAL"), ("dim_profundidade", "REAL"), ("dim_altura", "REAL"),
        ("categoria_peca", "TEXT"), ("custos_extras", "TEXT"), ("markup_aplicado", "REAL")
    ]
    for col, tipo in colunas_novas:
        try:
            cursor.execute(f"ALTER TABLE historico ADD COLUMN {col} {tipo}")
        except sqlite3.OperationalError:
            pass 

    # --- DADOS PADRÃO PARA EVITAR BANCO VAZIO ---
    cursor.execute("SELECT COUNT(*) FROM configuracoes")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO configuracoes (id, kwh, mao_obra) VALUES (1, 0.95, 35.0)")

    cursor.execute("SELECT COUNT(*) FROM categorias")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO categorias (nome, tipo_categoria) VALUES (?, ?)", [
            ("Embalagem", "Insumo"), ("Insumo Geral", "Insumo"), 
            ("Decorativo", "Peça"), ("Funcional", "Peça")
        ])

    cursor.execute("SELECT COUNT(*) FROM filamentos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO filamentos (nome, preco_kg) VALUES (?, ?)", [("PLA", 99.0), ("PETG", 119.0)])
        
    cursor.execute("SELECT COUNT(*) FROM impressoras")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO impressoras (nome, watts, preco_maquina, vida_util_h) VALUES (?, ?, ?, ?)", [
            ("Ender 3", 150.0, 1800.0, 4000.0), ("Bambu Lab A1 + AMS Lite", 150.0, 4200.0, 5000.0)
        ])
        
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect(DB_NAME)

def converter_imagem(upload):
    if upload is not None:
        return base64.b64encode(upload.read()).decode()
    return None

# Inicializando variáveis de sessão (Memória do App)
if "lista_extras" not in st.session_state:
    st.session_state.lista_extras = []
if "markup" not in st.session_state:
    st.session_state.markup = 100

def set_markup(val):
    st.session_state.markup = val

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
menu = st.sidebar.radio("Módulos do Sistema", [
    "⚙️ Módulo 1: CADASTROS", 
    "🚀 Módulo 2: NOVO PROJETO", 
    "📜 Módulo 3: RELATÓRIO"
])

# =====================================================================
# MÓDULO 1: CADASTROS (Configurações, Categorias, Filamentos, Outros, Impressoras)
# =====================================================================
if menu == "⚙️ Módulo 1: CADASTROS":
    st.title("⚙️ Cadastros e Custos da Gráfica")
    tab_cfg, tab_cat, tab_fil, tab_out, tab_imp = st.tabs(["💵 Custos Fixos", "🏷️ Categorias", "🧵 Filamentos", "📦 Outros", "🖨️ Impressoras"])
    
    # --- CONFIGURAÇÕES GERAIS ---
    with tab_cfg:
        conn = get_db_connection()
        cfg_df = pd.read_sql("SELECT * FROM configuracoes WHERE id=1", conn)
        kwh_atual = float(cfg_df['kwh'][0])
        mao_obra_atual = float(cfg_df['mao_obra'][0])
        
        st.markdown("### Parâmetros Base da Sua Produção")
        with st.form("form_cfg"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                novo_kwh = st.number_input("Custo do kWh (R$)", value=kwh_atual, step=0.05)
            with col_c2:
                nova_mao_obra = st.number_input("Seu Valor Hora - Mão de Obra (R$/h)", value=mao_obra_atual, step=5.0)
            if st.form_submit_button("Atualizar Custos Fixos"):
                conn.cursor().execute("UPDATE configuracoes SET kwh=?, mao_obra=? WHERE id=1", (novo_kwh, nova_mao_obra))
                conn.commit()
                st.success("✅ Custos base atualizados!")
                time.sleep(1)
                st.rerun()
        conn.close()

    # --- CRUD: CATEGORIAS ---
    with tab_cat:
        conn = get_db_connection()
        cat_df = pd.read_sql("SELECT id, nome as 'Nome da Categoria', tipo_categoria as 'Tipo' FROM categorias", conn)
        st.dataframe(cat_df, use_container_width=True, hide_index=True)

        st.markdown("### 📝 Nova Categoria")
        with st.form("form_cat", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1: nome_cat = st.text_input("Nome da Categoria")
            with col2: tipo_cat = st.selectbox("Aplica-se à:", ["Insumo", "Peça"])
            if st.form_submit_button("Salvar Categoria") and nome_cat:
                try:
                    conn.cursor().execute("INSERT INTO categorias (nome, tipo_categoria) VALUES (?, ?)", (nome_cat, tipo_cat))
                    conn.commit()
                    st.success("✅ Categoria adicionada!")
                    time.sleep(1)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Categoria já existe!")
        conn.close()

    # --- CRUD: FILAMENTOS ---
    with tab_fil:
        conn = get_db_connection()
        filamentos_df = pd.read_sql("SELECT id, nome as 'Nome', preco_kg as 'Preço/KG (R$)' FROM filamentos", conn)
        st.dataframe(filamentos_df, use_container_width=True, hide_index=True)

        st.markdown("### 📝 Novo Filamento")
        with st.form("form_fil", clear_on_submit=True):
            nome_fil = st.text_input("Nome do Filamento")
            preco_fil = st.number_input("Custo Unitário (R$/KG)", min_value=0.0, value=99.0)
            if st.form_submit_button("Salvar Filamento") and nome_fil:
                conn.cursor().execute("INSERT INTO filamentos (nome, preco_kg) VALUES (?, ?)", (nome_fil, preco_fil))
                conn.commit()
                st.success("✅ Filamento cadastrado!")
                time.sleep(1)
                st.rerun()
        conn.close()

    # --- CRUD: OUTROS ---
    with tab_out:
        conn = get_db_connection()
        outros_df = pd.read_sql("SELECT id, categoria as 'Categoria', nome as 'Nome', marca as 'Marca/Modelo', valor_unit as 'Valor Unitário (R$)', especificacoes as 'Especificações' FROM outros", conn)
        st.dataframe(outros_df, use_container_width=True, hide_index=True)

        categorias_insumo = pd.read_sql("SELECT nome FROM categorias WHERE tipo_categoria='Insumo'", conn)['nome'].tolist()
        if not categorias_insumo: categorias_insumo = ["Cadastre uma categoria primeiro"]

        st.markdown("### 📝 Novo Insumo/Extra")
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
                conn.cursor().execute("INSERT INTO outros (categoria, nome, marca, valor_unit, especificacoes) VALUES (?, ?, ?, ?, ?)", 
                                      (cat_outro, nome_outro, marca_outro, valor_outro, espec_outro))
                conn.commit()
                st.success("✅ Insumo cadastrado!")
                time.sleep(1)
                st.rerun()
        conn.close()

    # --- CRUD: IMPRESSORAS ---
    with tab_imp:
        conn = get_db_connection()
        imp_df = pd.read_sql("SELECT id, nome as 'Modelo', watts, preco_maquina as 'Valor (R$)', vida_util_h as 'Vida Útil (h)' FROM impressoras", conn)
        if not imp_df.empty:
            imp_df['Consumo (kW)'] = imp_df['watts'] / 1000
            st.dataframe(imp_df[['Modelo', 'Consumo (kW)', 'Valor (R$)', 'Vida Útil (h)']].style.format({
                "Consumo (kW)": "{:.2f} kW", "Valor (R$)": "R$ {:.2f}"
            }), use_container_width=True, hide_index=True)

        st.markdown("### 📝 Nova Impressora")
        with st.form("form_imp", clear_on_submit=True):
            nome_imp = st.text_input("Marca | Modelo da Impressora")
            kw_imp = st.number_input("Consumo Máquina (kW) - Ex: 0.15", value=0.15, step=0.05)
            preco_imp = st.number_input("Valor da Impressora (R$)", value=5000.0)
            vida_imp = st.number_input("Vida Útil Estimada (Horas)", value=3000)
            if st.form_submit_button("Salvar Máquina") and nome_imp:
                conn.cursor().execute("INSERT INTO impressoras (nome, watts, preco_maquina, vida_util_h) VALUES (?, ?, ?, ?)", (nome_imp, kw_imp*1000, preco_imp, vida_imp))
                conn.commit()
                st.success("✅ Impressora cadastrada!")
                time.sleep(1)
                st.rerun()
        conn.close()


# =====================================================================
# MÓDULO 2: NOVO PROJETO (Criação, Custos e Markup)
# =====================================================================
elif menu == "🚀 Módulo 2: NOVO PROJETO":
    st.title("🚀 Criação e Precificação de Projeto")
    
    conn = get_db_connection()
    filamentos_df = pd.read_sql("SELECT * FROM filamentos", conn)
    impressoras_df = pd.read_sql("SELECT * FROM impressoras", conn)
    categorias_peca_df = pd.read_sql("SELECT nome FROM categorias WHERE tipo_categoria='Peça'", conn)
    outros_df = pd.read_sql("SELECT * FROM outros", conn)
    cfg_df = pd.read_sql("SELECT * FROM configuracoes WHERE id=1", conn)
    
    kwh_cost = float(cfg_df['kwh'][0])
    mao_obra_rate = float(cfg_df['mao_obra'][0])
    
    col1, col2 = st.columns([1.2, 1], gap="large")

    with col1:
        st.subheader("📋 Identidade da Peça")
        
        opcoes_cat_peca = categorias_peca_df['nome'].tolist() if not categorias_peca_df.empty else ["Nenhuma categoria cadastrada"]
        cat_peca_selecionada = st.selectbox("Categoria da Peça", opcoes_cat_peca)
        
        proj_name = st.text_input("Nome da Peça", placeholder="Ex: Vaso Geométrico")
        
        foto_upload = st.file_uploader("📸 Anexar Foto do Projeto", type=["png", "jpg", "jpeg"])
        foto_b64 = converter_imagem(foto_upload)
        if foto_upload: st.image(foto_upload, width=150)

        origem = st.radio("Origem do Design", ["Autoral", "Fornecedor"], horizontal=True)
        link_projeto = ""
        arquivo_pago = "Não"
        preco_arquivo = 0.0
        
        if origem == "Fornecedor":
            link_projeto = st.text_input("🔗 Link do Projeto (Onde baixou/comprou)")
            arquivo_pago = st.radio("O arquivo (STL/3MF) é pago?", ["Não", "Sim"], horizontal=True)
            if arquivo_pago == "Sim":
                preco_arquivo = st.number_input("Preço de Aquisição do Arquivo (R$)", min_value=0.0, step=5.0)

        st.divider()
        st.subheader("⚙️ Parâmetros de Fabricação")
        
        descricao = st.text_area("Descrição / Observações", placeholder="Ex: Preenchimento giroide 15%.")
        
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1: cores = st.number_input("Qtd. de Cores", min_value=1, value=1, step=1)
        with col_c2:
            st.caption("Dimensões Finais (cm)")
            d1, d2, d3 = st.columns(3)
            with d1: dim_l = st.number_input("Largura", min_value=0.0)
            with d2: dim_p = st.number_input("Profund.", min_value=0.0)
            with d3: dim_a = st.number_input("Altura", min_value=0.0)
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            printer_selected = st.selectbox("Impressora", impressoras_df['nome'].tolist() if not impressoras_df.empty else ["Nenhuma"])
            printer_info = impressoras_df[impressoras_df['nome'] == printer_selected].iloc[0] if not impressoras_df.empty else None
        with col_m2:
            fil_selected = st.selectbox("Filamento", filamentos_df['nome'].tolist() if not filamentos_df.empty else ["Nenhum"])
            fil_info = filamentos_df[filamentos_df['nome'] == fil_selected].iloc[0] if not filamentos_df.empty else None
            mat_cost_per_kg = float(fil_info['preco_kg']) if fil_info is not None else 0.0

        col_w, col_t1, col_t2 = st.columns([1, 1, 1])
        with col_w: weight_g = st.number_input("Peso total (g)", min_value=0.0, value=0.0)
        with col_t1: hours = st.number_input("Tempo (h)", min_value=0, value=0)
        with col_t2: mins = st.number_input("Tempo (min)", min_value=0, max_value=59, value=0)

        tempo_mao_obra_min = st.number_input("Sua Mão de Obra Dedicada (Minutos)", min_value=0, value=15, step=5)

        st.divider()
        st.subheader("📦 Custos Extras")
        st.caption("Adicione itens de montagem, imãs, elásticos ou embalagens.")
        
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
                    col_l1.markdown(f"- {ex['qtd']}x {ex['nome']} (R$ {ex['subtotal']:.2f})")
                    if col_l2.button("❌", key=f"del_ex_{i}"):
                        st.session_state.lista_extras.pop(i)
                        st.rerun()
                    custo_extras_total += ex['subtotal']
        else:
            st.info("Cadastre insumos no Módulo 1 para usá-locomo custos extras.")
            custo_extras_total = 0.0

    # CÁLCULOS BASE
    total_hours = hours + (mins / 60)
    cost_mat = (weight_g / 1000) * mat_cost_per_kg
    cost_energy = (printer_info['watts'] / 1000) * total_hours * kwh_cost if printer_info is not None else 0
    cost_depr = (printer_info['preco_maquina'] / max(1, printer_info['vida_util_h'])) * total_hours if printer_info is not None else 0
    cost_mao_obra = (tempo_mao_obra_min / 60) * mao_obra_rate
    
    total_cost_prod = cost_mat + cost_energy + cost_depr + cost_mao_obra + custo_extras_total
    
    with col2:
        # IMPLEMENTAÇÃO DO MARKUP IDÊNTICA À IMAGEM
        st.markdown("### 📈 Lucro Desejado")
        st.markdown("""
        <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0;'>
        """, unsafe_allow_html=True)
        
        st.session_state.markup = st.slider("Markup (%)", 0, 500, st.session_state.markup, key="markup_slider")
        
        # Botões Rápidos
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
        btn_col1.button("50%", on_click=set_markup, args=(50,), use_container_width=True)
        btn_col2.button("100%", on_click=set_markup, args=(100,), use_container_width=True)
        btn_col3.button("150%", on_click=set_markup, args=(150,), use_container_width=True)
        btn_col4.button("200%", on_click=set_markup, args=(200,), use_container_width=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # CÁLCULO DE VENDA
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

            if st.button("💾 Salvar Precificação Completa", type="primary", use_container_width=True):
                cursor = conn.cursor()
                data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                cursor.execute("""
                    INSERT INTO historico (
                        nome_projeto, material, peso_g, tempo_h, custo_total, preco_venda, data, 
                        memoria_calculo, foto_principal, origem, link_projeto, custo_mao_obra,
                        arquivo_pago, preco_arquivo, descricao, cores, dim_largura, dim_profundidade, dim_altura,
                        categoria_peca, custos_extras, markup_aplicado
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    proj_name, fil_selected, weight_g, total_hours, total_cost_prod, preco_venda_final, data_hoje, 
                    memoria_calc_str, foto_b64, origem, link_projeto, cost_mao_obra,
                    arquivo_pago, preco_arquivo, descricao, cores, dim_l, dim_p, dim_a,
                    cat_peca_selecionada, json.dumps(st.session_state.lista_extras), st.session_state.markup
                ))
                conn.commit()
                st.session_state.lista_extras = [] # Limpa os extras para o próximo projeto
                st.success("✅ Projeto salvo com a precificação completa!")
                time.sleep(1.5)
                st.rerun()
        else:
            st.info("👈 Preencha os parâmetros e adicione o peso da peça para gerar o cálculo de venda.")
            
    conn.close()


# =====================================================================
# MÓDULO 3: RELATÓRIO (Landscape Print & Memória de Cálculo)
# =====================================================================
elif menu == "📜 Módulo 3: RELATÓRIO":
    st.title("📜 Vitrine de Produção e Venda")
    
    st.markdown("""
        <button onclick="window.print()" style="background-color: #000; color: white; padding: 10px 24px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; margin-bottom: 20px;">
            🖨️ IMPRIMIR FICHA TÉCNICA (LANDSCAPE)
        </button>
    """, unsafe_allow_html=True)
    
    conn = get_db_connection()
    df_hist = pd.read_sql("SELECT * FROM historico ORDER BY id DESC", conn)
    conn.close()

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
                
                # Exibindo itens extras se houver
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
                    conn = get_db_connection()
                    conn.cursor().execute("DELETE FROM historico WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.success("Ficha removida com sucesso!")
                    time.sleep(1)
                    st.rerun()
            
            st.divider()
    else:
        st.info("Nenhuma ficha de produção e venda salva.")
