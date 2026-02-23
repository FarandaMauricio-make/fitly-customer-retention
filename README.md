# 🏋️‍♀️ Fitly Churn Analytics

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Pandas](https://img.shields.io/badge/Data_Engineering-Pandas-150458)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red)
![Status](https://img.shields.io/badge/Status-Finalizado-brightgreen)

> **Projeto End-to-End de Inteligência de Retenção** para a *Fitly* (empresa fictícia de tecnologia fitness). Este repositório contempla um pipeline completo de dados: desde a extração e limpeza de bases cruas (ETL) até a criação de um Data Mart que alimenta um Dashboard interativo e estratégico.

## 📋 Sobre o Projeto

O Churn (cancelamento de assinaturas) é o principal inimigo de produtos baseados em assinatura (SaaS). O objetivo deste projeto é cruzar dados de três frentes diferentes da Fitly: **Informações de Conta**, **Tickets de Suporte** e **Atividade no App**, para descobrir os padrões comportamentais de usuários propensos ao cancelamento.

A arquitetura do projeto foi desenhada com **separação de responsabilidades**, refletindo as melhores práticas do mercado de dados: um script focado 100% no tratamento de dados (Back-end/ETL) e outro focado 100% na interface com o usuário (Front-end/BI).

---

## ⚙️ Arquitetura da Solução (Data Flow)

### 1. 🧹 Engenharia de Dados e ETL (`fitly_churn_analysis.py`)
O script de processamento lida com problemas reais encontrados em bancos de dados corporativos:
* **Padronização de Chaves:** Resolução de conflitos de IDs (ex: unificando o `user_id` "10125" do suporte com o `customer_id` "C10125" da base de contas).
* **Feature Engineering:** Criação de métricas de alto valor agregado, como:
  * `engagement_quartile`: Segmentação robusta de usuários baseada na frequência de uso do app.
  * `days_since_last_activity`: Cálculo de recência para identificar usuários inativos ("dorminhocos").
  * `avg_resolution_time_hours`: Média de tempo que o suporte leva para resolver problemas de cada cliente.
* **Criação do Data Mart:** Consolidação das três bases em uma única tabela analítica otimizada (`fitly_dashboard_mart.csv`).

### 2. 📊 Visualização e Estratégia (`dashboard_fitly_churn_analysis.py`)
O aplicativo construído em Streamlit consome o Data Mart limpo e oferece:
* **Métricas de KPI:** Visão rápida da taxa de churn e engajamento.
* **Validação Técnica (Auditoria):** Aba dedicada a documentar a integridade e governança dos dados (crucial para o ganho de confiança dos stakeholders).
* **Plano de Ação:** Recomendações práticas e acionáveis para as lideranças (ex: Nudges de ativação para novos usuários e priorização de tickets de contas Pro/Enterprise).

---

## 🛠️ Tecnologias Utilizadas

* **[Python](https://www.python.org/):** Linguagem core da aplicação.
* **[Pandas](https://pandas.pydata.org/):** Limpeza, junção (`merge`) e manipulação dos DataFrames.
* **[Streamlit](https://streamlit.io/):** Criação rápida e responsiva do Web App de visualização.
* **[Plotly Express](https://plotly.com/python/):** Gráficos dinâmicos para exploração de dados.

---

## 📦 Como Rodar o Projeto

Siga os passos abaixo para executar o pipeline completo na sua máquina:

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/SEU-USUARIO/fitly-churn-analytics.git](https://github.com/SEU-USUARIO/fitly-churn-analytics.git)
    cd fitly-churn-analytics
    ```

2.  **Crie e ative um ambiente virtual (Recomendado):**
    ```bash
    python -m venv venv
    # No Windows:
    venv\Scripts\activate
    # No Mac/Linux:
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install pandas numpy streamlit plotly
    ```

4.  **Etapa 1: Rode o Pipeline de Dados (ETL)**
    Isso vai ler as bases brutas (`da_fitly_...`) e gerar o Data Mart limpo.
    ```bash
    python fitly_churn_analysis.py
    ```

5.  **Etapa 2: Inicie o Dashboard**
    Inicie a interface gráfica no seu navegador.
    ```bash
    streamlit run dashboard_fitly_churn_analysis.py
    ```

---

## 📂 Estrutura do Repositório

```text
fitly-churn-analytics/
├── fitly_churn_analysis.py             # Script de ETL e Feature Engineering
├── dashboard_fitly_churn_analysis.py   # Script do App Streamlit (Front-end)
├── da_fitly_account_info.csv           # Dados Brutos: Contas
├── da_fitly_customer_support.csv       # Dados Brutos: Suporte
├── da_fitly_user_activity.csv          # Dados Brutos: Atividade
├── fitly_dashboard_mart.csv            # Data Mart (Output do ETL / Input do Dashboard)
└── README.md                           # Documentação
```
🤝 Contribuição
Tem ideias para prever o churn utilizando Machine Learning (Scikit-Learn)?

Faça um Fork do projeto.

Crie uma Branch para sua feature (git checkout -b feature/PredictiveModel).

Commit suas mudanças.

Push para a Branch.

Abra um Pull Request.

Pode conferir o Dashboard no seguinte link: [fitly-customer-retention](https://fitly-customer-retention.onrender.com)

Construindo produtos melhores através de Dados. 📊
