## Stack
- n8n (orchestration)
- FastAPI (backend)
- Next.js 14 App Router (frontend)
- Supabase Auth + PostgreSQL (user data)
- Pinecone (vector storage)
- OpenRouter (LLM gateway)
- OpenAI Whisper (STT) + OpenAI TTS (voice)
- Railway (FastAPI hosting) + Vercel (Next.js hosting)

## Setup
```bash
cd bloomberg-terminal
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload
```
