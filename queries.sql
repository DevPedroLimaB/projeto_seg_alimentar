-- Dashboard de Segurança Alimentar no Brasil
-- Queries para análise de dados do IBGE

-- 1. Taxa Nacional de Segurança Alimentar
SELECT 
    'Taxa Nacional de Segurança Alimentar' as metrica,
    ROUND(
        SUM(CASE WHEN nivel_seguranca = 'com_seguranca' THEN valor ELSE 0 END) * 100.0 / 
        NULLIF(SUM(CASE WHEN nivel_seguranca = 'com_seguranca' THEN valor ELSE 0 END) + 
               SUM(CASE WHEN nivel_seguranca = 'inseg_total' THEN valor ELSE 0 END), 0), 
    2) as percentual
FROM seguranca_alimentar_completa;

-- 2. Pessoas em Insegurança Grave
SELECT 
    'Pessoas em Insegurança Grave' as metrica,
    ROUND(SUM(CASE WHEN nivel_seguranca = 'inseg_grave' THEN valor ELSE 0 END), 0) as total_pessoas
FROM seguranca_alimentar_completa;

-- 3. Mapa do Brasil por Estados
SELECT 
    localidade as estado,
    SUM(valor) as total_pessoas,
    CASE 
        WHEN SUM(valor) > 3000 THEN 'Muito Alto'
        WHEN SUM(valor) > 2000 THEN 'Alto'
        WHEN SUM(valor) > 1000 THEN 'Médio'
        ELSE 'Baixo'
    END as intensidade,
    ROUND(SUM(valor) * 100.0 / (SELECT SUM(valor) FROM seguranca_alimentar_completa WHERE categoria_localidade = 'estado'), 2) as percentual_nacional
FROM seguranca_alimentar_completa 
WHERE categoria_localidade = 'estado'
GROUP BY localidade
ORDER BY total_pessoas DESC;

-- 4. Ranking Estados - Top 15
SELECT 
    SUBSTR(localidade, 1, 12) as estado,
    SUM(valor) as total_pessoas,
    CASE 
        WHEN SUM(valor) > 2000 THEN 'Alto'
        WHEN SUM(valor) > 1500 THEN 'Médio-Alto'
        WHEN SUM(valor) > 1000 THEN 'Médio'
        ELSE 'Baixo'
    END as categoria,
    ROUND(SUM(valor) * 100.0 / (SELECT SUM(valor) FROM seguranca_alimentar_completa WHERE categoria_localidade = 'estado'), 2) as percentual
FROM seguranca_alimentar_completa 
WHERE categoria_localidade = 'estado'
GROUP BY localidade
ORDER BY total_pessoas DESC
LIMIT 15;

-- 5. Distribuição de Renda
SELECT 
    CASE 
        WHEN localidade LIKE '%Sem rendimento%' THEN '1. Sem Rendimento'
        WHEN localidade LIKE '%Até 1/4%' THEN '2. Até 1/4 SM'
        WHEN localidade LIKE '%1/4 a 1/2%' THEN '3. 1/4 a 1/2 SM'
        WHEN localidade LIKE '%1/2 a 1%' THEN '4. 1/2 a 1 SM'
        WHEN localidade LIKE '%1 a 2%' THEN '5. 1 a 2 SM'
        WHEN localidade LIKE '%Mais de 2%' THEN '6. Mais de 2 SM'
        ELSE localidade
    END as faixa_renda,
    SUM(valor) as total_pessoas,
    ROUND(SUM(valor) * 100.0 / (SELECT SUM(valor) FROM seguranca_alimentar_completa WHERE categoria_localidade = 'faixa_renda'), 2) as percentual
FROM seguranca_alimentar_completa 
WHERE categoria_localidade = 'faixa_renda'
GROUP BY localidade
ORDER BY faixa_renda;

-- 6. Regiões Brasileiras
SELECT 
    localidade as regiao,
    SUM(valor) as total_pessoas,
    ROUND(SUM(valor) * 100.0 / (SELECT SUM(valor) FROM seguranca_alimentar_completa WHERE categoria_localidade = 'regiao'), 2) as percentual_nacional
FROM seguranca_alimentar_completa 
WHERE categoria_localidade = 'regiao'
GROUP BY localidade
ORDER BY total_pessoas DESC;

-- 7. Urbano vs Rural
SELECT 
    CASE 
        WHEN localidade LIKE '%Urbana%' THEN 'Área Urbana'
        WHEN localidade LIKE '%Rural%' THEN 'Área Rural'
        ELSE localidade
    END as tipo_area,
    SUM(valor) as total_pessoas,
    ROUND(SUM(valor) * 100.0 / (SELECT SUM(valor) FROM seguranca_alimentar_completa WHERE categoria_localidade = 'situacao_domicilio'), 2) as percentual
FROM seguranca_alimentar_completa 
WHERE categoria_localidade = 'situacao_domicilio'
GROUP BY localidade
ORDER BY total_pessoas DESC;

-- 8. Diversidade Étnico-Racial
SELECT 
    CASE 
        WHEN localidade LIKE '%Branca%' THEN 'Branca'
        WHEN localidade LIKE '%Preta%' THEN 'Preta'
        WHEN localidade LIKE '%Amarela%' OR localidade LIKE '%indígena%' THEN 'Amarela/Indígena'
        WHEN localidade LIKE '%Parda%' THEN 'Parda'
        ELSE localidade
    END as cor_raca,
    SUM(valor) as total_pessoas,
    ROUND(SUM(valor) * 100.0 / (SELECT SUM(valor) FROM seguranca_alimentar_completa WHERE categoria_localidade = 'cor_raca'), 2) as percentual
FROM seguranca_alimentar_completa 
WHERE categoria_localidade = 'cor_raca'
GROUP BY localidade
ORDER BY total_pessoas DESC;