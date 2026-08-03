import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(page_title="3D Calc Pro - Gestão Completa", page_icon="🎲", layout="wide")

# Estilo CSS moderno e limpo
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .stButton>button { border-radius: 8px; font-weight: 600; }
    .stSelectbox, .stTextInput, .stNumberInput { font-weight: 500; }
    .slicer-box { background-color: #f1f5f9; padding: 15px; border-radius: 10px; border-left: 5px solid #10b981; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

DB_NAME = "3d_gestao_completa.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite():
    conn = get_db()
    c = conn.cursor()
    
    # 1. Catálogo de Produtos
    c.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            categoria TEXT DEFAULT 'Geral',
            peso_padrao_g REAL DEFAULT 0.0,
            tempo_padrao_h REAL DEFAULT 0.0,
            descricao TEXT
        )
    """)
    
    # 2. Insumos
    c.execute("""
        CREATE TABLE IF NOT EXISTS insumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            fabricante TEXT,
            preco_kg REAL NOT NULL,
            avaliacao INTEGER DEFAULT 5,
            observacoes TEXT
        )
    """)
    
    # 3. Impressoras
    c.execute("""
        CREATE TABLE IF NOT EXISTS impressoras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            watts REAL NOT NULL,
            investimento REAL DEFAULT 0,
            vida_util_h REAL DEFAULT 4000,
            reserva_manutencao_pct REAL DEFAULT 10
        )
    """)
    
    # 4. Histórico de Lotes
    c.execute("""
        CREATE TABLE IF NOT EXISTS projetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_projeto TEXT NOT NULL,
            data TEXT,
            unidades_lote INTEGER DEFAULT 1,
            insumo_nome TEXT,
            preco_kg_usado REAL,
            peso_unit_g REAL,
            peso_suporte_g REAL DEFAULT 0.0,
            trocas_filamento INTEGER DEFAULT 0,
            impressora_nome TEXT,
            tempo_prep_min REAL DEFAULT 7.0,
            tempo_impressao_h REAL,
            tarifa_kwh REAL,
            valor_hora_mo REAL,
            horas_modelagem REAL,
            qtd_amortizar_modelagem INTEGER,
            horas_preparacao REAL,
            horas_pos_processo REAL,
            horas_admin REAL,
            embalagem_unit REAL,
            consumiveis_lote REAL,
            outros_custos_lote REAL,
            descricao_outros TEXT,
            taxa_desperdicio_pct REAL,
            taxas_venda_pct REAL,
            impostos_pct REAL,
            margem_alvo_pct REAL,
            custo_total_lote REAL,
            custo_unitario REAL,
            preco_sugerido_unit REAL,
            preco_praticado_unit REAL,
            lucro_lote REAL
        )
    """)
    
    # Dados iniciais padronizados
    c.execute("SELECT COUNT(*) FROM produtos")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO produtos (nome, categoria, peso_padrao_g, tempo_padrao_h, descricao) VALUES (?, ?, ?, ?, ?)", [
            ("Vaso Geométrico 3D", "Decoração", 85.0, 4.5, "Vaso decorativo estilo poliédrico"),
            ("Suporte Singer Ultralock", "Peças Funcionais", 160.0, 5.0, "Peça funcional para máquina de costura"),
            ("Organizador de Cabos", "Utilitários", 25.0, 1.2, "Organizador de mesa para cabos")
        ])
        
    c.execute("SELECT COUNT(*) FROM insumos")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO insumos (nome, fabricante, preco_kg, avaliacao, observacoes) VALUES (?, ?, ?, ?, ?)", [
            ("PLA Standard", "3D Fila", 110.0, 5, "Ótima aderência e acabamento"),
            ("PLA Premium HT", "Voolt3D", 135.0, 5, "Resistência térmica aprimorada"),
            ("PETG XT", "Creality", 125.0, 4, "Excelente para peças mecânicas"),
            ("Resina Standard", "Anycubic", 180.0, 4, "Alta precisão de detalhes")
        ])
        
    c.execute("SELECT COUNT(*) FROM impressoras")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO impressoras (nome, watts, investimento, vida_util_h, reserva_manutencao_pct) VALUES (?, ?, ?, ?, ?)", [
            ("Bambu Lab P2S", 150, 4200.0, 5000, 10.0),
            ("Ender 3 V2", 130, 1800.0, 4000, 10.0),
            ("Bambu Lab X1C", 350, 11000.0, 6000, 12.0),
            ("Elegoo Mars 3 (Resina)", 60, 2500.0, 3000, 15.0)
        ])
        
    conn.commit()
    conn.close()

init_sqlite()

# NAVEGAÇÃO PRINCIPAL
st.sidebar.title("🎲 3D Calc Pro")
st.sidebar.caption("Gestão de Produção & Precificação")

menu = st.sidebar.radio("Navegação", [
    "🧮 Nova Ficha de Produção",
    "📁 Catálogo de Produtos",
    "📦 Gestão de Insumos",
    "🖨️ Gestão de Impressoras",
    "📜 Histórico de Orçamentos"
])

# ==========================================
# 1. NOVA FICHA DE PRODUÇÃO (CÁLCULO + FATIADOR)
# ==========================================
if menu == "🧮 Nova Ficha de Produção":
    st.title("🧮 Ficha de Produção & Precificação Completa")
    st.caption("Preencha os dados de consumo copiando direto do seu Fatiador 3D.")

    conn = get_db()
    produtos_df = pd.read_sql("SELECT * FROM produtos ORDER BY nome ASC", conn)
    insumos_df = pd.read_sql("SELECT * FROM insumos ORDER BY nome ASC", conn)
    impressoras_df = pd.read_sql("SELECT * FROM impressoras ORDER BY nome ASC", conn)
    conn.close()

    if insumos_df.empty or impressoras_df.empty:
        st.warning("⚠️ Cadastre ao menos um insumo e uma impressora nos menus para realizar cálculos.")
        st.stop()

    st.markdown("### 1. Seleção do Produto do Catálogo")
    prod_options = ["-- Criar Item Avulso / Digitar Nome --"] + produtos_df['nome'].tolist()
    prod_selected_name = st.selectbox("Escolha um Produto do Catálogo:", prod_options)
    
    def_peso = 144.78
    def_tempo = 3.75
    nome_final_prod = "Vaso Geométrico 3D"

    if prod_selected_name != "-- Criar Item Avulso / Digitar Nome --":
        prod_row = produtos_df[produtos_df['nome'] == prod_selected_name].iloc[0]
        nome_final_prod = prod_row['nome']
        def_peso = float(prod_row['peso_padrao_g']) if prod_row['peso_padrao_g'] > 0 else 144.78
        def_tempo = float(prod_row['tempo_padrao_h']) if prod_row['tempo_padrao_h'] > 0 else 3.75

    with st.form("form_calculadora"):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.subheader("Dados do Projeto e Lote")
            if prod_selected_name == "-- Criar Item Avulso / Digitar Nome --":
                nome_proj = st.text_input("Nome do Produto / Projeto (Avulso)", value="Novo Projeto 3D")
            else:
                nome_proj = st.text_input("Nome do Produto / Projeto", value=nome_final_prod)

            unidades_lote = st.number_input("Unidades Aprovadas no Lote", min_value=1, value=1, step=1)
            
            options_insumos = [f"{row['nome']} ({row['fabricante'] if row['fabricante'] else 'Geral'}) - R$ {row['preco_kg']:.2f}/kg" for _, row in insumos_df.iterrows()]
            sel_insumo_idx = st.selectbox("Selecione o Insumo", range(len(options_insumos)), format_func=lambda x: options_insumos[x])
            insumo_sel = insumos_df.iloc[sel_insumo_idx]
            custo_kg_materia = st.number_input("Custo do KG do Insumo (R$)", value=float(insumo_sel['preco_kg']))

            st.markdown("---")
            st.markdown("#### 📐 Consumo do Fatiador")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                peso_modelo_g = st.number_input("Peso do Modelo (g)", value=def_peso, step=1.0)
                trocas_filamento = st.number_input("Trocas de Filamento (Multicor/AMS)", value=0, min_value=0)
            with col_f2:
                peso_suporte_g = st.number_input("Peso do Suporte/Purga (g)", value=4.35, step=0.5)
                taxa_desperdicio = st.number_input("Margem Perda Extra (%)", value=3.0, step=1.0)

        with col_p2:
            st.subheader("Impressora & Tempo de Impressão")
            options_imp = [f"{row['nome']} ({row['watts']}W)" for _, row in impressoras_df.iterrows()]
            sel_imp_idx = st.selectbox("Selecione a Impressora", range(len(options_imp)), format_func=lambda x: options_imp[x])
            imp_sel = impressoras_df.iloc[sel_imp_idx]
            
            tarifa_kwh = st.number_input("Tarifa de Energia (R$ / kWh)", value=1.25, step=0.05)
            reserva_manutencao = st.number_input("Reserva para Manutenção (%)", value=float(imp_sel['reserva_manutencao_pct']), step=1.0)

            st.markdown("---")
            st.markdown("#### ⏱️ Tempos do Fatiamento")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                tempo_prep_min = st.number_input("Tempo Preparação (Min)", value=7.0, step=1.0, help="Nivelamento, aquecimento de mesa")
                horas_imp = st.number_input("Modelo - Horas", value=3, min_value=0)
            with col_t2:
                mins_imp = st.number_input("Modelo - Minutos", value=45, min_value=0, max_value=59)

        st.markdown("---")
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            st.subheader("Mão de Obra & Operação")
            valor_hora_mo = st.number_input("Valor Hora Mão de Obra (R$/h)", value=30.0, step=5.0)
            
            col_mo1, col_mo2 = st.columns(2)
            with col_mo1:
                horas_modelagem = st.number_input("Horas Modelagem 3D", value=1.0, step=0.5)
                qtd_amortizar = st.number_input("Amortizar Modelagem em (un)", value=10, min_value=1)
            with col_mo2:
                horas_preparacao = st.number_input("Fatiamento / G-code (h)", value=0.1, step=0.1)
                horas_pos_processo = st.number_input("Retirar Suporte / Pós (h)", value=0.2, step=0.1)
                horas_admin = st.number_input("Embalagem / Admin (h)", value=0.1, step=0.1)

        with col_m2:
            st.subheader("Custos Adicionais & Venda")
            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                embalagem_unit = st.number_input("Embalagem por Unidade (R$)", value=2.50, step=0.5)
                consumiveis_lote = st.number_input("Consumíveis do Lote (R$)", value=1.50, step=0.5)
            with col_ex2:
                outros_custos = st.number_input("Outros Custos Lote (R$)", value=0.0, step=1.0)
                desc_outros = st.text_input("Descrição Outros Custos", value="")

            taxas_venda = st.number_input("Taxas Plataforma Venda (%)", value=12.0, step=1.0)
            impostos_pct = st.number_input("Impostos (%)", value=6.0, step=1.0)
            margem_alvo = st.number_input("Margem de Lucro Alvo (%)", value=40.0, step=5.0)

        btn_calcular = st.form_submit_button("📊 Processar Ficha de Produção", type="primary", use_container_width=True)

    # CÁLCULOS
    peso_unit_total_g = (peso_modelo_g + peso_suporte_g) * (1 + (taxa_desperdicio / 100))
    peso_lote_total_g = peso_unit_total_g * unidades_lote
    custo_material_total = (peso_lote_total_g / 1000) * custo_kg_materia
    
    tempo_impressao_modelo_h = horas_imp + (mins_imp / 60)
    tempo_prep_h = tempo_prep_min / 60
    tempo_maquina_unit_h = tempo_prep_h + tempo_impressao_modelo_h
    tempo_maquina_lote_h = tempo_maquina_unit_h * unidades_lote

    custo_energia_total = (imp_sel['watts'] / 1000) * tempo_maquina_lote_h * tarifa_kwh
    custo_depreciacao_h = (imp_sel['investimento'] / max(1, imp_sel['vida_util_h']))
    custo_maquina_total = (custo_depreciacao_h * tempo_maquina_lote_h) * (1 + (reserva_manutencao / 100))
    
    custo_modelagem_alocado = (horas_modelagem * valor_hora_mo) / qtd_amortizar * unidades_lote
    horas_operacionais_lote = (horas_preparacao + horas_pos_processo + horas_admin) * unidades_lote
    custo_mo_operacional = horas_operacionais_lote * valor_hora_mo
    custo_mo_total = custo_modelagem_alocado + custo_mo_operacional
    
    custo_extras_total = (embalagem_unit * unidades_lote) + consumiveis_lote + outros_custos
    
    custo_direto_lote = custo_material_total + custo_energia_total + custo_maquina_total + custo_mo_total + custo_extras_total
    custo_unitario = custo_direto_lote / unidades_lote
    
    percentual_deducoes = (taxas_venda + impostos_pct + margem_alvo) / 100
    if percentual_deducoes >= 1.0:
        percentual_deducoes = 0.90
        
    preco_sugerido_lote = custo_direto_lote / (1 - percentual_deducoes)
    preco_sugerido_unit = preco_sugerido_lote / unidades_lote
    lucro_estimado_lote = preco_sugerido_lote * (margem_alvo / 100)

    st.markdown("---")
    st.subheader("📌 Resumo Consolidado do Lote")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Custo Direto Lote", f"R$ {custo_direto_lote:.2f}", f"R$ {custo_unitario:.2f} / un")
    c2.metric("🏷️ Preço Sugerido (Unidade)", f"R$ {preco_sugerido_unit:.2f}", f"Margem: {margem_alvo}%")
    c3.metric("📊 Faturamento do Lote", f"R$ {preco_sugerido_lote:.2f}")
    c4.metric("📈 Lucro Limpo do Lote", f"R$ {lucro_estimado_lote:.2f}")

    pct_suporte = (peso_suporte_g / max(1, (peso_modelo_g + peso_suporte_g))) * 100

    st.markdown(f"""
    <div class="slicer-box">
        <strong>🔍 Resultado do Fatiamento:</strong><br>
        • Peso Único Real: <b>{peso_unit_total_g:.2f}g</b> (Modelo: {peso_modelo_g}g | Suporte/Purga: {peso_suporte_g}g — <i>{pct_suporte:.1f}% é suporte/desperdício</i>)<br>
        • Tempo de Máquina por Peça: <b>{int(tempo_maquina_unit_h)}h {int((tempo_maquina_unit_h%1)*60)}m</b> (Prep: {tempo_prep_min:.0f}m | Impressão: {horas_imp}h {mins_imp}m)<br>
        • Trocas de Filamento Multicor: <b>{trocas_filamento} trocas</b>
    </div>
    """, unsafe_allow_html=True)

    df_resumo = pd.DataFrame({
        "Categoria de Custo": ["Material (Modelo + Suporte + Perdas)", "Energia & Depreciação de Máquina", "Mão de Obra (Modelagem + Operação)", "Embalagens & Extras"],
        "Valor Total Lote (R$)": [custo_material_total, custo_energia_total + custo_maquina_total, custo_mo_total, custo_extras_total],
        "Custo por Unidade (R$)": [custo_material_total/unidades_lote, (custo_energia_total + custo_maquina_total)/unidades_lote, custo_mo_total/unidades_lote, custo_extras_total/unidades_lote]
    })
    st.dataframe(df_resumo.style.format({"Valor Total Lote (R$)": "R$ {:.2f}", "Custo por Unidade (R$)": "R$ {:.2f}"}), use_container_width=True, hide_index=True)

    if st.button("💾 Salvar Ficha de Produção no Histórico", type="primary", use_container_width=True):
        conn = get_db()
        c = conn.cursor()
        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
        c.execute("""
            INSERT INTO projetos (
                nome_projeto, data, unidades_lote, insumo_nome, preco_kg_usado, peso_unit_g,
                peso_suporte_g, trocas_filamento, impressora_nome, tempo_prep_min, tempo_impressao_h, tarifa_kwh, valor_hora_mo, horas_modelagem,
                qtd_amortizar_modelagem, horas_preparacao, horas_pos_processo, horas_admin,
                embalagem_unit, consumiveis_lote, outros_custos_lote, descricao_outros,
                taxa_desperdicio_pct, taxas_venda_pct, impostos_pct, margem_alvo_pct,
                custo_total_lote, custo_unitario, preco_sugerido_unit, preco_praticado_unit, lucro_lote
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nome_proj, data_atual, unidades_lote, insumo_sel['nome'], custo_kg_materia, peso_modelo_g,
            peso_suporte_g, trocas_filamento, imp_sel['nome'], tempo_prep_min, tempo_impressao_modelo_h, tarifa_kwh, valor_hora_mo, horas_modelagem,
            qtd_amortizar, horas_preparacao, horas_pos_processo, horas_admin,
            embalagem_unit, consumiveis_lote, outros_custos, desc_outros,
            taxa_desperdicio, taxas_venda, impostos_pct, margem_alvo,
            custo_direto_lote, custo_unitario, preco_sugerido_unit, preco_sugerido_unit, lucro_estimado_lote
        ))
        conn.commit()
        conn.close()
        st.success(f"✅ Ficha de Produção de '{nome_proj}' gravada no histórico!")

