# LGPD Guard

Ferramenta de auditoria contínua de conformidade com a LGPD integrada a pipelines CI/CD via GitHub Actions. Analisa diffs de Pull Requests, detecta padrões de dados pessoais e violações regulatórias, e bloqueia merges em casos críticos.

Funciona com **qualquer repositório** — basta extrair o diff e apontar para a ferramenta.

---

## Como funciona

1. Extrai o diff do Pull Request (ou de qualquer commit)
2. Detector estático identifica padrões de dados pessoais via regex
3. Camada LLM+RAG analisa semanticamente com base nos artigos da LGPD
4. Relatório é publicado como comentário no PR e o merge é bloqueado se houver violações Alta/Crítica

---

## Setup local

### 1. Clone e ambiente

```powershell
git clone https://github.com/L42Matheus/lgpd-guard
cd lgpd-guard
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Se houver erro no `faiss-cpu`:

```powershell
pip install faiss-cpu --prefer-binary
```

### 2. Configure o `.env`

```powershell
copy .env.example .env
```

Abra o `.env` e preencha a chave da Anthropic:

```powershell
notepad .env
```

Adicione sua chave e salve:

```
ANTHROPIC_API_KEY=sk-ant-...
```

> As demais variáveis do `.env.example` são preenchidas automaticamente pelo GitHub Actions no CI/CD — não são necessárias para execução local.

> `main.py` carrega o `.env` automaticamente.

---

## Execução local

### Com LLM (Anthropic — recomendado)

```powershell
python lgpd_guard\main.py `
  --diff .\diffs\<nome>.txt `
  --provider anthropic `
  --output json
```

### Ver raciocínio jurídico completo do LLM

```powershell
python lgpd_guard\main.py `
  --diff .\diffs\<nome>.txt `
  --provider anthropic `
  --output json `
  --include-llm-raw
```

### Sem LLM (apenas detector estático — reprodutível sem API key)

```powershell
python lgpd_guard\main.py `
  --diff .\diffs\<nome>.txt `
  --no-llm `
  --output json
```

### Comparação lado a lado

```powershell
python lgpd_guard\main.py --diff .\diffs\<nome>.txt --provider anthropic --output json > com_llm.json
python lgpd_guard\main.py --diff .\diffs\<nome>.txt --no-llm --output json > sem_llm.json
```

---

## Testando com os exemplos incluídos

O repositório já inclui arquivos de exemplo em `examples/violations/` com violações LGPD anotadas — ideal para testar sem depender de nenhum repositório externo.

### 1. Configurar a API Key (se ainda não fez)

```powershell
copy .env.example .env
notepad .env
```

> Preencha `ANTHROPIC_API_KEY=sk-ant-...` e salve.

### 2. Gerar o diff a partir dos exemplos

O `git diff --no-index` pode gerar formato inválido no Windows. Use o script abaixo que garante o formato correto:

```powershell
# Gera diff do exemplo Java
"diff --git a/UsuarioService.java b/UsuarioService.java`n+++ b/UsuarioService.java" | Out-File .\diffs\exemplo_java.txt -Encoding utf8
Get-Content examples\violations\UsuarioService.java | ForEach-Object { "+$_" } | Add-Content .\diffs\exemplo_java.txt -Encoding utf8

# Gera diff do exemplo Python
"diff --git a/usuario_service.py b/usuario_service.py`n+++ b/usuario_service.py" | Out-File .\diffs\exemplo_python.txt -Encoding utf8
Get-Content examples\violations\usuario_service.py | ForEach-Object { "+$_" } | Add-Content .\diffs\exemplo_python.txt -Encoding utf8
```

### 2. Executar a análise

```powershell
# Sem LLM
python lgpd_guard\main.py --diff .\diffs\exemplo_java.txt --no-llm --output json

