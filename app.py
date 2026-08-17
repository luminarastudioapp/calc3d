import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
import base64
import json

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS (SQLite) ---
DB_NAME = "3d_calc_pro.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Módulo de Cadastros
    cursor.execute('''CREATE TABLE IF NOT EXISTS materiais (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, preco_kg REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS impressoras (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, watts REAL, preco_maquina REAL, vida_util_h REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS catalogo_pecas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, fotos_b64 TEXT)''')
    
    # Cria a tabela base se não existir
    cursor.execute('''CREATE TABLE IF NOT EXISTS historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nome_projeto TEXT, material TEXT, peso_g REAL, tempo_h REAL, 
        custo_total REAL, preco_venda REAL, data TEXT
    )''')
    
    # --- SCRIPT DE MIGRAÇÃO (Atualiza bancos antigos automaticamente) ---
    try:
        cursor.execute("ALTER TABLE historico ADD COLUMN memoria_calculo TEXT")
    except sqlite3.OperationalError:
        pass # Ignora o erro se a coluna já existir

    try:
        cursor.execute("ALTER TABLE historico ADD COLUMN foto_principal TEXT")
    except sqlite3.OperationalError:
        pass # Ignora o erro se a coluna já existir
    # -------------------------------------------------------------------

    # Dados padrão para evitar banco vazio
    cursor.execute("SELECT COUNT(*) FROM materiais")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO materiais (nome, preco_kg) VALUES (?, ?)", [("PLA", 99.0), ("PETG", 119.0)])
        
    cursor.execute("SELECT COUNT(*) FROM impressoras")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO impressoras (nome, watts, preco_maquina, vida_util_h) VALUES (?, ?, ?, ?)", [
            ("Ender 3", 130.0, 1800.0, 4000.0), ("Bambu Lab A1 + AMS Lite", 150.0, 4200.0, 5000.0)
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

# --- 2. ESTILOS DE IMPRESSÃO (LANDSCAPE & CLEAN) ---
st.set_page_config(page_title="3D Calc Pro", page_icon="🎲", layout="wide")

