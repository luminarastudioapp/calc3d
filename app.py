import streamlit as st
import pandas as pd
import sqlite3
import re
from datetime import datetime

st.set_page_config(page_title="3D Calc Pro - Gestão Completa", page_icon="🎲", layout="wide")

# Estilo CSS personalizado
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .stButton>button { border-radius: 8px; font-weight: 600; }
    .card-box { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS LOCAL (SQLITE) PARA PERSISTÊNCIA TOTAL E EDIÇÃO ---
DB_NAME = "3d_gestao_completa.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite():
    conn = get_db()
    c = conn.cursor()
    
    # Tabela de Insumos (Material + Fabricante + Nota)
    c.execute('''
        CREATE TABLE IF NOT EXISTS insumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            fabricante TEXT,
            preco_kg REAL NOT NULL,
            avaliacao INTEGER DEFAULT 5,
            observacoes TEXT
        )
    ''')
    
    # Tabela de Impressoras
    c.execute('''
        CREATE TABLE IF NOT EXISTS impressoras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            watts REAL NOT NULL,
            investimento REAL DEFAULT 0,
            vida_util_h REAL DEFAULT 4000,
            reserva_manutencao_pct REAL DEFAULT 10
        )
    ''')
    
    # Tabela de Ficha Técnica / Projetos
    c.execute('''
        CREATE TABLE IF NOT EXISTS projetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_projeto TEXT NOT NULL,
            data TEXT,
            unidades_lote INTEGER DEFAULT 1,
            insumo_nome TEXT,
            preco_kg_usado REAL,
            peso_unit_g REAL,
            impressora_nome TEXT,
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
    ''')
    
    # Inserir dados padrões se estiver vazio
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
            ("Ender 3 V2", 130, 1800.0, 4000, 10.0),
            ("Bambu Lab A1", 150, 3600.0, 5000, 10.0),
            ("Bambu Lab X1C", 350, 11000.0, 6000, 12.0),
            ("Elegoo Mars 3 (Resina)", 60, 2500.0, 3000, 15.0)
        ])
        
    conn.commit()
    conn.close()

init_sqlite()

# --- NAVEGAÇÃO PRINCIPAL ---
st.sidebar.title("🎲 3D Calc Pro")
st.sidebar.caption("Sistema de Gestão & Ficha de Produção")

menu = st.sidebar.radio("Navegação", [
    "🧮 Nova Ficha de Produção",
    "📜 Projetos Salvos (Visualizar & Editar)",
    "📦 Cadastro de Insumos & Fabricantes",
    "🖨️ Cadastro de Impressoras & Máquinas"
])

