import os
import re
import time
import asyncio
import logging
from typing import List, Dict, Any, Tuple, TYPE_CHECKING
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END  # type: ignore
from langchain_core.prompts import ChatPromptTemplate  # type: ignore
from langchain_core.output_parsers import StrOutputParser  # type: ignore
from langchain_groq import ChatGroq  # type: ignore

if TYPE_CHECKING:
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore

from app.services.vector_tools import query_project_papers, list_project_documents  # type: ignore

from dotenv import load_dotenv  # type: ignore

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------

def get_llm() -> Any:
    from app.config import get_settings  # type: ignore
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore

        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            temperature=0.0,
        )
    else:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
        return ChatGroq(
            model=settings.GROQ_MODEL,
            temperature=0.0,
        )


LLM = get_llm()
OUTPUT_PARSER = StrOutputParser()


# ---------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------

class ResearchState(TypedDict, total=False):
    project_id: str
    question: str

    # Internal state
    local_hits: List[Dict[str, Any]]

    # Output
    answer: str
    answer_source: str  # "document" or "llm"
    sources: List[Dict[str, Any]]


_LOCAL_CITATION_RE = re.compile(r"\[LOCAL\s+\d+\]")

# Phrases the doc-grounded LLM uses when it can't find info
_NOT_FOUND_PHRASES = [
    "could not find information",
    "could not find relevant",
    "not found in",
    "no information about",
    "does not contain",
    "not mentioned in",
    "not available in",
    "i could not find",
    "unable to find",
    "no relevant information",
]


def _answer_needs_fallback(answer: str) -> bool:
    """Check if the document-grounded answer indicates the info wasn't found."""
    lower = answer.lower()
    return any(phrase in lower for phrase in _NOT_FOUND_PHRASES)


def _best_local_title(hit: Dict[str, Any]) -> str:
    md = (hit.get("metadata") or {})
    title = (md.get("title") or "").strip()
    if title:
        return title

    src = (md.get("source") or "").strip()
    if src:
        try:
            base = os.path.basename(src)
            return os.path.splitext(base)[0] or base
        except Exception:
            return src

    return ""


# ---------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------

def retrieve_local(state: ResearchState) -> ResearchState:
    """Retrieve local chunks with similarity scores for relevance filtering."""
    project_id = state["project_id"]
    question = state["question"]
    
    try:
        hits = query_project_papers.invoke({
            "project_id": project_id,
            "query": question,
            "top_k": 15,
        })
    except Exception as exc:
        logger.error("Retrieval failed: %s", exc)
        hits = []
    
    # Filter out low-relevance chunks using similarity score
    RELEVANCE_THRESHOLD = 1.5
    filtered = []
    for hit in hits:
        score = hit.get("score")
        if score is not None and score > RELEVANCE_THRESHOLD:
            logger.debug("Filtered out chunk (score=%.3f): %s...", score, hit.get("content", "")[:60])
            continue
        filtered.append(hit)
    
    # Keep at least top 5 even if scores are high
    if len(filtered) < 3 and hits:
        filtered = hits[:5]  # type: ignore[index]
        
    state["local_hits"] = filtered
    logger.info("Retrieval: %d raw hits -> %d after relevance filtering", len(hits), len(filtered))
    return state


def _build_context(state: ResearchState) -> str:
    """Build context string from local hits."""
    lines = []
    
    local_hits = state.get("local_hits") or []
    if local_hits:
        lines.append("=== UPLOADED DOCUMENTS (Primary Context) ===")
        for i, hit in enumerate(local_hits, start=1):  # type: ignore[arg-type]
            md = hit.get("metadata", {})
            # Use a clean display name, stripping local file paths
            raw_title = md.get("title") or md.get("source") or "Unknown"
            title = raw_title.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]  # basename only
            content = (hit.get("content") or "").strip()
            lines.append(f"[Source {i}] {title}\n{content}\n")

    return "\n".join(lines)


