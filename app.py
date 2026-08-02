import streamlit as st
import boto3
import uuid
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="LogixHub", page_icon="📦", layout="centered")

# 2. CSS PARA DESIGN
st.markdown("""
    <style>
    /* Configura a imagem de fundo */
    .stApp {
        background-image: url("https://i.postimg.cc/SRSWBYZ1/imagem-eaata.png");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* Container centralizado e com aspecto de "vidro" */
    .stApp > div:first-child {
        background-color: rgba(0, 0, 0, 0.4); 
        backdrop-filter: blur(10px);          
        padding: 40px;
        border-radius: 20px;                 
        border: 1px solid rgba(255, 255, 255, 0.1); 
        max-width: 850px;                    
        margin: 50px auto;                   
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); 
    }
    
    /* Ajusta cores dos textos e títulos para contraste */
    h1, h2, h3, p, label { color: #ffffff !important; }
    
    /* Botões */
    .stButton>button { 
        width: 100%; 
        border-radius: 5px; 
        background-color: #1f77b4 !important; 
        color: white !important; 
    }
    </style>
""", unsafe_allow_html=True)

# 3. CONFIGURAÇÕES AWS
NOME_BUCKET = 'controle-logistica-app'
NOME_TABELA = 'Controle-Logistica'

dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
table = dynamodb.Table(NOME_TABELA)
s3 = boto3.client('s3', region_name='us-east-2')

# --- DEFINIÇÃO DAS ABAS ---
aba_registro, aba_gerenciamento = st.tabs(["📥 Registrar Novo", "📋 Gerenciamento"])

# --- CONTEÚDO DA ABA 1: REGISTRO ---
with aba_registro:
    st.title("📦 LogixHub")
    st.subheader("Controle de Ativos e Logística")
    
    nome = st.text_input("Seu Nome")
    tipo = st.selectbox("Tipo de Item", ["Veículo", "Equipamento"])
    
    # Nova funcionalidade: Câmera ativa
    captured_image = st.camera_input("Tirar foto do item")

    if st.button("Registrar"):
        if nome and captured_image:
            item_id = str(uuid.uuid4())
            file_name = f"{item_id}.jpg"
            
            # O st.camera_input retorna o arquivo no formato perfeito para o S3
            s3.upload_fileobj(captured_image, NOME_BUCKET, file_name)
            
            table.put_item(
                Item={
                    'id': item_id,
                    'nome_usuario': nome,
                    'tipo': tipo,
                    'foto_url': f"https://{NOME_BUCKET}.s3.amazonaws.com/{file_name}",
                    'data': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            )
            st.success("Registro feito com sucesso!")
            st.rerun()
        else:
            st.error("Por favor, preencha o nome e tire a foto.")

# --- CONTEÚDO DA ABA 2: GERENCIAMENTO ---
with aba_gerenciamento:
    st.header("🖼️ Galeria e Gerenciamento")
    
    # 1. Busca e Filtro (que já fizemos)
    col1, col2 = st.columns(2)
    busca_nome = col1.text_input("🔍 Buscar por nome do usuário")
    filtro_tipo = col2.multiselect("⚙️ Filtrar por tipo", ["Veículo", "Equipamento"])
    
    try:
        response = table.scan()
        items = response.get('Items', [])

        if items:
            # Filtros
            if busca_nome:
                items = [i for i in items if busca_nome.lower() in i['nome_usuario'].lower()]
            if filtro_tipo:
                items = [i for i in items if i['tipo'] in filtro_tipo]

            items = sorted(items, key=lambda x: x['data'], reverse=True)
            
            # Galeria com botões de Edição e Exclusão
            cols = st.columns(3) 
            for i, item in enumerate(items):
                with cols[i % 3]:
                    st.write(f"**{item['nome_usuario']}**")
                    st.caption(f"Tipo: {item['tipo']}")
                    st.image(item['foto_url'], use_container_width=True)
                    st.caption(f"Data: {item['data']}")
                    
                    # Ação: Excluir
                    if st.button("🗑️ Excluir", key=f"del_{item['id']}"):
                        # Remove do S3
                        file_name = item['foto_url'].split('/')[-1]
                        s3.delete_object(Bucket=NOME_BUCKET, Key=file_name)
                        # Remove do DynamoDB
                        table.delete_item(Key={'id': item['id']})
                        st.rerun()

                    # Ação: Editar (Expander)
                    with st.expander("✏️ Editar"):
                        novo_nome = st.text_input("Novo Nome", value=item['nome_usuario'], key=f"name_{item['id']}")
                        novo_tipo = st.selectbox("Novo Tipo", ["Veículo", "Equipamento"], 
                                                index=0 if item['tipo']=="Veículo" else 1, 
                                                key=f"type_{item['id']}")
                        
                        if st.button("Salvar Alterações", key=f"save_{item['id']}"):
                            table.update_item(
                                Key={'id': item['id']},
                                UpdateExpression="set nome_usuario = :n, tipo = :t",
                                ExpressionAttributeValues={':n': novo_nome, ':t': novo_tipo}
                            )
                            st.success("Atualizado!")
                            st.rerun()
        else:
            st.info("Nenhum item registrado.")
            
    except Exception as e:
        st.error(f"Erro: {e}")