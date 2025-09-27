# Análise de Segurança Alimentar no Brasil

Um projeto de análise de dados sobre segurança alimentar brasileira usando dados do IBGE.

## Sobre

Este projeto nasceu da necessidade de visualizar e analisar dados reais de segurança alimentar no Brasil. Utilizando planilhas oficiais do IBGE, criei um pipeline de dados que processa múltiplos arquivos Excel e gera visualizações interativas.

## Tecnologias

- **Python** - Processamento dos dados
- **PostgreSQL** - Armazenamento 
- **Metabase** - Dashboards interativos    http://localhost:3000/public/dashboard/f5e2afda-daf6-4034-bd6e-e6f8b2c962d6
- **Docker** - Containerização dos serviços

## Como executar

### Requisitos
- Docker Desktop
- Python 3.8+

### Instalação

1. Clone o repositório:
```bash
git clone https://github.com/DevPedroLimaB/projeto_seg_alimentar.git
cd projeto_seg_alimentar
```

2. Configure o ambiente Python:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r scripts/requirements.txt
```

3. Inicie os serviços:
```bash
docker-compose up -d
```

### 4. Processe os Dados

```bash
# Execute o script de ETL aprimorado
python ingest_final.py
```

### 5. Configure o Metabase

1. Acesse: http://localhost:3000
2. Configure a conexão com PostgreSQL:
   - **Host**: `postgres` (ou `localhost` se não funcionar)
   - **Port**: `5432` (interno do Docker) ou `5499` (externo)
   - **Database**: `analytics_db`
   - **Username**: `postgres`
   - **Password**: `postgres`

## Estrutura dos dados

A tabela principal `seguranca_alimentar_completa` contém:

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `id` | Identificador único do registro | 1, 2, 3... |
| `localidade` | Nome do estado, região ou categoria | "São Paulo", "Nordeste", "Área Urbana" |
| `categoria_localidade` | Tipo de agrupamento dos dados | "estado", "regiao", "situacao_domicilio" |
| `nivel_seguranca` | Classificação de segurança alimentar | "com_seguranca", "inseg_leve", "inseg_grave" |
| `valor` | Valores populacionais (em milhares) | 15420.3, 8934.7 |
| `arquivo_origem` | Arquivo XLS original | "cv1011.xls", "cv1142.xls" |
| `data_processamento` | Timestamp do processamento | "2025-09-27 10:30:15" |

### Categorias disponíveis:
- `estado` - 27 estados brasileiros
- `regiao` - 5 regiões (Norte, Nordeste, Sul, Sudeste, Centro-Oeste)  
- `situacao_domicilio` - Urbano/Rural
- `faixa_renda` - Classes de renda por salário mínimo
- `cor_raca` - Distribuição étnico-racial
- `num_moradores` - Composição familiar
- `condicao_ocupacao` - Situação de trabalho
- `situacao_seguranca` - Níveis de segurança alimentar

## 🔧 Resolução de Problemas

### Erro: "Docker não encontrado"
- Instale o Docker Desktop
- Certifique-se que está rodando

### Erro: "Conexão recusada PostgreSQL"
- Execute: `docker-compose up -d`
- Aguarde 2-3 minutos
- Verifique: `docker-compose ps`

### Erro: "Arquivo XLS não processado"
- Alguns arquivos têm estruturas diferentes
- O script agora trata automaticamente diferentes formatos
- Verifique os logs para detalhes específicos

### Metabase não mostra dados
- Verifique se o PostgreSQL está conectado
- Use host `postgres` (interno) ou `localhost:5499` (externo)
- Confirme que a tabela `seguranca_alimentar` existe

## Estrutura do projeto

```
projeto_seg_alimentar/
├── .gitignore
├── README.md
├── docker-compose.yml          # Configuração dos serviços
├── queries.sql                 # Queries prontas para Metabase
├── data/
│   └── brasil/                 # 40+ arquivos XLS do IBGE
│       ├── cv1011.xls
│       ├── cv1012.xls
│       └── ...
└── scripts/
    ├── requirements.txt        # Dependências Python
    └── ingest_intelligent.py   # Script principal de ETL
```