def generate_answer(state: ResearchState) -> ResearchState:
    """Try to answer from documents first."""
    question = state["question"]

    local_hits = state.get("local_hits") or []
    
    # If no local hits at all, go straight to LLM fallback
    if not local_hits:
        state["answer"] = ""
        state["answer_source"] = "llm"  # Signal: need fallback
        state["sources"] = []
        return state

    # Build context from local documents
    context = _build_context(state)
    
    logger.info("Context length: %d chars, local_hits: %d", 
                len(context), len(local_hits))  # type: ignore[arg-type]
    
    system_prompt = (
        "You are a STRICTLY document-grounded research assistant.\n\n"
        "CRITICAL RULES — YOU MUST FOLLOW THESE EXACTLY:\n"
        "1. You are given Context below containing text chunks extracted from the user's uploaded documents.\n"
        "2. You MUST answer ONLY using information that appears in the Context chunks below.\n"
        "3. FORBIDDEN: Do NOT use your training data, prior knowledge, or any information outside the Context.\n"
        "4. FORBIDDEN: Do NOT generate information that does not appear verbatim or paraphrased in the Context.\n"
        "5. Do NOT include citation tags like [Source 1] in your answer. Just answer naturally.\n"
        "6. If the Context does not contain enough information to answer, say EXACTLY: "
        "'Based on the uploaded documents, I could not find information about this topic.'\n"
        "7. You may combine information from multiple chunks, but every claim MUST be traceable to a Context chunk.\n"
        "8. Be clear, organized, and thorough. Use bullet points when listing multiple items.\n\n"
        "Remember: The Context below is the ONLY source of truth. Read it carefully before answering.\n"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Question: {question}\n\nContext:\n{context}")
    ])

    chain = prompt | LLM | OUTPUT_PARSER

    try:
        logger.info("Sending to LLM: question=%r, context_len=%d", question, len(context))
        answer = chain.invoke({"question": question, "context": context})
        logger.info("LLM answer preview: %s", (answer or "")[:200])
    except Exception as exc:
        logger.error("LLM generation failed: %s", exc)
        answer = "I encountered an error while generating the response. Please try again."

    # Check if the answer says "not found in documents" → trigger fallback
    if _answer_needs_fallback(answer):
        logger.info("Document answer triggered fallback — routing to LLM general knowledge")
        state["answer"] = ""
        state["answer_source"] = "llm"  # Signal: need fallback
        state["sources"] = []
        return state

    # Document-grounded answer succeeded — strip any leftover citation tags
    import re
    clean_answer = re.sub(r'\[(?:LOCAL|Source)\s*\d+\]', '', answer).strip()
    state["answer"] = clean_answer
    state["answer_source"] = "document"
    
    # Build sources list for UI
    sources = []
    for idx, hit in enumerate(local_hits, start=1):  # type: ignore[arg-type]
        md = hit.get("metadata") or {}
        sources.append({
            "id": f"Source {idx}",
            "type": "local",
            "title": md.get("title") or md.get("source"),
            "pdf_url": md.get("pdf_url"),
            "page": md.get("page"),
        })
        
    state["sources"] = sources  # type: ignore[typeddict-item]
    return state


def llm_fallback(state: ResearchState) -> ResearchState:
    """Answer using the LLM's general knowledge when documents don't have the answer."""
    question = state["question"]

    system_prompt = (
        "You are a knowledgeable AI assistant.\n\n"
        "The user asked a question that could not be answered from their uploaded documents.\n"
        "Answer the question using your general knowledge.\n\n"
        "RULES:\n"
        "1. Be accurate, clear, and thorough.\n"
        "2. Use bullet points when listing multiple items.\n"
        "3. If you're not sure about something, say so.\n"
        "4. Do NOT pretend the answer came from uploaded documents.\n"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{question}")
    ])

    chain = prompt | LLM | OUTPUT_PARSER

    try:
        logger.info("LLM fallback for question: %r", question)
        answer = chain.invoke({"question": question})
        logger.info("LLM fallback answer preview: %s", (answer or "")[:200])
    except Exception as exc:
        logger.error("LLM fallback failed: %s", exc)
        answer = "I encountered an error while generating the response. Please try again."

    state["answer"] = answer
    state["answer_source"] = "llm"
    state["sources"] = [{
        "id": "LLM",
        "type": "llm",
        "title": "LLM General Knowledge",
    }]
    return state


# ---------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------

def route_after_generate(state: ResearchState) -> str:
    """Route to llm_fallback if the document answer wasn't sufficient."""
    if state.get("answer_source") == "llm" and not state.get("answer"):
        return "llm_fallback"
    return "end"


# ---------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------

def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("retrieve_local", retrieve_local)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("llm_fallback", llm_fallback)

    # Flow: START -> retrieve -> generate -> (conditional) -> llm_fallback or END
    graph.add_edge(START, "retrieve_local")
    graph.add_edge("retrieve_local", "generate_answer")
    graph.add_conditional_edges(
        "generate_answer",
        route_after_generate,
        {
            "llm_fallback": "llm_fallback",
            "end": END,
        },
    )
    graph.add_edge("llm_fallback", END)

    return graph.compile()


APP = build_graph()


# ---------------------------------------------------------------------
# Caching & Thread-safe execution
# ---------------------------------------------------------------------

_query_cache: Dict[Tuple[str, str], Tuple[Dict[str, Any], float]] = {}
CACHE_TTL = 600  # 10 minutes


async def get_research_response(project_id: str, question: str) -> Dict[str, Any]:
    """
    Get a research response, using an in-memory cache for identical queries.
    Runs the synchronous LangGraph pipeline in a thread pool.
    """
    cache_key = (project_id, question)
    
    # 1. Check Cache
    if cache_key in _query_cache:
        state, cached_at = _query_cache[cache_key]
        if time.time() - cached_at < CACHE_TTL:
            logger.info("Query cache hit for %s", project_id)
            return state
        else:
            _query_cache.pop(cache_key, None)

    # 2. Run Pipeline (in thread pool)
    logger.info("Executing research pipeline for %s", project_id)
    state = await asyncio.to_thread(
        APP.invoke,
        {
            "project_id": project_id,
            "question": question,
        }
    )
    
    # 3. Cache Result (simple dict conversion)
    result = {
        "answer": state.get("answer", "No answer generated"),
        "sources": state.get("sources", []),
        "answer_source": state.get("answer_source", "document"),
    }
    _query_cache[cache_key] = (result, time.time())
    
    return result
