import os
import glob
import pandas as pd
import psycopg2
import re
from datetime import datetime

# Configuração PostgreSQL
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5499,
    'database': 'analytics_db',
    'user': 'postgres',
    'password': 'postgres'
}

# Pasta dos dados
DATA_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'data', 'brasil')

class DataProcessor:
    def __init__(self):
        self.processed_records = []
        self.processing_stats = {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }

    def detect_table_type(self, df_raw, filename):
        """
        Detecta o tipo de tabela baseado no conteúdo e estrutura
        """
        # Converte tudo para string para análise
        content_text = ' '.join([str(cell) for row in df_raw.values for cell in row if pd.notna(cell)])
        
        # Tipos de tabela identificados pelos padrões
        table_patterns = {
            'demografia_sexo_idade': ['sexo', 'grupos de idade', 'cor ou raça'],
            'domicilios_situacao': ['situação do domicílio', 'número de moradores'],
            'rendimento_classes': ['classes de rendimento', 'salário mínimo'],
            'regioes_geograficas': ['Grandes Regiões', 'Unidades da Federação', 'Norte', 'Nordeste', 'Sul'],
            'moradores_seguranca': ['moradores em domicílios particulares', 'situação de segurança alimentar'],
            'ocupacao_trabalho': ['pessoa de referência ocupada', 'horas trabalhadas', 'semana de referência'],
            'inseguranca_tipos': ['tipo de insegurança alimentar', 'leve', 'moderada', 'grave']
        }
        
        detected_type = 'unknown'
        max_matches = 0
        
        for table_type, patterns in table_patterns.items():
            matches = sum(1 for pattern in patterns if pattern.lower() in content_text.lower())
            if matches > max_matches:
                max_matches = matches
                detected_type = table_type
        
        print(f"  📋 Tipo detectado: {detected_type} (matches: {max_matches})")
        return detected_type

    def find_data_start(self, df_raw):
        """
        Encontra onde começam os dados numéricos na tabela
        """
        for i, row in df_raw.iterrows():
            # Procura por linhas que tenham pelo menos 2 valores numéricos
            numeric_count = 0
            for val in row:
                if pd.notna(val) and isinstance(val, (int, float)) and val != 0:
                    numeric_count += 1
            
            # Também verifica se há anos (2004, 2009, etc.)
            has_year = any(str(val).isdigit() and 2000 <= float(val) <= 2030 
                          for val in row if pd.notna(val))
            
            if numeric_count >= 2 or has_year:
                return i
        
        return -1

    def extract_year(self, df_data):
        """
        Extrai o ano dos dados
        """
        for _, row in df_data.head(10).iterrows():
            for val in row:
                if pd.notna(val) and str(val).isdigit():
                    year = int(float(val))
                    if 2000 <= year <= 2030:
                        return year
        return None

    def classify_localidade(self, localidade_raw):
        """
        Classifica e limpa os nomes das localidades
        """
        if pd.isna(localidade_raw):
            return None, None, None
        
        localidade = str(localidade_raw).strip()
        
        # Remove prefixos comuns
        localidade = re.sub(r'^[\s]*[-]*[\s]*', '', localidade)
        localidade = re.sub(r'^\s*\d+\s*', '', localidade)  # Remove números no início
        
        # Classificações
        categoria = 'outros'
        subcategoria = None
        localidade_clean = localidade
        
        # Faixas etárias
        if re.search(r'\d+\s*a\s*\d+\s*anos?', localidade, re.IGNORECASE):
            categoria = 'faixa_etaria'
            if '0 a 4' in localidade or '0-4' in localidade:
                subcategoria = '0-4_anos'
                localidade_clean = '0 a 4 anos'
            elif '5 a 17' in localidade or '5-17' in localidade:
                subcategoria = '5-17_anos'
                localidade_clean = '5 a 17 anos'
            elif '18 a 49' in localidade or '18-49' in localidade:
                subcategoria = '18-49_anos'
                localidade_clean = '18 a 49 anos'
            elif '50 a 64' in localidade or '50-64' in localidade:
                subcategoria = '50-64_anos'
                localidade_clean = '50 a 64 anos'
            elif '65 anos' in localidade or '65+' in localidade:
                subcategoria = '65_anos_mais'
                localidade_clean = '65 anos ou mais'
        
        # Gênero
        elif 'homens' in localidade.lower() and 'mulheres' not in localidade.lower():
            categoria = 'genero'
            subcategoria = 'homens'
            localidade_clean = 'Homens'
        elif 'mulheres' in localidade.lower():
            categoria = 'genero'
            subcategoria = 'mulheres'
            localidade_clean = 'Mulheres'
        
        # Faixas de renda - Melhorada para capturar mais casos
        elif 'salário' in localidade.lower() or 'rendimento' in localidade.lower():
            categoria = 'faixa_renda'
            if '1/4 do salário' in localidade or 'até 1/4' in localidade:
                subcategoria = 'ate_1_4_sm'
                localidade_clean = 'Até 1/4 do salário mínimo'
            elif '1/4 a 1/2' in localidade or 'de 1/4 a 1/2' in localidade:
                subcategoria = '1_4_a_1_2_sm'
                localidade_clean = 'Mais de 1/4 a 1/2 salário mínimo'
            elif '1/2 a 1 salário' in localidade or 'de 1/2 a 1' in localidade:
                subcategoria = '1_2_a_1_sm'
                localidade_clean = 'Mais de 1/2 a 1 salário mínimo'
            elif '1 a 2 salários' in localidade or 'de 1 a 2' in localidade:
                subcategoria = '1_a_2_sm'
                localidade_clean = 'Mais de 1 a 2 salários mínimos'
            elif '2 a 3 salários' in localidade or 'de 2 a 3' in localidade:
                subcategoria = '2_a_3_sm'
                localidade_clean = 'Mais de 2 a 3 salários mínimos'
            elif '3 a 5 salários' in localidade or 'de 3 a 5' in localidade:
                subcategoria = '3_a_5_sm'
                localidade_clean = 'Mais de 3 a 5 salários mínimos'
            elif ('mais de 2 salários' in localidade.lower() and 'mínimos' in localidade.lower()) or 'mais de 2 sm' in localidade.lower():
                subcategoria = 'mais_2_sm'
                localidade_clean = 'Mais de 2 salários mínimos'
            elif '5 salários' in localidade and 'mais' in localidade:
                subcategoria = 'mais_5_sm'
                localidade_clean = 'Mais de 5 salários mínimos'
            elif 'sem rend' in localidade.lower():
                subcategoria = 'sem_rendimento'
                localidade_clean = 'Sem rendimento'
        
        # Regiões geográficas
        elif any(regiao in localidade for regiao in ['Norte', 'Nordeste', 'Sudeste', 'Sul', 'Centro-Oeste']):
            categoria = 'regiao'
            for regiao in ['Norte', 'Nordeste', 'Sudeste', 'Sul', 'Centro-Oeste']:
                if regiao in localidade:
                    subcategoria = regiao.lower().replace('-', '_')
                    localidade_clean = regiao
                    break
        
        # Cor ou raça
        elif any(cor in localidade.lower() for cor in ['branca', 'preta', 'amarela', 'parda', 'indígena']):
            categoria = 'cor_raca'
            if 'branca' in localidade.lower():
                subcategoria = 'branca'
                localidade_clean = 'Branca'
            elif 'preta' in localidade.lower():
                subcategoria = 'preta'
                localidade_clean = 'Preta'
            elif 'amarela' in localidade.lower():
                subcategoria = 'amarela'
                localidade_clean = 'Amarela'
            elif 'parda' in localidade.lower():
                subcategoria = 'parda'
                localidade_clean = 'Parda'
            elif 'indígena' in localidade.lower():
                subcategoria = 'indigena'
                localidade_clean = 'Indígena'
        
        # Estados (UF) - Lista completa e melhorada
        elif any(uf in localidade for uf in ['Acre', 'Alagoas', 'Amapá', 'Amazonas', 'Bahia', 'Ceará', 
                                            'Distrito Federal', 'Espírito Santo', 'Goiás', 'Maranhão',
                                            'Mato Grosso do Sul', 'Mato Grosso', 'Minas Gerais', 'Pará', 
                                            'Paraíba', 'Paraná', 'Pernambuco', 'Piauí', 'Rio de Janeiro', 
                                            'Rio Grande do Norte', 'Rio Grande do Sul', 'Rondônia', 'Roraima', 
                                            'Santa Catarina', 'São Paulo', 'Sergipe', 'Tocantins']):
            categoria = 'estado'
            # Mapeamento específico para estados
            estado_map = {
                'Acre': 'acre', 'Alagoas': 'alagoas', 'Amapá': 'amapa', 'Amazonas': 'amazonas',
                'Bahia': 'bahia', 'Ceará': 'ceara', 'Distrito Federal': 'distrito_federal',
                'Espírito Santo': 'espirito_santo', 'Goiás': 'goias', 'Maranhão': 'maranhao',
                'Mato Grosso do Sul': 'mato_grosso_do_sul', 'Mato Grosso': 'mato_grosso',
                'Minas Gerais': 'minas_gerais', 'Pará': 'para', 'Paraíba': 'paraiba',
                'Paraná': 'parana', 'Pernambuco': 'pernambuco', 'Piauí': 'piaui',
                'Rio de Janeiro': 'rio_de_janeiro', 'Rio Grande do Norte': 'rio_grande_do_norte',
                'Rio Grande do Sul': 'rio_grande_do_sul', 'Rondônia': 'rondonia',
                'Roraima': 'roraima', 'Santa Catarina': 'santa_catarina',
                'São Paulo': 'sao_paulo', 'Sergipe': 'sergipe', 'Tocantins': 'tocantins'
            }
            for estado_nome, estado_cod in estado_map.items():
                if estado_nome in localidade:
                    subcategoria = estado_cod
                    localidade_clean = estado_nome
                    break
        
        # Situação do domicílio
        elif 'urbana' in localidade.lower():
            categoria = 'situacao_domicilio'
            subcategoria = 'urbana'
            localidade_clean = 'Urbana'
        elif 'rural' in localidade.lower():
            categoria = 'situacao_domicilio'
            subcategoria = 'rural'
            localidade_clean = 'Rural'
        
        # Número de moradores
        elif re.search(r'\d+\s*moradores?', localidade, re.IGNORECASE):
            categoria = 'num_moradores'
            if 'até 3' in localidade or 'Até 3' in localidade:
                subcategoria = 'ate_3'
                localidade_clean = 'Até 3 moradores'
            elif '4 a 6' in localidade:
                subcategoria = '4_a_6'
                localidade_clean = '4 a 6 moradores'
            elif '7 moradores ou mais' in localidade or '7 ou mais' in localidade:
                subcategoria = '7_ou_mais'
                localidade_clean = '7 moradores ou mais'
        
        # Ocupação/Trabalho
        elif 'horas' in localidade.lower() and 'trabalh' in localidade.lower():
            categoria = 'horas_trabalho'
            if 'até 39' in localidade.lower():
                subcategoria = 'ate_39h'
                localidade_clean = 'Até 39 horas'
            elif '40 a 44' in localidade:
                subcategoria = '40_a_44h'
                localidade_clean = '40 a 44 horas'
            elif '45 horas ou mais' in localidade or '45 ou mais' in localidade:
                subcategoria = '45h_ou_mais'
                localidade_clean = '45 horas ou mais'
        
        # Situações de segurança alimentar (que não deveriam ser localidades)
        elif any(seg in localidade.lower() for seg in ['com segurança alimentar', 'insegurança alimentar', 'com insegurança']):
            categoria = 'situacao_seguranca'
            if 'com segurança alimentar' in localidade.lower():
                subcategoria = 'com_seguranca'
                localidade_clean = 'Com segurança alimentar'
            elif 'insegurança alimentar leve' in localidade.lower():
                subcategoria = 'inseg_leve'
                localidade_clean = 'Com insegurança alimentar leve'
            elif 'insegurança alimentar moderada' in localidade.lower() or 'moderada ou grave' in localidade.lower():
                subcategoria = 'inseg_moderada_grave'
                localidade_clean = 'Com insegurança alimentar moderada ou grave'
            elif 'insegurança alimentar' in localidade.lower():
                subcategoria = 'inseg_total'
                localidade_clean = 'Com insegurança alimentar'
        
        # Condição de ocupação do domicílio
        elif any(ocup in localidade.lower() for ocup in ['próprio', 'alugado', 'cedido', 'outra']):
            categoria = 'condicao_ocupacao'
            if 'próprio' in localidade.lower():
                subcategoria = 'proprio'
                localidade_clean = 'Próprio'
            elif 'alugado' in localidade.lower():
                subcategoria = 'alugado'
                localidade_clean = 'Alugado'
            elif 'cedido' in localidade.lower():
                subcategoria = 'cedido'
                localidade_clean = 'Cedido'
        
        # Brasil e totais
        elif 'brasil' in localidade.lower():
            categoria = 'pais'
            subcategoria = 'brasil'
            localidade_clean = 'Brasil'
        elif 'total' in localidade.lower():
            categoria = 'total'
            subcategoria = 'geral'
            localidade_clean = 'Total Geral'
        
        return localidade_clean, categoria, subcategoria

    def process_file_by_type(self, filepath, table_type):
        """
        Processa arquivo baseado no tipo detectado
        """
        filename = os.path.basename(filepath)
        df_raw = pd.read_excel(filepath, header=None, engine="xlrd")
        
        # Encontra início dos dados
        data_start = self.find_data_start(df_raw)
        if data_start == -1:
            return None
        
        # Extrai dados
        df_data = df_raw.iloc[data_start:].copy()
        df_data = df_data.dropna(how='all')  # Remove linhas vazias
        
        # Extrai ano
        ano = self.extract_year(df_data)
        
        # Processa baseado no tipo
        records = []
        
        for _, row in df_data.iterrows():
            # Primeiro valor não-nulo é geralmente a localidade
            localidade_raw = None
            valores = []
            
            for i, val in enumerate(row):
                if pd.notna(val):
                    if localidade_raw is None and not isinstance(val, (int, float)):
                        localidade_raw = val
                    elif isinstance(val, (int, float)) and val != 0:
                        valores.append((i, val))
            
            if localidade_raw and valores:
                localidade_clean, categoria, subcategoria = self.classify_localidade(localidade_raw)
                
                if localidade_clean and categoria != 'total':  # Pula totais genéricos
                    for col_idx, valor in valores:
                        # Determina o tipo de segurança baseado na posição da coluna
                        nivel_seguranca = self.determine_security_level(col_idx, table_type, len(row))
                        
                        record = {
                            'localidade': localidade_clean,
                            'categoria_localidade': categoria,
                            'subcategoria_localidade': subcategoria,
                            'nivel_seguranca': nivel_seguranca,
                            'valor': float(valor),
                            'arquivo_origem': filename,
                            'ano': ano,
                            'tipo_tabela': table_type,
                            'data_processamento': datetime.now()
                        }
                        records.append(record)
        
        return records

    def determine_security_level(self, col_idx, table_type, total_cols):
        """
        Determina o nível de segurança baseado na posição da coluna e tipo de tabela
        """
        # Mapeamentos básicos por posição (ajustáveis conforme padrões encontrados)
        if table_type == 'demografia_sexo_idade':
            mapping = {1: 'total_geral', 2: 'com_seguranca', 3: 'inseg_total', 
                      4: 'inseg_leve', 5: 'inseg_moderada', 6: 'inseg_grave'}
        elif table_type == 'rendimento_classes':
            mapping = {1: 'inseg_total', 2: 'ate_1_4_sm', 3: 'mais_1_4_a_1_2_sm',
                      4: 'mais_1_2_a_1_sm', 5: 'mais_1_2_sm', 6: 'sem_rendimento'}
        elif table_type == 'regioes_geograficas':
            mapping = {1: 'inseg_total', 2: 'ate_1_4_sm', 3: 'mais_1_4_a_1_2_sm',
                      4: 'mais_1_2_a_1_sm', 5: 'mais_1_2_sm', 6: 'mais_2_sm', 7: 'sem_rendimento'}
        elif table_type == 'moradores_seguranca':
            mapping = {1: 'total_homens', 2: 'total_mulheres', 3: 'seg_homens', 4: 'seg_mulheres',
                      5: 'inseg_leve_homens', 6: 'inseg_leve_mulheres', 7: 'inseg_grave_homens', 8: 'inseg_grave_mulheres'}
        elif table_type == 'ocupacao_trabalho':
            mapping = {1: 'total_geral', 2: 'ate_39h', 3: 'de_40_a_44h', 4: 'mais_45h'}
        else:
            # Mapeamento genérico
            mapping = {1: 'total_geral', 2: 'com_seguranca', 3: 'inseg_total',
                      4: 'inseg_leve', 5: 'inseg_moderada', 6: 'inseg_grave'}
        
        return mapping.get(col_idx, f'coluna_{col_idx}')

    def save_to_postgres(self, all_records):
        """
        Salva todos os registros no PostgreSQL com estrutura melhorada
        """
        try:
            conn = psycopg2.connect(**POSTGRES_CONFIG)
            cursor = conn.cursor()
            
            # Remove views dependentes primeiro
            cursor.execute("""
            DROP VIEW IF EXISTS v_analise_faixa_etaria CASCADE;
            DROP VIEW IF EXISTS v_analise_genero CASCADE;
            DROP VIEW IF EXISTS v_analise_renda CASCADE;
            DROP VIEW IF EXISTS v_analise_regioes CASCADE;
            DROP VIEW IF EXISTS v_analise_domicilio CASCADE;
            DROP VIEW IF EXISTS v_resumo_categorias CASCADE;
            DROP VIEW IF EXISTS v_ranking_geral CASCADE;
            DROP VIEW IF EXISTS v_metricas_dashboard CASCADE;
            """)
            
            # Cria tabela melhorada
            cursor.execute("""
            DROP TABLE IF EXISTS seguranca_alimentar_completa CASCADE;
            CREATE TABLE seguranca_alimentar_completa (
                id SERIAL PRIMARY KEY,
                localidade VARCHAR(500) NOT NULL,
                categoria_localidade VARCHAR(100),
                subcategoria_localidade VARCHAR(100),
                nivel_seguranca VARCHAR(100) NOT NULL,
                valor DECIMAL(15,10),
                arquivo_origem VARCHAR(100) NOT NULL,
                ano INTEGER,
                tipo_tabela VARCHAR(100),
                data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Índices para performance
            CREATE INDEX idx_localidade_completa ON seguranca_alimentar_completa(localidade);
            CREATE INDEX idx_categoria ON seguranca_alimentar_completa(categoria_localidade);
            CREATE INDEX idx_nivel_seguranca_completa ON seguranca_alimentar_completa(nivel_seguranca);
            CREATE INDEX idx_ano_completa ON seguranca_alimentar_completa(ano);
            """)
            
            # Insere dados
            insert_query = """
            INSERT INTO seguranca_alimentar_completa 
            (localidade, categoria_localidade, subcategoria_localidade, nivel_seguranca, 
             valor, arquivo_origem, ano, tipo_tabela)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            batch_size = 1000
            total_records = len(all_records)
            
            for i in range(0, total_records, batch_size):
                batch = all_records[i:i+batch_size]
                
                data_to_insert = [
                    (
                        record['localidade'],
                        record['categoria_localidade'],
                        record['subcategoria_localidade'],
                        record['nivel_seguranca'],
                        record['valor'],
                        record['arquivo_origem'],
                        record['ano'],
                        record['tipo_tabela']
                    )
                    for record in batch
                ]
                
                cursor.executemany(insert_query, data_to_insert)
                print(f"     📊 Salvos {min(i+batch_size, total_records)}/{total_records} registros...")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print("✅ Dados salvos com sucesso na nova tabela estruturada!")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar no PostgreSQL: {e}")
            return False

    def process_all_files(self):
        """
        Processa todos os arquivos XLS
        """
        print("🚀 INICIANDO PROCESSAMENTO COMPLETO E INTELIGENTE")
        print("=" * 60)
        
        # Busca todos os arquivos
        pattern = os.path.join(DATA_FOLDER, '*.xls')
        files = glob.glob(pattern)
        
        if not files:
            print(f"❌ Nenhum arquivo encontrado em {DATA_FOLDER}")
            return
        
        self.processing_stats['total_files'] = len(files)
        print(f"📂 Encontrados {len(files)} arquivos para processar")
        print("-" * 60)
        
        all_records = []
        
        for filepath in files:
            filename = os.path.basename(filepath)
            print(f"  📄 Processando: {filename}")
            
            try:
                # Lê arquivo para detectar tipo
                df_raw = pd.read_excel(filepath, header=None, engine="xlrd")
                
                # Detecta tipo de tabela
                table_type = self.detect_table_type(df_raw, filename)
                
                # Processa baseado no tipo
                records = self.process_file_by_type(filepath, table_type)
                
                if records:
                    all_records.extend(records)
                    self.processing_stats['successful'] += 1
                    print(f"     ✅ {len(records)} registros extraídos (Tipo: {table_type})")
                else:
                    self.processing_stats['failed'] += 1
                    print(f"     ⚠️ Nenhum registro extraído")
                
            except Exception as e:
                self.processing_stats['failed'] += 1
                self.processing_stats['errors'].append(f"{filename}: {str(e)}")
                print(f"     ❌ ERRO: {e}")
        
        # Salva todos os registros
        if all_records:
            print(f"\n💾 Salvando {len(all_records)} registros no banco...")
            success = self.save_to_postgres(all_records)
            
            # Relatório final
            self.generate_final_report(len(all_records))
        else:
            print("❌ Nenhum registro foi processado!")

    def generate_final_report(self, total_records):
        """
        Gera relatório final detalhado
        """
        print("\n" + "="*70)
        print("📊 RELATÓRIO FINAL - PROCESSAMENTO COMPLETO")
        print("="*70)
        
        stats = self.processing_stats
        print(f"📁 Total de arquivos: {stats['total_files']}")
        print(f"✅ Processados com sucesso: {stats['successful']}")
        print(f"❌ Falharam: {stats['failed']}")
        print(f"📈 Total de registros: {total_records:,}")
        print(f"📊 Taxa de sucesso: {(stats['successful']/stats['total_files']*100):.1f}%")
        
        if stats['errors']:
            print(f"\n❌ Erros encontrados ({len(stats['errors'])}):")
            for error in stats['errors'][:10]:  # Mostra apenas os primeiros 10
                print(f"   • {error}")
            if len(stats['errors']) > 10:
                print(f"   ... e mais {len(stats['errors'])-10} erros")
        
        print(f"\n🎉 PROCESSAMENTO CONCLUÍDO!")
        print(f"💾 Nova tabela: 'seguranca_alimentar_completa'")
        print(f"🔗 Acesse o Metabase: http://localhost:3000")

def main():
    processor = DataProcessor()
    processor.process_all_files()

if __name__ == "__main__":
    main()