st.markdown("""
    <style>
    @media print {
        @page { size: landscape; margin: 15mm; }
        section[data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .stButton, .stDownloadButton, .stFileUploader, .stSelectbox { display: none !important; }
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
    "🧮 Módulo 2: PROJETOS", 
    "📜 Módulo 3: RELATÓRIO"
])
kwh_cost = st.sidebar.number_input("Custo da Energia Elétrica (R$ / kWh)", value=1.25, step=0.05)

# =====================================================================
# MÓDULO 1: CADASTROS (CRUD COMPLETO COM FEEDBACK VISUAL)
# =====================================================================
if menu == "⚙️ Módulo 1: CADASTROS":
    st.title("⚙️ Cadastros Base do Sistema")
    tab_pecas, tab_mat, tab_imp = st.tabs(["🧩 Peças e Produtos", "📦 Materiais", "🖨️ Impressoras"])
    
    # --- CRUD: CATÁLOGO DE PEÇAS ---
    with tab_pecas:
        conn = get_db_connection()
        cat_df = pd.read_sql("SELECT id, nome as 'Nome' FROM catalogo_pecas", conn)
        st.dataframe(cat_df, use_container_width=True, hide_index=True)
        
        st.markdown("### 📝 Gerenciar Catálogo")
        acao_peca = st.radio("Ação", ["Novo", "Editar Nome", "Excluir"], horizontal=True, key="rad_peca")
        
        if acao_peca == "Novo":
            with st.form("form_peca", clear_on_submit=True):
                nome_peca = st.text_input("Nome da Peça / Produto")
                fotos_upload = st.file_uploader("Anexar Fotos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
                if st.form_submit_button("Salvar Peça") and nome_peca:
                    fotos_b64 = [converter_imagem(f) for f in fotos_upload]
                    fotos_json = json.dumps(fotos_b64)
                    try:
                        conn.cursor().execute("INSERT INTO catalogo_pecas (nome, fotos_b64) VALUES (?, ?)", (nome_peca, fotos_json))
                        conn.commit()
                        st.success("✅ Cadastrado com sucesso!")
                        import time; time.sleep(1.5)
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Já existe uma peça com este nome.")
                        
        elif acao_peca == "Editar Nome":
            if not cat_df.empty:
                peca_ed = st.selectbox("Selecione a Peça", cat_df['Nome'].tolist(), key="sel_ed_peca")
                peca_id = int(cat_df[cat_df['Nome'] == peca_ed]['id'].values[0])
                with st.form("form_ed_peca"):
                    novo_nome = st.text_input("Novo Nome", value=peca_ed)
                    if st.form_submit_button("Atualizar"):
                        conn.cursor().execute("UPDATE catalogo_pecas SET nome=? WHERE id=?", (novo_nome, peca_id))
                        conn.commit()
                        st.success("✅ Alterado com sucesso!")
                        import time; time.sleep(1.5)
                        st.rerun()
                        
        elif acao_peca == "Excluir":
            if not cat_df.empty:
                peca_del = st.selectbox("Selecione a Peça", cat_df['Nome'].tolist(), key="sel_del_peca")
                peca_id = int(cat_df[cat_df['Nome'] == peca_del]['id'].values[0])
                if st.button("🚨 Confirmar Exclusão"):
                    conn.cursor().execute("DELETE FROM catalogo_pecas WHERE id=?", (peca_id,))
                    conn.commit()
                    st.success("✅ Excluído com sucesso!")
                    import time; time.sleep(1.5)
                    st.rerun()
        conn.close()

    # --- CRUD: MATERIAIS ---
    with tab_mat:
        conn = get_db_connection()
        materiais_df = pd.read_sql("SELECT id, nome as 'Nome', preco_kg as 'Preço/KG (R$)' FROM materiais", conn)
        st.dataframe(materiais_df, use_container_width=True, hide_index=True)

        st.markdown("### 📝 Gerenciar Materiais")
        acao_mat = st.radio("Ação", ["Novo", "Editar", "Excluir"], horizontal=True, key="rad_mat")
        
        if acao_mat == "Novo":
            with st.form("form_novo_mat", clear_on_submit=True):
                nome_mat = st.text_input("Nome do Material")
                preco_mat = st.number_input("Custo Unitário (R$/KG)", min_value=0.0, value=130.0)
                if st.form_submit_button("Salvar") and nome_mat:
                    conn.cursor().execute("INSERT INTO materiais (nome, preco_kg) VALUES (?, ?)", (nome_mat, preco_mat))
                    conn.commit()
                    st.success("✅ Cadastrado com sucesso!")
                    import time; time.sleep(1.5)
                    st.rerun()
                    
        elif acao_mat == "Editar":
            if not materiais_df.empty:
                mat_ed = st.selectbox("Selecione para Editar", materiais_df['Nome'].tolist(), key="sel_ed_mat")
                mat_id = int(materiais_df[materiais_df['Nome'] == mat_ed]['id'].values[0])
                mat_preco_atual = float(materiais_df[materiais_df['Nome'] == mat_ed]['Preço/KG (R$)'].values[0])
                
                with st.form("form_edita_mat"):
                    novo_nome = st.text_input("Nome", value=mat_ed)
                    novo_preco = st.number_input("Preço/KG", value=mat_preco_atual)
                    if st.form_submit_button("Atualizar"):
                        conn.cursor().execute("UPDATE materiais SET nome=?, preco_kg=? WHERE id=?", (novo_nome, novo_preco, mat_id))
                        conn.commit()
                        st.success("✅ Alterado com sucesso!")
                        import time; time.sleep(1.5)
                        st.rerun()
                        
        elif acao_mat == "Excluir":
             if not materiais_df.empty:
                mat_del = st.selectbox("Selecione para Excluir", materiais_df['Nome'].tolist(), key="sel_del_mat")
                mat_id = int(materiais_df[materiais_df['Nome'] == mat_del]['id'].values[0])
                if st.button("🚨 Confirmar Exclusão", key="btn_del_mat"):
                    conn.cursor().execute("DELETE FROM materiais WHERE id=?", (mat_id,))
                    conn.commit()
                    st.success("✅ Excluído com sucesso!")
                    import time; time.sleep(1.5)
                    st.rerun()
        conn.close()

    # --- CRUD: IMPRESSORAS ---
    with tab_imp:
        conn = get_db_connection()
        impressoras_df = pd.read_sql("SELECT id, nome as 'Modelo', watts as 'Consumo (W)', preco_maquina as 'Valor (R$)', vida_util_h as 'Vida Útil (h)' FROM impressoras", conn)
        st.dataframe(impressoras_df, use_container_width=True, hide_index=True)

        st.markdown("### 📝 Gerenciar Impressoras")
        acao_imp = st.radio("Ação", ["Nova", "Editar", "Excluir"], horizontal=True, key="rad_imp")
        
        if acao_imp == "Nova":
            with st.form("form_nova_imp", clear_on_submit=True):
                nome_imp = st.text_input("Marca | Modelo da Impressora")
                watts_imp = st.number_input("Consumo (em W)", value=350)
                preco_imp = st.number_input("Custo do Equipamento (R$)", value=4500.0)
                vida_imp = st.number_input("Vida Útil Estimada (h)", value=5000)
                if st.form_submit_button("Salvar Máquina") and nome_imp:
                    conn.cursor().execute("INSERT INTO impressoras (nome, watts, preco_maquina, vida_util_h) VALUES (?, ?, ?, ?)", (nome_imp, watts_imp, preco_imp, vida_imp))
                    conn.commit()
                    st.success("✅ Cadastrado com sucesso!")
                    import time; time.sleep(1.5)
                    st.rerun()
                    
        elif acao_imp == "Editar":
            if not impressoras_df.empty:
                imp_ed = st.selectbox("Selecione para Editar", impressoras_df['Modelo'].tolist(), key="sel_ed_imp")
                row_imp = impressoras_df[impressoras_df['Modelo'] == imp_ed].iloc[0]
                imp_id = int(row_imp['id'])
                
                with st.form("form_edita_imp"):
                    novo_nome = st.text_input("Modelo", value=row_imp['Modelo'])
                    novo_watts = st.number_input("Consumo (W)", value=float(row_imp['Consumo (W)']))
                    novo_preco = st.number_input("Valor (R$)", value=float(row_imp['Valor (R$)']))
                    nova_vida = st.number_input("Vida Útil (h)", value=float(row_imp['Vida Útil (h)']))
                    
                    if st.form_submit_button("Atualizar"):
                        conn.cursor().execute("UPDATE impressoras SET nome=?, watts=?, preco_maquina=?, vida_util_h=? WHERE id=?", 
                                              (novo_nome, novo_watts, novo_preco, nova_vida, imp_id))
                        conn.commit()
                        st.success("✅ Alterado com sucesso!")
                        import time; time.sleep(1.5)
                        st.rerun()
                        
        elif acao_imp == "Excluir":
             if not impressoras_df.empty:
                imp_del = st.selectbox("Selecione para Excluir", impressoras_df['Modelo'].tolist(), key="sel_del_imp")
                imp_id = int(impressoras_df[impressoras_df['Modelo'] == imp_del]['id'].values[0])
                if st.button("🚨 Confirmar Exclusão", key="btn_del_imp"):
                    conn.cursor().execute("DELETE FROM impressoras WHERE id=?", (imp_id,))
                    conn.commit()
                    st.success("✅ Excluído com sucesso!")
                    import time; time.sleep(1.5)
                    st.rerun()
        conn.close()

# =====================================================================
# MÓDULO 2: PROJETOS (Calculadora)
# =====================================================================
elif menu == "🧮 Módulo 2: PROJETOS":
    st.title("🧮 Definição e Cálculo de Projeto")
    
    conn = get_db_connection()
    materiais_df = pd.read_sql("SELECT * FROM materiais", conn)
    impressoras_df = pd.read_sql("SELECT * FROM impressoras", conn)
    pecas_df = pd.read_sql("SELECT * FROM catalogo_pecas", conn)
    
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("📋 Parâmetros da Peça")
        
        # 1. Opção neutra como padrão para esconder o formulário inicialmente
        opcoes_pecas = ["-- Selecione uma opção --", "-- Digitar Nome Manualmente --"] + pecas_df['nome'].tolist()
        selecao_peca = st.selectbox("Selecionar Peça do Catálogo", opcoes_pecas)
        
    # 2. Só exibe o restante da tela SE uma opção válida for escolhida
    if selecao_peca != "-- Selecione uma opção --":
        with col1:
            if selecao_peca == "-- Digitar Nome Manualmente --":
                proj_name = st.text_input("Nome da Peça", placeholder="Ex: Vaso Geométrico")
                foto_base = None
            else:
                proj_name = selecao_peca
                # Recupera a primeira foto do catálogo para vincular ao orçamento
                row_peca = pecas_df[pecas_df['nome'] == selecao_peca].iloc[0]
                fotos_lista = json.loads(row_peca['fotos_b64'])
                foto_base = fotos_lista[0] if len(fotos_lista) > 0 else None
                if foto_base:
                    st.image(base64.b64decode(foto_base), width=150, caption="Foto do Catálogo Vinculada")

            qty = st.number_input("Quantidade de Peças", min_value=1, value=1)
            printer_selected = st.selectbox("Tipo de impressora", impressoras_df['nome'].tolist())
            printer_info = impressoras_df[impressoras_df['nome'] == printer_selected].iloc[0]

            mat_selected = st.selectbox("Tipo de filamento", materiais_df['nome'].tolist())
            mat_info = materiais_df[materiais_df['nome'] == mat_selected].iloc[0]
            mat_cost_per_kg = st.number_input("Custo do filamento (R$ por Kilo)", value=float(mat_info['preco_kg']))

            col_w, col_t = st.columns(2)
            # 3. Valores padrão zerados para evitar cálculos fantasmas
            with col_w: weight_g = st.number_input("Peso total da peça (g)", min_value=0.0, value=0.0)
            with col_t:
                hours = st.number_input("Tempo (h)", min_value=0, value=0)
                mins = st.number_input("Tempo (min)", min_value=0, max_value=59, value=0)

            markup = st.slider("Margem de Lucro (%)", 20, 300, 100, step=10)

        # Lógica de cálculo
        total_hours = hours + (mins / 60)
        cost_mat = (weight_g / 1000) * mat_cost_per_kg
        cost_energy = (printer_info['watts'] / 1000) * total_hours * kwh_cost
        cost_depr = (printer_info['preco_maquina'] / max(1, printer_info['vida_util_h'])) * total_hours
        
        total_cost = cost_mat + cost_energy + cost_depr
        final_price = total_cost * (1 + (markup / 100))
        profit = final_price - total_cost

        memoria_calc_str = f"Material: R${cost_mat:.2f} | Energia: R${cost_energy:.2f} | Depreciação: R${cost_depr:.2f} | Custo Total: R${total_cost:.2f} | Margem: {markup}%"

        with col2:
            st.subheader("📊 Resultado do Orçamento")
            
            # 4. Só mostra o placar financeiro SE o peso e tempo forem maiores que zero
            if proj_name and weight_g > 0 and total_hours > 0:
                st.metric(label="💰 PREÇO DE VENDA SUGERIDO", value=f"R$ {final_price:.2f}", delta=f"Lucro: R$ {profit:.2f}")
                st.divider()
                df_detalhes = pd.DataFrame({"Componente": ["Custo com Material", "Gasto com Energia", "Depreciação Máquina", "Lucro Limpo"], "Valor (R$)": [cost_mat, cost_energy, cost_depr, profit]})
                st.dataframe(df_detalhes.style.format({"Valor (R$)": "R$ {:.2f}"}), use_container_width=True, hide_index=True)

                if st.button("💾 Salvar Projeto no Relatório", type="primary"):
                    cursor = conn.cursor()
                    data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
                    cursor.execute("""
                        INSERT INTO historico (nome_projeto, material, peso_g, tempo_h, custo_total, preco_venda, data, memoria_calculo, foto_principal) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (proj_name, mat_selected, weight_g, total_hours, total_cost, final_price, data_hoje, memoria_calc_str, foto_base))
                    conn.commit()
                    st.success("✅ Projeto salvo e enviado para o Módulo de Relatórios!")
                    import time; time.sleep(1.5) # O mesmo truque do delay visual aqui
                    st.rerun()
            elif proj_name == "":
                st.warning("⚠️ Digite um nome para a peça antes de prosseguir.")
            else:
                st.info("👈 Preencha o peso (g) e o tempo da impressão para gerar o orçamento detalhado.")
    else:
        # Mensagem neutra quando a tela é aberta pela primeira vez
        with col2:
            st.info("👈 Selecione uma peça no menu ao lado para iniciar a configuração do projeto.")
            
    conn.close()
    
