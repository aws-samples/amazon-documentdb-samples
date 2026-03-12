"""
Financial Research Agent — S&P 500 Company Profiles
Uses Strands SDK with Bedrock Claude + DocumentDB vector search via pymongo.
"""

import json
import os
import boto3
import pymongo
from dotenv import load_dotenv
from strands import Agent, tool
from strands.models import BedrockModel

load_dotenv()

# --- Configuration ---
DOCDB_URI = os.environ["DOCDB_URI"]
DB_NAME = "financial_research"
COLLECTION_NAME = "sp500_companies"
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSION = 1024
AWS_REGION = "us-east-1"

# --- Clients (initialized lazily) ---
_bedrock_client = None
_docdb_client = None


def get_bedrock():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    return _bedrock_client


def get_collection():
    global _docdb_client
    if _docdb_client is None:
        _docdb_client = pymongo.MongoClient(DOCDB_URI)
    return _docdb_client[DB_NAME][COLLECTION_NAME]


def generate_embedding(text: str) -> list:
    """Generate embedding using Bedrock Titan."""
    response = get_bedrock().invoke_model(
        modelId=EMBEDDING_MODEL,
        body=json.dumps({"inputText": text[:8000], "dimensions": EMBEDDING_DIMENSION}),
    )
    return json.loads(response["body"].read())["embedding"]


# --- Agent Tools ---

@tool
def semantic_search(query: str, top_k: int = 5) -> str:
    """Search S&P 500 company profiles using semantic vector search in DocumentDB.

    Use this to find companies by meaning — e.g. "companies involved in cloud computing",
    "semiconductor manufacturers", "renewable energy firms". Returns the most
    semantically similar company profiles.

    Args:
        query: Natural language search query about companies, products, or industries.
        top_k: Number of results to return (default 5).
    """
    collection = get_collection()
    query_embedding = generate_embedding(query)

    pipeline = [
        {
            "$search": {
                "vectorSearch": {
                    "vector": query_embedding,
                    "path": "embedding",
                    "similarity": "cosine",
                    "k": top_k,
                }
            }
        },
        {
            "$project": {
                "embedding": 0,
                "_id": 0,
            }
        },
    ]

    results = list(collection.aggregate(pipeline))

    if not results:
        return "No matching companies found."

    output = []
    for i, doc in enumerate(results, 1):
        m = doc.get("metrics", {})
        metrics_highlights = []
        if m.get("marketCap"):
            metrics_highlights.append(f"Market Cap: ${m['marketCap']/1e9:.1f}B")
        if m.get("currentPrice"):
            metrics_highlights.append(f"Price: ${m['currentPrice']:.2f}")
        if m.get("revenueGrowth") is not None:
            metrics_highlights.append(f"Rev Growth: {m['revenueGrowth']:.1%}")
        if m.get("profitMargins") is not None:
            metrics_highlights.append(f"Profit Margin: {m['profitMargins']:.1%}")

        output.append(
            f"--- Result {i} ---\n"
            f"Company: {doc.get('company')} ({doc.get('symbol')}) | Sector: {doc.get('sector')}\n"
            f"Industry: {doc.get('industry')} | Sub-Industry: {doc.get('sub_industry')}\n"
            f"HQ: {doc.get('headquarters')} | Founded: {doc.get('founded')}\n"
            f"Metrics: {' | '.join(metrics_highlights)}\n"
            f"Description: {doc.get('description', '')[:400]}..."
        )

    return "\n\n".join(output)


@tool
def filter_by_sector(sector: str) -> str:
    """Find all companies in a specific GICS sector.

    Args:
        sector: The GICS sector to filter by. Valid sectors: Information Technology,
                Health Care, Financials, Consumer Discretionary, Communication Services,
                Industrials, Consumer Staples, Energy, Utilities, Real Estate, Materials.
    """
    collection = get_collection()
    results = list(collection.find(
        {"sector": {"$regex": sector, "$options": "i"}},
        {"embedding": 0, "_id": 0},
    ).sort("metrics.marketCap", pymongo.DESCENDING).limit(30))

    if not results:
        return f"No companies found in sector '{sector}'."

    output = []
    for doc in results:
        m = doc.get("metrics", {})
        mcap = f"${m['marketCap']/1e9:.1f}B" if m.get("marketCap") else "N/A"
        output.append(
            f"{doc['company']} ({doc.get('symbol')}) — {doc.get('sub_industry')}\n"
            f"  Market Cap: {mcap} | Industry: {doc.get('industry')}"
        )

    total = collection.count_documents({"sector": {"$regex": sector, "$options": "i"}})
    return f"Found {total} companies in '{sector}' (showing top 30 by market cap):\n\n" + "\n\n".join(output)


