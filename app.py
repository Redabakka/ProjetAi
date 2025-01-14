import streamlit as st
import requests

# Configuration de la page
st.set_page_config(page_title="Chatbot Automobile", layout="wide", initial_sidebar_state="expanded")

# URL du backend FastAPI
BACKEND_URL = "http://127.0.0.1:8000/generate"

# Barre de navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller à", ["Diagnostic", "Entretien", "Recherche de véhicules (Conseil)"])

# Fonction pour interroger le backend avec un fichier PDF
def query_backend_with_pdf(prompt, file):
    try:
        if file:
            files = {
                "prompt": (None, prompt),
                "file": (file.name, file.getvalue(), "application/pdf")
            }
        else:
            files = {"prompt": (None, prompt)}

        # Envoi de la requête au backend
        response = requests.post(BACKEND_URL, files=files)

        # Vérifier la réponse HTTP
        if response.status_code == 200:
            st.info("Requête envoyée avec succès.")
            return response.json()  # Retourne la réponse JSON complète
        else:
            st.error(f"Erreur du backend : {response.status_code}")
            st.error(f"Message d'erreur : {response.text}")
            return None
    except Exception as e:
        st.error(f"Erreur de communication avec le backend : {str(e)}")
        return None

# Fonction pour afficher les résultats
def display_results(response):
    if response:
        gemini_response = response.get("gemini_response", "Pas de réponse générée.")
        local_response = response.get("local_response", "Pas de réponse locale disponible.")

        st.write("### Résultat IA :")
       # st.write("**Réponse de Gemini :**")
        st.markdown(gemini_response)

        #st.write("**Réponse locale :**")
        #st.write(local_response)
    else:
        st.error("Aucune réponse valide reçue du backend.")

# Fonction générique pour chaque page
def process_page(title, input_key, file_key, button_text):
    st.title(title)
    uploaded_file = st.file_uploader("Déposez un fichier PDF", type=["pdf"], key=file_key)
    user_input = st.text_input("Décrivez votre problème ou besoin ici :", key=input_key)
   
    if st.button(button_text):
        if not user_input.strip():
            st.warning("Veuillez entrer une description.")
        else:
            response = query_backend_with_pdf(user_input, uploaded_file)
            display_results(response)

# Fonctionnalités pour chaque page
if page == "Diagnostic":
    process_page("🔧 Diagnostic assisté par IA", "diagnostic_input", "diagnostic_pdf", "Diagnostiquer")

elif page == "Entretien":
    process_page("🛠️ Gestion de l'entretien", "entretien_input", "entretien_pdf", "Obtenir des conseils d'entretien")

elif page == "Recherche de véhicules (Conseil)":
    process_page("🚗 Recherche de véhicules (Conseil)", "recherche_input", "recherche_pdf", "Rechercher")
