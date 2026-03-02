# AI Document Analysis (RAG Assistant)

A powerful Retrieval-Augmented Generation (RAG) assistant that allows users to upload documents (PDF, DOCX, TXT) and chat with them using LLMs (Groq/Gemini).

## Features
- **Multi-format Support**: Ingest PDF, DOCX, and TXT files.
- **S3 & Supabase Integration**: Persistent document storage and metadata management.
- **Hybrid Search**: Local FAISS vector store for fast retrieval.
- **LLM Fallback**: Answers from general knowledge when docs don't have the answer.
- **Q&A Export**: Export your chat history as clean, styled HTML.

## Tech Stack
- **Backend**: FastAPI, LangGraph, FAISS, Boto3, Supabase-py.
- **Frontend**: Next.js (App Router), Tailwind CSS, Lucide Icons.

## Setup

### Backend
1. `cd backend`
2. `python -m venv .venv`
3. `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
4. `pip install -r requirements.txt`
5. Create `.env` from `.env.example`
6. `python main.py`

### Frontend
1. `cd frontend`
2. `npm install`
3. `npm run dev`