@tool
def keyword_search(keywords: str, top_k: int = 10) -> str:
    """Search companies using keyword/text search powered by DocumentDB text index.

    Unlike semantic_search (which finds conceptually similar results using vector embeddings),
    this tool does exact keyword matching against company descriptions, names, and industries.
    Use this when the user asks for specific terms, product names, or industry keywords.

    Args:
        keywords: One or more keywords to search for (e.g. "semiconductor", "electric vehicle",
                  "cloud computing", "insulin", "credit card").
        top_k: Number of results to return (default 10).
    """
    collection = get_collection()

    results = list(collection.find(
        {"$text": {"$search": keywords}},
        {"score": {"$meta": "textScore"}, "embedding": 0},
    ).sort([("score", {"$meta": "textScore"})]).limit(top_k))

    if not results:
        return f"No companies found matching keywords '{keywords}'."

    output = []
    for i, doc in enumerate(results, 1):
        m = doc.get("metrics", {})
        mcap = f"${m['marketCap']/1e9:.1f}B" if m.get("marketCap") else "N/A"
        output.append(
            f"  {i}. {doc.get('company')} ({doc.get('symbol')}) [{doc.get('sector')}]\n"
            f"     Industry: {doc.get('industry')} | Market Cap: {mcap} | "
            f"Text Score: {doc.get('score', 0):.2f}"
        )

    return f"Keyword search results for '{keywords}' (top {len(results)}):\n\n" + "\n\n".join(output)


@tool
def compare_metrics(metric_name: str, top_n: int = 10) -> str:
    """Compare a specific financial metric across S&P 500 companies. Returns top N ranked.

    Args:
        metric_name: The metric to compare. Available metrics:
            marketCap, totalRevenue, revenueGrowth, grossMargins, operatingMargins,
            profitMargins, returnOnEquity, debtToEquity, trailingPE, forwardPE,
            dividendYield, beta, currentPrice, fiftyTwoWeekHigh, fiftyTwoWeekLow,
            fullTimeEmployees.
        top_n: Number of top companies to return (default 10).
    """
    collection = get_collection()
    results = list(collection.find(
        {f"metrics.{metric_name}": {"$exists": True, "$ne": None}},
        {"company": 1, "symbol": 1, "sector": 1, f"metrics.{metric_name}": 1, "_id": 0},
    ).sort(f"metrics.{metric_name}", pymongo.DESCENDING).limit(top_n))

    if not results:
        return (
            f"No companies found with metric '{metric_name}'. "
            f"Available: marketCap, totalRevenue, revenueGrowth, grossMargins, "
            f"operatingMargins, profitMargins, returnOnEquity, debtToEquity, "
            f"trailingPE, forwardPE, dividendYield, beta, currentPrice."
        )

    def fmt(val):
        if metric_name in ("marketCap", "totalRevenue"):
            return f"${val/1e9:.1f}B"
        if metric_name in ("revenueGrowth", "grossMargins", "operatingMargins",
                           "profitMargins", "returnOnEquity", "dividendYield"):
            return f"{val:.1%}"
        if metric_name in ("currentPrice", "fiftyTwoWeekHigh", "fiftyTwoWeekLow"):
            return f"${val:.2f}"
        return f"{val:,.1f}"

    output = []
    for i, doc in enumerate(results, 1):
        val = doc["metrics"][metric_name]
        output.append(f"  {i}. {doc['company']} ({doc['symbol']}) [{doc['sector']}]: {fmt(val)}")

    return f"Top {len(results)} companies by '{metric_name}':\n\n" + "\n".join(output)


@tool
def get_company_detail(company_name: str) -> str:
    """Get full profile for a specific S&P 500 company including all financial data.

    Args:
        company_name: Company name or ticker symbol to look up (e.g., "Apple", "AAPL").
    """
    collection = get_collection()
    doc = collection.find_one(
        {"$or": [
            {"company": {"$regex": company_name, "$options": "i"}},
            {"symbol": {"$regex": f"^{company_name}$", "$options": "i"}},
        ]},
        {"embedding": 0, "_id": 0},
    )

    if not doc:
        return f"Company '{company_name}' not found in S&P 500 database."

    m = doc.get("metrics", {})
    metrics_lines = []
    label_map = {
        "marketCap": ("Market Cap", lambda v: f"${v/1e9:.1f}B"),
        "currentPrice": ("Current Price", lambda v: f"${v:.2f}"),
        "totalRevenue": ("Total Revenue", lambda v: f"${v/1e9:.1f}B"),
        "revenueGrowth": ("Revenue Growth", lambda v: f"{v:.1%}"),
        "grossMargins": ("Gross Margins", lambda v: f"{v:.1%}"),
        "operatingMargins": ("Operating Margins", lambda v: f"{v:.1%}"),
        "profitMargins": ("Profit Margins", lambda v: f"{v:.1%}"),
        "returnOnEquity": ("Return on Equity", lambda v: f"{v:.1%}"),
        "debtToEquity": ("Debt/Equity", lambda v: f"{v:.1f}"),
        "trailingPE": ("Trailing P/E", lambda v: f"{v:.1f}"),
        "forwardPE": ("Forward P/E", lambda v: f"{v:.1f}"),
        "dividendYield": ("Dividend Yield", lambda v: f"{v:.2%}"),
        "beta": ("Beta", lambda v: f"{v:.3f}"),
        "fiftyTwoWeekHigh": ("52-Week High", lambda v: f"${v:.2f}"),
        "fiftyTwoWeekLow": ("52-Week Low", lambda v: f"${v:.2f}"),
        "fullTimeEmployees": ("Employees", lambda v: f"{int(v):,}"),
    }
    for key, (label, formatter) in label_map.items():
        if key in m and m[key] is not None:
            metrics_lines.append(f"  {label}: {formatter(m[key])}")

    return (
        f"Company: {doc['company']} ({doc['symbol']})\n"
        f"Sector: {doc['sector']}\n"
        f"Sub-Industry: {doc.get('sub_industry')}\n"
        f"Industry: {doc.get('industry')}\n"
        f"Headquarters: {doc.get('headquarters')}\n"
        f"Founded: {doc.get('founded')}\n\n"
        f"Financial Metrics:\n" + "\n".join(metrics_lines) + "\n\n"
        f"Business Description:\n{doc.get('description', 'N/A')}"
    )