# =====================================================================
# MÓDULO 3: RELATÓRIO (Landscape Print & Memória de Cálculo)
# =====================================================================
elif menu == "📜 Módulo 3: RELATÓRIO":
    st.title("📜 Relação de Projetos Salvos")
    
    st.markdown("""
        <button onclick="window.print()" style="background-color: #000; color: white; padding: 10px 24px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; margin-bottom: 20px;">
            🖨️ IMPRIMIR RELATÓRIO (LANDSCAPE)
        </button>
    """, unsafe_allow_html=True)
    
    conn = get_db_connection()
    df_hist = pd.read_sql("SELECT * FROM historico ORDER BY id DESC", conn)
    conn.close()

    if not df_hist.empty:
        for idx, row in df_hist.iterrows():
            # Estrutura HTML/CSS que será formatada para impressão limpa
            st.markdown(f"""
            <div class="print-container">
                <div class="print-header">Projeto: {row['nome_projeto']} <span style="float:right; font-size:16px; color:gray;">Data: {row['data']}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 2, 1])
            
            with c1:
                # Usa o get() e checa se não é nulo/vazio para evitar quebrar com registros antigos
                foto = row.get('foto_principal')
                if pd.notna(foto) and foto:
                    st.image(base64.b64decode(foto), use_column_width=True)
                else:
                    st.info("Nenhuma foto atrelada.")
            
            with c2:
                st.markdown(f"**Material:** {row['material']}")
                st.markdown(f"**Peso Total:** {row['peso_g']} g")
                st.markdown(f"**Tempo Estimado:** {row['tempo_h']:.2f} horas")
                st.markdown(f"**Custo de Confecção:** R$ {row['custo_total']:.2f}")
                st.markdown(f"**Preço de Venda Sugerido:** R$ {row['preco_venda']:.2f}")
                
            with c3:
                st.markdown("**🧠 Memória de Cálculo:**")
                memoria = row.get('memoria_calculo')
                if pd.notna(memoria) and memoria:
                    st.caption(memoria.replace(" | ", "<br>"))
                else:
                    st.caption("Memória de cálculo não disponível para registros legados.")
                
                # --- BOTÃO DE EXCLUIR PROJETO ESPECÍFICO ---
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Excluir Este Projeto", key=f"del_proj_{row['id']}", use_container_width=True):
                    conn = get_db_connection()
                    conn.cursor().execute("DELETE FROM historico WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.rerun()
            
            st.divider()
            
        if st.button("🗑️ Limpar Relatório"):
            conn = get_db_connection()
            conn.cursor().execute("DELETE FROM historico")
            conn.commit()
            conn.close()
            st.rerun()
    else:
        st.info("Nenhum projeto salvo no banco de dados ainda.")
