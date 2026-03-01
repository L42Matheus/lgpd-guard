"""
Gera diffs dos exemplos de violações LGPD no formato esperado pelo LGPD Guard.
Execute na raiz do repositório: python scripts-local/generate_example_diffs.py
"""
import pathlib

# Raiz do projeto (um nível acima de scripts-local/)
ROOT = pathlib.Path(__file__).parent.parent

EXEMPLOS = [
    ("UsuarioService.java", ROOT / "examples/violations/UsuarioService.java"),
    ("usuario_service.py",  ROOT / "examples/violations/usuario_service.py"),
]

(ROOT / "diffs").mkdir(exist_ok=True)

for nome, caminho in EXEMPLOS:
    conteudo = caminho.read_text(encoding="utf-8")
    linhas = "\n".join("+" + l for l in conteudo.splitlines())
    diff = f"diff --git a/{nome} b/{nome}\n+++ b/{nome}\n{linhas}"
    saida = ROOT / f"diffs/exemplo_{nome.split('.')[0].lower()}.txt"
    saida.write_text(diff, encoding="utf-8")
    print(f"✓ {saida}")

print("\nPronto! Agora rode:")
print("  python lgpd_guard\\main.py --diff .\\diffs\\exemplo_usuarioservice.txt --no-llm --output json")
print("  python lgpd_guard\\main.py --diff .\\diffs\\exemplo_usuarioservice.txt --provider anthropic --output json")