# ==========================================
# 2. CATÁLOGO DE PRODUTOS (CRUD UNIFICADO DE TELA ÚNICA)
# ==========================================
elif menu == "📁 Catálogo de Produtos":
    st.title("📁 Catálogo de Produtos & Peças (CRUD Unificado)")
    st.caption("Cadastre, edite ou exclua produtos recorrentes diretamente na mesma tela.")

    conn = get_db()
    produtos_df = pd.read_sql("SELECT * FROM produtos ORDER BY nome ASC", conn)
    conn.close()

    # Seleção Unificada: Novo ou Existente
    options_crud = ["➕ [NOVO CADASTRO]"] + [f"✏️ {row['nome']} ({row['categoria']})" for _, row in produtos_df.iterrows()]
    selected_option = st.selectbox("Selecione uma Ação ou Produto para Editar/Excluir:", options_crud)

    is_novo = selected_option == "➕ [NOVO CADASTRO]"
    
    val_nome = ""
    val_cat = "Geral"
    val_peso = 145.0
    val_tempo = 3.8
    val_desc = ""
    selected_id = None

    if not is_novo:
        selected_index = options_crud.index(selected_option) - 1
        prod_row = produtos_df.iloc[selected_index]
        selected_id = int(prod_row['id'])
        val_nome = prod_row['nome']
        val_cat = prod_row['categoria']
        val_peso = float(prod_row['peso_padrao_g'])
        val_tempo = float(prod_row['tempo_padrao_h'])
        val_desc = prod_row['descricao'] if prod_row['descricao'] else ""

    st.markdown("---")
    with st.form("form_produto_unificado"):
        st.subheader("📝 Formulário do Produto")
        
        c1, c2 = st.columns(2)
        with c1:
            f_nome = st.text_input("Nome do Produto", value=val_nome)
            f_cat = st.text_input("Categoria", value=val_cat)
        with c2:
            f_peso = st.number_input("Peso Padrão Estimado (g)", value=val_peso, step=5.0)
            f_tempo = st.number_input("Tempo Padrão de Impressão (h)", value=val_tempo, step=0.1)
            
        f_desc = st.text_area("Descrição / Observações do Produto", value=val_desc)

        b_col1, b_col2 = st.columns(2)
        with b_col1:
            btn_salvar = st.form_submit_button("💾 Salvar Produto" if is_novo else "🔄 Atualizar Produto", type="primary", use_container_width=True)
        with b_col2:
            btn_excluir = st.form_submit_button("🗑️ Excluir Produto", use_container_width=True, disabled=is_novo)

        if btn_salvar and f_nome:
            conn = get_db()
            c = conn.cursor()
            if is_novo:
                try:
                    c.execute("INSERT INTO produtos (nome, categoria, peso_padrao_g, tempo_padrao_h, descricao) VALUES (?, ?, ?, ?, ?)",
                              (f_nome, f_cat, f_peso, f_tempo, f_desc))
                    conn.commit()
                    st.success(f"✅ Produto '{f_nome}' cadastrado!")
                except sqlite3.IntegrityError:
                    st.error("⚠️ Já existe um produto com este nome!")
            else:
                c.execute("UPDATE produtos SET nome=?, categoria=?, peso_padrao_g=?, tempo_padrao_h=?, descricao=? WHERE id=?",
                          (f_nome, f_cat, f_peso, f_tempo, f_desc, selected_id))
                conn.commit()
                st.success(f"✅ Produto '{f_nome}' atualizado!")
            conn.close()
            st.rerun()

        if btn_excluir and not is_novo:
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM produtos WHERE id=?", (selected_id,))
            conn.commit()
            conn.close()
            st.success("🗑️ Produto excluído!")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Tabela Geral de Produtos Cadastrados")
    st.dataframe(produtos_df, use_container_width=True, hide_index=True)

