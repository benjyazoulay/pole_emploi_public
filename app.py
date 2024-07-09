import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import io

# Set page config at the very beginning
st.set_page_config(layout="wide", page_title="Pôle Emploi public")

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
@st.cache_data
def load_data():
    df = pd.read_csv("offres.csv", sep=';', encoding='utf-8')
    # Convert all object columns to string to avoid issues with float values
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str)
    return df

# Function to get unique non-null values
def get_unique_values(series):
    return series.dropna().unique().tolist()

# Main function to run the app
def main():
    # Banner
    st.markdown("""
        <div style='background-color: #F5F5F5; padding: 10px; color: black; text-align: center; border-radius: 10px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);'>
            <h1 style='font-size: 24px; font-weight: bold; margin: 0;'>Pôle Emploi public</h1>
        </div>
    """, unsafe_allow_html=True)

    st.write("")  # Add some space

    # Load data
    df = load_data()

    # Sidebar
    st.sidebar.header("Filtres")

    intitule_poste = st.sidebar.text_input("Intitulé du poste", value="data&Data&générative& IA&LLM")

    versant_options = get_unique_values(df['Versant'])
    versant = st.sidebar.multiselect("Versant", options=versant_options, default=[v for v in versant_options if 'Etat' in v])

    categorie_options = get_unique_values(df['Catégorie'])
    categorie = st.sidebar.multiselect("Catégorie", options=categorie_options, default=[c for c in categorie_options if 'Catégorie A' in c])

    nature_emploi_options = get_unique_values(df['Nature de l\'emploi'])
    nature_emploi = st.sidebar.multiselect("Nature de l'emploi", options=nature_emploi_options, default=[n for n in nature_emploi_options if 'itulaire' in n])


    localisation_options = get_unique_values(df['Localisation du poste'])
    localisation_poste = st.sidebar.multiselect("Localisation du poste", options=localisation_options, default=[l for l in localisation_options if re.search(r'Paris|91|92|93|94|95|77|78', l)])

    if st.sidebar.button("Mettre à jour la base (lundi)"):
        new_df = update_dataframe()
        if new_df is not None:
            df = new_df
            st.success("Base de données mise à jour avec succès!")

    # Filter dataframe
    filtered_df = df[
        df['Versant'].isin(versant) &
        df['Catégorie'].isin(categorie) &
        df['Nature de l\'emploi'].isin(nature_emploi) &
        df['Localisation du poste'].isin(localisation_poste)
    ]

    # Filter by job title
    intitule_keywords = intitule_poste.split('&')
    filtered_df = filtered_df[filtered_df['Intitulé du poste'].str.contains('|'.join(intitule_keywords), case=False, na=False)]

    final_df = filtered_df[['Organisme de rattachement', 'Intitulé du poste', 'Localisation du poste', 'Date de première publication', 'Référence']]
    final_df['Date de première publication'] = pd.to_datetime(final_df['Date de première publication'], format='%d/%m/%Y', errors='coerce')
    final_df['Lien'] = 'https://choisirleservicepublic.gouv.fr/nos-offres/filtres/mot-cles/' + final_df['Référence'].astype(str) + '/'

    # Assurez-vous que les intitulés de poste contiennent les liens
    final_df['Intitulé du poste cliquable'] = final_df.apply(lambda row: row['Lien'], axis=1)
    final_df = final_df.sort_values(by='Date de première publication', ascending=False)


    # Afficher le dataframe avec les liens configurés
    st.dataframe(
        final_df,
        column_config={
            "Intitulé du poste cliquable": st.column_config.LinkColumn(
                label="Lien",
                help="Cliquez pour voir l'offre",
                display_text="(?:)",  # Utilisation d'une regex pour extraire le texte de l'URL
            ),
            "Date de première publication": st.column_config.DateColumn(
                label="Date de première publication", 
                format="DD/MM/YYYY"
            ),
            "Lien": st.column_config.Column(
                label="Lien", 
                disabled=True
            ),
            "Intitulé du poste": st.column_config.Column(
                label="Intitulé du poste", 
                disabled=True
            ),
        },
        hide_index=True,
        column_order=['Organisme de rattachement', 'Intitulé du poste', 'Localisation du poste', 'Date de première publication', 'Référence', 'Intitulé du poste cliquable']
    )
    # Download buttons
    csv = final_df.to_csv(index=False).encode('utf-8')
    excel = io.BytesIO()
    final_df.to_excel(excel, index=False, engine='openpyxl')
    excel.seek(0)

    col1, col2, col3 = st.columns(3)
    

# Run the app
if __name__ == "__main__":
    main()