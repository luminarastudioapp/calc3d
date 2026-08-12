import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS (SQLite) ---
DB_NAME = "3d_calc_pro.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS materiais (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, preco_kg REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS impressoras (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, watts REAL, preco_maquina REAL, vida_util_h REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS historico (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_projeto TEXT, material TEXT, peso_g REAL, tempo_h REAL, custo_total REAL, preco_venda REAL, data TEXT)''')
    
    cursor.execute("SELECT COUNT(*) FROM materiais")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO materiais (nome, preco_kg) VALUES (?, ?)", [("PLA", 99.0), ("PLA Premium HT", 103.41), ("PETG", 119.0)])
        
    cursor.execute("SELECT COUNT(*) FROM impressoras")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO impressoras (nome, watts, preco_maquina, vida_util_h) VALUES (?, ?, ?, ?)", [
            ("Ender 3 / V2", 130.0, 1800.0, 4000.0), 
            ("Bambu Lab A1 + AMS Lite", 150.0, 4200.0, 5000.0), 
            ("Bambu X1C", 350.0, 11000.0, 6000.0), 
            ("Impressora Resina", 60.0, 2500.0, 3000.0)
        ])
        
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect(DB_NAME)

# --- 2. CONFIGURAÇÃO DA PÁGINA STREAMLIT ---
st.set_page_config(page_title="3D Calc Pro", page_icon="🎲", layout="wide")

st.sidebar.title("🎲 3D Calc Pro")
menu = st.sidebar.radio("Navegação", [
    "🧮 Calculadora de Orçamentos", 
    "🧩 Fatiamento Otimizado",
    "⚙️ Gerenciar Materiais & Máquinas", 
    "📜 Histórico de Projetos"
])
kwh_cost = st.sidebar.number_input("Custo da Energia Elétrica (R$ / kWh)", value=1.25, step=0.05)


