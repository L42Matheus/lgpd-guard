"""
Reporter: formata o resultado da análise como comentário de PR no GitHub.
"""

from typing import List, Optional
from detector import Violation, PersonalDataUsage


SEVERIDADE_EMOJI = {
    "CRÍTICA": "🔴",
    "ALTA":    "🟠",
    "MÉDIA":   "🟡",
    "BAIXA":   "🟢",
}


def format_pr_comment(
    violations: List[Violation],
    personal_data: List[PersonalDataUsage],
    llm_analysis: Optional[str] = None,
    pr_url: Optional[str] = None
) -> str:
    """Formata o comentário completo para o PR do GitHub."""

    linhas = []
    linhas.append("## 🔍 LGPD Guard — Relatório de Conformidade\n")

    # ── Resumo executivo ──────────────────────────────────────────────
    total_criticas = sum(1 for v in violations if v.severidade == "CRÍTICA")
    total_altas    = sum(1 for v in violations if v.severidade == "ALTA")
    total_outras   = sum(1 for v in violations if v.severidade not in ("CRÍTICA", "ALTA"))

    if not violations and not personal_data:
        linhas.append("✅ **Nenhuma violação de LGPD detectada neste PR.**\n")
        linhas.append("> Este resultado é baseado em análise automatizada. "
                      "Revise manualmente em caso de dúvida.\n")
        return "\n".join(linhas)

    # Bloco de status
    if total_criticas > 0:
        linhas.append(f"🔴 **{total_criticas} violação(ões) CRÍTICA(S) — merge bloqueado até correção.**\n")
    elif total_altas > 0:
        linhas.append(f"🟠 **{total_altas} violação(ões) de severidade ALTA — revisão obrigatória.**\n")
    else:
        linhas.append(f"🟡 **{len(violations)} alerta(s) de conformidade — revise antes de mergear.**\n")

    linhas.append(f"| 🔴 Críticas | 🟠 Altas | 🟡 Outras | 📦 Arquivos com dados pessoais |")
    linhas.append(f"|:-----------:|:--------:|:---------:|:-----------------------------:|")
    arquivos_com_dados = len(set(u.arquivo for u in personal_data))
    linhas.append(f"| {total_criticas} | {total_altas} | {total_outras} | {arquivos_com_dados} |")
    linhas.append("")

    # ── Violações detalhadas ──────────────────────────────────────────
    if violations:
        linhas.append("---")
        linhas.append("### ⚠️ Violações Detectadas\n")

        # Agrupa por arquivo
        por_arquivo: dict = {}
        for v in violations:
            por_arquivo.setdefault(v.arquivo, []).append(v)

        for arquivo, viols in por_arquivo.items():
            linhas.append(f"**📄 `{arquivo}`**\n")
            for v in viols:
                emoji = SEVERIDADE_EMOJI.get(v.severidade, "⚪")
                linhas.append(f"{emoji} **[{v.severidade}]** Linha {v.linha} — {v.descricao}")
                linhas.append(f"> **Artigo LGPD:** {v.artigo}")
                linhas.append(f"> **Código:** `{v.codigo[:100]}`")
                linhas.append(f"> **Sugestão:** {v.sugestao}")
                linhas.append("")

    # ── Dados pessoais identificados (sem violação direta) ────────────
    dados_sem_violacao = [
        u for u in personal_data
        if not any(v.arquivo == u.arquivo and v.linha == u.linha for v in violations)
    ]
    if dados_sem_violacao:
        linhas.append("---")
        linhas.append("### 📋 Dados Pessoais Identificados (sem violação direta)\n")
        linhas.append("Os itens abaixo contêm dados pessoais. Verifique se o tratamento "
                      "possui base legal (Art. 7 LGPD):\n")
        for u in dados_sem_violacao[:8]:  # Limita exibição
            linhas.append(f"- `{u.arquivo}:{u.linha}` → campo `{u.campo}`: "
                          f"`{u.codigo[:70]}`")
        if len(dados_sem_violacao) > 8:
            linhas.append(f"- *(+ {len(dados_sem_violacao) - 8} ocorrências adicionais)*")
        linhas.append("")

    # ── Análise LLM (se disponível) ───────────────────────────────────
    if llm_analysis:
        linhas.append("---")
        linhas.append("### 🤖 Análise Semântica (LLM + RAG LGPD)\n")
        linhas.append(llm_analysis)
        linhas.append("")

    # ── Rodapé ───────────────────────────────────────────────────────
    linhas.append("---")
    linhas.append(
        "> 🤖 **LGPD Guard** | Análise automatizada — não substitui revisão jurídica. "
        "Em caso de dúvida, consulte o DPO da empresa."
    )
    if pr_url:
        linhas.append(f"> 🔗 [Ver PR]({pr_url})")

    return "\n".join(linhas)


def format_summary_log(violations: List[Violation], personal_data: List[PersonalDataUsage]) -> str:
    """Resumo para o log da GitHub Action (stdout)."""
    if not violations:
        return "✅ LGPD Guard: Nenhuma violação encontrada."

    criticas = [v for v in violations if v.severidade == "CRÍTICA"]
    msg = f"⚠️  LGPD Guard: {len(violations)} violação(ões) encontrada(s)."
    if criticas:
        msg += f" {len(criticas)} CRÍTICA(S) — pipeline deve falhar."
    return msg


def should_fail_pipeline(violations: List[Violation]) -> bool:
    """Retorna True se o pipeline deve falhar (violações críticas ou altas)."""
    return any(v.severidade in ("CRÍTICA", "ALTA") for v in violations)
