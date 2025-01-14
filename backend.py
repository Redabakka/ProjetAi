from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from sentence_transformers import SentenceTransformer
import fitz  # PyMuPDF pour extraction du texte PDF
import faiss
import os
import numpy as np
import requests
app = FastAPI()

# Configuration de l'API Gemini
GEMINI_API_KEY = "AIzaSyDiyT3x5563LM3k277sR8qQ2wAwWIpb-lQ"  
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

# Configuration des embeddings et FAISS
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
model = SentenceTransformer(EMBEDDING_MODEL)
INDEX_PATH = "faiss_index"
documents = []  # Liste pour stocker les textes indexés

# Chargement ou création de l'index FAISS
if os.path.exists(INDEX_PATH):
    index = faiss.read_index(INDEX_PATH)
    print("Index FAISS chargé avec succès.")
else:
    index = faiss.IndexFlatL2(model.get_sentence_embedding_dimension())
    print("Nouvel index FAISS créé.")

# Fonction pour extraire le texte des fichiers PDF
def extract_text_from_pdf(file_content: bytes):
    pdf = fitz.open(stream=file_content, filetype="pdf")
    paragraphs = []
    for page in pdf:
        text = page.get_text()
        if text.strip():
            paragraphs.extend([p.strip() for p in text.split("\n\n") if p.strip()])
    return paragraphs

# Ajouter des documents à l'index FAISS
def add_to_faiss(paragraphs):
    global index, documents
    embeddings = model.encode(paragraphs)
    index.add(np.array(embeddings, dtype="float32"))
    documents.extend(paragraphs)
    faiss.write_index(index, INDEX_PATH)

# Recherche dans FAISS pour trouver les documents pertinents
def search_faiss(query, k=100):
    query_embedding = model.encode([query])
    distances, indices = index.search(np.array(query_embedding, dtype="float32"), k)
    results = [documents[i] for i in indices[0] if i < len(documents)]
    return results

# Appel à l'API Gemini (structure spécifique : "contents" → "parts")
def call_gemini_api(prompt):
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    try:
        response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        
        # Extraction propre de la réponse
        candidates = response_json.get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"]
        return "Pas de réponse disponible depuis Gemini."
    except requests.exceptions.RequestException as e:
        return f"Erreur API Gemini : {str(e)}"

# Endpoint pour uploader un PDF
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")
        
        file_content = await file.read()
        paragraphs = extract_text_from_pdf(file_content)

        if paragraphs:
            add_to_faiss(paragraphs)
            return {"message": f"{len(paragraphs)} paragraphes ajoutés à l'index FAISS."}
        return {"message": "Aucun texte valide extrait du PDF."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement : {str(e)}")

# Endpoint pour générer une réponse augmentée avec FAISS et Gemini
@app.post("/generate")
async def generate_response(prompt: str = Form(...)):
    try:
        # Recherche dans FAISS
        relevant_docs = search_faiss(prompt, k=100)
        context = "\n".join(relevant_docs)

        # Enrichir le prompt avec le contexte trouvé
        enriched_prompt = f"Question : {prompt}\n\nContexte pertinent :\n{context}"
        gemini_response = call_gemini_api(enriched_prompt)

        return {
            "gemini_response": gemini_response,
            "relevant_docs": relevant_docs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")

# Endpoint de test
@app.get("/")
async def root():
    return {"message": "Backend RAG avec FAISS et Gemini API opérationnel."}
