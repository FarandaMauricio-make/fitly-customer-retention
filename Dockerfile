# Usa uma imagem oficial e leve do Python
FROM python:3.10-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de requisitos primeiro (aproveita o cache do Docker)
COPY requirements.txt .

# Instala as dependências do projeto sem guardar cache para deixar a imagem menor
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos os arquivos do projeto (scripts e dados brutos) para o container
COPY . .

# Executa o pipeline de ETL para processar os dados brutos e gerar o Data Mart
RUN python fitly_churn_analysis.py

# Expõe a porta padrão que o Streamlit utiliza
EXPOSE 8501

# Comando de saúde para plataformas de nuvem saberem se o app está no ar
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Comando final que inicia o Dashboard em Streamlit
ENTRYPOINT ["streamlit", "run", "dashboard_fitly_churn_analysis.py", "--server.port=8501", "--server.address=0.0.0.0"]
