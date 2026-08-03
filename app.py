import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="3D Calc Pro - Google Sheets DB", page_icon="🎲", layout="wide")

# Estilo visual moderno
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 18px; border-radius: 12px; border: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

st.title("🎲 3D Calc Pro (Conectado ao Google Planilhas)")
st.caption("Calculadora de precificação sincronizada em tempo real com o Google Sheets")

# Cole aqui o link publico da sua planilha do Google Sheets
# Importante: A planilha deve estar compartilhada como 'Qualquer pessoa com o link pode ver' ou editável.
URL_PLANILHA = st.sidebar.text_input(
    "🔗 Link da Planilha Google Sheets:", 
    value="https://docs.google.com/spreadsheets/d/SEU_LINK_AQUI/edit"
)

if "SEU_LINK_AQUI" in URL_PLANILHA or not URL_PLANILHA:
    st.info("👈 Cole o link da sua planilha do Google Sheets no menu lateral para começar!")
    st.markdown("""
    ### 🚀 Como configurar em 3 passos:
    1. Crie uma planilha no Google Drive usando a estrutura fornecida no arquivo **3D_Calc_Pro_DB.xlsx**.
    2. Clique em **Compartilhar** (canto superior direito) e mude para **'Qualquer pessoa com o link'** (Editor).
    3. Copie o link do navegador e cole na barra lateral ali ao lado.
    """)
    st.stop()

# Conexão com o Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_materiais = conn.read(spreadsheet=URL_PLANILHA, worksheet="Materiais", ttl="10s")
    df_impressoras = conn.read(spreadsheet=URL_PLANILHA, worksheet="Impressoras", ttl="10s")
except Exception as e:
    st.error(f"Erro ao conectar com o Google Sheets. Verifique o link e as permissões da planilha. Detalhes: {e}")
    st.stop()

# Sidebar - Parâmetros gerais
st.sidebar.divider()
st.sidebar.subheader("⚙️ Custos Operacionais")
kwh_cost = st.sidebar.number_input("Custo Energia Elétrica (R$ / kWh)", value=1.25, step=0.05)

# Layout da Calculadora
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📋 Parâmetros do Projeto")
    proj_name = st.text_input("Nome do Projeto", value="Vaso Geométrico 3D")
    qty = st.number_input("Quantidade de Peças", min_value=1, value=1)

    # Seleção vinda do Google Sheets
    printer_options = df_impressoras['nome'].dropna().tolist()
    printer_selected = st.selectbox("Selecione a Impressora", printer_options)
    printer_info = df_impressoras[df_impressoras['nome'] == printer_selected].iloc[0]

    mat_options = df_materiais['nome'].dropna().tolist()
    mat_selected = st.selectbox("Selecione o Material", mat_options)
    mat_info = df_materiais[df_materiais['nome'] == mat_selected].iloc[0]

    mat_cost_per_kg = st.number_input("Custo/KG do Material (R$)", value=float(mat_info['preco_kg']))

    col_w, col_t = st.columns(2)
    with col_w:
        weight_g = st.number_input("Peso Total (gramas)", min_value=0.0, value=85.0, step=5.0)
    with col_t:
        hours = st.number_input("Tempo (Horas)", min_value=0, value=4)
        mins = st.number_input("Tempo (Minutos)", min_value=0, max_value=59, value=30)

    markup = st.slider("Margem de Lucro / Markup (%)", min_value=20, max_value=300, value=100, step=10)

# Cálculos de Precificação
total_hours = hours + (mins / 60)
cost_mat = (weight_g / 1000) * mat_cost_per_kg
cost_energy = (printer_info['watts'] / 1000) * total_hours * kwh_cost
cost_depr = (printer_info['preco_maquina'] / max(1, printer_info['vida_util_h'])) * total_hours

total_cost = cost_mat + cost_energy + cost_depr
final_price = total_cost * (1 + (markup / 100))
profit = final_price - total_cost

with col2:
    st.subheader("📊 Demonstrativo de Orçamento")
    
    if weight_g > 0 and total_hours > 0:
        st.metric(label="💰 PREÇO DE VENDA SUGERIDO", value=f"R$ {final_price:.2f}", delta=f"Lucro Limpo: R$ {profit:.2f}")
        
        if qty > 1:
            st.caption(f"Valor por unidade ({qty} un): **R$ {final_price/qty:.2f}**")
            
        st.divider()
        
        df_detalhes = pd.DataFrame({
            "Componente": ["Material (Filamento/Resina)", "Energia Elétrica", "Depreciação Máquina", "Lucro Bruto"],
            "Valor (R$)": [cost_mat, cost_energy, cost_depr, profit]
        })
        st.dataframe(df_detalhes.style.format({"Valor (R$)": "R$ {:.2f}"}), use_container_width=True, hide_index=True)

        st.bar_chart(df_detalhes.set_index("Componente"))

        # Botão para salvar no Google Sheets
        if st.button("💾 Salvar Orçamento no Google Sheets", type="primary"):
            try:
                df_hist = conn.read(spreadsheet=URL_PLANILHA, worksheet="Historico", ttl="0s")
                
                novo_registro = pd.DataFrame([{
                    "nome_projeto": proj_name,
                    "material": mat_selected,
                    "peso_g": weight_g,
                    "tempo_h": round(total_hours, 2),
                    "custo_total": round(total_cost, 2),
                    "preco_venda": round(final_price, 2),
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M")
                }])
                
                df_atualizado = pd.concat([df_hist, novo_registro], ignore_index=True)
                conn.update(spreadsheet=URL_PLANILHA, worksheet="Historico", data=df_atualizado)
                st.success("✅ Orçamento gravado com sucesso na sua planilha do Google!")
            except Exception as ex:
                st.error(f"Erro ao salvar na planilha: {ex}")
    else:
        st.info("Preencha o peso e o tempo de impressão para gerar os resultados.")
