"""
Analisador principal de conformidade LGPD.
Usa LangChain + RAG sobre o texto da LGPD para análise semântica.
"""

import os
from pathlib import Path
from typing import List, Optional

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from detector import Violation, PersonalDataUsage


def get_llm(provider: str = "anthropic"):
    """Retorna o LLM configurado conforme provider."""
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-sonnet-4-6",
            anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
            max_tokens=2048,
            temperature=0
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o",
            openai_api_key=os.environ["OPENAI_API_KEY"],
            max_tokens=2048,
            temperature=0
        )
    else:
        raise ValueError(f"Provider '{provider}' não suportado. Use 'anthropic' ou 'openai'.")


def get_embeddings(provider: str = "anthropic"):
    """Retorna embeddings conforme provider."""
    # Ambos os providers usam OpenAI embeddings por padrão (mais econômico)
    # Se quiser usar apenas Anthropic, pode usar HuggingFace embeddings
    from langchain_openai import OpenAIEmbeddings
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])
    else:
        # Fallback: embeddings locais via HuggingFace (sem custo)
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def build_lgpd_knowledge_base(embeddings) -> FAISS:
    """Constrói a base vetorial com o texto da LGPD."""
    knowledge_path = Path(__file__).parent / "knowledge" / "lgpd.txt"

    loader = TextLoader(str(knowledge_path), encoding="utf-8")
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(documents)

    vectorstore = FAISS.from_documents(chunks, embeddings)
    return vectorstore


ANALYSIS_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""Você é um especialista em conformidade com a LGPD (Lei Geral de Proteção de Dados 
Pessoais - Lei 13.709/2018) analisando código-fonte para identificar violações.

Use o contexto abaixo sobre a LGPD para fundamentar sua análise:
{context}

Analise o seguinte código e responda:
{question}

INSTRUÇÕES:
- Identifique violações específicas com o artigo da LGPD violado
- Seja objetivo e técnico
- Sugira correções práticas
- Se não houver violação, diga explicitamente "Nenhuma violação identificada"
- Formato da resposta: JSON com campos "violacoes" (lista) e "recomendacoes" (lista)

Resposta:"""
)


class LGPDAnalyzer:
    def __init__(self, provider: str = "anthropic"):
        self.provider = provider
        self.llm = get_llm(provider)
        self.embeddings = get_embeddings(provider)
        self.vectorstore = build_lgpd_knowledge_base(self.embeddings)
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
            chain_type_kwargs={"prompt": ANALYSIS_PROMPT}
        )

    def analyze_snippet(self, codigo: str, contexto: str = "") -> str:
        """Analisa um trecho de código com RAG sobre a LGPD."""
        pergunta = f"""
Analise este trecho de código para conformidade com a LGPD:

```
{codigo}
```

Contexto adicional: {contexto if contexto else "Microserviço em produção que trata dados de usuários brasileiros."}

Identifique:
1. Quais dados pessoais estão sendo tratados
2. Quais violações da LGPD existem (com artigo específico)
3. Qual a severidade (CRÍTICA/ALTA/MÉDIA/BAIXA)
4. Como corrigir cada violação
"""
        resultado = self.qa_chain.invoke({"query": pergunta})
        return resultado.get("result", "Erro na análise")

    def analyze_personal_data_flow(
        self,
        usages: List[PersonalDataUsage],
        violations: List[Violation]
    ) -> str:
        """Análise de alto nível do fluxo de dados pessoais no diff."""
        if not usages and not violations:
            return "✅ Nenhum dado pessoal ou violação detectada neste diff."

        # Monta resumo para o LLM
        resumo_usages = "\n".join([
            f"- {u.arquivo}:{u.linha} → campo '{u.campo}': {u.codigo[:80]}"
            for u in usages[:10]  # Limita para não estourar contexto
        ])

        resumo_violations = "\n".join([
            f"- [{v.severidade}] {v.arquivo}:{v.linha} → {v.descricao} ({v.artigo})"
            for v in violations[:10]
        ])

        pergunta = f"""
Este diff de código apresenta os seguintes usos de dados pessoais:
{resumo_usages if usages else "Nenhum detectado automaticamente"}

E as seguintes violações detectadas por regras estáticas:
{resumo_violations if violations else "Nenhuma detectada automaticamente"}

Com base na LGPD, forneça:
1. Uma avaliação geral do risco de conformidade (ALTO/MÉDIO/BAIXO)
2. As 3 ações mais urgentes que o desenvolvedor deve tomar
3. Se há necessidade de revisão por DPO/jurídico
"""
        resultado = self.qa_chain.invoke({"query": pergunta})
        return resultado.get("result", "Erro na análise")