# --- System Prompt ---
SYSTEM_PROMPT = """You are a senior financial research analyst AI assistant powered by Amazon DocumentDB and Amazon Bedrock.

You help analysts research S&P 500 companies, compare financial metrics, analyze sectors, and identify investment themes.

You have access to a database of ~500 S&P 500 company profiles stored in Amazon DocumentDB with vector search capabilities. Each profile includes business descriptions, GICS sector/sub-industry classification, and key financial metrics from market data.

Your tools:
- **semantic_search**: Vector search (HNSW index) to find companies by meaning (e.g. "AI chip makers", "cloud infrastructure providers", "electric vehicle companies"). Best for conceptual/thematic queries.
- **keyword_search**: Text index search for exact keyword matching (e.g. "semiconductor", "insulin", "credit card"). Best for specific product/technology terms. Uses DocumentDB text index with relevance scoring.
- **filter_by_sector**: List companies in a GICS sector (Information Technology, Health Care, Financials, etc.)
- **compare_metrics**: Rank companies by a metric (marketCap, revenueGrowth, profitMargins, returnOnEquity, etc.)
- **get_company_detail**: Full profile for a specific company by name or ticker

When to use semantic_search vs keyword_search:
- Use semantic_search for broad, conceptual, or thematic queries ("companies benefiting from AI boom", "semiconductor manufacturers", "firms with strong recurring revenue")
- Use keyword_search for specific product names, technical terms, or exact phrases ("insulin", "SaaS", "lithium", "5G")
- IMPORTANT: Pick ONE search tool per query — do not use both semantic_search and keyword_search together. They serve different purposes and combining them creates redundant results.
- You CAN combine a search tool with other tools like compare_metrics or get_company_detail in the same query.

Available metrics: marketCap, totalRevenue, revenueGrowth, grossMargins, operatingMargins, profitMargins, returnOnEquity, debtToEquity, trailingPE, forwardPE, dividendYield, beta, currentPrice, fiftyTwoWeekHigh, fiftyTwoWeekLow, fullTimeEmployees.

GICS Sectors: Information Technology, Health Care, Financials, Consumer Discretionary, Communication Services, Industrials, Consumer Staples, Energy, Utilities, Real Estate, Materials.

Guidelines:
- Always use your tools to ground answers in actual data
- For quantitative comparisons, use compare_metrics; for qualitative/thematic queries, use semantic_search
- Provide specific numbers and cite the data
- Format financial figures clearly (percentages, billions, etc.)
- Keep responses concise — use bullet points and tables, avoid lengthy paragraphs
- When asked for "top N" or "bottom N" companies by a metric, respond with a simple numbered list showing company name, ticker, and that metric value.
- IMPORTANT: Do NOT call get_company_detail after a search or compare. The search and compare tools already return enough data (company name, symbol, sector, metrics). Only use get_company_detail when the user asks about ONE specific company.
- Aim to answer in 1-2 tool calls maximum.
"""


def create_agent(callback_handler=None):
    """Create and return the financial research agent."""
    model = BedrockModel(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        region_name=AWS_REGION,
        max_tokens=2048,
    )

    kwargs = dict(
        model=model,
        tools=[semantic_search, keyword_search, filter_by_sector, compare_metrics, get_company_detail],
        system_prompt=SYSTEM_PROMPT,
    )
    if callback_handler is not None:
        kwargs["callback_handler"] = callback_handler

    return Agent(**kwargs)


# --- CLI mode ---
if __name__ == "__main__":
    print("S&P 500 Financial Research Agent (type 'quit' to exit)")
    print("-" * 50)
    agent = create_agent()
    while True:
        query = input("\nYou: ").strip()
        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue
        response = agent(query)
        print(f"\nAgent: {response}")