# ==========================================
# 3. GESTÃO DE INSUMOS (CRUD UNIFICADO DE TELA ÚNICA)
# ==========================================
elif menu == "📦 Gestão de Insumos":
    st.title("📦 Gestão de Insumos & Matéria-Prima (CRUD Unificado)")
    st.caption("Cadastre, edite ou exclua filamentos e resinas diretamente na mesma tela.")

    conn = get_db()
    insumos_df = pd.read_sql("SELECT * FROM insumos ORDER BY nome ASC", conn)
    conn.close()

    options_crud = ["➕ [NOVO INSUMO]"] + [f"✏️ {row['nome']} ({row['fabricante'] if row['fabricante'] else 'Geral'}) - R$ {row['preco_kg']:.2f}/kg" for _, row in insumos_df.iterrows()]
    selected_option = st.selectbox("Selecione uma Ação ou Insumo para Editar/Excluir:", options_crud)

    is_novo = selected_option == "➕ [NOVO INSUMO]"
    
    val_nome = ""
    val_fab = ""
    val_preco = 120.0
    val_nota = 5
    val_obs = ""
    selected_id = None

    if not is_novo:
        selected_index = options_crud.index(selected_option) - 1
        insumo_row = insumos_df.iloc[selected_index]
        selected_id = int(insumo_row['id'])
        val_nome = insumo_row['nome']
        val_fab = insumo_row['fabricante'] if insumo_row['fabricante'] else ""
        val_preco = float(insumo_row['preco_kg'])
        val_nota = int(insumo_row['avaliacao'])
        val_obs = insumo_row['observacoes'] if insumo_row['observacoes'] else ""

    st.markdown("---")
    with st.form("form_insumo_unificado"):
        st.subheader("📝 Formulário do Insumo")
        
        c1, c2 = st.columns(2)
        with c1:
            f_nome = st.text_input("Nome do Insumo (Ex: PLA Premium HT)", value=val_nome)
            f_fab = st.text_input("Fabricante (Ex: Voolt3D, 3D Fila)", value=val_fab)
        with c2:
            f_preco = st.number_input("Custo por KG (R$)", value=val_preco, step=5.0)
            f_nota = st.slider("Nota / Avaliação de Qualidade (1 a 5 ⭐)", 1, 5, val_nota)
            
        f_obs = st.text_area("Observações Técnicas", value=val_obs)

        b_col1, b_col2 = st.columns(2)
        with b_col1:
            btn_salvar = st.form_submit_button("💾 Salvar Insumo" if is_novo else "🔄 Atualizar Insumo", type="primary", use_container_width=True)
        with b_col2:
            btn_excluir = st.form_submit_button("🗑️ Excluir Insumo", use_container_width=True, disabled=is_novo)

        if btn_salvar and f_nome:
            conn = get_db()
            c = conn.cursor()
            if is_novo:
                c.execute("INSERT INTO insumos (nome, fabricante, preco_kg, avaliacao, observacoes) VALUES (?, ?, ?, ?, ?)",
                          (f_nome, f_fab, f_preco, f_nota, f_obs))
                conn.commit()
                st.success(f"✅ Insumo '{f_nome}' cadastrado!")
            else:
                c.execute("UPDATE insumos SET nome=?, fabricante=?, preco_kg=?, avaliacao=?, observacoes=? WHERE id=?",
                          (f_nome, f_fab, f_preco, f_nota, f_obs, selected_id))
                conn.commit()
                st.success(f"✅ Insumo '{f_nome}' atualizado!")
            conn.close()
            st.rerun()

        if btn_excluir and not is_novo:
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM insumos WHERE id=?", (selected_id,))
            conn.commit()
            conn.close()
            st.success("🗑️ Insumo excluído!")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Tabela Geral de Insumos Cadastrados")
    st.dataframe(insumos_df, use_container_width=True, hide_index=True)