# Com LLM
python lgpd_guard\main.py --diff .\diffs\exemplo_java.txt --provider anthropic --output json
```

> Os exemplos contêm violações conhecidas dos Arts. 6º e 46 da LGPD (CPF em log, senha em texto puro, SQL injection com dado pessoal, comunicação sem HTTPS) — útil para validar que a ferramenta está funcionando corretamente antes de apontar para repositórios reais.

---

## Analisando qualquer repositório

O LGPD Guard funciona com qualquer repositório Git. O fluxo completo:

### 1. Clone o repositório alvo lado a lado com o lgpd-guard

```
<pasta-pai>/
├── lgpd-guard/
└── meu-projeto/
```

```powershell
cd <pasta-pai>
git clone https://github.com/<org>/<repositorio>
```

### 2. Buscar commits com dados pessoais (Git Pickaxe)

Dentro do repositório alvo:

```powershell
cd <repositorio>

# Buscar commits que adicionaram/removeram referências a CPF
git log --all -S "cpf" --oneline

# Outros termos úteis
git log --all -S "email" --oneline
git log --all -S "senha" --oneline
git log --all -S "telefone" --oneline
```

### 3. Inspecionar o commit

```powershell
git show <hash> --stat
git show <hash>
```

### 4. Extrair o diff

```powershell
# Diff completo
git show <hash> | Out-File `
  -FilePath ..\lgpd-guard\diffs\<nome>.txt `
  -Encoding utf8

# Se houver ruído de bundles/minificados, filtrar para src/
git show <hash> -- src/ | Out-File `
  -FilePath ..\lgpd-guard\diffs\<nome>_src.txt `
  -Encoding utf8
```

### 5. Executar a análise

```powershell
cd ..\lgpd-guard

python lgpd_guard\main.py `
  --diff .\diffs\<nome>.txt `
  --provider anthropic `
  --output json
```

---

## Campos do resultado JSON

| Campo | Descrição |
|-------|-----------|
| `violations` | Violações detectadas pelo módulo estático |
| `llm_violations` | Violações adicionais identificadas pelo LLM |
| `personal_data_count` | Linhas com indício de dado pessoal |
| `should_fail` | `true` = merge deve ser bloqueado |
| `llm_analysis_raw` | Raciocínio jurídico completo do LLM (com `--include-llm-raw`) |

**Regra de bloqueio:** se houver pelo menos 1 violação de severidade `ALTA` ou `CRÍTICA` (estática ou LLM), o pipeline falha e o merge fica bloqueado.

---

## Integração CI/CD (GitHub Actions)

Adicione ao seu repositório em `.github/workflows/lgpd-check.yml`:

```yaml
name: LGPD Guard
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  lgpd-check:
    runs-on: ubuntu-latest
    steps:
      - uses: L42Matheus/lgpd-guard@main
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Configure o secret `ANTHROPIC_API_KEY` em **Settings → Secrets → Actions** do seu repositório.

---

## Troubleshooting

**Falha de chave LLM**
```
Analise LLM falhou: 'ANTHROPIC_API_KEY'
```
1. Verifique se `.env` existe na raiz
2. Verifique se `ANTHROPIC_API_KEY=...` está preenchido
3. Alternativa: rode com `--no-llm`

---

**Aviso de deprecação do LangChain**
```
LangChainDeprecationWarning: HuggingFaceEmbeddings was deprecated...
```
Não interrompe a execução. Migração para `langchain_huggingface` planejada em versão futura.

---

**Pipeline bloqueado por LGPD**
```
Pipeline falhando devido a violacoes criticas/altas de LGPD.
```
Causa comum: `log` ou `print` com CPF, e-mail, nome ou telefone sem mascaramento. Veja o campo `violations` no JSON para localizar arquivo e linha.

---

## Estrutura do projeto

```
lgpd-guard/
├── .github/workflows/lgpd-check.yml
├── lgpd_guard/
│   ├── main.py
│   ├── detector.py
│   ├── analyzer.py
│   ├── reporter.py
│   └── knowledge/lgpd.txt
├── diffs/
├── examples/
├── requirements.txt
├── .env.example
└── README.md
```
