import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime

# --- 1. CONFIGURAÇÃO E CRIAÇÃO DO BANCO DE DADOS (SQLite) ---
DB_NAME = "3d_calc_pro.db"

def init_db():
    """Inicializa o banco de dados SQLite com as tabelas necessárias e dados padrão."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela de Materiais
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materiais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE,
            preco_kg REAL
        )
    ''')
    
    # Tabela de Impressoras
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS impressoras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE,
            watts REAL,
            preco_maquina REAL,
            vida_util_h REAL
        )
    ''')
    
    # Tabela de Histórico de Projetos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_projeto TEXT,
            material TEXT,
            peso_g REAL,
            tempo_h REAL,
            custo_total REAL,
            preco_venda REAL,
            data TEXT
        )
    ''')
    
    # Inserir Materiais Padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM materiais")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO materiais (nome, preco_kg) VALUES (?, ?)", [
            ("PLA", 99.0),
            ("PLA Premium HT", 103.41),
            ("PETG", 119.0)
        ])
        
    # Inserir Impressoras Padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM impressoras")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO impressoras (nome, watts, preco_maquina, vida_util_h) VALUES (?, ?, ?, ?)", [
            ("Ender 3 / V2", 130.0, 1800.0, 4000.0),
            ("Bambu A1", 150.0, 3600.0, 5000.0),
            ("Bambu X1C", 350.0, 11000.0, 6000.0),
            ("Impressora Resina", 60.0, 2500.0, 3000.0)
        ])
        
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect(DB_NAME)

# --- FUNÇÃO DE BUSCA NA API DO MERCADO LIVRE ---
def buscar_mercadolivre(termo_busca):
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={termo_busca}&limit=30"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            resultados = []
            for item in data.get('results', []):
                # Extrai a marca das propriedades se disponível
                marca = "Não informada"
                for attr in item.get('attributes', []):
                    if attr.get('id') == 'BRAND':
                        marca = attr.get('value_name', 'Não informada')
                        break
                
                resultados.append({
                    "Título": item.get('title'),
                    "Preço (R$)": float(item.get('price', 0.0)),
                    "Marca": marca,
                    "Link": item.get('permalink'),
                    "Imagem": item.get('thumbnail')
                })
            return pd.DataFrame(resultados)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao buscar no Mercado Livre: {e}")
        return pd.DataFrame()


# --- 2. CONFIGURAÇÃO DA PÁGINA STREAMLIT ---
st.set_page_config(page_title="3D Calc Pro", page_icon="🎲", layout="wide")

# Sidebar - Navegação do App
st.sidebar.title("🎲 3D Calc Pro")
menu = st.sidebar.radio("Navegação", [
    "🧮 Calculadora de Orçamentos", 
    "🔎 Cotar Filamentos (Mercado Livre)",
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
        with col_w:
            weight_g = st.number_input("Peso Total (gramas)", min_value=0.0, value=85.0, step=5.0)
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
            if qty > 1:
                st.caption(f"Valor unitário: R$ {final_price/qty:.2f}")

            st.divider()
            
            df_detalhes = pd.DataFrame({
                "Componente": ["Material", "Energia", "Depreciação Máquina", "Lucro Limpo"],
                "Valor (R$)": [cost_mat, cost_energy, cost_depr, profit]
            })
            st.dataframe(df_detalhes.style.format({"Valor (R$)": "R$ {:.2f}"}), use_container_width=True, hide_index=True)

            if st.button("💾 Salvar Orçamento no Banco de Dados", type="primary"):
                conn = get_db_connection()
                cursor = conn.cursor()
                data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
                cursor.execute("""
                    INSERT INTO historico (nome_projeto, material, peso_g, tempo_h, custo_total, preco_venda, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (proj_name, mat_selected, weight_g, total_hours, total_cost, final_price, data_hoje))
                conn.commit()
                conn.close()
                st.success("✅ Projeto registrado com sucesso no banco de dados!")
        else:
            st.info("Preencha o peso e tempo para visualizar os custos.")


