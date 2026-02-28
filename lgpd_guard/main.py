"""
Script principal do LGPD Guard.
Orquestra detecÃ§Ã£o, anÃ¡lise e report para o PR do GitHub.

Uso:
  python main.py --diff diff.txt
  python main.py --diff diff.txt --post-comment --pr-number 42
  python main.py --diff diff.txt --provider openai
"""

import argparse
import json
import os
import re
import sys
import subprocess

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

from detector import parse_diff, detect_personal_data, detect_violations
from reporter import (
    format_pr_comment,
    format_summary_log,
    should_fail_pipeline
)


def get_pr_diff() -> str:
    """ObtÃ©m o diff do PR via git."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD^", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        # Fallback: diff da Ã¡rea de staging
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True
        )
        return result.stdout


def post_github_comment(comment: str, pr_number: int, repo: str, token: str):
    """Posta o comentÃ¡rio no PR via GitHub API."""
    import urllib.request

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    data = json.dumps({"body": comment}).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/vnd.github+json")

    with urllib.request.urlopen(req) as response:
        if response.status == 201:
            print("Comentario postado no PR com sucesso.")
        else:
            print(f"Falha ao postar comentario: {response.status}")


def _extract_llm_violations(llm_analysis: str | None) -> list:
    """Extrai violaÃ§Ãµes estruturadas do texto retornado pelo LLM.

    O prompt pede JSON, mas alguns modelos podem responder com markdown/fences.
    """
    if not llm_analysis:
        return []

    candidates = [llm_analysis.strip()]
    candidates.extend(
        re.findall(r"```(?:json)?\s*(.*?)\s*```", llm_analysis, flags=re.IGNORECASE | re.DOTALL)
    )

    start = llm_analysis.find("{")
    end = llm_analysis.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(llm_analysis[start:end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue

        if isinstance(parsed, dict):
            violations = parsed.get("violacoes") or parsed.get("violations") or []
            if isinstance(violations, list):
                return violations

    return []


def main():
    if load_dotenv:
        load_dotenv()

    parser = argparse.ArgumentParser(description="LGPD Guard - Analisador de conformidade LGPD")
    parser.add_argument("--diff", help="Arquivo com o diff git (se omitido, usa git diff)")
    parser.add_argument("--provider", default="anthropic",
                        choices=["anthropic", "openai"],
                        help="Provider do LLM (default: anthropic)")
    parser.add_argument("--no-llm", action="store_true",
                        help="Executa apenas analise estatica (sem LLM, mais rapido)")
    parser.add_argument("--post-comment", action="store_true",
                        help="Posta comentÃ¡rio no PR do GitHub")
    parser.add_argument("--pr-number", type=int,
                        help="Numero do PR para postar comentario")
    parser.add_argument("--output", choices=["text", "json"], default="text",
                        help="Formato de saida")
    parser.add_argument("--include-llm-raw", action="store_true",
                        help="Inclui llm_analysis_raw completo no JSON de saida")
    args = parser.parse_args()

    # â”€â”€ 1. ObtÃ©m o diff â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if args.diff:
        with open(args.diff, "r", encoding="utf-8") as f:
            diff_text = f.read()
    else:
        diff_text = get_pr_diff()

    if not diff_text.strip():
        print("Nenhuma alteracao encontrada no diff.")
        sys.exit(0)

    # â”€â”€ 2. AnÃ¡lise estÃ¡tica â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("Analisando diff...")
    files = parse_diff(diff_text)
    personal_data = detect_personal_data(files)
    violations = detect_violations(files)

    print(f"  -> {len(personal_data)} uso(s) de dados pessoais detectado(s)")
    print(f"  -> {len(violations)} violacao(oes) detectada(s) por regras estaticas")

    # â”€â”€ 3. AnÃ¡lise semÃ¢ntica com LLM (opcional) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    llm_analysis = None
    if not args.no_llm and (personal_data or violations):
        print(f"Iniciando analise semantica com LLM ({args.provider})...")
        try:
            from analyzer import LGPDAnalyzer
            analyzer = LGPDAnalyzer(provider=args.provider)
            llm_analysis = analyzer.analyze_personal_data_flow(personal_data, violations)
            print("  -> Analise LLM concluida")
        except Exception as e:
            print(f"  !! Analise LLM falhou: {e}")
            print("  -> Continuando apenas com analise estatica")

    # â”€â”€ 4. Formata resultado â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    pr_url = None
    if os.environ.get("GITHUB_SERVER_URL") and os.environ.get("GITHUB_REPOSITORY"):
        pr_url = (f"{os.environ['GITHUB_SERVER_URL']}/"
                  f"{os.environ['GITHUB_REPOSITORY']}/pull/"
                  f"{args.pr_number or ''}")

    comment = format_pr_comment(violations, personal_data, llm_analysis, pr_url)
    summary = format_summary_log(violations, personal_data)

    # â”€â”€ 5. Output â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if args.output == "json":
        llm_violations = _extract_llm_violations(llm_analysis)
        output = {
            "violations": [
                {
                    "arquivo": v.arquivo,
                    "linha": v.linha,
                    "tipo": v.tipo,
                    "artigo": v.artigo,
                    "severidade": v.severidade,
                    "descricao": v.descricao,
                    "sugestao": v.sugestao,
                }
                for v in violations
            ],
            "llm_violations": llm_violations,
            "personal_data_count": len(personal_data),
            "should_fail": should_fail_pipeline(violations),
        }
        if args.include_llm_raw:
            output["llm_analysis_raw"] = llm_analysis
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 60)
        print(comment)
        print("=" * 60)
        print(f"\n{summary}")

    # â”€â”€ 6. Posta comentÃ¡rio no PR (se configurado) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if args.post_comment:
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPOSITORY")
        pr_num = args.pr_number or int(os.environ.get("PR_NUMBER", "0"))

        if token and repo and pr_num:
            post_github_comment(comment, pr_num, repo, token)
        else:
            print("Para postar comentario, configure: GITHUB_TOKEN, "
                  "GITHUB_REPOSITORY, --pr-number")

    # â”€â”€ 7. Exit code â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if should_fail_pipeline(violations):
        print("\nPipeline falhando devido a violacoes criticas/altas de LGPD.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

