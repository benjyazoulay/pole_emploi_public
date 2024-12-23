import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import re
import io
import base64
import json
import unicodedata
import sys

# Set page config at the very beginning
st.set_page_config(layout="wide", page_title="Pôle Emploi Public", page_icon="https://github.com/user-attachments/assets/e376bdba-3b42-43d2-ba7e-0b2d6845aa09", menu_items=None)

# Injecter du CSS pour masquer la barre par défaut de Streamlit
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Supprimer l'espace en haut de la page */
    .main .block-container {
        padding-top: 0 !important;
        margin-top: -40px !important;
    }

    /* Style spécifique pour les mobiles */
    @media only screen and (max-width: 600px) {
        img {
            display: block;
            margin-left: auto;
            margin-right: auto;
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        .main .block-container {
            padding-top: 0 !important;
            margin-top: -30px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# Function to update the dataframe from Hugging Face
def update_dataframe():
    csv_url = "https://huggingface.co/datasets/BenjaminAzoulay/choisirleservicepublic/resolve/main/offres_historique.csv"
    try:
        response = requests.get(csv_url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        download_size = 0

        chunks = []
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                chunks.append(chunk)
                download_size += len(chunk)
                progress = (download_size / total_size) * 100
                sys.stdout.write(f"\rTéléchargement en cours : {progress:.2f}%")
                sys.stdout.flush()

        csv_content = b''.join(chunks)
        df = pd.read_csv(io.StringIO(csv_content.decode('utf-8')), sep=',', encoding='utf-8')
        print("\nTéléchargement terminé.")
        return df
    except Exception as e:
        st.error(f"Erreur lors du téléchargement du CSV depuis Hugging Face : {str(e)}")
        return None

# Load initial data
@st.cache_data(ttl="30s")
def load_data():
    try:
        df = update_dataframe()
        if df is None:
            raise Exception("Unable to update dataframe")
    except Exception as e:
        st.warning(f"Impossible de mettre à jour la base de données : {str(e)}. Chargement des données locales.")
        df = pd.read_csv("offres.csv", sep=';', encoding='utf-8')
    
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str)
    return df

def get_unique_values(series):
    return series.dropna().unique().tolist()

def encode_state(state):
    json_string = json.dumps(state)
    return base64.urlsafe_b64encode(json_string.encode()).decode()

def decode_state(encoded_state):
    json_string = base64.urlsafe_b64decode(encoded_state.encode()).decode()
    return json.loads(json_string)

def extract_department_number(location):
    match = re.search(r'\b(\d{2,3})\b', location)
    if match:
        return int(match.group(1))
    return float('inf')

def get_sorted_localisation_values(series):
    unique_values = series.dropna().unique()
    sorted_values = sorted(unique_values, key=extract_department_number)
    return sorted_values

def clean_string(s):
    if not isinstance(s, str):
        return s
    cleaned_str = unicodedata.normalize('NFD', s)
    cleaned_str = ''.join([c for c in cleaned_str if unicodedata.category(c) != 'Mn'])
    cleaned_str = cleaned_str.replace('(', '').replace(')', '').replace('"', '').replace('/', '').replace('«', '').replace('»', '')
    cleaned_str = cleaned_str.replace(',', '').replace(':', '').replace(';', '').replace('.', '')
    cleaned_str = cleaned_str.replace("'", '-')
    return cleaned_str

def create_job_url(intitule, reference):
    clean_intitule = clean_string(intitule.lower()).replace(' ', '-')
    return f"https://choisirleservicepublic.gouv.fr/offre-emploi/{clean_intitule}-reference-{reference}/"

def main():
    st.markdown("""
    <h1> 
        <a href="https://pole-emploi-public.streamlit.app/" target="_self" style="color: inherit; text-decoration: none;">
            Pôle Emploi Public
        </a> 
    </h1>
    """, unsafe_allow_html=True)

    st.write("")

    if 'df' not in st.session_state:
        st.session_state.df = load_data()
        st.success("Base de données mise à jour avec succès!")

    df = st.session_state.df

    if 'state' in st.query_params:
        state = decode_state(st.query_params['state'])
    else:
        state = {
            'intitule_poste': "data&générative& IA&LLM&données",
            'organisme': "",
            'versant': [v for v in get_unique_values(df['Versant']) if 'Etat' in v],
            'categorie': [c for c in get_unique_values(df['Catégorie']) if 'Catégorie A' in c],
            'nature_emploi': [n for n in get_unique_values(df['Nature de l\'emploi']) if 'itulaire' in n],
            'localisation_poste': [l for l in get_unique_values(df['Localisation du poste']) if re.search(r'Paris|91|92|93|94|95|\(77|\(78', l)],
            'fiche_de_poste': ""
        }

    st.sidebar.header("Filtres")
    sidebar_header_style = """
        <style>
        [data-testid="stSidebarHeader"] {
            padding: 10px !important;
            margin-bottom: -50px !important;
        }
        </style>
        """
    st.markdown(sidebar_header_style, unsafe_allow_html=True)

    # Filtres
    intitule_poste = st.sidebar.text_input("Intitulé du poste", value=state['intitule_poste'])
    organisme = st.sidebar.text_input("Organisme de rattachement", value=state['organisme'])
    fiche_de_poste = st.sidebar.text_input("Recherche dans la fiche de poste", value=state['fiche_de_poste'])

    versant_options = get_unique_values(df['Versant'])
    versant = st.sidebar.multiselect("Versant", options=versant_options, default=state['versant'])

    categorie_options = get_unique_values(df['Catégorie'])
    categorie = st.sidebar.multiselect("Catégorie", options=categorie_options, default=state['categorie'])

    nature_emploi_options = get_unique_values(df['Nature de l\'emploi'])
    nature_emploi = st.sidebar.multiselect("Nature de l'emploi", options=nature_emploi_options, default=state['nature_emploi'])

    localisation_options = get_sorted_localisation_values(df['Localisation du poste'])
    localisation_poste = st.sidebar.multiselect("Localisation du poste", options=localisation_options, default=state['localisation_poste'])

    current_state = {
        'intitule_poste': intitule_poste,
        'organisme': organisme,
        'versant': versant,
        'categorie': categorie,
        'nature_emploi': nature_emploi,
        'localisation_poste': localisation_poste,
        'fiche_de_poste': fiche_de_poste
    }

    encoded_state = encode_state(current_state)
    st.query_params['state'] = encoded_state

    # Filtrage
    filtered_df = df[df['alive'] == "True"].copy()

    if versant:
        filtered_df = filtered_df[filtered_df['Versant'].isin(versant)]
    if categorie:
        filtered_df = filtered_df[filtered_df['Catégorie'].isin(categorie)]
    if nature_emploi:
        filtered_df = filtered_df[filtered_df['Nature de l\'emploi'].isin(nature_emploi)]
    if localisation_poste:
        filtered_df = filtered_df[filtered_df['Localisation du poste'].isin(localisation_poste)]

    intitule_keywords = intitule_poste.split('&')
    filtered_df = filtered_df[filtered_df['Intitulé du poste'].str.contains('|'.join(intitule_keywords), case=False, na=False)]
    
    organisme_keywords = organisme.split('&')
    filtered_df = filtered_df[filtered_df['Organisme de rattachement'].str.contains('|'.join(organisme_keywords), case=False, na=False)]

    if fiche_de_poste:
        fiche_keywords = fiche_de_poste.split('&')
        filtered_df = filtered_df[filtered_df['fiche_de_poste'].str.contains('|'.join(fiche_keywords), case=False, na=False)]

    # Préparation du DataFrame final
    final_df = filtered_df[['Organisme de rattachement', 'Intitulé du poste', 'Localisation du poste', 
                           'Date de première publication', 'Référence', 'Catégorie', 'Versant', 
                           'Nature de l\'emploi']].copy()
    
    final_df = final_df.sort_values(by='Date de première publication', ascending=False)

    # Créer les liens hypertextes
    final_df['Lien'] = final_df.apply(lambda x: create_job_url(x['Intitulé du poste'], x['Référence']), axis=1)

    # Configuration des colonnes pour st.dataframe
    column_config = {
        "Lien": st.column_config.LinkColumn(
            "Lien",
            help="Cliquez pour voir l'offre détaillée",
            validate="https://.*",
            max_chars=200,
            display_text="🔗"
        ),
        "Intitulé du poste": st.column_config.Column(
            "Titre du poste",
            width="medium"
        ),
        "Date de première publication": st.column_config.DateColumn(
            "Date de publication",
            format="DD/MM/YYYY"
        ),
        "Organisme de rattachement": st.column_config.Column(
            "Organisme",
            width="medium"
        ),
        "Localisation du poste": st.column_config.Column(
            "Localisation",
            width="small"
        ),
        "Référence": st.column_config.Column(
            "Référence",
            width="small"
        )
    }

    # Réorganiser les colonnes pour l'affichage
    display_columns = ['Intitulé du poste', 'Lien', 'Organisme de rattachement', 'Localisation du poste', 
                      'Date de première publication', 'Référence', 'Catégorie', 'Versant', 
                      'Nature de l\'emploi']
    display_df = final_df[display_columns]

    # Affichage du nombre d'offres
    lundi = (datetime.now() - timedelta(days=datetime.now().weekday() + 1)).strftime("%d-%m-%Y")
    st.write(f"{final_df.shape[0]} offres correspondantes au {lundi}")

    # Affichage du tableau
    st.dataframe(
        display_df,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        height=800
    )

    # Boutons de téléchargement
    csv = final_df.to_csv(index=False).encode('utf-8')
    excel = io.BytesIO()
    final_df.to_excel(excel, index=False, engine='openpyxl')
    excel.seek(0)

    st.sidebar.header("Télécharger les données")
    st.sidebar.download_button(
        label="CSV",
        data=csv,
        file_name="offres.csv",
        mime="text/csv"
    )
    st.sidebar.download_button(
        label="Excel",
        data=excel,
        file_name="offres.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("""<p style='text-align: right;'>Application créée par <a href='https://www.linkedin.com/in/benjaminazoulay/' target='_blank'>Benjamin Azoulay</a></p>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()