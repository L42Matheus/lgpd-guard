# LGPD Guard

Auditoria continua de conformidade LGPD em diffs de Pull Requests, com integracao nativa em GitHub Actions.

Arquitetura:
- Scanner estatico (regex/regras)
- Analise semantica com LLM + RAG (opcional)
- Comentario automatico no PR
- Bloqueio de merge para severidade `ALTA` ou `CRITICA`

## 1. Objetivo do projeto

O LGPD Guard foi projetado para o fluxo de CI/CD descrito no artigo:
- analisar diffs de PR
- mapear evidencias tecnicas para artigos da LGPD
- gerar relatorio acionavel no PR
- bloquear merge quando houver risco relevante

## 2. Fluxo oficial no GitHub Actions (principal)

Workflow: [.github/workflows/lgpd-check.yml](C:\Users\DeLL\Videos\lgpd-guard\.github\workflows\lgpd-check.yml)

Fluxo executado a cada `pull_request`:
1. Faz checkout com historico (`fetch-depth: 0`).
2. Gera diff do PR (`git diff origin/<base>...HEAD`).
3. Executa analise estatica (sempre).
4. Executa analise LLM + RAG (se `LGPD_LLM_ENABLED=true`).
5. Publica comentario no PR.
6. Soma violacoes `ALTA/CRITICA` da camada estatica e LLM.
7. Falha o job se total > 0 (merge bloqueado).

## 3. Como habilitar no seu repositorio

1. Copie o workflow:
```powershell
mkdir .github\workflows -Force
copy .\lgpd-check.yml .\.github\workflows\lgpd-check.yml
```

2. Configure Secrets (Settings -> Secrets and variables -> Actions):
- `ANTHROPIC_API_KEY` (obrigatorio se usar provider anthropic)
- `OPENAI_API_KEY` (opcional, se usar provider openai)

3. Configure Variables (Settings -> Secrets and variables -> Actions):
- `LGPD_LLM_ENABLED=true` para ativar LLM no CI

4. Abra um Pull Request para disparar o pipeline.

## 4. Setup local (suporte e reproducao)

1. Clone e ambiente:
```powershell
git clone <repo>
cd lgpd-guard
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure `.env`:
```powershell
copy .env.example .env
```

Exemplo:
```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=
GITHUB_TOKEN=
GITHUB_REPOSITORY=
GITHUB_SERVER_URL=https://github.com
PR_NUMBER=
```

Observacao: `main.py` carrega `.env` automaticamente.

## 5. Execucao local (com e sem LLM)

Com LLM (Anthropic):
```powershell
python lgpd_guard\main.py --diff .\diffs\sigpae_1e42fbb5a.txt --provider anthropic --output json
```

Sem LLM:
```powershell
python lgpd_guard\main.py --diff .\diffs\sigpae_1e42fbb5a.txt --no-llm --output json
```

Incluir resposta bruta do LLM:
```powershell
python lgpd_guard\main.py --diff .\diffs\sigpae_1e42fbb5a.txt --provider anthropic --output json --include-llm-raw
```

Comparacao lado a lado:
```powershell
python lgpd_guard\main.py --diff .\diffs\sigpae_1e42fbb5a.txt --provider anthropic --output json > com_llm.json
python lgpd_guard\main.py --diff .\diffs\sigpae_1e42fbb5a.txt --no-llm --output json > sem_llm.json
```

## 6. Reproducao da avaliacao do artigo

### 6.1 Estrutura esperada

```text
<pasta-pai>/
|-- lgpd-guard/
|-- SME-SIGPAE-API/
`-- Sistema_Programa_de_Gestao_Susep/
```

### 6.2 Buscar commits com dados pessoais (pickaxe)

Dentro de cada repositorio alvo:
```powershell
git log --all -S "cpf" --oneline
```

Inspecionar commit:
```powershell
git show <hash>
git show <hash> --stat
```

### 6.3 Extrair diffs para o LGPD Guard

Diff completo:
```powershell
git show <hash> | Out-File -FilePath ..\lgpd-guard\diffs\<nome>.txt -Encoding utf8
```

Quando houver ruido de bundles/minificados, filtrar para `src/`:
```powershell
git show <hash> -- src/ | Out-File -FilePath ..\lgpd-guard\diffs\<nome>_src.txt -Encoding utf8
```

### 6.4 Executar analise

```powershell
cd ..\lgpd-guard
python lgpd_guard\main.py --diff .\diffs\<nome>.txt --no-llm --output json
```

## 7. Regra de decisao e bloqueio

Campos relevantes no JSON:
- `violations`: violacoes estaticas
- `llm_violations`: violacoes estruturadas do LLM
- `personal_data_count`: linhas com indicio de dado pessoal
- `should_fail`: bloqueio segundo camada estatica

No GitHub Actions, o bloqueio final considera:
- total de `ALTA/CRITICA` da analise estatica
- + total de `ALTA/CRITICA` da analise LLM (quando habilitada)

Se total > 0, o job falha e o merge fica bloqueado.

## 8. Troubleshooting

### 8.1 Falha de chave LLM

Mensagem:
```text
Analise LLM falhou: 'ANTHROPIC_API_KEY'
```

Checklist:
1. Verifique se `.env` existe na raiz.
2. Verifique se `ANTHROPIC_API_KEY=...` esta preenchido.
3. Se necessario, rode com `--no-llm`.

### 8.2 Aviso de deprecacao do LangChain

Mensagem:
```text
LangChainDeprecationWarning: HuggingFaceEmbeddings was deprecated...
```

Status:
- nao interrompe execucao agora
- requer migracao futura para `langchain_huggingface`

### 8.3 Pipeline falhando por LGPD

Mensagem:
```text
Pipeline falhando devido a violacoes criticas/altas de LGPD.
```

Causa comum:
- log/print com CPF, email, nome ou telefone sem mascaramento

No caso `sigpae_1e42fbb5a.txt`, as ocorrencias reportadas foram em:
- `report_parceiras.py:102`
- `report_parceiras.py:142`

## 9. Estrutura do projeto

```text
lgpd-guard/
|-- .github/workflows/lgpd-check.yml
|-- lgpd_guard/main.py
|-- lgpd_guard/detector.py
|-- lgpd_guard/analyzer.py
|-- lgpd_guard/reporter.py
|-- lgpd_guard/knowledge/lgpd.txt
|-- diffs/
|-- examples/
|-- requirements.txt
|-- .env.example
`-- README.md
```
