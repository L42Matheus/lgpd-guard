"""
Script principal do LGPD Guard.
Orquestra detecção, análise e report para o PR do GitHub.

Uso:
  python main.py --diff diff.txt
  python main.py --diff diff.txt --post-comment --pr-number 42
  python main.py --diff diff.txt --provider openai
"""

import argparse
import json
import os
import sys
import subprocess

from detector import parse_diff, detect_personal_data, detect_violations
from reporter import (
    format_pr_comment,
    format_summary_log,
    should_fail_pipeline
)


def get_pr_diff() -> str:
    """Obtém o diff do PR via git."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD^", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        # Fallback: diff da área de staging
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True
        )
        return result.stdout


def post_github_comment(comment: str, pr_number: int, repo: str, token: str):
    """Posta o comentário no PR via GitHub API."""
    import urllib.request

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    data = json.dumps({"body": comment}).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/vnd.github+json")

    with urllib.request.urlopen(req) as response:
        if response.status == 201:
            print("✅ Comentário postado no PR com sucesso.")
        else:
            print(f"⚠️  Falha ao postar comentário: {response.status}")


def main():
    parser = argparse.ArgumentParser(description="LGPD Guard — Analisador de conformidade LGPD")
    parser.add_argument("--diff", help="Arquivo com o diff git (se omitido, usa git diff)")
    parser.add_argument("--provider", default="anthropic",
                        choices=["anthropic", "openai"],
                        help="Provider do LLM (default: anthropic)")
    parser.add_argument("--no-llm", action="store_true",
                        help="Executa apenas análise estática (sem LLM, mais rápido)")
    parser.add_argument("--post-comment", action="store_true",
                        help="Posta comentário no PR do GitHub")
    parser.add_argument("--pr-number", type=int,
                        help="Número do PR para postar comentário")
    parser.add_argument("--output", choices=["text", "json"], default="text",
                        help="Formato de saída")
    args = parser.parse_args()

    # ── 1. Obtém o diff ───────────────────────────────────────────────
    if args.diff:
        with open(args.diff, "r", encoding="utf-8") as f:
            diff_text = f.read()
    else:
        diff_text = get_pr_diff()

    if not diff_text.strip():
        print("ℹ️  Nenhuma alteração encontrada no diff.")
        sys.exit(0)

    # ── 2. Análise estática ───────────────────────────────────────────
    print("🔍 Analisando diff...")
    files = parse_diff(diff_text)
    personal_data = detect_personal_data(files)
    violations = detect_violations(files)

    print(f"   → {len(personal_data)} uso(s) de dados pessoais detectado(s)")
    print(f"   → {len(violations)} violação(ões) detectada(s) por regras estáticas")

    # ── 3. Análise semântica com LLM (opcional) ───────────────────────
    llm_analysis = None
    if not args.no_llm and (personal_data or violations):
        print(f"🤖 Iniciando análise semântica com LLM ({args.provider})...")
        try:
            from analyzer import LGPDAnalyzer
            analyzer = LGPDAnalyzer(provider=args.provider)
            llm_analysis = analyzer.analyze_personal_data_flow(personal_data, violations)
            print("   → Análise LLM concluída")
        except Exception as e:
            print(f"   ⚠️  Análise LLM falhou: {e}")
            print("   → Continuando apenas com análise estática")

    # ── 4. Formata resultado ──────────────────────────────────────────
    pr_url = None
    if os.environ.get("GITHUB_SERVER_URL") and os.environ.get("GITHUB_REPOSITORY"):
        pr_url = (f"{os.environ['GITHUB_SERVER_URL']}/"
                  f"{os.environ['GITHUB_REPOSITORY']}/pull/"
                  f"{args.pr_number or ''}")

    comment = format_pr_comment(violations, personal_data, llm_analysis, pr_url)
    summary = format_summary_log(violations, personal_data)

    # ── 5. Output ─────────────────────────────────────────────────────
    if args.output == "json":
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
            "personal_data_count": len(personal_data),
            "should_fail": should_fail_pipeline(violations),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 60)
        print(comment)
        print("=" * 60)
        print(f"\n{summary}")

    # ── 6. Posta comentário no PR (se configurado) ────────────────────
    if args.post_comment:
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPOSITORY")
        pr_num = args.pr_number or int(os.environ.get("PR_NUMBER", "0"))

        if token and repo and pr_num:
            post_github_comment(comment, pr_num, repo, token)
        else:
            print("⚠️  Para postar comentário, configure: GITHUB_TOKEN, "
                  "GITHUB_REPOSITORY, --pr-number")

    # ── 7. Exit code ──────────────────────────────────────────────────
    if should_fail_pipeline(violations):
        print("\n❌ Pipeline falhando devido a violações críticas/altas de LGPD.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
