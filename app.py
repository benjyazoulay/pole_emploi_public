import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import io
import base64
import json
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import unicodedata

# Set page config at the very beginning
st.set_page_config(layout="wide", page_title="Pôle Emploi Public", menu_items = None)

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
        margin-top: -10px !important; /* Ajustez cette valeur si nécessaire */
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
            margin-top: -10px !important; /* Ajustez cette valeur pour mobile si nécessaire */
        }
    }
    </style>
    """, unsafe_allow_html=True)

# Function to update the dataframe
def update_dataframe():
    monday = (datetime.now() - timedelta(days=datetime.now().weekday() + 1)).strftime("%Y%m%d")
    
    # URL of the page to scrape
    page_url = "https://www.data.gouv.fr/fr/datasets/6322e99e12175f7eb26ff465/"
    
    # Read the HTML content of the page
    response = requests.get(page_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Use a regular expression to extract the CSV file URL
    pattern = f'"name": "offres-datagouv-{monday}.csv", "url": "(https://www.data.gouv.fr/fr/datasets/r/[^"]+)"'
    match = re.search(pattern, str(soup))
    
    if match:
        csv_url = match.group(1)
        # Download the CSV file
        response = requests.get(csv_url)
        df = pd.read_csv(io.StringIO(response.content.decode('utf-8')), sep=';')
        return df
    else:
        st.error("CSV file URL not found.")
        st.error(pattern)
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
    
    # Convert all object columns to string to avoid issues with float values
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str)
    return df

# Function to get unique non-null values
def get_unique_values(series):
    return series.dropna().unique().tolist()

# Function to encode state to URL
def encode_state(state):
    json_string = json.dumps(state)
    return base64.urlsafe_b64encode(json_string.encode()).decode()

# Function to decode state from URL
def decode_state(encoded_state):
    json_string = base64.urlsafe_b64decode(encoded_state.encode()).decode()
    return json.loads(json_string)

# Function to extract department number from location string
def extract_department_number(location):
    match = re.search(r'\b(\d{2,3})\b', location)
    if match:
        return int(match.group(1))
    return float('inf')  # Assign a large number to non-department locations

# Function to get sorted unique values based on department numbers
def get_sorted_localisation_values(series):
    unique_values = series.dropna().unique()
    sorted_values = sorted(unique_values, key=extract_department_number)
    return sorted_values

def clean_string(s):
    if not isinstance(s, str):
        return s
    
    # Normaliser la chaîne pour séparer les caractères de base des accents
    cleaned_str = unicodedata.normalize('NFD', s)
    
    # Supprimer les accents
    cleaned_str = ''.join([c for c in cleaned_str if unicodedata.category(c) != 'Mn'])
    
    # Supprimer les parenthèses, guillemets, slashs et autres caractères spéciaux
    cleaned_str = cleaned_str.replace('(', '').replace(')', '').replace('"', '').replace('/', '').replace('«', '').replace('»', '')
    cleaned_str = cleaned_str.replace(',', '').replace(':', '').replace(';', '').replace('.', '')
    cleaned_str = cleaned_str.replace("'", '-')
    
    return cleaned_str

# Main function to run the app
def main():
    # Banner
    st.markdown("""
    <style>
    /* Style spécifique pour les mobiles */
    @media only screen and (max-width: 600px) {
        h1 {
            text-align: center; /* Centre le texte */
        }
    }
    </style>
    <h1> 
        <a href="https://pole-emploi-public.streamlit.app/" target="_self" style="color: inherit; text-decoration: none;">
            Pôle Emploi Public
        </a> 
    </h1>
    """, unsafe_allow_html=True)
    

    st.write("")  # Add some space

    # Load data
    if 'df' not in st.session_state:
        st.session_state.df = load_data()
        st.success("Base de données mise à jour avec succès!")

    df = st.session_state.df

    # Check for state in URL
    if 'state' in st.query_params:
        state = decode_state(st.query_params['state'])
    else:
        state = {
            'intitule_poste': "data&générative& IA&LLM&données",
            'organisme': "",
            'versant': [v for v in get_unique_values(df['Versant']) if 'Etat' in v],
            'categorie': [c for c in get_unique_values(df['Catégorie']) if 'Catégorie A' in c],
            'nature_emploi': [n for n in get_unique_values(df['Nature de l\'emploi']) if 'itulaire' in n],
            'localisation_poste': [l for l in get_unique_values(df['Localisation du poste']) if re.search(r'Paris|91|92|93|94|95|\(77|\(78', l)]
        }

    # Sidebar
    st.sidebar.header("Filtres")

    intitule_poste = st.sidebar.text_input("Intitulé du poste", value=state['intitule_poste'])
    organisme = st.sidebar.text_input("Organisme de rattachement", value=state['organisme'])

    versant_options = get_unique_values(df['Versant'])
    versant = st.sidebar.multiselect("Versant", options=versant_options, default=state['versant'])

    categorie_options = get_unique_values(df['Catégorie'])
    categorie = st.sidebar.multiselect("Catégorie", options=categorie_options, default=state['categorie'])

    nature_emploi_options = get_unique_values(df['Nature de l\'emploi'])
    nature_emploi = st.sidebar.multiselect("Nature de l'emploi", options=nature_emploi_options, default=state['nature_emploi'])

    localisation_options = get_sorted_localisation_values(df['Localisation du poste'])
    localisation_poste = st.sidebar.multiselect("Localisation du poste", options=localisation_options, default=state['localisation_poste'])

    # Update state
    current_state = {
        'intitule_poste': intitule_poste,
        'organisme': organisme,
        'versant': versant,
        'categorie': categorie,
        'nature_emploi': nature_emploi,
        'localisation_poste': localisation_poste
    }

    # Create shareable link
    encoded_state = encode_state(current_state)
    shareable_link = f"{st.get_option('browser.serverAddress')}/?state={encoded_state}"
    
    # Update URL with current state
    st.query_params['state'] = encoded_state

    # Filter dataframe
    filtered_df = df.copy()

    # Apply filters only if options are selected
    if versant:
        filtered_df = filtered_df[filtered_df['Versant'].isin(versant)]
    if categorie:
        filtered_df = filtered_df[filtered_df['Catégorie'].isin(categorie)]
    if nature_emploi:
        filtered_df = filtered_df[filtered_df['Nature de l\'emploi'].isin(nature_emploi)]
    if localisation_poste:
        filtered_df = filtered_df[filtered_df['Localisation du poste'].isin(localisation_poste)]

    # Filter by job title
    intitule_keywords = intitule_poste.split('&')
    filtered_df = filtered_df[filtered_df['Intitulé du poste'].str.contains('|'.join(intitule_keywords), case=False, na=False)]
    organisme_keywords = organisme.split('&')
    filtered_df = filtered_df[filtered_df['Organisme de rattachement'].str.contains('|'.join(organisme_keywords), case=False, na=False)]

    final_df = filtered_df[['Organisme de rattachement', 'Intitulé du poste', 'Localisation du poste', 'Date de première publication', 'Référence', 'Catégorie', 'Versant', 'Nature de l\'emploi']].copy()
    final_df['Date de première publication'] = pd.to_datetime(final_df['Date de première publication'], format='%d/%m/%Y', errors='coerce')
    #final_df['Date de première publication'] = final_df['Date de première publication'].dt.strftime('%d/%m/%Y')
    final_df.loc[:, 'Lien'] = ('https://choisirleservicepublic.gouv.fr/offre-emploi/' +
                    final_df['Intitulé du poste'].apply(lambda x: clean_string(x.lower()).replace(' ', '-')) +
                    '-reference-' +
                    final_df['Référence'].astype(str) +
                    '/')
    final_df.loc[:, 'Lien'] = final_df['Lien'].apply(lambda x: clean_string(x.lower()).replace(' ', ''))
    # Download buttons
    csv = final_df.to_csv(index=False).encode('utf-8')
    excel = io.BytesIO()
    final_df.to_excel(excel, index=False, engine='openpyxl')
    excel.seek(0)

    # Create clickable job titles
    #final_df['Intitulé du poste'] = final_df.apply(lambda row: f'<a href="{row["Lien"]}" target="_blank">{row["Intitulé du poste"]}</a>', axis=1)
    final_df = final_df.sort_values(by='Date de première publication', ascending=False)

    lundi = (datetime.now() - timedelta(days=datetime.now().weekday() + 1)).strftime("%d-%m-%Y")
    st.write(f"{final_df.shape[0]} offres correspondantes au {lundi}")

    # AgGrid table
    gb = GridOptionsBuilder.from_dataframe(final_df[['Organisme de rattachement', 'Intitulé du poste', 'Localisation du poste', 'Date de première publication', 'Référence', 'Catégorie', 'Versant', 'Nature de l\'emploi']])
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    gb.configure_default_column(resizable=True, filterable=True, sortable=True, autoHeight=True, wrapText=True, cellStyle={"line-height": "18px"})

    # Define minimum width for each column
    min_widths = {
        'Organisme de rattachement': 200,
        'Intitulé du poste': 200,
        'Localisation du poste': 150,
        'Date de première publication': 150,
        'Référence': 150,
        'Catégorie': 150,
        'Versant': 200,
        'Nature de l\'emploi': 300
    }

    # Apply the minimum widths to each column
    for column, min_width in min_widths.items():
        gb.configure_column(column, minWidth=min_width)

    # Custom JS class for rendering clickable links
    cellrender_jscode = JsCode("""
    class UrlCellRenderer {
    init(params) {
        this.eGui = document.createElement('a');

        // Fonction pour supprimer l'accentuation et les caractères spéciaux
        function cleanString(str) {
        // Supprimer l'accentuation
        let cleanedStr = str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        // Supprimer les parenthèses, guillemets, slashs et autres caractères spéciaux
        cleanedStr = cleanedStr.replace(/[\(\)\"\/\,\:\;\.]/g, '');
        cleanedStr = cleanedStr.replace(/\'/g, '-');
        return cleanedStr;
        }

        // Utilisation des crochets pour accéder aux propriétés avec des espaces
        const intitule = params.data['Intitulé du poste']
        ? cleanString(params.data['Intitulé du poste'].toLowerCase()).replace(/ /g, '-')
        : '';
        const reference = params.data['Référence']
        ? params.data['Référence']
        : '';

        this.eGui.innerText = params.value;
        this.eGui.setAttribute('href', `https://choisirleservicepublic.gouv.fr/offre-emploi/${intitule}-reference-${reference}/`);
        this.eGui.setAttribute('target', "_blank");
    }

    getGui() {
        return this.eGui;
    }
    }

    """)

    # Apply the custom renderer to the 'Intitulé du poste' column
    gb.configure_column("Intitulé du poste", cellRenderer=cellrender_jscode)

    grid_options = gb.build()

    AgGrid(final_df, gridOptions=grid_options, height=1200, fit_columns_on_grid_load=True, allow_unsafe_jscode=True)
    
    st.markdown("""
    <p style='text-align: right;'>Application créée par <a href='https://www.linkedin.com/in/benjaminazoulay/' target='_blank'>Benjamin Azoulay</a></p>
    """, unsafe_allow_html=True)
    
    # Move download buttons to sidebar
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

# Run the app
if __name__ == "__main__":
    main()
