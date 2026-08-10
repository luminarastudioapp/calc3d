import streamlit as st
import sqlite3
import pandas as pd
import requests
import urllib.parse
from datetime import datetime

# --- 1. CONFIGURAÇÃO E CRIAÇÃO DO BANCO DE DADOS (SQLite) ---
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
            ("Ender 3 / V2", 130.0, 1800.0, 4000.0), ("Bambu Lab A1 + AMS Lite", 150.0, 4200.0, 5000.0), 
            ("Bambu X1C", 350.0, 11000.0, 6000.0), ("Impressora Resina", 60.0, 2500.0, 3000.0)
        ])
        
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect(DB_NAME)

# --- FUNÇÕES DE BUSCA (API) ---
def buscar_mercadolivre(termo_busca):
    termo_codificado = urllib.parse.quote(termo_busca)
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={termo_codificado}&limit=20"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            resultados = []
            for item in data.get('results', []):
                marca = "Não informada"
                for attr in item.get('attributes', []):
                    if attr.get('id') == 'BRAND':
                        marca = attr.get('value_name', 'Não informada')
                        break
                
                resultados.append({
                    "Plataforma": "🟡 Mercado Livre",
                    "Título": item.get('title'),
                    "Preço (R$)": float(item.get('price', 0.0)),
                    "Marca": marca,
                    "Avaliação": 0.0, # ML não fornece rating na busca simples
                    "Link": item.get('permalink'),
                    "Imagem": item.get('thumbnail')
                })
            return pd.DataFrame(resultados)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def buscar_shopee(termo_busca):
    termo_codificado = urllib.parse.quote(termo_busca)
    url = f"https://shopee.com.br/api/v4/search/search_items?keyword={termo_codificado}&limit=20"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            resultados = []
            itens = data.get('items', [])
            
            for item_wrapper in itens:
                item = item_wrapper.get('item_basic', {})
                # O preço da Shopee na API vem multiplicado por 100.000
                preco = item.get('price', 0) / 100000 
                marca = item.get('brand', 'Não informada')
                if marca in ["None", "0", "", None]: marca = "Não informada"
                
                avaliacao = round(item.get('item_rating', {}).get('rating_star', 0.0), 1)
                
                shopid = item.get('shopid')
                itemid = item.get('itemid')
                link = f"https://shopee.com.br/product/{shopid}/{itemid}"
                
                image_id = item.get('image')
                imagem = f"https://cf.shopee.com.br/file/{image_id}" if image_id else ""
                
                resultados.append({
                    "Plataforma": "🟠 Shopee",
                    "Título": item.get('name', 'Sem título'),
                    "Preço (R$)": float(preco),
                    "Marca": marca,
                    "Avaliação": avaliacao,
                    "Link": link,
                    "Imagem": imagem
                })
            return pd.DataFrame(resultados)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# --- 2. CONFIGURAÇÃO DA PÁGINA STREAMLIT ---
st.set_page_config(page_title="3D Calc Pro", page_icon="🎲", layout="wide")

st.sidebar.title("🎲 3D Calc Pro")
menu = st.sidebar.radio("Navegação", ["🧮 Calculadora de Orçamentos", "🔎 Radar de Preços (ML & Shopee)", "⚙️ Gerenciar Materiais & Máquinas", "📜 Histórico de Projetos"])
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


