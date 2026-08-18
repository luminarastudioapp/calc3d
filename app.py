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
    
    # --- TABELAS BASE ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS materiais (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, preco_kg REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS impressoras (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, watts REAL, preco_maquina REAL, vida_util_h REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, kwh REAL, mao_obra REAL)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nome_projeto TEXT, material TEXT, peso_g REAL, tempo_h REAL, 
        custo_total REAL, preco_venda REAL, data TEXT
    )''')
    
    # --- SCRIPT DE MIGRAÇÃO (Atualiza bancos antigos automaticamente) ---
    colunas_novas = [
        ("memoria_calculo", "TEXT"), ("foto_principal", "TEXT"), 
        ("origem", "TEXT"), ("link_projeto", "TEXT"), ("custo_mao_obra", "REAL")
    ]
    for col, tipo in colunas_novas:
        try:
            cursor.execute(f"ALTER TABLE historico ADD COLUMN {col} {tipo}")
        except sqlite3.OperationalError:
            pass # Ignora se a coluna já existir

    # --- DADOS PADRÃO ---
    cursor.execute("SELECT COUNT(*) FROM configuracoes")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO configuracoes (id, kwh, mao_obra) VALUES (1, 0.95, 35.0)")

    cursor.execute("SELECT COUNT(*) FROM materiais")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO materiais (nome, preco_kg) VALUES (?, ?)", [("PLA", 99.0), ("PETG", 119.0)])
        
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

# --- 2. ESTILOS VISUAIS E IMPRESSÃO ---
st.set_page_config(page_title="3D Calc Pro", page_icon="🎲", layout="wide")

st.markdown("""
    <style>
    @media print {
        @page { size: landscape; margin: 15mm; }
        section[data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .stButton, .stDownloadButton, .stFileUploader, .stSelectbox, .stRadio { display: none !important; }
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
    "⚙️ Módulo 1: CADASTROS BASE", 
    "🚀 Módulo 2: NOVO PROJETO", 
    "📜 Módulo 3: RELATÓRIO"
])

# =====================================================================
# MÓDULO 1: CADASTROS BASE (Configurações, Materiais, Impressoras)
# =====================================================================
if menu == "⚙️ Módulo 1: CADASTROS BASE":
    st.title("⚙️ Almoxarifado e Custos da Gráfica")
    tab_cfg, tab_mat, tab_imp = st.tabs(["💵 Custos Fixos", "📦 Materiais", "🖨️ Impressoras"])
    
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
                novo_kwh = st.number_input("Custo do kWh (R$) - Veja na conta de luz", value=kwh_atual, step=0.05)
            with col_c2:
                nova_mao_obra = st.number_input("Seu Valor Hora - Mão de Obra (R$/h)", value=mao_obra_atual, step=5.0)
                
            if st.form_submit_button("Atualizar Custos Fixos"):
                conn.cursor().execute("UPDATE configuracoes SET kwh=?, mao_obra=? WHERE id=1", (novo_kwh, nova_mao_obra))
                conn.commit()
                st.success("✅ Custos base atualizados com sucesso!")
                time.sleep(1.5)
                st.rerun()
        conn.close()

    # --- CRUD: MATERIAIS ---
    with tab_mat:
        conn = get_db_connection()
        materiais_df = pd.read_sql("SELECT id, nome as 'Nome', preco_kg as 'Preço/KG (R$)' FROM materiais", conn)
        st.dataframe(materiais_df, use_container_width=True, hide_index=True)

        st.markdown("### 📝 Gerenciar Materiais")
        acao_mat = st.radio("Ação Material", ["Novo", "Editar", "Excluir"], horizontal=True, label_visibility="collapsed")
        
        if acao_mat == "Novo":
            with st.form("form_novo_mat", clear_on_submit=True):
                nome_mat = st.text_input("Nome do Material")
                preco_mat = st.number_input("Custo Unitário (R$/KG)", min_value=0.0, value=99.0)
                if st.form_submit_button("Salvar") and nome_mat:
                    conn.cursor().execute("INSERT INTO materiais (nome, preco_kg) VALUES (?, ?)", (nome_mat, preco_mat))
                    conn.commit()
                    st.success("✅ Cadastrado com sucesso!")
                    time.sleep(1.5)
                    st.rerun()
        elif acao_mat == "Editar":
            if not materiais_df.empty:
                mat_ed = st.selectbox("Selecione para Editar", materiais_df['Nome'].tolist())
                mat_id = int(materiais_df[materiais_df['Nome'] == mat_ed]['id'].values[0])
                mat_preco_atual = float(materiais_df[materiais_df['Nome'] == mat_ed]['Preço/KG (R$)'].values[0])
                with st.form("form_edita_mat"):
                    novo_nome = st.text_input("Nome", value=mat_ed)
                    novo_preco = st.number_input("Preço/KG", value=mat_preco_atual)
                    if st.form_submit_button("Atualizar"):
                        conn.cursor().execute("UPDATE materiais SET nome=?, preco_kg=? WHERE id=?", (novo_nome, novo_preco, mat_id))
                        conn.commit()
                        st.success("✅ Alterado com sucesso!")
                        time.sleep(1.5)
                        st.rerun()
        elif acao_mat == "Excluir":
             if not materiais_df.empty:
                mat_del = st.selectbox("Selecione para Excluir", materiais_df['Nome'].tolist())
                mat_id = int(materiais_df[materiais_df['Nome'] == mat_del]['id'].values[0])
                if st.button("🚨 Confirmar Exclusão"):
                    conn.cursor().execute("DELETE FROM materiais WHERE id=?", (mat_id,))
                    conn.commit()
                    st.success("✅ Excluído com sucesso!")
                    time.sleep(1.5)
                    st.rerun()
        conn.close()

    # --- CRUD: IMPRESSORAS ---
    with tab_imp:
        conn = get_db_connection()
        imp_df = pd.read_sql("SELECT id, nome as 'Modelo', watts, preco_maquina as 'Valor (R$)', vida_util_h as 'Vida Útil (h)' FROM impressoras", conn)
        
        # Cria colunas calculadas para visualização inteligente
        if not imp_df.empty:
            imp_df['Consumo (kW)'] = imp_df['watts'] / 1000
            imp_df['Depreciação (R$/h)'] = imp_df['Valor (R$)'] / imp_df['Vida Útil (h)']
            st.dataframe(imp_df[['Modelo', 'Consumo (kW)', 'Valor (R$)', 'Vida Útil (h)', 'Depreciação (R$/h)']].style.format({
                "Consumo (kW)": "{:.2f} kW", "Valor (R$)": "R$ {:.2f}", "Depreciação (R$/h)": "R$ {:.2f}"
            }), use_container_width=True, hide_index=True)

        st.markdown("### 📝 Gerenciar Impressoras")
        acao_imp = st.radio("Ação Impressora", ["Nova", "Editar", "Excluir"], horizontal=True, label_visibility="collapsed")
        
        if acao_imp == "Nova":
            with st.form("form_nova_imp", clear_on_submit=True):
                nome_imp = st.text_input("Marca | Modelo da Impressora")
                kw_imp = st.number_input("Consumo Máquina (kW) - Ex: 0.15 para 150W", value=0.15, step=0.05)
                preco_imp = st.number_input("Valor da Impressora (R$)", value=5000.0)
                vida_imp = st.number_input("Vida Útil Estimada (Horas)", value=3000)
                if st.form_submit_button("Salvar Máquina") and nome_imp:
                    watts = kw_imp * 1000
                    conn.cursor().execute("INSERT INTO impressoras (nome, watts, preco_maquina, vida_util_h) VALUES (?, ?, ?, ?)", (nome_imp, watts, preco_imp, vida_imp))
                    conn.commit()
                    st.success("✅ Cadastrado com sucesso!")
                    time.sleep(1.5)
                    st.rerun()
        elif acao_imp == "Editar":
            if not imp_df.empty:
                imp_ed = st.selectbox("Selecione para Editar", imp_df['Modelo'].tolist())
                row_imp = imp_df[imp_df['Modelo'] == imp_ed].iloc[0]
                imp_id = int(row_imp['id'])
                with st.form("form_edita_imp"):
                    novo_nome = st.text_input("Modelo", value=row_imp['Modelo'])
                    novo_kw = st.number_input("Consumo (kW)", value=float(row_imp['watts'])/1000, step=0.05)
                    novo_preco = st.number_input("Valor (R$)", value=float(row_imp['Valor (R$)']))
                    nova_vida = st.number_input("Vida Útil (Horas)", value=int(row_imp['Vida Útil (h)']))
                    if st.form_submit_button("Atualizar"):
                        conn.cursor().execute("UPDATE impressoras SET nome=?, watts=?, preco_maquina=?, vida_util_h=? WHERE id=?", 
                                              (novo_nome, novo_kw*1000, novo_preco, nova_vida, imp_id))
                        conn.commit()
                        st.success("✅ Alterado com sucesso!")
                        time.sleep(1.5)
                        st.rerun()
        elif acao_imp == "Excluir":
             if not imp_df.empty:
                imp_del = st.selectbox("Selecione para Excluir", imp_df['Modelo'].tolist())
                imp_id = int(imp_df[imp_df['Modelo'] == imp_del]['id'].values[0])
                if st.button("🚨 Confirmar Exclusão"):
                    conn.cursor().execute("DELETE FROM impressoras WHERE id=?", (imp_id,))
                    conn.commit()
                    st.success("✅ Excluído com sucesso!")
                    time.sleep(1.5)
                    st.rerun()
        conn.close()


# =====================================================================
# MÓDULO 2: NOVO PROJETO (Criação e Precificação da Peça)
# =====================================================================
elif menu == "🚀 Módulo 2: NOVO PROJETO":
    st.title("🚀 Criação e Precificação de Projeto")
    
    conn = get_db_connection()
    materiais_df = pd.read_sql("SELECT * FROM materiais", conn)
    impressoras_df = pd.read_sql("SELECT * FROM impressoras", conn)
    cfg_df = pd.read_sql("SELECT * FROM configuracoes WHERE id=1", conn)
    
    kwh_cost = float(cfg_df['kwh'][0])
    mao_obra_rate = float(cfg_df['mao_obra'][0])
    
    col1, col2 = st.columns([1.2, 1], gap="large")

    with col1:
        st.subheader("📋 Identidade da Peça")
        proj_name = st.text_input("Nome da Peça", placeholder="Ex: Vaso Geométrico")
        
        foto_upload = st.file_uploader("📸 Anexar Foto do Projeto", type=["png", "jpg", "jpeg"])
        foto_b64 = converter_imagem(foto_upload)
        if foto_upload: st.image(foto_upload, width=150)

        # Autoral ou Fornecedor
        origem = st.radio("Origem do Design", ["Autoral", "Fornecedor"], horizontal=True)
        link_projeto = ""
        if origem == "Fornecedor":
            link_projeto = st.text_input("🔗 Link do Projeto (Onde baixou/comprou)")

        st.divider()
        st.subheader("⚙️ Parâmetros de Fabricação")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            printer_selected = st.selectbox("Tipo de impressora", impressoras_df['nome'].tolist())
            printer_info = impressoras_df[impressoras_df['nome'] == printer_selected].iloc[0]
        with col_m2:
            mat_selected = st.selectbox("Tipo de filamento", materiais_df['nome'].tolist())
            mat_info = materiais_df[materiais_df['nome'] == mat_selected].iloc[0]
            mat_cost_per_kg = float(mat_info['preco_kg'])

        col_w, col_t1, col_t2 = st.columns([1, 1, 1])
        with col_w: 
            weight_g = st.number_input("Peso total (g)", min_value=0.0, value=0.0)
        with col_t1:
            hours = st.number_input("Tempo Máquina (h)", min_value=0, value=0)
        with col_t2:
            mins = st.number_input("Tempo Máquina (min)", min_value=0, max_value=59, value=0)

        st.caption("⏳ **Sua Mão de Obra:** Tempo real que você gasta fatiando, limpando suportes e embalando esta peça.")
        tempo_mao_obra_min = st.number_input("Tempo de Mão de Obra Dedicada (Minutos)", min_value=0, value=15, step=5)

        markup = st.slider("Margem de Lucro (%)", 20, 300, 100, step=10)

    # Lógica de cálculo
    total_hours = hours + (mins / 60)
    cost_mat = (weight_g / 1000) * mat_cost_per_kg
    cost_energy = (printer_info['watts'] / 1000) * total_hours * kwh_cost
    cost_depr = (printer_info['preco_maquina'] / max(1, printer_info['vida_util_h'])) * total_hours
    
    # Custo da sua hora trabalhada em cima do preparo
    cost_mao_obra = (tempo_mao_obra_min / 60) * mao_obra_rate
    
    total_cost = cost_mat + cost_energy + cost_depr + cost_mao_obra
    final_price = total_cost * (1 + (markup / 100))
    profit = final_price - total_cost

    memoria_calc_str = f"Material: R${cost_mat:.2f} | Energia: R${cost_energy:.2f} | Depreciação: R${cost_depr:.2f} | Mão de Obra: R${cost_mao_obra:.2f} | Custo Total: R${total_cost:.2f} | Margem: {markup}%"

    with col2:
        st.subheader("📊 Resultado do Orçamento")
        
        if proj_name and weight_g > 0 and (total_hours > 0 or tempo_mao_obra_min > 0):
            st.metric(label="💰 PREÇO DE VENDA SUGERIDO", value=f"R$ {final_price:.2f}", delta=f"Lucro: R$ {profit:.2f}")
            st.divider()
            df_detalhes = pd.DataFrame({
                "Componente": ["Material", "Energia", "Depreciação Máquina", "Sua Mão de Obra", "Lucro Limpo"], 
                "Valor (R$)": [cost_mat, cost_energy, cost_depr, cost_mao_obra, profit]
            })
            st.dataframe(df_detalhes.style.format({"Valor (R$)": "R$ {:.2f}"}), use_container_width=True, hide_index=True)

            if st.button("💾 Salvar Projeto no Relatório", type="primary", use_container_width=True):
                cursor = conn.cursor()
                data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
                cursor.execute("""
                    INSERT INTO historico (nome_projeto, material, peso_g, tempo_h, custo_total, preco_venda, data, memoria_calculo, foto_principal, origem, link_projeto, custo_mao_obra) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (proj_name, mat_selected, weight_g, total_hours, total_cost, final_price, data_hoje, memoria_calc_str, foto_b64, origem, link_projeto, cost_mao_obra))
                conn.commit()
                st.success("✅ Projeto salvo na Vitrine/Relatório!")
                time.sleep(1.5)
                st.rerun()
        elif proj_name == "":
            st.warning("⚠️ Digite um nome para a peça antes de prosseguir.")
        else:
            st.info("👈 Preencha o peso (g) e o tempo para gerar o orçamento detalhado.")
            
    conn.close()


# =====================================================================
# MÓDULO 3: RELATÓRIO (Landscape Print & Memória de Cálculo)
# =====================================================================
elif menu == "📜 Módulo 3: RELATÓRIO":
    st.title("📜 Vitrine de Projetos Salvos")
    
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
                <div class="print-header">Projeto: {row['nome_projeto']} <span style="float:right; font-size:16px; color:gray;">Data: {row['data']}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 1.5, 1.5])
            
            with c1:
                foto = row.get('foto_principal')
                if pd.notna(foto) and foto:
                    st.image(base64.b64decode(foto), use_column_width=True)
                else:
                    st.info("Nenhuma foto atrelada.")
            
            with c2:
                origem_lbl = row.get('origem', 'Não Informado')
                link_lbl = row.get('link_projeto', '')
                st.markdown(f"**Origem:** {origem_lbl}")
                if origem_lbl == "Fornecedor" and pd.notna(link_lbl) and link_lbl:
                    st.markdown(f"🔗 [Acessar Link do Fornecedor]({link_lbl})")
                
                st.markdown(f"**Material:** {row['material']}")
                st.markdown(f"**Peso Total:** {row['peso_g']} g")
                st.markdown(f"**Tempo de Máquina:** {row['tempo_h']:.2f} h")
                st.markdown(f"**Custo Base + Mão de Obra:** R$ {row['custo_total']:.2f}")
                st.markdown(f"**Preço de Venda Sugerido:** <span style='font-size:18px; color:#2e7d32; font-weight:bold;'>R$ {row['preco_venda']:.2f}</span>", unsafe_allow_html=True)
                
            with c3:
                st.markdown("**🧠 Memória de Cálculo:**")
                memoria = row.get('memoria_calculo')
                if pd.notna(memoria) and memoria:
                    st.caption(memoria.replace(" | ", "<br>"))
                else:
                    st.caption("Memória não disponível para registros antigos.")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Excluir Projeto", key=f"del_proj_{row['id']}", use_container_width=True):
                    conn = get_db_connection()
                    conn.cursor().execute("DELETE FROM historico WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.success("Peça removida da vitrine.")
                    time.sleep(1)
                    st.rerun()
            
            st.divider()
    else:
        st.info("Nenhum projeto salvo no banco de dados ainda.")
