"""
Financial Research Assistant - Streamlit UI
S&P 500 Company Profiles powered by Amazon DocumentDB + Bedrock + Strands Agents
"""

import queue
import threading
import streamlit as st
from agent import create_agent

# Map tool names to friendly labels with icons
TOOL_LABELS = {
    "semantic_search": "🔍 Semantic Search (HNSW Vector Index)",
    "keyword_search": "📝 Keyword Search (Text Index)",
    "filter_by_sector": "📁 Sector Filter (Compound Index)",
    "compare_metrics": "📊 Metric Comparison",
    "get_company_detail": "🏢 Company Lookup",
}


class StreamlitCallbackHandler:
    """Captures tool calls and streams text chunks for Streamlit display."""

    def __init__(self):
        self.tool_calls = []
        self.tool_count = 0
        self.text_queue = queue.Queue()
        self._done = False

    def __call__(self, **kwargs):
        event = kwargs.get("event", {})

        # Capture tool use starts
        tool_use = (
            event.get("contentBlockStart", {})
            .get("start", {})
            .get("toolUse")
        )
        if tool_use:
            self.tool_count += 1
            name = tool_use["name"]
            label = TOOL_LABELS.get(name, f"🔧 {name}")
            self.tool_calls.append(label)

        # Capture streaming text deltas
        delta = event.get("contentBlockDelta", {}).get("delta", {})
        text = delta.get("text")
        if text:
            self.text_queue.put(text)

    def mark_done(self):
        self._done = True
        self.text_queue.put(None)  # sentinel

    def stream(self):
        """Generator that yields text chunks as they arrive."""
        while True:
            try:
                chunk = self.text_queue.get(timeout=60)
            except queue.Empty:
                break
            if chunk is None:
                break
            yield chunk


st.set_page_config(
    page_title="S&P 500 Research Assistant",
    page_icon="📊",
    layout="wide",
)

# Initialize session state early (before sidebar references it)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = create_agent()

# --- Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/amazon-web-services.png", width=60)
    st.title("S&P 500 Research Assistant")
    st.caption("Flexible schemas. Vector + text search. Aggregation pipelines. All in DocumentDB.")
    st.markdown("---")
    st.markdown(
        """
        **Why DocumentDB for AI?**

        Store structured and unstructured data side by side.
        Query with vector search, text search, and aggregation
        pipelines — no extra databases, no sync pipelines.

        **What's Under the Hood:**
        - 🗄️ **Amazon DocumentDB** — MongoDB-compatible, with native vector + text search
        - 🧠 **Amazon Bedrock** — Claude (reasoning) + Titan (embeddings)
        - 🤖 **Strands Agents SDK** — agentic orchestration

        **DocumentDB Indexes Powering This Demo:**
        - 🔍 HNSW Vector Index → semantic search (cosine, 1024d)
        - 📝 Text Index → keyword search with relevance scoring
        - 📁 Compound Index → sector + market cap filtering

        **Try These:**
        """
    )
    sample_questions = [
        "Find AI chip companies and compare their revenue growth",
        "Which companies are involved in cloud computing?",
        "Search for semiconductor manufacturers",
        "What are the top 5 S&P 500 companies by market cap?",
        "Tell me about Amazon",
        "Find companies in the Health Care sector",
        "Which companies mention lithium in their business?",
        "Which S&P 500 companies are in the insurance industry?",
    ]
    for q in sample_questions:
        if st.button(q, key=q, use_container_width=True):
            st.session_state["pending_question"] = q
            st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent = create_agent()
        st.rerun()
    st.caption("Demo: Amazon DocumentDB for AI Workloads")

# --- Main Area ---
st.header("📊 AI-Powered S&P 500 Research")
st.caption("Ask questions about ~500 S&P 500 companies across 11 GICS sectors")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "tools_used" in msg:
            with st.expander("🛠️ Tools Used", expanded=True):
                for t in msg["tools_used"]:
                    st.markdown(f"- {t}")

# Always show chat input
prompt = st.chat_input("Ask about S&P 500 companies, sectors, or financial metrics...")

# Override with sidebar question if one was clicked
if "pending_question" in st.session_state:
    prompt = st.session_state.pop("pending_question")

if prompt:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get agent response with streaming and tool tracking
    with st.chat_message("assistant"):
        callback = StreamlitCallbackHandler()
        status_container = st.status("🤖 Agent is thinking...", expanded=True)
        agent_error = [None]
        agent = st.session_state.agent
        agent.callback_handler = callback

        def run_agent():
            try:
                agent(prompt)
            except Exception as e:
                agent_error[0] = e
            finally:
                callback.mark_done()

        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

        # Stream text as it arrives
        response_text = st.write_stream(callback.stream())

        thread.join()

        if agent_error[0]:
            response_text = f"Error: {str(agent_error[0])}"
            st.error(response_text)

        # Show tools used in the status
        if callback.tool_calls:
            for t in callback.tool_calls:
                status_container.write(f"✅ {t}")
            status_container.update(
                label=f"✅ Agent used {len(callback.tool_calls)} tool(s)",
                state="complete",
                expanded=True,
            )
        else:
            status_container.update(label="✅ Done", state="complete", expanded=False)

        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "tools_used": callback.tool_calls,
        })
