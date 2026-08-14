import os
import sys
import asyncio
import logging

# root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# load loggings from the embedding models and databse
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)

from dotenv import load_dotenv

from google.genai import types
from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io, llm
from livekit.plugins import (google, noise_cancellation)

from rag import load_embedder, load_chroma, TOP_K

try:
    from .prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION, SYSTEM_INSTRUCTION
except ImportError:
    from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION, SYSTEM_INSTRUCTION


load_dotenv()

LIVEKIT_URL = os.getenv("LIVEKIT_URL")

_GLOBAL_EMBEDDER = None
_GLOBAL_COLLECTION = None

def get_embedder():
    global _GLOBAL_EMBEDDER
    if _GLOBAL_EMBEDDER is None:
        _GLOBAL_EMBEDDER = load_embedder()
    return _GLOBAL_EMBEDDER

def get_collection():
    global _GLOBAL_COLLECTION
    if _GLOBAL_COLLECTION is None:
        _GLOBAL_COLLECTION = load_chroma()
    return _GLOBAL_COLLECTION


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=AGENT_INSTRUCTION)

    @llm.function_tool(description="Search the RAG vector database for relevant information matching the user's query.")
    async def search_knowledge_base(self, query: str) -> str:
        """Search the ChromaDB vector store for relevant context matching the user's query.
        
        Args:
            query: The user's query or search term to look up in the database.
        """
        try:
            embedder = get_embedder()
            collection = get_collection()
            embedding = embedder.encode(f"query: {query}", normalize_embeddings=True).tolist()
            results = collection.query(query_embeddings=[embedding], n_results=TOP_K)
            documents = results.get("documents", [[]])[0]
            if documents:
                return "\n\n".join(documents)
            return "No relevant information found in the database."
        except Exception as e:
            return f"Error retrieving context from database: {e}"


server = AgentServer()

@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    # load embedidng model before call starts so that latency is less during conversation
    get_embedder()
    get_collection()

    # connect worker process to livekit room after models loaded
    await ctx.connect()

    # init gemini realtime session
    session = AgentSession(
        llm=google.beta.realtime.RealtimeModel(
            model="gemini-3.1-flash-live-preview",
            voice="Zephyr",
            instructions=f"{SYSTEM_INSTRUCTION}\n\n{AGENT_INSTRUCTION}",
            api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            conn_options=agents.APIConnectOptions(max_retry=5, timeout=60.0),
            http_options=types.HttpOptions(async_client_args={'open_timeout': 60.0}),
        ),
        aec_warmup_duration=0.0
    )

    agent = Assistant()
        
    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony() 
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP 
                else noise_cancellation.BVC(),
            ),
        ),
    )

    # wait 0.5 sec after session live then trigger greeting
    await asyncio.sleep(0.5)
    if session._activity and session._activity.realtime_llm_session:
        session._activity.realtime_llm_session._send_client_event(
            types.LiveClientContent(
                turns=[
                    types.Content(
                        parts=[types.Part(text="सत्र सुरु भयो। कृपया सामान्यभन्दा अलिकति छिटो, फुर्तिलो गतिमा (लगभग १.१ गुना) यो स्वागत अभिवादन भन्नुहोस्: 'नमस्कार! म तपाईंलाई के सहयोग गर्न सक्छु होला?'")],
                        role="user"
                    )
                ],
                turn_complete=True
            )
        )


if __name__ == "__main__":
    agents.cli.run_app(server)