# --- TELA 1: CALCULADORA DE ORÇAMENTOS ---
if menu == "🧮 Calculadora de Orçamentos":
    st.title("🧮 Calculadora de Precificação 3D")
    
    conn = get_db_connection()
    materiais_df = pd.read_sql("SELECT * FROM materiais", conn)
    impressoras_df = pd.read_sql("SELECT * FROM impressoras", conn)
    conn.close()

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("📋 Dados do Projeto")
        proj_name = st.text_input("Nome do Projeto", value="Vaso Geométrico")
        qty = st.number_input("Quantidade de Peças", min_value=1, value=1)

        printer_selected = st.selectbox("Selecione a Impressora", impressoras_df['nome'].tolist())
        printer_info = impressoras_df[impressoras_df['nome'] == printer_selected].iloc[0]

        mat_selected = st.selectbox("Selecione o Material", materiais_df['nome'].tolist())
        mat_info = materiais_df[materiais_df['nome'] == mat_selected].iloc[0]
        
        mat_cost_per_kg = st.number_input("Custo por KG do Material (R$)", value=float(mat_info['preco_kg']))

        col_w, col_t = st.columns(2)
        with col_w: weight_g = st.number_input("Peso Total (gramas)", min_value=0.0, value=85.0, step=5.0)
        with col_t:
            hours = st.number_input("Tempo (Horas)", min_value=0, value=4)
            mins = st.number_input("Tempo (Minutos)", min_value=0, max_value=59, value=30)

        markup = st.slider("Margem de Lucro / Markup (%)", 20, 300, 100, step=10)

    total_hours = hours + (mins / 60)
    cost_mat = (weight_g / 1000) * mat_cost_per_kg
    cost_energy = (printer_info['watts'] / 1000) * total_hours * kwh_cost
    cost_depr = (printer_info['preco_maquina'] / max(1, printer_info['vida_util_h'])) * total_hours
    
    total_cost = cost_mat + cost_energy + cost_depr
    final_price = total_cost * (1 + (markup / 100))
    profit = final_price - total_cost

    with col2:
        st.subheader("📊 Demonstrativo de Preço")
        if weight_g > 0 and total_hours > 0:
            st.metric(label="💰 PREÇO DE VENDA SUGERIDO", value=f"R$ {final_price:.2f}", delta=f"Lucro: R$ {profit:.2f}")
            st.divider()
            df_detalhes = pd.DataFrame({"Componente": ["Material", "Energia", "Depreciação Máquina", "Lucro Limpo"], "Valor (R$)": [cost_mat, cost_energy, cost_depr, profit]})
            st.dataframe(df_detalhes.style.format({"Valor (R$)": "R$ {:.2f}"}), use_container_width=True, hide_index=True)

            if st.button("💾 Salvar Orçamento", type="primary"):
                conn = get_db_connection()
                conn.cursor().execute("INSERT INTO historico (nome_projeto, material, peso_g, tempo_h, custo_total, preco_venda, data) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                                      (proj_name, mat_selected, weight_g, total_hours, total_cost, final_price, datetime.now().strftime("%d/%m/%Y %H:%M")))
                conn.commit()
                conn.close()
                st.success("✅ Salvo no banco de dados!")


# --- TELA 2: FATIAMENTO OTIMIZADO ---
elif menu == "🧩 Fatiamento Otimizado":
    st.title("🧩 Assistente de Fatiamento Otimizado")
    st.caption("Recomendações técnicas para fatiadores (Bambu Studio, OrcaSlicer, PrusaSlicer, Cura) com base na aplicação do projeto.")

    col_in, col_out = st.columns([1, 1], gap="large")

    with col_in:
        st.subheader("🎯 Requisitos do Projeto")
        
        categoria = st.selectbox(
            "Tipo de Aplicação",
            [
                "Decorativo / Visual (Sem esforço mecânico)",
                "Funcional Leve (Suporte de celular, caixas organizadoras)",
                "Estrutural Médio / Pesado (Suporte de Notebook, suporte de parede)",
                "Peça Mecânica / Alto Impacto (Engrenagens, presilhas sob tensão)",
                "Alta Exposição ao Calor / Ambiente Externo"
            ]
        )

        bico = st.selectbox("Diâmetro do Bico (Nozzle)", [0.2, 0.4, 0.6, 0.8], index=1)
        
        esforco = st.select_slider(
            "Carga de Peso / Esforço Mecânico Estimado",
            options=["Nenhum (< 200g)", "Leve (< 1 kg)", "Médio (1 kg a 3 kg)", "Pesado (> 3 kg)"]
        )

    # Matriz de Regras de Fatiamento
    if "Decorativo" in categoria:
        paredes = 2
        infill = 10
        padrao = "Lightning / Grid"
        topo_base = "3 Topo / 3 Base"
        gerador = "Arachne"
        mat_rec = "PLA"
        dica = "Foco em acabamento estético e economia de filamento. Não recomendado para suportar peso."
    elif "Leve" in categoria and esforco != "Pesado (> 3 kg)":
        paredes = 3
        infill = 15
        padrao = "Gyroid / Cubic"
        topo_base = "4 Topo / 3 Base"
        gerador = "Arachne"
        mat_rec = "PLA ou PETG"
        dica = "Resistência adequada para uso cotidiano simples, como apoios leves."
    elif "Estrutural Médio" in categoria or esforco in ["Médio (1 kg a 3 kg)", "Pesado (> 3 kg)"]:
        paredes = 4
        infill = 25
        padrao = "Gyroid"
        topo_base = "5 Topo / 4 Base"
        gerador = "Arachne"
        mat_rec = "PLA Reforçado ou PETG"
        dica = "Configuração ideal para notebooks pesados (ex: Acer Nitro 5). As 4 paredes absorvem a flexão sem trincar."
    elif "Mecânica" in categoria:
        paredes = 5
        infill = 40
        padrao = "3D Honeycomb / Gyroid"
        topo_base = "5 Topo / 5 Base"
        gerador = "Clássico"
        mat_rec = "PETG / ABS / ASA"
        dica = "Máxima coesão de camadas para resistir à torção, atrito e impactos repetidos."
    else:
        paredes = 4
        infill = 30
        padrao = "Gyroid"
        topo_base = "5 Topo / 4 Base"
        gerador = "Arachne"
        mat_rec = "PETG / ASA / ABS"
        dica = "Atenção: O PLA amolece acima de 50°C. Para contato direto com saídas de ar quente ou sol, use PETG ou ASA."

    with col_out:
        st.subheader("⚙️ Parâmetros Recomendados para o Slicer")
        
        st.info(f"💡 **Diretriz de Impressão:** {dica}")

        m1, m2 = st.columns(2)
        m1.metric("Paredes (Wall Loops)", f"{paredes} voltas")
        m2.metric("Preenchimento (Infill)", f"{infill}%")

        m3, m4 = st.columns(2)
        m3.metric("Padrão de Infill", padrao)
        m4.metric("Camadas Topo / Base", topo_base)

        st.divider()
        
        df_resumo = pd.DataFrame({
            "Parâmetro Avançado": ["Gerador de Parede", "Material Indicado", "Bico Selecionado"],
            "Configuração Recomendada": [gerador, mat_rec, f"{bico} mm"]
        })
        st.dataframe(df_resumo, use_container_width=True, hide_index=True)


# --- TELA 3: GERENCIAR MATERIAIS & MÁQUINAS ---
elif menu == "⚙️ Gerenciar Materiais & Máquinas":
    st.title("⚙️ Gerenciamento de Preços e Maquinário")
    tab_mat, tab_imp = st.tabs(["📦 Materiais Cadastrados", "🖨️ Impressoras Cadastradas"])
    
    with tab_mat:
        conn = get_db_connection()
        materiais_df = pd.read_sql("SELECT id, nome as 'Nome', preco_kg as 'Preço/KG (R$)' FROM materiais", conn)
        st.dataframe(materiais_df, use_container_width=True, hide_index=True)

        st.markdown("### Cadastrar / Atualizar Material")
        with st.form("form_material"):
            nome_mat = st.text_input("Nome do Material (ex: PLA Silk Gold)")
            preco_mat = st.number_input("Preço do KG (R$)", min_value=0.0, value=130.0)
            btn_mat = st.form_submit_button("Salvar no Banco")

            if btn_mat and nome_mat:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO materiais (nome, preco_kg) VALUES (?, ?)
                    ON CONFLICT(nome) DO UPDATE SET preco_kg=excluded.preco_kg
                """, (nome_mat, preco_mat))
                conn.commit()
                conn.close()
                st.success(f"Material '{nome_mat}' salvo!")
                st.rerun()

    with tab_imp:
        conn = get_db_connection()
        impressoras_df = pd.read_sql("SELECT id, nome as 'Modelo', watts as 'Consumo (W)', preco_maquina as 'Valor (R$)', vida_util_h as 'Vida Útil (h)' FROM impressoras", conn)
        st.dataframe(impressoras_df, use_container_width=True, hide_index=True)

        st.markdown("### Cadastrar / Atualizar Impressora")
        with st.form("form_impressora"):
            nome_imp = st.text_input("Modelo da Impressora")
            watts_imp = st.number_input("Consumo em Watts", value=350)
            preco_imp = st.number_input("Valor de Compra (R$)", value=4500.0)
            vida_imp = st.number_input("Vida Útil Estimada em Horas", value=5000)
            btn_imp = st.form_submit_button("Salvar no Banco")

            if btn_imp and nome_imp:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO impressoras (nome, watts, preco_maquina, vida_util_h) VALUES (?, ?, ?, ?)
                    ON CONFLICT(nome) DO UPDATE SET watts=excluded.watts, preco_maquina=excluded.preco_maquina, vida_util_h=excluded.vida_util_h
                """, (nome_imp, watts_imp, preco_imp, vida_imp))
                conn.commit()
                conn.close()
                st.success(f"Impressora '{nome_imp}' salva!")
                st.rerun()


# --- TELA 4: HISTÓRICO DE PROJETOS ---
elif menu == "📜 Histórico de Projetos":
    st.title("📜 Histórico de Orçamentos")
    conn = get_db_connection()
    df_hist = pd.read_sql("SELECT id, nome_projeto as 'Projeto', material as 'Material', peso_g as 'Peso (g)', tempo_h as 'Tempo (h)', custo_total as 'Custo (R$)', preco_venda as 'Venda (R$)', data as 'Data' FROM historico ORDER BY id DESC", conn)
    conn.close()

    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        if st.button("🗑️ Limpar Todo o Histórico"):
            conn = get_db_connection()
            conn.cursor().execute("DELETE FROM historico")
            conn.commit()
            conn.close()
            st.success("Histórico limpo!")
            st.rerun()
    else:
        st.info("Nenhum orçamento salvo no banco de dados ainda.")
