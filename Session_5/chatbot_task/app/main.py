import streamlit as st
import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Any

@dataclass
class ChatMessage:
    role: str
    content: str
    sources: List[Any] = field(default_factory=list)
from src.chatbot import CustomChatBot
import os

INDEX_DATA = os.environ.get("INDEX_DATA", "0")
PULL_EMBEDDING_MODEL = os.environ.get("PULL_EMBEDDING_MODEL", "0")

# Configure logger
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more details
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console logs
    ],
)

logger = logging.getLogger(__name__)

# Initialize chatbot instance (avoid reloading)
if "bot" not in st.session_state:
    st.session_state["bot"] = CustomChatBot(index_data=bool(int(INDEX_DATA)), pull_embedding_model=bool(int(PULL_EMBEDDING_MODEL)))

# Streamlit UI setup
st.set_page_config(page_title="ChatDoc", page_icon="📄")
st.header("Chat with your Document")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [ChatMessage(role="assistant", content="How can I help you?")]

if len(st.session_state["messages"]) == 0 or st.sidebar.button("Clear message history"):
    st.session_state["messages"].clear()
    st.session_state["messages"] = [ChatMessage(role="assistant", content="How can I help you?")]

# Display chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg.role):
        st.write(msg.content)
        # Wenn es Quellen gibt, zeige sie als aufklappbares Menü an
        if getattr(msg, "sources", None):
            with st.expander("Gefundene Quellen / Metadaten"):
                for i, doc in enumerate(msg.sources):
                    page = doc.metadata.get('page', 'Unbekannt')
                    st.markdown(f"**Quelle {i+1} (Seite {page}):**\n{doc.page_content}")

# Handle user input
if user_query := st.chat_input(placeholder="Ask me anything!"):
    st.session_state.messages.append(ChatMessage(role="user", content=user_query))
    logger.info(f"Write user message in session state {user_query}")
    st.chat_message("user").write(user_query)

    async def handle_user_query(user_query):
        container = st.empty()
        answer = ""
        retrieved_docs = []
        try:
            # Wir verarbeiten jetzt Dictionaries statt reinen Strings
            async for data in st.session_state["bot"].astream(user_query):
                if data["type"] == "context":
                    retrieved_docs = data["docs"]
                elif data["type"] == "chunk":
                    answer += data["content"]
                    container.markdown(answer)
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            container.error("An error occurred while processing your request.")

        # Store assistant response and sources in session state
        if answer:
            logger.info(f"Write assistant message in session state {user_query}")
            
            # Zeige die Quellen sofort für die aktuelle Antwort an
            if retrieved_docs:
                with st.expander("Gefundene Quellen / Metadaten"):
                    for i, doc in enumerate(retrieved_docs):
                        page = doc.metadata.get('page', 'Unbekannt')
                        st.markdown(f"**Quelle {i+1} (Seite {page}):**\n{doc.page_content}")
            
            st.session_state.messages.append(ChatMessage(role="assistant", content=answer, sources=retrieved_docs))

    with st.chat_message("assistant"):
        with st.spinner("Searching for information in your documents and generation response..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(handle_user_query(user_query))