# ==========================================
# 4. GESTÃO DE IMPRESSORAS (CRUD UNIFICADO DE TELA ÚNICA)
# ==========================================
elif menu == "🖨️ Gestão de Impressoras":
    st.title("🖨️ Gestão de Impressoras & Equipamentos (CRUD Unificado)")
    st.caption("Cadastre, edite ou exclua impressoras e parâmetros na mesma tela.")

    conn = get_db()
    imp_df = pd.read_sql("SELECT * FROM impressoras ORDER BY nome ASC", conn)
    conn.close()

    options_crud = ["➕ [NOVA IMPRESSORA]"] + [f"✏️ {row['nome']} ({row['watts']}W)" for _, row in imp_df.iterrows()]
    selected_option = st.selectbox("Selecione uma Ação ou Impressora para Editar/Excluir:", options_crud)

    is_novo = selected_option == "➕ [NOVA IMPRESSORA]"
    
    val_nome = "Bambu Lab P2S"
    val_watts = 150
    val_inv = 4200.0
    val_vida = 5000
    val_manut = 10.0
    selected_id = None

    if not is_novo:
        selected_index = options_crud.index(selected_option) - 1
        imp_row = imp_df.iloc[selected_index]
        selected_id = int(imp_row['id'])
        val_nome = imp_row['nome']
        val_watts = int(imp_row['watts'])
        val_inv = float(imp_row['investimento'])
        val_vida = int(imp_row['vida_util_h'])
        val_manut = float(imp_row['reserva_manutencao_pct'])

    st.markdown("---")
    with st.form("form_impressora_unificada"):
        st.subheader("📝 Formulário da Impressora")
        
        c1, c2 = st.columns(2)
        with c1:
            f_nome = st.text_input("Modelo da Impressora", value=val_nome if not is_novo else "")
            f_watts = st.number_input("Consumo em Watts (W)", value=val_watts)
            f_inv = st.number_input("Investimento da Máquina + Acessórios (R$)", value=val_inv)
        with c2:
            f_vida = st.number_input("Vida Útil Estimada (Horas)", value=val_vida)
            f_manut = st.number_input("Reserva para Manutenção (%)", value=val_manut)

        b_col1, b_col2 = st.columns(2)
        with b_col1:
            btn_salvar = st.form_submit_button("💾 Salvar Impressora" if is_novo else "🔄 Atualizar Impressora", type="primary", use_container_width=True)
        with b_col2:
            btn_excluir = st.form_submit_button("🗑️ Excluir Impressora", use_container_width=True, disabled=is_novo)

        if btn_salvar and f_nome:
            conn = get_db()
            c = conn.cursor()
            if is_novo:
                c.execute("INSERT INTO impressoras (nome, watts, investimento, vida_util_h, reserva_manutencao_pct) VALUES (?, ?, ?, ?, ?)",
                          (f_nome, f_watts, f_inv, f_vida, f_manut))
                conn.commit()
                st.success(f"✅ Impressora '{f_nome}' cadastrada!")
            else:
                c.execute("UPDATE impressoras SET nome=?, watts=?, investimento=?, vida_util_h=?, reserva_manutencao_pct=? WHERE id=?",
                          (f_nome, f_watts, f_inv, f_vida, f_manut, selected_id))
                conn.commit()
                st.success(f"✅ Impressora '{f_nome}' atualizada!")
            conn.close()
            st.rerun()

        if btn_excluir and not is_novo:
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM impressoras WHERE id=?", (selected_id,))
            conn.commit()
            conn.close()
            st.success("🗑️ Impressora excluída!")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Tabela Geral de Impressoras Cadastradas")
    st.dataframe(imp_df, use_container_width=True, hide_index=True)