# --- TELA 2: RADAR DE PREÇOS ---
elif menu == "🔎 Radar de Preços (ML & Shopee)":
    st.title("🔎 Radar de Preços e Qualidade")
    st.caption("Faça uma varredura cruzada entre Mercado Livre e Shopee para garantir o melhor custo-benefício para seus projetos.")

    col_busca, col_plat, col_ordem = st.columns([2, 1, 1])
    
    with col_busca:
        termo = st.text_input("O que você procura?", value="Filamento PLA 1kg")
    with col_plat:
        plataforma = st.selectbox("Plataforma", ["Ambas", "Shopee", "Mercado Livre"])
    with col_ordem:
        ordem = st.selectbox("Organizar por", ["Menor Preço", "Maior Preço", "Melhor Avaliação", "Marca (A-Z)"])
    
    if st.button("🚀 Iniciar Varredura", type="primary"):
        with st.spinner("Conectando aos servidores... (A Shopee pode demorar um pouco mais ou bloquear requisições)"):
            df_final = pd.DataFrame()
            
            if plataforma in ["Ambas", "Mercado Livre"]:
                df_ml = buscar_mercadolivre(termo)
                df_final = pd.concat([df_final, df_ml], ignore_index=True)
                
            if plataforma in ["Ambas", "Shopee"]:
                df_shopee = buscar_shopee(termo)
                df_final = pd.concat([df_final, df_shopee], ignore_index=True)
            
            st.session_state['busca_radar'] = df_final

    if 'busca_radar' in st.session_state and not st.session_state['busca_radar'].empty:
        df = st.session_state['busca_radar'].copy()
        
        # Filtros de Ordenação
        if ordem == "Menor Preço":
            df = df.sort_values(by="Preço (R$)", ascending=True)
        elif ordem == "Maior Preço":
            df = df.sort_values(by="Preço (R$)", ascending=False)
        elif ordem == "Melhor Avaliação":
            df = df.sort_values(by="Avaliação", ascending=False)
        elif ordem == "Marca (A-Z)":
            df = df.sort_values(by="Marca", ascending=True)

        st.subheader(f"Resultados encontrados: {len(df)} ofertas")
        
        for idx, row in df.iterrows():
            with st.container():
                c_img, c_info, c_acao = st.columns([1, 3, 1])
                
                with c_img:
                    if row['Imagem']:
                        st.image(row['Imagem'], width=90)
                with c_info:
                    st.markdown(f"**[{row['Plataforma']}] [{row['Título']}]({row['Link']})**")
                    estrelas = f"⭐ {row['Avaliação']}/5.0" if row['Avaliação'] > 0 else "⭐ Sem Nota Pública"
                    st.caption(f"🏷️ Marca: **{row['Marca']}** | {estrelas}")
                    st.markdown(f"💵 **R$ {row['Preço (R$)']:.2f}**")
                with c_acao:
                    if st.button("➕ Enviar pro App", key=f"add_{idx}"):
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            cursor.execute("INSERT INTO materiais (nome, preco_kg) VALUES (?, ?)", (row['Título'][:35], row['Preço (R$)']))
                            conn.commit()
                            st.success("Salvo!")
                        except sqlite3.IntegrityError:
                            st.warning("Já existe.")
                        finally:
                            conn.close()
                st.divider()
    elif 'busca_radar' in st.session_state:
        st.warning("Nenhum resultado retornado. Tente um termo diferente ou os servidores podem ter bloqueado o robô temporariamente.")


# --- TELA 3 e 4: GERENCIAR E HISTÓRICO (Mantidos Inalterados para focar na inovação) ---
elif menu == "⚙️ Gerenciar Materiais & Máquinas":
    st.title("⚙️ Gerenciamento")
    tab_mat, tab_imp = st.tabs(["📦 Materiais", "🖨️ Impressoras"])
    with tab_mat:
        conn = get_db_connection()
        st.dataframe(pd.read_sql("SELECT id, nome as 'Nome', preco_kg as 'Preço/KG (R$)' FROM materiais", conn), hide_index=True)
    with tab_imp:
        st.dataframe(pd.read_sql("SELECT id, nome as 'Modelo', watts as 'Consumo (W)', preco_maquina as 'Valor (R$)', vida_util_h as 'Vida Útil (h)' FROM impressoras", conn), hide_index=True)

elif menu == "📜 Histórico de Projetos":
    st.title("📜 Histórico")
    conn = get_db_connection()
    df_hist = pd.read_sql("SELECT * FROM historico ORDER BY id DESC", conn)
    if not df_hist.empty:
        st.dataframe(df_hist, hide_index=True)
        if st.button("🗑️ Limpar"):
            conn.cursor().execute("DELETE FROM historico")
            conn.commit()
            st.rerun()