# ==========================================
# 1. NOVA FICHA DE PRODUÇÃO (CÁLCULO COMPLETO)
# ==========================================
if menu == "🧮 Nova Ficha de Produção":
    st.title("🧮 Ficha de Produção & Precificação Completa")
    st.caption("Substitui a planilha técnica com cálculo de material, máquinas, mão de obra e impostos.")

    conn = get_db()
    insumos_df = pd.read_sql("SELECT * FROM insumos", conn)
    impressoras_df = pd.read_sql("SELECT * FROM impressoras", conn)
    conn.close()

    with st.form("form_calculadora"):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.subheader("1. Dados do Projeto e Lote")
            nome_proj = st.text_input("Nome do Produto / Projeto", value="Vaso Geométrico 3D")
            unidades_lote = st.number_input("Unidades Aprovadas no Lote", min_value=1, value=1, step=1)
            
            # Insumo
            options_insumos = [f"{row['nome']} ({row['fabricante'] if row['fabricante'] else 'Geral'}) - R$ {row['preco_kg']:.2f}/kg" for _, row in insumos_df.iterrows()]
            sel_insumo_idx = st.selectbox("Selecione o Insumo", range(len(options_insumos)), format_func=lambda x: options_insumos[x])
            insumo_sel = insumos_df.iloc[sel_insumo_idx]
            
            custo_kg_materia = st.number_input("Custo do KG do Insumo (R$)", value=float(insumo_sel['preco_kg']))
            peso_unit_g = st.number_input("Peso Unitário Real (g)", value=85.0, step=5.0)
            taxa_desperdicio = st.number_input("Taxa de Perdas / Desperdício (%)", value=5.0, step=1.0)

        with col_p2:
            st.subheader("2. Impressora & Energia")
            options_imp = [f"{row['nome']} ({row['watts']}W)" for _, row in impressoras_df.iterrows()]
            sel_imp_idx = st.selectbox("Selecione a Impressora", range(len(options_imp)), format_func=lambda x: options_imp[x])
            imp_sel = impressoras_df.iloc[sel_imp_idx]
            
            tempo_h = st.number_input("Tempo Total de Impressão do Lote (Horas)", value=4.5, step=0.5)
            tarifa_kwh = st.number_input("Tarifa de Energia (R$ / kWh)", value=1.25, step=0.05)
            reserva_manutencao = st.number_input("Reserva para Manutenção (%)", value=float(imp_sel['reserva_manutencao_pct']), step=1.0)

        st.markdown("---")
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            st.subheader("3. Mão de Obra & Homem-Hora")
            valor_hora_mo = st.number_input("Valor da Hora de Trabalho (R$/h)", value=30.0, step=5.0)
            
            col_mo1, col_mo2 = st.columns(2)
            with col_mo1:
                horas_modelagem = st.number_input("Horas de Modelagem/3D", value=1.0, step=0.5)
                qtd_amortizar = st.number_input("Qtd. de Peças para Amortizar 3D", value=10, min_value=1)
            with col_mo2:
                horas_preparacao = st.number_input("Preparação/Fatiamento (h)", value=0.2, step=0.1)
                horas_pos_processo = st.number_input("Pós-processamento (h)", value=0.3, step=0.1)
                horas_admin = st.number_input("Embalagem/Admin (h)", value=0.2, step=0.1)

        with col_m2:
            st.subheader("4. Custos Adicionais, Taxas & Margem")
            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                embalagem_unit = st.number_input("Embalagem por Unidade (R$)", value=2.50, step=0.5)
                consumiveis_lote = st.number_input("Consumíveis do Lote (R$)", value=1.50, step=0.5)
            with col_ex2:
                outros_custos = st.number_input("Outros Custos do Lote (R$)", value=0.0, step=1.0)
                desc_outros = st.text_input("Descrição dos Outros Custos", value="")

            taxas_venda = st.number_input("Taxas de Venda / Plataforma (%)", value=12.0, step=1.0)
            impostos_pct = st.number_input("Impostos (%)", value=6.0, step=1.0)
            margem_alvo = st.number_input("Margem de Lucro Alvo (%)", value=40.0, step=5.0)

        btn_calcular = st.form_submit_button("📊 Processar Ficha de Produção", type="primary", use_container_width=True)

    # CÁLCULOS TÉCNICOS E FINANCEIROS
    peso_total_g = (peso_unit_g * unidades_lote) * (1 + (taxa_desperdicio / 100))
    custo_material_total = (peso_total_g / 1000) * custo_kg_materia
    
    custo_energia_total = (imp_sel['watts'] / 1000) * tempo_h * tarifa_kwh
    custo_depreciacao_h = (imp_sel['investimento'] / max(1, imp_sel['vida_util_h']))
    custo_maquina_total = (custo_depreciacao_h * tempo_h) * (1 + (reserva_manutencao / 100))
    
    # Mão de obra do lote
    custo_modelagem_alocado = (horas_modelagem * valor_hora_mo) / qtd_amortizar * unidades_lote
    horas_operacionais_lote = horas_preparacao + horas_pos_processo + horas_admin
    custo_mo_operacional = horas_operacionais_lote * valor_hora_mo
    custo_mo_total = custo_modelagem_alocado + custo_mo_operacional
    
    # Extras
    custo_extras_total = (embalagem_unit * unidades_lote) + consumiveis_lote + outros_custos
    
    # Custo Direto Total
    custo_direto_lote = custo_material_total + custo_energia_total + custo_maquina_total + custo_mo_total + custo_extras_total
    custo_unitario = custo_direto_lote / unidades_lote
    
    # Formação de Preço (considerando taxas sobre a venda final)
    # Preco_Sugerido = Custo_Direto / (1 - (Taxas + Impostos + Margem)/100)
    percentual_deducoes = (taxas_venda + impostos_pct + margem_alvo) / 100
    if percentual_deducoes >= 1.0:
        percentual_deducoes = 0.90 # Evitar divisão por zero/negativo
        
    preco_sugerido_lote = custo_direto_lote / (1 - percentual_deducoes)
    preco_sugerido_unit = preco_sugerido_lote / unidades_lote
    lucro_estimado_lote = preco_sugerido_lote * (margem_alvo / 100)

    st.markdown("---")
    st.subheader("📌 Resumo Consolidado do Lote")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Custo Direto do Lote", f"R$ {custo_direto_lote:.2f}", f"R$ {custo_unitario:.2f} / un")
    c2.metric("🏷️ Preço Sugerido (Unidade)", f"R$ {preco_sugerido_unit:.2f}", f"Margem: {margem_alvo}%")
    c3.metric("📊 Faturamento do Lote", f"R$ {preco_sugerido_lote:.2f}")
    c4.metric("📈 Lucro Limpo do Lote", f"R$ {lucro_estimado_lote:.2f}")

    # Detalhamento de Custos
    df_resumo = pd.DataFrame({
        "Categoria de Custo": ["Material (Com Perdas)", "Energia & Máquina", "Mão de Obra (Modelagem + Operação)", "Embalagens & Extras"],
        "Valor Total Lote (R$)": [custo_material_total, custo_energia_total + custo_maquina_total, custo_mo_total, custo_extras_total],
        "Custo por Unidade (R$)": [custo_material_total/unidades_lote, (custo_energia_total + custo_maquina_total)/unidades_lote, custo_mo_total/unidades_lote, custo_extras_total/unidades_lote]
    })
    st.dataframe(df_resumo.style.format({"Valor Total Lote (R$)": "R$ {:.2f}", "Custo por Unidade (R$)": "R$ {:.2f}"}), use_container_width=True, hide_index=True)

    # Salvar Projeto no Banco
    if st.button("💾 Salvar Ficha de Produção no Banco de Dados", type="primary", use_container_width=True):
        conn = get_db()
        c = conn.cursor()
        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
        c.execute('''
            INSERT INTO projetos (
                nome_projeto, data, unidades_lote, insumo_nome, preco_kg_usado, peso_unit_g,
                impressora_nome, tempo_impressao_h, tarifa_kwh, valor_hora_mo, horas_modelagem,
                qtd_amortizar_modelagem, horas_preparacao, horas_pos_processo, horas_admin,
                embalagem_unit, consumiveis_lote, outros_custos_lote, descricao_outros,
                taxa_desperdicio_pct, taxas_venda_pct, impostos_pct, margem_alvo_pct,
                custo_total_lote, custo_unitario, preco_sugerido_unit, preco_praticado_unit, lucro_lote
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            nome_proj, data_atual, unidades_lote, insumo_sel['nome'], custo_kg_materia, peso_unit_g,
            imp_sel['nome'], tempo_h, tarifa_kwh, valor_hora_mo, horas_modelagem,
            qtd_amortizar, horas_preparacao, horas_pos_processo, horas_admin,
            embalagem_unit, consumiveis_lote, outros_custos, desc_outros,
            taxa_desperdicio, taxas_venda, impostos_pct, margem_alvo,
            custo_direto_lote, custo_unitario, preco_sugerido_unit, preco_sugerido_unit, lucro_estimado_lote
        ))
        conn.commit()
        conn.close()
        st.success(f"✅ Projeto '{nome_proj}' salvo no banco de dados com sucesso!")

# ==========================================
# 2. PROJETOS SALVOS (VISUALIZAR & EDITAR)
# ==========================================
elif menu == "📜 Projetos Salvos (Visualizar & Editar)":
    st.title("📜 Projetos Salvos & Fichas de Produção")
    st.caption("Consulte, altere ou corrija dados de qualquer projeto cadastrado.")

    conn = get_db()
    projetos_df = pd.read_sql("SELECT * FROM projetos ORDER BY id DESC", conn)
    conn.close()

    if projetos_df.empty:
        st.info("Nenhum projeto salvo ainda.")
    else:
        st.subheader("Selecione um Projeto para Visualizar ou Editar")
        
        proj_list = [f"ID {row['id']} - {row['nome_projeto']} ({row['data']})" for _, row in projetos_df.iterrows()]
        sel_proj_idx = st.selectbox("Escolha o Projeto:", range(len(proj_list)), format_func=lambda x: proj_list[x])
        proj_sel = projetos_df.iloc[sel_proj_idx]

        st.markdown("---")
        st.markdown(f"### ✏️ Editando: **{proj_sel['nome_projeto']}**")

        with st.form("form_editar_projeto"):
            e_col1, e_col2 = st.columns(2)
            with e_col1:
                e_nome = st.text_input("Nome do Projeto", value=proj_sel['nome_projeto'])
                e_unidades = st.number_input("Unidades no Lote", value=int(proj_sel['unidades_lote']), min_value=1)
                e_peso = st.number_input("Peso Unitário (g)", value=float(proj_sel['peso_unit_g']))
                e_tempo = st.number_input("Tempo Total (h)", value=float(proj_sel['tempo_impressao_h']))
                e_preco_kg = st.number_input("Custo/KG do Material (R$)", value=float(proj_sel['preco_kg_usado']))

            with e_col2:
                e_vh = st.number_input("Valor da Hora Mão de Obra (R$/h)", value=float(proj_sel['valor_hora_mo']))
                e_emb = st.number_input("Embalagem Unitária (R$)", value=float(proj_sel['embalagem_unit']))
                e_margem = st.number_input("Margem de Lucro (%)", value=float(proj_sel['margem_alvo_pct']))
                e_preco_praticado = st.number_input("Preço Praticado Final Unitário (R$)", value=float(proj_sel['preco_praticado_unit']))

            btn_update = st.form_submit_button("🔄 Atualizar Dados do Projeto", type="primary")
            
            if btn_update:
                conn = get_db()
                c = conn.cursor()
                c.execute('''
                    UPDATE projetos SET
                        nome_projeto = ?, unidades_lote = ?, peso_unit_g = ?,
                        tempo_impressao_h = ?, preco_kg_usado = ?, valor_hora_mo = ?,
                        embalagem_unit = ?, margem_alvo_pct = ?, preco_praticado_unit = ?
                    WHERE id = ?
                ''', (e_nome, e_unidades, e_peso, e_tempo, e_preco_kg, e_vh, e_emb, e_margem, e_preco_praticado, int(proj_sel['id'])))
                conn.commit()
                conn.close()
                st.success("✅ Dados do projeto atualizados com sucesso!")
                st.rerun()

        st.markdown("---")
        st.subheader("📋 Tabela Geral de Projetos Registrados")
        st.dataframe(projetos_df[['id', 'nome_projeto', 'data', 'unidades_lote', 'insumo_nome', 'custo_total_lote', 'preco_sugerido_unit', 'preco_praticado_unit']], use_container_width=True, hide_index=True)

# ==========================================
# 3. CADASTRO DE INSUMOS (FABRICANTE + NOTA)
# ==========================================
elif menu == "📦 Cadastro de Insumos & Fabricantes":
    st.title("📦 Insumos & Matéria-Prima")
    st.caption("Cadastre e edite filamentos, resinas, fabricantes e avaliações de qualidade.")

    conn = get_db()
    insumos_df = pd.read_sql("SELECT * FROM insumos", conn)
    conn.close()

    st.subheader("Lista de Insumos Cadastrados")
    st.dataframe(insumos_df, use_container_width=True, hide_index=True)

    col_i1, col_i2 = st.columns(2)

    with col_i1:
        st.markdown("### ➕ Cadastrar Novo Insumo")
        with st.form("form_add_insumo"):
            add_nome = st.text_input("Nome do Insumo (Ex: PLA Premium HT)")
            add_fab = st.text_input("Fabricante (Ex: 3D Fila, Voolt3D)")
            add_preco = st.number_input("Custo por KG (R$)", min_value=0.0, value=120.0, step=5.0)
            add_nota = st.slider("Nota / Avaliação de Qualidade (1 a 5 ⭐)", 1, 5, 5)
            add_obs = st.text_area("Observações Técnicas", value="")
            btn_insumo = st.form_submit_button("Salvar Insumo")

            if btn_insumo and add_nome:
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO insumos (nome, fabricante, preco_kg, avaliacao, observacoes) VALUES (?, ?, ?, ?, ?)",
                          (add_nome, add_fab, add_preco, add_nota, add_obs))
                conn.commit()
                conn.close()
                st.success(f"Insumo '{add_nome}' cadastrado!")
                st.rerun()

    with col_i2:
        st.markdown("### ✏️ Editar Insumo Existente")
        if not insumos_df.empty:
            sel_edit_insumo = st.selectbox("Selecione para Editar:", insumos_df['nome'].tolist())
            insumo_to_edit = insumos_df[insumos_df['nome'] == sel_edit_insumo].iloc[0]

            with st.form("form_edit_insumo"):
                ed_nome = st.text_input("Nome do Insumo", value=insumo_to_edit['nome'])
                ed_fab = st.text_input("Fabricante", value=insumo_to_edit['fabricante'] if insumo_to_edit['fabricante'] else "")
                ed_preco = st.number_input("Preço / KG (R$)", value=float(insumo_to_edit['preco_kg']))
                ed_nota = st.slider("Nota / Avaliação", 1, 5, int(insumo_to_edit['avaliacao']))
                ed_obs = st.text_area("Observações", value=insumo_to_edit['observacoes'] if insumo_to_edit['observacoes'] else "")
                btn_up_insumo = st.form_submit_button("Atualizar Insumo")

                if btn_up_insumo:
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("UPDATE insumos SET nome=?, fabricante=?, preco_kg=?, avaliacao=?, observacoes=? WHERE id=?",
                              (ed_nome, ed_fab, ed_preco, ed_nota, ed_obs, int(insumo_to_edit['id'])))
                    conn.commit()
                    conn.close()
                    st.success(f"Insumo '{ed_nome}' atualizado!")
                    st.rerun()

# ==========================================
# 4. CADASTRO DE IMPRESSORAS
# ==========================================
elif menu == "🖨️ Cadastro de Impressoras & Máquinas":
    st.title("🖨️ Impressoras & Equipamentos")
    st.caption("Cadastre o consumo, investimento e vida útil de cada máquina.")

    conn = get_db()
    imp_df = pd.read_sql("SELECT * FROM impressoras", conn)
    conn.close()

    st.dataframe(imp_df, use_container_width=True, hide_index=True)

    st.markdown("### ➕ Cadastrar / Editar Impressora")
    with st.form("form_imp"):
        imp_nome = st.text_input("Modelo da Impressora", value="Bambu Lab P1S")
        imp_watts = st.number_input("Consumo em Watts (W)", value=200)
        imp_inv = st.number_input("Investimento da Máquina + Acessórios (R$)", value=4500.0)
        imp_vida = st.number_input("Vida Útil Estimada (Horas)", value=5000)
        imp_manut = st.number_input("Reserva para Manutenção (%)", value=10.0)
        btn_imp_save = st.form_submit_button("Salvar Impressora")

        if btn_imp_save and imp_nome:
            conn = get_db()
            c = conn.cursor()
            c.execute('''
                INSERT INTO impressoras (nome, watts, investimento, vida_util_h, reserva_manutencao_pct)
                VALUES (?, ?, ?, ?, ?)
            ''', (imp_nome, imp_watts, imp_inv, imp_vida, imp_manut))
            conn.commit()
            conn.close()
            st.success(f"Impressora '{imp_nome}' salva com sucesso!")
            st.rerun()
