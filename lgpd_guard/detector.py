"""
Detector de dados pessoais em diffs de código.
Suporte: Java, Python, JavaScript/TypeScript
"""

import re
from dataclasses import dataclass
from typing import List

# Padrões que indicam dados pessoais em código
PERSONAL_DATA_PATTERNS = [
    # Identificadores brasileiros
    r'\bcpf\b', r'\brg\b', r'\bcnpj\b', r'\bcnh\b', r'\btitulo_eleitor\b',
    # Dados de contato
    r'\bemail\b', r'\be_mail\b', r'\btelefone\b', r'\bcelular\b', r'\bphone\b',
    r'\bmobile\b', r'\bcontato\b',
    # Dados pessoais gerais
    r'\bnome\b', r'\bsobrenome\b', r'\bname\b', r'\bfullname\b',
    r'\bnascimento\b', r'\bdata_nascimento\b', r'\bbirth\b', r'\bbirthdate\b',
    r'\bendereco\b', r'\baddress\b', r'\bcep\b', r'\bzip\b',
    # Dados sensíveis
    r'\bsaude\b', r'\bhealth\b', r'\bmedico\b', r'\bdiagnostico\b',
    r'\breligiao\b', r'\bpolitica\b', r'\betnia\b', r'\braca\b',
    r'\bbiometria\b', r'\bbiometric\b', r'\bgenetic\b',
    # Credenciais
    r'\bsenha\b', r'\bpassword\b', r'\bpasswd\b', r'\bsecret\b',
    r'\btoken\b', r'\bapi_key\b', r'\bcredential\b',
    # Financeiro
    r'\bcartao\b', r'\bcredito\b', r'\bcredit_card\b', r'\biban\b',
    r'\baccount\b', r'\bconta\b',
]

# Padrões de violações conhecidas
VIOLATION_PATTERNS = {
    "log_com_dado_pessoal": {
        "pattern": r'(log\.|logger\.|console\.|print|System\.out)[^;]*'
                   r'(cpf|email|nome|senha|password|telefone|rg|cartao)',
        "artigo": "Art. 46",
        "descricao": "Dado pessoal exposto em log sem mascaramento",
        "severidade": "ALTA",
        "sugestao": "Mascare o dado antes de logar. Ex: cpf.substring(0,3) + '.***.***-**'"
    },
    "hardcoded_credential": {
        "pattern": r'(password|senha|secret|api_key|token)\s*=\s*["\'][^"\']{4,}["\']',
        "artigo": "Art. 46",
        "descricao": "Credencial hardcoded no código-fonte",
        "severidade": "CRÍTICA",
        "sugestao": "Use variáveis de ambiente ou um cofre de segredos (Vault, AWS Secrets Manager)"
    },
    "http_sem_https": {
        "pattern": r'http://[^\s]*\.(com|br|org|net|gov)',
        "artigo": "Art. 46",
        "descricao": "Comunicação sem criptografia (HTTP) para domínio externo",
        "severidade": "ALTA",
        "sugestao": "Use HTTPS para todas as comunicações com dados pessoais"
    },
    "sql_sem_prepared": {
        "pattern": r'(executeQuery|execute)\s*\(\s*["\'].*\+\s*(cpf|email|nome|senha)',
        "artigo": "Art. 46",
        "descricao": "Concatenação direta de dado pessoal em query SQL (risco de SQL Injection)",
        "severidade": "CRÍTICA",
        "sugestao": "Use PreparedStatement ou ORM com parâmetros nomeados"
    },
    "dado_pessoal_em_url": {
        "pattern": r'(get|post|put|delete|fetch|axios|requests)\s*\([^)]*'
                   r'(cpf|rg|email|telefone)[^)]*\)',
        "artigo": "Art. 6 (necessidade) + Art. 46 (segurança)",
        "descricao": "Dado pessoal possivelmente exposto em URL ou parâmetro de requisição",
        "severidade": "MÉDIA",
        "sugestao": "Dados pessoais não devem trafegar em query params ou path params de URLs"
    },
    "sem_criptografia_senha": {
        "pattern": r'(password|senha)\s*=\s*(request\.|body\.|dto\.|user\.)'
                   r'[a-zA-Z]*[Pp]assword',
        "artigo": "Art. 46",
        "descricao": "Senha possivelmente armazenada sem hash criptográfico",
        "severidade": "CRÍTICA",
        "sugestao": "Use BCrypt, Argon2 ou PBKDF2 para armazenar senhas"
    },
    "analytics_com_dado_pessoal": {
        "pattern": r'(analytics|tracking|segment|mixpanel|amplitude|datadog)'
                   r'[^;]*(cpf|email|nome|telefone|rg)',
        "artigo": "Art. 6 (finalidade) + Art. 7 (base legal)",
        "descricao": "Dado pessoal enviado para serviço de analytics sem base legal clara",
        "severidade": "ALTA",
        "sugestao": "Avalie se o CPF/dado é necessário para analytics. "
                    "Prefira identificadores anonimizados"
    },
}

@dataclass
class Violation:
    arquivo: str
    linha: int
    codigo: str
    tipo: str
    artigo: str
    descricao: str
    severidade: str
    sugestao: str

@dataclass
class PersonalDataUsage:
    arquivo: str
    linha: int
    codigo: str
    campo: str

def parse_diff(diff_text: str) -> dict:
    """Parseia um diff git e retorna linhas adicionadas por arquivo."""
    files = {}
    current_file = None
    current_line = 0

    for line in diff_text.split('\n'):
        if line.startswith('diff --git'):
            # Extrai nome do arquivo
            match = re.search(r'b/(.+)$', line)
            if match:
                current_file = match.group(1)
                files[current_file] = []
        elif line.startswith('@@'):
            # Extrai número da linha
            match = re.search(r'\+(\d+)', line)
            if match:
                current_line = int(match.group(1)) - 1
        elif line.startswith('+') and not line.startswith('+++'):
            current_line += 1
            if current_file:
                files[current_file].append({
                    'numero': current_line,
                    'codigo': line[1:]  # Remove o '+' do diff
                })
        elif not line.startswith('-'):
            current_line += 1

    return files

def detect_personal_data(files: dict) -> List[PersonalDataUsage]:
    """Detecta uso de dados pessoais nas linhas do diff."""
    usages = []

    for arquivo, linhas in files.items():
        for linha in linhas:
            codigo = linha['codigo'].lower()
            for pattern in PERSONAL_DATA_PATTERNS:
                if re.search(pattern, codigo, re.IGNORECASE):
                    campo = re.search(pattern, codigo, re.IGNORECASE)
                    usages.append(PersonalDataUsage(
                        arquivo=arquivo,
                        linha=linha['numero'],
                        codigo=linha['codigo'].strip(),
                        campo=campo.group(0) if campo else pattern
                    ))
                    break  # Uma ocorrência por linha é suficiente

    return usages

def detect_violations(files: dict) -> List[Violation]:
    """Detecta violações conhecidas de LGPD nas linhas do diff."""
    violations = []

    for arquivo, linhas in files.items():
        for linha in linhas:
            codigo = linha['codigo']
            for tipo, config in VIOLATION_PATTERNS.items():
                if re.search(config['pattern'], codigo, re.IGNORECASE):
                    violations.append(Violation(
                        arquivo=arquivo,
                        linha=linha['numero'],
                        codigo=codigo.strip(),
                        tipo=tipo,
                        artigo=config['artigo'],
                        descricao=config['descricao'],
                        severidade=config['severidade'],
                        sugestao=config['sugestao']
                    ))

    return violations
