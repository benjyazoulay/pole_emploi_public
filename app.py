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

# Main function to run the app
def main():
    # Banner
    st.title('Pôle Emploi public')

    st.write("")  # Add some space

    # Load data
    if 'df' not in st.session_state:
        st.session_state.df = load_data()
        st.success("Base de données mise à jour avec succès!")

    df = st.session_state.df

    # Sidebar
    st.sidebar.header("Filtres")

    intitule_poste = st.sidebar.text_input("Intitulé du poste", value="data&générative& IA&LLM&données")
    organisme = st.sidebar.text_input("Organisme de rattachement", value="")

    versant_options = get_unique_values(df['Versant'])
    versant = st.sidebar.multiselect("Versant", options=versant_options, default=[v for v in versant_options if 'Etat' in v])

    categorie_options = get_unique_values(df['Catégorie'])
    categorie = st.sidebar.multiselect("Catégorie", options=categorie_options, default=[c for c in categorie_options if 'Catégorie A' in c])

    nature_emploi_options = get_unique_values(df['Nature de l\'emploi'])
    nature_emploi = st.sidebar.multiselect("Nature de l'emploi", options=nature_emploi_options, default=[n for n in nature_emploi_options if 'itulaire' in n])

    localisation_options = get_unique_values(df['Localisation du poste'])
    localisation_poste = st.sidebar.multiselect("Localisation du poste", options=localisation_options, default=[l for l in localisation_options if re.search(r'Paris|91|92|93|94|95|\(77|\(78', l)])


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

    final_df = filtered_df[['Organisme de rattachement', 'Intitulé du poste', 'Localisation du poste', 'Date de première publication', 'Référence', 'Catégorie', 'Versant', 'Nature de l\'emploi']]
    final_df['Date de première publication'] = pd.to_datetime(final_df['Date de première publication'], format='%d/%m/%Y', errors='coerce')
    final_df['Lien'] = 'https://choisirleservicepublic.gouv.fr/nos-offres/filtres/mot-cles/' + final_df['Référence'].astype(str) + '/'

    # Download buttons
    csv = final_df.to_csv(index=False).encode('utf-8')
    excel = io.BytesIO()
    final_df.to_excel(excel, index=False, engine='openpyxl')
    excel.seek(0)

    # Create clickable job titles
    final_df['Intitulé du poste'] = final_df.apply(lambda row: f'<a href="{row["Lien"]}" target="_blank">{row["Intitulé du poste"]}</a>', axis=1)
    final_df = final_df.sort_values(by='Date de première publication', ascending=False)

    lundi = (datetime.now() - timedelta(days=datetime.now().weekday() + 1)).strftime("%d-%m-%Y")
    st.write(f"{final_df.shape[0]} offres correspondantes au {lundi}")
    
    # CSS to style the table
    table_style = """
    <style>
        .dataframe th {
            text-align: left !important;
        }
    </style>
    """
    
    # Display the CSS
    st.markdown(table_style, unsafe_allow_html=True)

    # Convert the dataframe to HTML and apply custom classes
    html_table = final_df[['Organisme de rattachement', 'Intitulé du poste', 'Localisation du poste', 'Date de première publication', 'Référence', 'Catégorie', 'Versant', 'Nature de l\'emploi']].to_html(escape=False, index=False, classes='dataframe')
    
    # Display the styled table
    st.markdown(html_table, unsafe_allow_html=True)

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