# ==========================================
# 5. HISTÓRICO DE ORÇAMENTOS (CRUD UNIFICADO DE TELA ÚNICA)
# ==========================================
elif menu == "📜 Histórico de Orçamentos":
    st.title("📜 Histórico de Orçamentos & Lotes (CRUD Unificado)")
    st.caption("Consulte, altere ou remova fichas de produção gravadas.")

    conn = get_db()
    projetos_df = pd.read_sql("SELECT * FROM projetos ORDER BY id DESC", conn)
    conn.close()

    if projetos_df.empty:
        st.info("Nenhum orçamento salvo no histórico.")
    else:
        options_crud = [f"📋 ID {row['id']} — {row['nome_projeto']} ({row['data']})" for _, row in projetos_df.iterrows()]
        selected_option = st.selectbox("Selecione um Registro do Histórico para Editar ou Excluir:", options_crud)

        selected_index = options_crud.index(selected_option)
        proj_sel = projetos_df.iloc[selected_index]
        selected_id = int(proj_sel['id'])

        st.markdown("---")
        with st.form("form_projeto_unificado"):
            st.subheader(f"📝 Editando Registro: {proj_sel['nome_projeto']}")

            c1, c2 = st.columns(2)
            with c1:
                e_nome = st.text_input("Nome do Projeto", value=proj_sel['nome_projeto'])
                e_unidades = st.number_input("Unidades no Lote", value=int(proj_sel['unidades_lote']), min_value=1)
                e_peso = st.number_input("Peso Modelo (g)", value=float(proj_sel['peso_unit_g']))
                e_peso_sup = st.number_input("Peso Suporte (g)", value=float(proj_sel['peso_suporte_g']) if 'peso_suporte_g' in proj_sel and proj_sel['peso_suporte_g'] is not None else 0.0)
                e_preco_kg = st.number_input("Custo/KG do Material (R$)", value=float(proj_sel['preco_kg_usado']))

            with c2:
                e_vh = st.number_input("Valor Hora Mão de Obra (R$/h)", value=float(proj_sel['valor_hora_mo']))
                e_emb = st.number_input("Embalagem Unitária (R$)", value=float(proj_sel['embalagem_unit']))
                e_margem = st.number_input("Margem de Lucro (%)", value=float(proj_sel['margem_alvo_pct']))
                e_preco_praticado = st.number_input("Preço Praticado Final Unitário (R$)", value=float(proj_sel['preco_praticado_unit']))

            b_col1, b_col2 = st.columns(2)
            with b_col1:
                btn_update = st.form_submit_button("🔄 Salvar Alterações", type="primary", use_container_width=True)
            with b_col2:
                btn_delete = st.form_submit_button("🗑️ Excluir Registro do Histórico", use_container_width=True)

            if btn_update:
                conn = get_db()
                c = conn.cursor()
                c.execute("""
                    UPDATE projetos SET
                        nome_projeto = ?, unidades_lote = ?, peso_unit_g = ?, peso_suporte_g = ?,
                        preco_kg_usado = ?, valor_hora_mo = ?,
                        embalagem_unit = ?, margem_alvo_pct = ?, preco_praticado_unit = ?
                    WHERE id = ?
                """, (e_nome, e_unidades, e_peso, e_peso_sup, e_preco_kg, e_vh, e_emb, e_margem, e_preco_praticado, selected_id))
                conn.commit()
                conn.close()
                st.success("✅ Registro atualizado!")
                st.rerun()

            if btn_delete:
                conn = get_db()
                c = conn.cursor()
                c.execute("DELETE FROM projetos WHERE id = ?", (selected_id,))
                conn.commit()
                conn.close()
                st.success("🗑️ Registro excluído!")
                st.rerun()

        st.markdown("---")
        st.subheader("📋 Tabela Geral de Orçamentos Salvos")
        st.dataframe(projetos_df[['id', 'nome_projeto', 'data', 'unidades_lote', 'insumo_nome', 'custo_total_lote', 'preco_sugerido_unit', 'preco_praticado_unit']], use_container_width=True, hide_index=True)
