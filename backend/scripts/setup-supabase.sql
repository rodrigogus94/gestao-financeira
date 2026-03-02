-- Executar no SQL Editor do Supabase

-- Tabela de despesas
CREATE TABLE despesas (
    id BIGSERIAL PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    valor DECIMAL(10,2) NOT NULL,
    categoria TEXT NOT NULL CHECK (categoria IN (
        'alimentacao', 'transporte', 'saude', 'educacao', 
        'moradia', 'lazer', 'outros'
    )),
    data DATE NOT NULL,
    descricao TEXT,
    fonte TEXT NOT NULL DEFAULT 'manual' CHECK (fonte IN (
        'manual', 'texto_natural', 'ocr', 'importacao'
    )),
    status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN (
        'pendente', 'confirmada', 'cancelada'
    )),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX idx_despesas_usuario_data ON despesas(usuario_id, data);
CREATE INDEX idx_despesas_categoria ON despesas(categoria);
CREATE INDEX idx_despesas_data ON despesas(data);

-- Tabela de orçamentos mensais
CREATE TABLE orcamentos_mensais (
    id BIGSERIAL PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    limites JSONB NOT NULL, -- {"alimentacao": 1000, "transporte": 500}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(usuario_id, ano, mes)
);

-- Tabela de documentos processados
CREATE TABLE documentos (
    id BIGSERIAL PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    nome_arquivo TEXT NOT NULL,
    tipo_documento TEXT NOT NULL, -- 'nota_fiscal', 'boleto', 'outros'
    conteudo_extraido JSONB,
    status TEXT NOT NULL DEFAULT 'processado',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_despesas_updated_at
    BEFORE UPDATE ON despesas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_orcamentos_updated_at
    BEFORE UPDATE ON orcamentos_mensais
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Políticas de segurança (RLS)
ALTER TABLE despesas ENABLE ROW LEVEL SECURITY;
ALTER TABLE orcamentos_mensais ENABLE ROW LEVEL SECURITY;
ALTER TABLE documentos ENABLE ROW LEVEL SECURITY;

-- Política: usuários só veem próprios dados
CREATE POLICY "Usuários podem ver próprias despesas"
    ON despesas FOR ALL
    USING (usuario_id = auth.uid()::text);

CREATE POLICY "Usuários podem ver próprios orçamentos"
    ON orcamentos_mensais FOR ALL
    USING (usuario_id = auth.uid()::text);

CREATE POLICY "Usuários podem ver próprios documentos"
    ON documentos FOR ALL
    USING (usuario_id = auth.uid()::text);