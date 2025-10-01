# Email Classifier

Este é um **Case de estágio da AutoU** desenvolvido em Python com FastAPI, HTML, CSS com Bootstrap, Javascript e SQLite.

> Este projeto foi configurado e testado no **Windows**.

# Funcionalidades

    - Upload de arquivos .txt ou .pdf ou colar texto manualmente.

    - Classificação automática do conteúdo em Produtivo ou Improdutivo.

    - Resposta sugerida com opção de copiar para a área de transferência.

    - Histórico de classificações com filtros por palavra-chave, categoria e data.

    - Exportação do histórico em CSV ou PDF.

    - Interface com cores diferenciadas e usabilidade otimizada.

    - Deploy em nuvem no Render.

# Pré-requisitos

    - Python 3.13 ou superior
    - Git
    - Editor de código (VS Code recomendado)
    - pip 
    - virtualenv (recomendado)

# Guia para executar o projeto localmente

## Clone o repositório
    git clone https://github.com/yLu4n/Email_classifier.git

## Crie e ative um ambiente virtual dentro da pasta clonada
    python -m venv venv
    source venv/bin/activate
    venv\Scripts\activate

## Instale as dependências
    pip install -r requirements.txt

## Rode a aplicação
    uvicorn backend.main:app --reload

## Acesse o link pelo navegador
    http://127.0.0.1:8000/app

# Banco de dados
    O projeto usa SQLite por padrão, armazenado no arquivo emails.db.
    Caso queira trocar para outro banco (ex: PostgreSQL), basta editar database.py e configurar a variável DATABASE_URL

# Tecnologias
    FastAPI
    - API backend

    SQLite
    - Banco de dados

    SQLAlchemy
    - ORM

    PyMuPDF (fitz)
    - Leitura de PDFs

    Bootstrap 5
    - UI/UX

    Render
    - Deploy