# --- TELA 2: COTAR FILAMENTOS EM TEMPO REAL ---
elif menu == "🔎 Cotar Filamentos (Mercado Livre)":
    st.title("🔎 Cotação e Pesquisa de Melhores Preços")
    st.caption("Pesquise os preços atuais no Mercado Livre e ordene por valor ou marca.")

    col_busca, col_ordem, col_filtro_marca = st.columns([2, 1, 1])
    
    with col_busca:
        termo = st.text_input("O que você procura?", value="Filamento PLA 1kg")
    with col_ordem:
        ordem = st.selectbox("Ordenar por", ["Menor Preço", "Maior Preço", "Título (A-Z)"])
    
    if st.button("🔎 Buscar Preços do Dia", type="primary"):
        with st.spinner("Buscando ofertas..."):
            df_ml = buscar_mercadolivre(termo)
            st.session_state['busca_ml'] = df_ml

    if 'busca_ml' in st.session_state and not st.session_state['busca_ml'].empty:
        df = st.session_state['busca_ml'].copy()
        
        # Aplicar ordenação
        if ordem == "Menor Preço":
            df = df.sort_values(by="Preço (R$)", ascending=True)
        elif ordem == "Maior Preço":
            df = df.sort_values(by="Preço (R$)", ascending=False)
        elif ordem == "Título (A-Z)":
            df = df.sort_values(by="Título", ascending=True)

        st.subheader(f"Resultados para: {termo}")
        
        # Exibição em Cards Interativos
        for idx, row in df.iterrows():
            with st.container():
                c_img, c_info, c_acao = st.columns([1, 3, 1])
                
                with c_img:
                    st.image(row['Imagem'], width=90)
                with c_info:
                    st.markdown(f"**[{row['Título']}]({row['Link']})**")
                    st.caption(f"🏷️ Marca: **{row['Marca']}**")
                    st.markdown(f"💵 **R$ {row['Preço (R$)']:.2f}**")
                with c_acao:
                    if st.button("➕ Cadastrar Material", key=f"add_{idx}"):
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            cursor.execute("INSERT INTO materiais (nome, preco_kg) VALUES (?, ?)", (row['Título'][:30], row['Preço (R$)']))
                            conn.commit()
                            st.success("Salvo no Banco!")
                        except sqlite3.IntegrityError:
                            st.warning("Já cadastrado.")
                        finally:
                            conn.close()
                st.divider()


# --- TELA 3: GERENCIAR BANCO DE DADOS ---
elif menu == "⚙️ Gerenciar Materiais & Máquinas":
    st.title("⚙️ Gerenciamento de Preços e Maquinário")
    st.caption("Altere ou adicione novos itens aqui sem precisar alterar o código Python.")

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
                st.success(f"Material '{nome_mat}' atualizado no banco de dados!")
                st.rerun()

    with tab_imp:
        conn = get_db_connection()
        impressoras_df = pd.read_sql("SELECT id, nome as 'Modelo', watts as 'Consumo (W)', preco_maquina as 'Valor (R$)', vida_util_h as 'Vida Útil (h)' FROM impressoras", conn)
        st.dataframe(impressoras_df, use_container_width=True, hide_index=True)

        st.markdown("### Cadastrar / Atualizar Impressora")
        with st.form("form_impressora"):
            nome_imp = st.text_input("Modelo da Impressora (ex: Creality K1 Max)")
            watts_imp = st.number_input("Consumo em Watts", value=350)
            preco_imp = st.number_input("Valor de Compra da Máquina (R$)", value=4500.0)
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
                st.success(f"Impressora '{nome_imp}' salva no banco de dados!")
                st.rerun()


# --- TELA 4: HISTÓRICO DE PROJETOS ---
elif menu == "📜 Histórico de Projetos":
    st.title("📜 Histórico de Orçamentos")
    
    conn = get_db_connection()
    historico_df = pd.read_sql("SELECT id, nome_projeto as 'Projeto', material as 'Material', peso_g as 'Peso (g)', tempo_h as 'Tempo (h)', custo_total as 'Custo (R$)', preco_venda as 'Venda (R$)', data as 'Data' FROM historico ORDER BY id DESC", conn)
    conn.close()

    if not historico_df.empty:
        st.dataframe(historico_df, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Limpar Todo o Histórico de Orçamentos"):
            conn = get_db_connection()
            conn.cursor().execute("DELETE FROM historico")
            conn.commit()
            conn.close()
            st.success("Histórico limpo!")
            st.rerun()
    else:
        st.info("Nenhum orçamento salvo no banco de dados ainda.")

```
