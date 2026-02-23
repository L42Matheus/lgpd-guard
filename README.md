# 🔍 LGPD Guard

> Análise automatizada de conformidade LGPD integrada ao CI/CD

O **LGPD Guard** é um GitHub Action que analisa Pull Requests em busca de violações da [Lei Geral de Proteção de Dados (LGPD - Lei 13.709/2018)](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm), postando um relatório diretamente no PR antes do merge.

---

## Como funciona

```
Developer abre PR
       ↓
GitHub Action dispara automaticamente
       ↓
Análise estática → detecta padrões conhecidos de violação
       ↓
Análise semântica → LangChain + RAG sobre texto da LGPD
       ↓
Comentário automático no PR com violações e sugestões
       ↓
Pipeline falha se houver violações CRÍTICAS ou ALTAS
```

---

## Instalação em 3 passos

### 1. Copie o workflow para seu repositório

```bash
mkdir -p .github/workflows
cp lgpd-check.yml .github/workflows/
```

### 2. Configure os secrets no GitHub

No seu repositório: **Settings → Secrets and variables → Actions**

| Secret | Descrição |
|--------|-----------|
| `ANTHROPIC_API_KEY` | Chave da API Anthropic (Claude) |
| `OPENAI_API_KEY` | Chave da API OpenAI (opcional, para embeddings) |

### 3. (Opcional) Habilite análise com LLM

Em **Settings → Variables → Actions**, adicione:
- `LGPD_LLM_ENABLED` = `true`

> Sem essa variável, roda apenas análise estática (mais rápida, sem custo de API).

---

## Exemplos de violações detectadas

### Java
```java
// ❌ DETECTADO — Art. 46: dado pessoal em log
log.info("Criando usuário CPF: " + usuario.getCpf());

// ✅ CORRETO
log.info("Criando usuário CPF: ***.***.{}-**", cpf.substring(7, 9));
```

### Python
```python
# ❌ DETECTADO — Art. 46: SQL injection com dado pessoal
query = f"SELECT * FROM usuarios WHERE cpf = '{cpf}'"

# ✅ CORRETO
query = "SELECT * FROM usuarios WHERE cpf = ?"
db.execute(query, (cpf,))
```

### JavaScript
```javascript
// ❌ DETECTADO — Art. 6: dado pessoal em analytics sem base legal
analytics.track('signup', { cpf: user.cpf, email: user.email })

// ✅ CORRETO
analytics.track('signup', { userId: user.anonymousId })
```

---

## Violações que o LGPD Guard detecta

| Tipo | Artigo LGPD | Severidade |
|------|-------------|------------|
| Dado pessoal em log sem mascaramento | Art. 46 | 🟠 ALTA |
| Credencial hardcoded no código | Art. 46 | 🔴 CRÍTICA |
| Senha armazenada sem hash | Art. 46 | 🔴 CRÍTICA |
| SQL injection com dado pessoal | Art. 46 | 🔴 CRÍTICA |
| HTTP sem criptografia | Art. 46 | 🟠 ALTA |
| CPF/email enviado para analytics | Art. 6 + Art. 7 | 🟠 ALTA |
| Dado pessoal exposto em URL | Art. 6 + Art. 46 | 🟡 MÉDIA |

---

## Estrutura do projeto

```
lgpd-guard/
├── .github/workflows/
│   └── lgpd-check.yml          ← GitHub Action
├── lgpd_guard/
│   ├── main.py                 ← Orquestrador principal
│   ├── detector.py             ← Análise estática (regex + AST)
│   ├── analyzer.py             ← Análise semântica (LangChain + RAG)
│   ├── reporter.py             ← Formata comentário do PR
│   └── knowledge/
│       └── lgpd.txt            ← Base de conhecimento LGPD
├── examples/violations/        ← Exemplos de código com violações
│   ├── UsuarioService.java
│   └── usuario_service.py
└── requirements.txt
```

---

## Uso local (para testes)

```bash
# Instala dependências
pip install -r requirements.txt

# Gera diff do último commit
git diff HEAD^ HEAD > diff.txt

# Analisa sem LLM (rápido)
cd lgpd_guard
python main.py --diff ../diff.txt --no-llm

# Analisa com LLM (requer API key)
export ANTHROPIC_API_KEY="sua-chave"
python main.py --diff ../diff.txt --provider anthropic

# Testa com os exemplos incluídos
git diff --no-index /dev/null examples/violations/UsuarioService.java > diff_exemplo.txt
python main.py --diff ../diff_exemplo.txt --no-llm
```

---

## Configuração avançada

### Ignorar arquivos ou padrões

Crie um arquivo `.lgpdguard-ignore` na raiz do repositório:

```
# Arquivos de teste podem ter dados fictícios
**/test/**
**/tests/**
**/__tests__/**
**/fixtures/**
```

### Ajustar severidade mínima para bloquear pipeline

No workflow, edite a variável `LGPD_MIN_SEVERITY`:
- `CRÍTICA` — bloqueia apenas violações críticas
- `ALTA` — bloqueia críticas e altas (padrão)
- `MÉDIA` — bloqueia a partir de média

---

## Contexto acadêmico

Este projeto é o MVP do artigo **"Uma Abordagem de Engenharia de Software Inteligente para Conformidade com a LGPD: Uso de LLMs em Pipelines CI/CD para Auditoria Automatizada de Código em Microserviços"**, submetido à Trilha de Ideias Inovadoras e Resultados Emergentes do **SBES 2026** (Simpósio Brasileiro de Engenharia de Software).

---

## Licença

MIT License — use, modifique e distribua livremente.
