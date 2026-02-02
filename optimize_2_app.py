"""
SlimAcademy AI Trainer - Streamlit Web Applicatie
Een interactieve studie-trainer die vragen stelt over oorzaak-gevolg relaties.
"""

import streamlit as st
import os
import base64
import json
import re
import random
from dotenv import load_dotenv
from openai import OpenAI
from PyPDF2 import PdfReader


# Laad environment variabelen
load_dotenv()


def clean_and_parse_json(response_text):
    """
    Ultra-Robuuste JSON parser.
    1. Repareert control characters.
    2. Forceert lijst-formaat.
    3. VERTAALT Engelse keys naar Nederlands (fix voor 'No options' bug).
    """
    if not response_text or not response_text.strip():
        return None
    
    try:
        text = response_text.strip()
        
        # Verwijder Markdown code blocks
        if "```" in text:
            text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
            text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
            text = text.strip()

        # Repareer control characters
        def escape_inner_newlines(match):
            return match.group(0).replace('\n', '\\n').replace('\r', '')
        text = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', escape_inner_newlines, text)

        # Parse JSON
        parsed = json.loads(text, strict=False)

        # --- NIEUW: CONTAINER LOGICA ---
        # Als de AI antwoordt met {"exam_questions": [...]}, pakken we die lijst.
        if isinstance(parsed, dict):
            # Check of het in een container zit
            for key in ["exam_questions", "questions", "vragen", "items"]:
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                # Geen container gevonden? Dan is het waarschijnlijk 1 los object -> maak lijst
                parsed = [parsed]

        # --- NIEUW: SLEUTEL VERTALER (Fix voor lege vragen) ---
        # Zorg dat alle keys ("question", "options") worden omgezet naar ("vraag", "opties")
        normalized_list = []
        if isinstance(parsed, list):
            for item in parsed:
                new_item = {}
                # Mapping tabel
                key_map = {
                    "question": "vraag", "vraag": "vraag",
                    "options": "opties", "opties": "opties", "choices": "opties",
                    "correct_answer": "correct_antwoord", "correct_antwoord": "correct_antwoord", "answer": "correct_antwoord",
                    "explanation": "uitleg", "uitleg": "uitleg"
                }
                
                for k, v in item.items():
                    k_lower = k.lower()
                    if k_lower in key_map:
                        new_item[key_map[k_lower]] = v
                    else:
                        new_item[k] = v # Behoud overige keys
                
                # Check of cruciale keys er zijn, anders skippen we dit item
                if "vraag" in new_item and "opties" in new_item:
                    normalized_list.append(new_item)
        
        return normalized_list

    except Exception as e:
        print(f"Parsing error: {e}")
        return None

# ============================================================================
# 🎛️ COCKPIT - CONFIGURATIE DASHBOARD
# ============================================================================
# Deze sectie bevat alle belangrijke instellingen voor deze app.
# Je kunt hier makkelijk wijzigingen aanbrengen zonder te programmeren.
# ============================================================================

# ───────────────────────────────────────────────────────────────────────────
# 1. BRANDING - Pas de naam en uitstraling van de app aan
# ───────────────────────────────────────────────────────────────────────────
CLIENT_NAME = "Toekomst van leren"
APP_EMOJI = "🎓"
APP_TITLE = "Toekomst van leren"

# ───────────────────────────────────────────────────────────────────────────
# 2. FEATURE TOGGLES - Schakel functionaliteit aan/uit
# ───────────────────────────────────────────────────────────────────────────
ENABLE_PERSONAL_UPLOADS = True   # Mag de student zelf bestanden uploaden?

# ───────────────────────────────────────────────────────────────────────────
# 3. API SLEUTEL CONFIGURATIE (Geheim - Eindgebruiker ziet dit NOOIT)
# ───────────────────────────────────────────────────────────────────────────
# GEBRUIK:
# - Zet hieronder 'None' om de veilige .env file te gebruiken (AANBEVOLEN VOOR VERKOOP)
# - Of plak hier tijdelijk je eigen key ('sk-proj-...') om te forceren tijdens testen
# 
# VOORBEELD:
# API_KEY_OVERRIDE = None                           # <- Gebruikt .env (Veilig)
# API_KEY_OVERRIDE = "sk-proj-jouwkeyxxxxxxxx"      # <- Forceert deze key (Tijdelijk testen)

API_KEY_OVERRIDE = None

# ───────────────────────────────────────────────────────────────────────────
# 4. VISUELE STIJL (Huisstijl) - Pas kleuren aan voor je klant
# ───────────────────────────────────────────────────────────────────────────
# GEBRUIK:
# - Voer hex-codes in om de hele app te restylen (bijv. #FF0000 voor rood)
# - PRIMARY_COLOR bepaalt de kleur van knoppen, accenten, en interactieve elementen
# - SIDEBAR_BACKGROUND en SIDEBAR_TEXT zorgen voor contrast en leesbaarheid in de zijbalk
# - HIDE_STREAMLIT_BRANDING verbergt het Streamlit menu en footer (professioneler)

PRIMARY_COLOR = "#6D071A"           # Diep Wijnrood (Bordeaux) - Knoppen en accenten
BACKGROUND_COLOR = "#0E1117"        # Zwart - Achtergrond hoofdscherm
TEXT_COLOR = "#FAFAFA"              # Lichtgrijs - Tekst hoofdscherm
SIDEBAR_BACKGROUND = "#262730"      # Donkergrijs - Achtergrond sidebar
SIDEBAR_TEXT = "#FAFAFA"            # Lichtgrijs - Tekst sidebar (CRUCIAAL voor leesbaarheid)
HIDE_STREAMLIT_BRANDING = True      # Verberg Streamlit menu/footer (True = professioneel)

# ───────────────────────────────────────────────────────────────────────────
# 5. VASTE CURSUS BIBLIOTHEEK - Voeg hier je cursus content toe
# ───────────────────────────────────────────────────────────────────────────
LIBRARY_CONTENT = {
    "Blok 1: Celbiologie": """
Celbiologie - Hoofdstuk 1: Celstructuur en Functie

De cel is de basiseenheid van het leven. Elke cel heeft een celmembraan die de cel afschermt van de omgeving.

Oorzaak-Gevolg Relaties:
- Beschadiging van het celmembraan → Verlies van cel-integriteit → Celdood
- Verhoogde ATP productie → Meer energie beschikbaar → Verhoogde celactiviteit
- Mitochondriale dysfunctie → Verminderde ATP → Cel kan niet functioneren

Endoplasmatisch reticulum (ER) speelt een rol bij eiwitsynthese. Het ruwe ER heeft ribosomen → Eiwitsynthese vindt plaats.
Het gladde ER heeft geen ribosomen → Lipidesynthese en detoxificatie.
    """,
    "Blok 2: Anatomie": """
Anatomie - Hoofdstuk 3: Het Cardiovasculaire Systeem

Het hart pompt bloed door het lichaam via een gesloten circulatiesysteem.

Oorzaak-Gevolg Relaties:
- Verhoogde bloeddruk → Meer druk op bloedvatwanden → Risico op vaatschade
- Arteriosclerose → Verminderde bloedstroom → Orgaanschade
- Hartinfarct → Zuurstoftekort in hartweefsel → Weefselschade → Verminderde pompfunctie

Het hart bestaat uit 4 kamers: 2 atria en 2 ventrikels. Het rechterventrikel pompt bloed naar de longen (kleine circulatie) → gasuitwisseling → zuurstofrijk bloed keert terug naar linker atrium → linkerventrikel pompt naar het lichaam (grote circulatie).
    """,
    "Blok 3: Fysiologie": """
Fysiologie - Hoofdstuk 5: Hormonale Regulatie

Het endocriene systeem reguleert lichaamsfuncties via hormonen.

Oorzaak-Gevolg Relaties:
- Verhoogde hormoonconcentratie → Downregulatie van receptoren → Verminderde gevoeligheid
- Hypofyse scheidt TSH uit → Schildklier produceert T3/T4 → Verhoogd metabolisme
- Te veel cortisol → Immuunsuppressie → Verhoogd infectierisico
- Insulineresistentie → Verhoogde bloedsuikerspiegel → Diabetes type 2

Negatieve feedback loops zorgen voor homeostase. Voorbeeld: Hoge bloedsuiker → Insuline afgifte → Glucose opname in cellen → Bloedsuiker daalt → Insuline afgifte vermindert.
    """,
    "Blok 4: Immunologie": """
Immunologie - Hoofdstuk 7: Het Immuunsysteem

Het immuunsysteem beschermt het lichaam tegen pathogenen.

Oorzaak-Gevolg Relaties:
- Pathogeen binnendringen → Activatie aangeboren immuniteit → Inflammatie
- T-cel activatie → B-cel activatie → Antilichaam productie
- Vaccinatie → Geheugencellen worden gevormd → Snellere respons bij herinfectie
- Auto-immuunziekte → Aanval op eigen cellen → Weefselschade

Het immuunsysteem heeft twee lijnen: aangeboren (snel, niet-specifiek) en verworven (langzaam, specifiek).
    """
}

# ============================================================================
# 🏁 EINDE COCKPIT - Hieronder begint de applicatie code
# ============================================================================

def apply_custom_styling():
    """
    Injecteer agressieve CSS om de app te restylen volgens Cockpit instellingen.
    Dit lost het "witte tekst op witte achtergrond" probleem definitief op.
    """
    # Bepaal of we Streamlit branding verbergen
    hide_branding_css = ""
    if HIDE_STREAMLIT_BRANDING:
        hide_branding_css = """
        /* Verberg Streamlit branding */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        """
    
    # Injecteer de agressieve custom CSS
    custom_css = f"""
    <style>
        /* ===== MAIN APP STYLING ===== */
        /* Forceer Main Background & Text */
        .stApp {{
            background-color: {BACKGROUND_COLOR};
            color: {TEXT_COLOR};
        }}
        
        .main {{
            background-color: {BACKGROUND_COLOR};
            color: {TEXT_COLOR};
        }}
        
        /* ===== SIDEBAR FIX - AGRESSIEVE STYLING ===== */
        /* FORCEER Sidebar Achtergrond */
        section[data-testid="stSidebar"] {{
            background-color: {SIDEBAR_BACKGROUND} !important;
        }}
        
        /* FORCEER Sidebar - ALLE tekst elementen */
        section[data-testid="stSidebar"] * {{
            color: {SIDEBAR_TEXT} !important;
        }}
        
        /* Sidebar - Specifieke elementen extra targeten */
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] h4,
        section[data-testid="stSidebar"] h5,
        section[data-testid="stSidebar"] h6,
        section[data-testid="stSidebar"] div,
        section[data-testid="stSidebar"] caption {{
            color: {SIDEBAR_TEXT} !important;
        }}
        
        /* Sidebar - Input velden (Radio, Selectbox) leesbaar houden */
        section[data-testid="stSidebar"] .stRadio label,
        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stSlider label {{
            color: {SIDEBAR_TEXT} !important;
        }}
        
        /* Sidebar - Markdown containers */
        section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {{
            color: {SIDEBAR_TEXT} !important;
        }}
        
        /* ===== KNOPPEN STYLING ===== */
        /* Primaire knoppen - Bordeaux thema */
        div.stButton > button {{
            background-color: {PRIMARY_COLOR} !important;
            color: white !important;
            border: none !important;
            border-radius: 4px;
            transition: all 0.3s;
        }}
        
        div.stButton > button:hover {{
            background-color: {PRIMARY_COLOR} !important;
            opacity: 0.85;
        }}
        
        /* Primary buttons (type="primary") */
        button[kind="primary"] {{
            background-color: {PRIMARY_COLOR} !important;
            color: white !important;
        }}
        
        /* ===== PROGRESS BARS ===== */
        .stProgress > div > div > div > div {{
            background-color: {PRIMARY_COLOR} !important;
        }}
        
        /* ===== SLIDERS ===== */
        .stSlider > div > div > div > div {{
            background-color: {PRIMARY_COLOR} !important;
        }}
        
        /* ===== TABS ===== */
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
            border-bottom-color: {PRIMARY_COLOR} !important;
            color: {PRIMARY_COLOR} !important;
        }}
        
        /* ===== LINKS ===== */
        a {{
            color: {PRIMARY_COLOR} !important;
        }}
        
        /* ===== METRICS ===== */
        [data-testid="stMetricValue"] {{
            color: {PRIMARY_COLOR} !important;
        }}
        
        /* ===== RADIO BUTTONS (Main screen) ===== */
        .stRadio > label > div[data-testid="stMarkdownContainer"] > p {{
            color: {TEXT_COLOR};
        }}
        
        {hide_branding_css}
    </style>
    """
    
    st.markdown(custom_css, unsafe_allow_html=True)


# System Prompt voor de interactieve studietrainer
SYSTEM_PROMPT = """Je bent een interactieve medische studietrainer. Je rol is om studenten te helpen door vragen te stellen over oorzaak-gevolg relaties (→) in de brontekst OF visuele elementen in afbeeldingen die ze hebben geüpload.

BELANGRIJKE INSTRUCTIES:

1. STRUCTUUR ANALYSE (CRITIEK BELANGRIJK):
   - Scan de brontekst actief op structuurelementen: hoofdstuktitels, kopjes, paragrafen, secties
   - Identificeer de hiërarchie: Hoofdstuk X → Kopje Y → Paragraaf Z
   - Noteer mentaal waar elke belangrijke informatie staat in de structuur
   - Gebruik deze structuurinformatie ALTIJD bij feedback en vragen
   - Als er een afbeelding is: analyseer visuele elementen zoals grafieken, anatomie diagrammen, schema's, flowcharts, en andere medische illustraties

2. INTERNE ANALYSE (niet zichtbaar voor student):
   - Analyseer de brontekst intern op oorzaak-gevolg relaties (→) en correlaties (↔)
   - Identificeer de belangrijkste logische verbanden
   - GEEN samenvatting geven - start direct met vragen stellen
   - De brontekst/afbeelding staat in het eerste bericht van de conversatie - gebruik deze altijd als referentie
   - Bij afbeeldingen: focus op visuele oorzaak-gevolg relaties, zoals pijlen in diagrammen, processen in flowcharts, anatomische structuren en hun relaties

3. QUIZ MODUS:
   - Stel telkens ÉÉN duidelijke vraag over een oorzaak-gevolg relatie uit de brontekst OF uit de afbeelding
   - Focus op het testen of de student de logische verbanden (pijlen) begrijpt
   - Begin met een basisvraag en ga geleidelijk dieper
   - Je MAG refereren naar de structuur om de student te sturen:
     * Bijvoorbeeld: "Laten we kijken naar de sectie over 'Downregulatie'. Wat is daar het gevolg van...?"
     * Bijvoorbeeld: "In het hoofdstuk over 'Endocrinologie' wordt gesproken over..."
     * Bij afbeeldingen: "Kijk naar de grafiek/diagram/schema. Wat gebeurt er wanneer...?"

4. FEEDBACK LOOP MET BRONVERMELDING (VERPLICHT):
   - Als antwoord FOUT is:
     * STAP 1 - IDENTIFICEER DE MISCONCEPTIE: Analyseer waarom het antwoord van de gebruiker fout is (verkeerde oorzaak-gevolg? verkeerde timing? begripsverwarring?)
     * STAP 2 - CORRIGEER DE MISCONCEPTIE EERST: Begin met het corrigeren van die specifieke fout in eigen woorden. Maak glashelder wat de gebruiker dacht versus wat er echt staat.
     * STAP 3 - ONDERSTEUN MET BRON: Citeer dan pas het EXACTE stukje uit de brontekst (met structuurlocatie: "[Hoofdstuk X] / [Kopje Y]") om je uitleg te ondersteunen
     * STAP 4 - LEG UIT IN TOEGANKELIJKE TAAL: Leg de logische stap (→) duidelijk uit, versimpel indien nodig, geef voorbeelden, of leg de 'waarom' uit. GEEN letterlijke herhaling van de quote.
     * STAP 5 - TEST BEGRIP: Stel een vergelijkbare vraag om te testen of het nu begrepen wordt
     * Voorbeeld: "❌ Ik zie de verwarring - je denkt dat meer hormonen → meer receptoren, maar het is juist andersom. In de sectie over 'Downregulatie' staat: '[exact citaat]' → Dus eigenlijk werkt het lichaam als een soort thermostat: te veel signaal → minder ontvangers, zodat de cel niet overstimuleerd raakt. Logisch toch? Nu, wat zou er dan gebeuren als..."
   
   - Als antwoord GOED is:
     * Bevestig kort en enthousiast (bijv. "✅ Correct!", "✅ Helemaal goed!", "✅ Prima!")
     * BELANGRIJK - HOUD HET KORT: Herhaal NIET de bron of sectienaam, tenzij het cruciaal is voor de context. De student weet al waar het stond uit de vraag.
     * Ga DIRECT door naar de volgende logische vervolgvraag
     * Voorbeeld: "✅ Correct! Wat gebeurt er dan met de gevoeligheid van de cel?"
     * Het doel is een snelle flow te behouden zodat de student in zijn ritme blijft

5. GESCHIEDENIS:
   - Houd rekening met eerdere vragen en antwoorden in het gesprek
   - Herhaal geen vragen die al gesteld zijn
   - Bouw voort op wat de student al heeft geleerd
   - Verwijs terug naar de brontekst in het eerste bericht voor exacte citaten

6. COMMUNICATIE STIJL:
   - Bemoedigend maar strikt inhoudelijk - focus op accuraatheid
   - Vriendelijk en ondersteunend, maar houd de student verantwoordelijk voor correcte antwoorden
   - Geef duidelijke, concrete vragen
   - Gebruik de notatie → om oorzaak-gevolg relaties aan te geven
   - ALTIJD structuurlocatie vermelden bij feedback (zowel goed als fout)

FORMAT:
- Stel vragen in een natuurlijke, gespreksmatige stijl
- Gebruik → om oorzaak-gevolg relaties te visualiseren
- CRITIEK BELANGRIJK - SCORE DETECTIE: Begin ALTIJD elk antwoord op een student-vraag met exact "✅" (voor goed antwoord) of "❌" (voor fout antwoord) als eerste karakter. Dit is verplicht voor score tracking.
- Bij foute antwoorden: "❌ [Leg eerst uit wat de misconceptie is] In [structuurlocatie] staat: '[exact citaat]' → [uitleg in eigen woorden met glashelder onderscheid tussen wat gebruiker dacht en wat er echt staat]"
- Bij goede antwoorden: "✅ Correct! [verdiepende vraag]" (KORT, geen bronvermelding, direct naar de volgende vraag)
- Bij vragen: Je mag refereren naar structuur: "Laten we kijken naar [sectie/kopje]..." """

# Tentamen prompt - Universitair Multiple Choice (HOOG NIVEAU)
EXAM_PROMPT = """Je bent een universitaire tentamen-generator voor medische studies op ACADEMISCH NIVEAU. Genereer uitdagende Multiple Choice vragen die studenten ECHT laten nadenken.

**KRITIEKE INSTRUCTIE - AANTAL VRAGEN:**
- De gebruiker wil EXACT {{num_q}} vragen. (Dit is het doel)
- Je MOET EXACT {{num_q}} items in de JSON lijst genereren.
- Tel intern mee: 1/{{num_q}}, 2/{{num_q}}... stop PAS bij {{num_q}}/{{num_q}}.
- Als de brontekst te kort is voor {{num_q}} unieke vragen:
  1. Zoom in op details.
  2. Vraag naar definities.
  3. Vraag naar verbanden ("Wat gebeurt er NIET?").
  4. Maak casus-vragen ("Patiënt X heeft...").
  - Geen uitleg vooraf, geen chatbericht - start DIRECT met de JSON array `[` en eindig met `]`.

MOEILIJKHEIDSGRAAD - STRIKTE REGELS:

1. PLAUSIBELE DISTRACTORS (VERPLICHT - MEEST BELANGRIJK):
   * De foute antwoorden mogen NIET overduidelijk fout zijn
   * Gebruik veelgemaakte studenten-misconcepties (bijv. "meer hormonen = meer receptoren" i.p.v. downregulatie)
   * Gebruik tegengestelde mechanismen die logisch klinken (bijv. vasodilatatie i.p.v. vasoconstrictie)
   * Gebruik termen die op elkaar lijken (bijv. transcriptie vs translatie, apoptose vs necrose)
   * Als de student de stof niet 100% beheerst, moet hij TWIJFELEN tussen minimaal 2 opties
   * VERBODEN: Absurde antwoorden zoals "De cel explodeert" of "Het proces stopt volledig"

2. GEFORCEERDE CASUS-STRUCTUUR (MINIMAAL 50%):
   * Minimaal 50% van de vragen MOET beginnen met een klinische casus ("Een patiënt...", "Een 45-jarige man...", etc.)
   * Casus-vragen moeten vragen naar het MECHANISME achter de klacht, NIET naar de diagnose
   * Voorbeeld GOED: "Een patiënt met chronische nierinsufficiëntie ontwikkelt anemie. Welk mechanisme verklaart dit op cellulair niveau?"
   * Voorbeeld FOUT: "Een patiënt heeft koorts. Wat heeft hij?" (te simpel, geen mechanisme)

3. DIEPGANG (VERPLICHT):
   * Vraag NOOIT "Wat is X?" - Vraag altijd "Waarom/Hoe werkt X?" of "Wat is het mechanisme achter X?"
   * Gebruik academische/medische terminologie (downregulatie, homeostase, apoptose, etc.)
   * Test BEGRIP van oorzaak-gevolg ketens, niet feiten
   * Voorbeeld GOED: "Waarom leidt chronische hypoxie tot verhoogde erytropoëtine-productie?"
   * Voorbeeld FOUT: "Wat is erytropoëtine?" (te basaal)

VRAAGTYPE VERDELING:
- TYPE A - Mechanisme/Oorzaak-Gevolg: 30%
- TYPE B - Stelling/Analyse: 20%
- TYPE C - Klinische Casus: 50% (VERPLICHT MINIMAAL 50%)

OUTPUT FORMAT (STRICT JSON):
[
  {
    "vraag": "De vraag hier...",
    "opties": [
      "A) Eerste optie (plausibel maar fout)",
      "B) Tweede optie (plausibel maar fout)", 
      "C) Derde optie (correct)",
      "D) Vierde optie (plausibel maar fout)"
    ],
    "correct_antwoord": "Het juiste antwoord (volledige tekst)",
    "uitleg": "VERPLICHT GESTRUCTUREERD FORMAT - Gebruik EXACT deze Markdown structuur:\n\n✅ **Het juiste antwoord is [Letter] omdat:** [Korte, krachtige reden met oorzaak-gevolg (→)].\n\n❌ **Analyse van de fouten:**\n* **A:** [Waarom deze optie fout is]\n* **B:** [Waarom deze optie fout is]\n* **C:** [Waarom deze optie fout is]\n* **D:** [Waarom deze optie fout is]\n\n(Bij het correcte antwoord schrijf je: 'Dit is het correcte antwoord')"
  }
]

VOORBEELDEN VAN GOEDE VRAGEN:

Type C (Casus - HOOG NIVEAU):
{
  "vraag": "Een 62-jarige patiënt met chronisch hartfalen gebruikt al jaren hoge doses diuretica. Recent ontwikkelt hij spierzwakte en hartritmestoornissen. Laboratoriumonderzoek toont een verlaagd kaliumgehalte. Welk cellulair mechanisme verklaart de hartritmestoornissen?",
  "opties": [
    "A) Hypokaliëmie leidt tot verhoogde Na+/K+-pomp activiteit, waardoor het rustmembraanpotentiaal positiever wordt",
    "B) Hypokaliëmie verstoort de repolarisatie van cardiomyocyten doordat K+-efflux verminderd is, wat de actiepoteniaalduur verlengt",
    "C) Hypokaliëmie activeert voltage-gated Ca2+-kanalen, waardoor spontane depolarisaties ontstaan",
    "D) Hypokaliëmie remt de Na+/K+-pomp, waardoor intracellulair Na+ accumuleert en de cel depolariseert"
  ],
  "correct_antwoord": "B) Hypokaliëmie verstoort de repolarisatie van cardiomyocyten doordat K+-efflux verminderd is, wat de actiepoteniaalduur verlengt",
  "uitleg": "✅ **Het juiste antwoord is B omdat:** Lage extracellulaire K+ → Verminderde K+-gradiënt → Tragere K+-efflux tijdens repolarisatie → Verlengde actiepoteniaalduur → QT-verlenging en aritmieën.\n\n❌ **Analyse van de fouten:**\n* **A:** De Na+/K+-pomp wordt juist MINDER actief bij hypokaliëmie (niet meer), en dit verklaart niet direct de ritmestoornissen.\n* **B:** Dit is het correcte antwoord.\n* **C:** Voltage-gated Ca2+-kanalen worden niet direct geactiveerd door K+-tekort; dit mechanisme speelt geen primaire rol.\n* **D:** Hoewel de pomp inderdaad geremd wordt, is het de verstoorde repolarisatie (niet de Na+-accumulatie) die de aritmieën veroorzaakt."
}

Type A (Mechanisme - HOOG NIVEAU):
{
  "vraag": "Bij chronische blootstelling aan hoge glucocorticoïd concentraties treedt downregulatie van glucocorticoïd-receptoren op. Welk cellulair mechanisme ligt hieraan ten grondslag?",
  "opties": [
    "A) Verhoogde receptor-expressie door positieve feedback, gevolgd door receptor-internalisatie",
    "B) Verminderde receptor-synthese en verhoogde receptor-degradatie via ubiquitinatie",
    "C) Competitieve inhibitie van receptor-binding door endogene antagonisten",
    "D) Conformatieverandering van de receptor waardoor ligand-binding afneemt"
  ],
  "correct_antwoord": "B) Verminderde receptor-synthese en verhoogde receptor-degradatie via ubiquitinatie",
  "uitleg": "✅ **Het juiste antwoord is B omdat:** Chronische hormoonblootstelling → Verminderde transcriptie van receptor-genen + Ubiquitinatie van bestaande receptoren → Proteasomale degradatie → Netto afname receptoren → Verminderde gevoeligheid.\n\n❌ **Analyse van de fouten:**\n* **A:** Dit beschrijft een tegengesteld proces (upregulatie met positieve feedback), niet downregulatie.\n* **B:** Dit is het correcte antwoord.\n* **C:** Competitieve inhibitie is een ander mechanisme; downregulatie gaat over het aantal receptoren, niet over blokkade.\n* **D:** Dit beschrijft desensitisatie (receptor blijft aanwezig maar reageert niet), niet downregulatie (receptor wordt afgebroken)."
}

Type B (Stelling - HOOG NIVEAU):
{
  "vraag": "Welke bewering over het verschil tussen apoptose en necrose op cellulair niveau is correct?",
  "opties": [
    "A) Bij apoptose zwelt de cel op door osmotische disbalans, bij necrose krimpt de cel",
    "B) Bij apoptose blijft het celmembraan intact tot late fase en worden apoptotische bodies gevormd, bij necrose rupt het membraan vroeg",
    "C) Bij apoptose treedt altijd een ontstekingsreactie op, bij necrose niet",
    "D) Bij apoptose is er willekeurige DNA-fragmentatie, bij necrose geordende DNA-klieven"
  ],
  "correct_antwoord": "B) Bij apoptose blijft het celmembraan intact tot late fase en worden apoptotische bodies gevormd, bij necrose rupt het membraan vroeg",
  "uitleg": "✅ **Het juiste antwoord is B omdat:** Apoptose = Membraan intact → Cel krimpt → Apoptotische bodies → Fagocytose zonder ontsteking. Necrose = Membraan rupt vroeg → Cel zwelt → Inhoud lekt → Ontstekingsreactie.\n\n❌ **Analyse van de fouten:**\n* **A:** Dit is precies omgekeerd: bij apoptose krimpt de cel, bij necrose zwelt de cel op.\n* **B:** Dit is het correcte antwoord.\n* **C:** Ook omgekeerd: apoptose veroorzaakt GEEN ontsteking (clean-up), necrose WEL (inhoud lekt naar buiten).\n* **D:** Wederom omgekeerd: apoptose heeft geordende DNA-klieven (door caspases), necrose heeft willekeurige fragmentatie."
}

BELANGRIJK: Maak de vragen MOEILIJK. Een goede student moet 60-70% halen, niet 100%."""


def initialize_session_state():
    """Initialiseer session state variabelen."""
    if "history" not in st.session_state:
        st.session_state.history = []
    if "context_set" not in st.session_state:
        st.session_state.context_set = False
    if "source_text" not in st.session_state:
        st.session_state.source_text = ""
    if "image_base64" not in st.session_state:
        st.session_state.image_base64 = None
    if "file_type" not in st.session_state:
        st.session_state.file_type = None
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "total_questions" not in st.session_state:
        st.session_state.total_questions = 0
    # Navigatie
    if "source_mode" not in st.session_state:
        st.session_state.source_mode = "Eigen Bestand Uploaden"
    if "study_mode" not in st.session_state:
        st.session_state.study_mode = "🟢 Oefenen"
    # Smart Loop (Tentamen → Oefenen)
    if "remedial_topic" not in st.session_state:
        st.session_state.remedial_topic = None
    # Persoonlijke Bibliotheek
    if "personal_library" not in st.session_state:
        st.session_state.personal_library = {}
    # Sticky Selectbox voor Bibliotheek Selectie
    if "library_selection" not in st.session_state:
        st.session_state.library_selection = "-- Selecteer --"
    # Context variabele voor Auto-Loader
    if "context" not in st.session_state:
        st.session_state.context = ""
    if "last_loaded_source" not in st.session_state:
        st.session_state.last_loaded_source = None
    # Tentamen
    if "exam_questions" not in st.session_state:
        st.session_state.exam_questions = []
    if "exam_answers" not in st.session_state:
        st.session_state.exam_answers = {}
    if "exam_completed" not in st.session_state:
        st.session_state.exam_completed = False
    if "exam_num_questions" not in st.session_state:
        st.session_state.exam_num_questions = 10
    if "exam_focus_mode" not in st.session_state:
        st.session_state.exam_focus_mode = "🔀 Mix (Alles door elkaar)"
    # Flashcards
    if "flashcards" not in st.session_state:
        st.session_state.flashcards = []


def get_api_key() -> str:
    """
    Haal OpenAI API key op in de volgende volgorde:
    1. API_KEY_OVERRIDE (vanuit Cockpit - voor tijdelijk testen)
    2. os.environ / .env file (voor veilige productie)
    3. st.secrets (voor Streamlit Cloud)
    """
    # STAP 1: Check eerst de Cockpit override (hoogste prioriteit voor testen)
    if API_KEY_OVERRIDE is not None and API_KEY_OVERRIDE.strip():
        return API_KEY_OVERRIDE
    
    # STAP 2: Probeer environment variable (.env file - AANBEVOLEN)
    if "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"]
    
    # STAP 3: Probeer st.secrets (Streamlit Cloud)
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    
    return ""


def get_openai_client():
    """Haal OpenAI client op of toon error."""
    api_key = get_api_key()
    if not api_key:
        st.error("❌ OPENAI_API_KEY niet gevonden in .env bestand. Voeg deze toe om de applicatie te gebruiken.")
        st.stop()
    return OpenAI(api_key=api_key)


def encode_image(image_file) -> str:
    """Encode een afbeelding naar base64 string."""
    return base64.b64encode(image_file.read()).decode('utf-8')


# --- HELPER FUNCTIE VOOR AI ---
def get_ai_response(client, messages, has_image=False, max_tokens=None, json_mode=False):
    """
    Slimme functie om antwoord op te halen van OpenAI.
    Regelt automatisch het juiste model en voorkomt crashes.
    """
    try:
        # 1. Zet tokens (standaard lekker ruim voor tentamens)
        if max_tokens is None:
            max_tokens = 8000
        
        # 2. Kies het slimste model
        # Voor medische tentamens willen we liever gpt-4o dan mini
        if has_image:
            model = "gpt-4o"
        else:
            # Als je gpt-4o-mini te dom vindt, verander dit dan naar "gpt-4o"
            model = "gpt-4o" 
        
        # 3. Bereid de instellingen voor
        params = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": max_tokens
        }
        
        # CRUCIAAL: Als we JSON willen (voor tentamens), dwing dat af
        if json_mode:
            params["response_format"] = {"type": "json_object"}

        # 4. De echte aanroep
        response = client.chat.completions.create(**params)
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"❌ Fout bij AI aanroep: {str(e)}"


def extract_text_from_pdf(pdf_file) -> tuple:
    """Extraheer tekst uit een PDF bestand."""
    try:
        pdf_reader = PdfReader(pdf_file)
        num_pages = len(pdf_reader.pages)
        
        text_parts = []
        for page in pdf_reader.pages:
            text_parts.append(page.extract_text())
        
        extracted_text = "\n".join(text_parts)
        return extracted_text, num_pages
    except Exception as e:
        st.error(f"❌ Fout bij het lezen van PDF: {str(e)}")
        return "", 0


def generate_flashcards(client: OpenAI, source_text: str) -> list:
    """Genereer flashcards op basis van de brontekst."""
    prompt = f"""Genereer 5 flashcards op basis van deze tekst. Elke flashcard moet een vraag en antwoord hebben over oorzaak-gevolg relaties.

BRONTEKST:
{source_text}

Format elk als:
Q: [Vraag over oorzaak-gevolg]
A: [Kort antwoord met → notatie]

Bijvoorbeeld:
Q: Wat is het gevolg van verhoogde hormoonconcentratie op receptoren?
A: Verhoogde hormoonconcentratie → Downregulatie van receptoren → Verminderde gevoeligheid"""
    
    messages = [{"role": "user", "content": prompt}]
    response = get_ai_response(client, messages)
    
    # Parse de flashcards
    flashcards = []
    lines = response.split('\n')
    current_q = ""
    current_a = ""
    
    for line in lines:
        line = line.strip()
        if line.startswith('Q:'):
            if current_q and current_a:
                flashcards.append({"question": current_q, "answer": current_a})
            current_q = line[2:].strip()
            current_a = ""
        elif line.startswith('A:'):
            current_a = line[2:].strip()
    
    if current_q and current_a:
        flashcards.append({"question": current_q, "answer": current_a})
    
    return flashcards[:5]  # Max 5 flashcards


def start_practice_mode(source_text: str, client: OpenAI, num_pages: int = 0, image_base64: str = None, file_type: str = None):
    """Start de oefenmodus met RANDOM STARTPUNT + HARDE OORZAAK-GEVOLG EIS."""
    if file_type == "image":
        if not image_base64:
            st.warning("⚠️ Upload eerst een afbeelding voordat je de training start.")
            return
        st.success("✅ Afbeelding succesvol verwerkt!")
    elif file_type == "pdf" or file_type == "library":
        if not source_text.strip():
            st.warning("⚠️ Geen tekst beschikbaar.")
            return
        if num_pages > 0:
            st.success(f"✅ PDF succesvol verwerkt! ({num_pages} pagina's)")
        elif file_type == "library":
            st.success("✅ Bibliotheek content geladen!")
    else:
        st.warning("⚠️ Upload eerst een bestand voordat je de training start.")
        return
    
    st.session_state.source_text = source_text
    st.session_state.image_base64 = image_base64
    st.session_state.file_type = file_type
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Genereer een "seed" voor variatie
    random_seed = random.randint(1, 100000)
    
    # Check of er een remedial topic is (Smart Loop van Tentamen)
    if st.session_state.remedial_topic is not None:
        remedial = st.session_state.remedial_topic
        
        # ... (Remedial logica blijft hetzelfde als hiervoor) ...
        if file_type == "image" and image_base64:
            image_url = f"data:image/jpeg;base64,{image_base64}"
            user_content = [
                {"type": "text", "text": f"BIJLES: Student zakte op: '{remedial['vraag']}'. Antwoord: '{remedial['correct_antwoord']}'. Start bijles via oorzaak-gevolg."},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
            messages.append({"role": "user", "content": user_content})
            has_image = True
        else:
            user_content = f"BRONTEKST:\n{source_text}\n\nBIJLES: Student zakte op: '{remedial['vraag']}'. Antwoord: '{remedial['correct_antwoord']}'. Start bijles via oorzaak-gevolg."
            messages.append({"role": "user", "content": user_content})
            has_image = False
        
        st.session_state.remedial_topic = None
        
    else:
        # Standaard oefenmodus
        if file_type == "image" and image_base64:
            image_url = f"data:image/jpeg;base64,{image_base64}"
            user_content = [
                {"type": "text", "text": f"Start met vragen over oorzaak-gevolg relaties in deze afbeelding. (Random ID: {random_seed})"},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
            messages.append({"role": "user", "content": user_content})
            has_image = True
        else:
            # HIER IS DE AANPASSING 👇
            # We combineren "Willekeurige Plek" met "Oorzaak-Gevolg Eis"
            user_content = f"""BRONTEKST:
{source_text}

INSTRUCTIE VOOR EERSTE VRAAG:
1. Kies een WILLEKEURIG onderwerp ergens uit het midden of einde van de tekst (Random ID: {random_seed}).
2. Zoek in dat specifieke deel naar een sterke OORZAAK-GEVOLG relatie (A → B).
3. Stel daarover je vraag.
4. Vraag NIET naar definities, feitjes of samenvattingen. Alleen logica en mechanismen.

Start nu."""
            messages.append({"role": "user", "content": user_content})
            has_image = False
    
    with st.spinner("🎲 Trainer zoekt een interessante oorzaak-gevolg keten..."):
        first_question = get_ai_response(client, messages, has_image=has_image)
    
    if first_question.startswith("❌"):
        st.error(first_question)
        st.session_state.context_set = False
        return
    
    st.session_state.history.append({"role": "assistant", "content": first_question})
    st.session_state.context_set = True
    st.rerun()


def start_exam_mode(source_text: str, client: OpenAI, num_questions: int = 10, focus_mode: str = "🔀 Mix (Alles door elkaar)"):
    """
    Start tentamen modus - CONTAINER METHODE.
    Vraagt om een root-object met een lijst erin. Dit lost het tel-probleem op.
    """
    if not source_text.strip():
        st.warning("⚠️ Upload eerst een bestand om een tentamen te genereren.")
        return

    st.session_state.source_text = source_text
    st.session_state.file_type = "exam"

    # Focus instructie
    if "🧬 Theorie" in focus_mode:
        focus_instruction = "FOCUS: Moleculaire mechanismen, celbiologie, theorie. GEEN klinische casussen."
    elif "🩺 Klinische" in focus_mode:
        focus_instruction = "FOCUS: Klinische casussen, patiënt-scenario's, diagnose."
    else:
        focus_instruction = "FOCUS: Mix van 40% theorie en 60% klinische casussen."

    all_questions = []
    questions_needed = num_questions
    batch_size = 5
    
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    
    import math
    num_batches = math.ceil(num_questions / batch_size)

    for i in range(num_batches):
        current_batch_size = min(batch_size, questions_needed)
        
        # Retry loop
        attempts = 0
        success = False
        
        while attempts < 3 and not success:
            attempts += 1
            status_text.markdown(f"**🤖 AI schrijft vragen... Batch {i+1}/{num_batches} (Poging {attempts})**")
            
            # --- DE NIEUWE PROMPT (CONTAINER STRATEGIE) ---
            system_content = f"""
Je bent een tentamen-generator. Genereer een JSON object met daarin een lijst van EXACT {current_batch_size} vragen.

STRUCTUUR EIS:
Jouw antwoord MOET dit formaat hebben (Root object met 'exam_questions' lijst):
{{
  "exam_questions": [
    {{
      "vraag": "...",
      "opties": ["A", "B", "C", "D"],
      "correct_antwoord": "...",
      "uitleg": "..."
    }},
    ... (totaal {current_batch_size} items)
  ]
}}

{focus_instruction}
Genereer nu {current_batch_size} vragen in deze lijst.
"""
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": f"Context (ingekort):\n{source_text[:20000]}\n\nOPDRACHT: Vul de lijst 'exam_questions' met PRECIES {current_batch_size} nieuwe vragen."}
            ]

            try:
                # 4000 tokens is ruim voldoende voor 5 vragen
                response_text = get_ai_response(client, messages, max_tokens=4000, json_mode=True)
                batch_questions = clean_and_parse_json(response_text)
                
                if batch_questions:
                    received = len(batch_questions)
                    if received >= current_batch_size:
                        all_questions.extend(batch_questions[:current_batch_size])
                        questions_needed -= current_batch_size
                        success = True
                    else:
                        print(f"⚠️ Batch {i+1} te weinig: {received}/{current_batch_size}. Retrying...")
                        if attempts == 3:
                            all_questions.extend(batch_questions)
                            questions_needed -= received
                else:
                     print(f"⚠️ Batch {i+1} leeg.")

            except Exception as e:
                print(f"❌ Error: {e}")

        progress_bar.progress((i + 1) / num_batches)

    status_text.empty()
    progress_bar.empty()

    if not all_questions:
        st.error("❌ Geen vragen gegenereerd.")
        return

    st.session_state.exam_questions = all_questions
    st.session_state.exam_answers = {}
    st.session_state.exam_completed = False
    st.session_state.context_set = True
    
    st.success(f"✅ Tentamen klaar! {len(all_questions)} vragen gegenereerd.")
    st.rerun()


def start_flashcard_mode(source_text: str, client: OpenAI):
    """Start flashcard modus."""
    if not source_text.strip():
        st.warning("⚠️ Geen tekst beschikbaar.")
        return
    
    st.session_state.source_text = source_text
    st.session_state.file_type = "flashcards"
    
    with st.spinner("🃏 Flashcards worden gegenereerd..."):
        flashcards = generate_flashcards(client, source_text)
    
    st.session_state.flashcards = flashcards
    st.session_state.context_set = True
    st.success(f"✅ {len(flashcards)} flashcards gegenereerd!")
    st.rerun()


def handle_practice_answer(user_answer: str, client: OpenAI):
    """Verwerk antwoord in oefenmodus."""
    if not user_answer.strip():
        return
    
    st.session_state.history.append({"role": "user", "content": user_answer})
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if st.session_state.file_type == "image" and st.session_state.image_base64:
        image_url = f"data:image/jpeg;base64,{st.session_state.image_base64}"
        initial_content = [
            {"type": "text", "text": "Start met het stellen van vragen."},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
        messages.append({"role": "user", "content": initial_content})
        has_image = True
    else:
        initial_content = f"BRONTEKST:\n{st.session_state.source_text}\n\nStart met het stellen van vragen."
        messages.append({"role": "user", "content": initial_content})
        has_image = False
    
    for msg in st.session_state.history:
        messages.append(msg)
    
    with st.spinner("📝 Trainer analyseert je antwoord..."):
        feedback = get_ai_response(client, messages, has_image=has_image)
    
    # Update score
    feedback_stripped = feedback.strip()
    if feedback_stripped.startswith("✅") or feedback_stripped.lower().startswith("correct"):
        st.session_state.score += 1
        st.session_state.total_questions += 1
    elif feedback_stripped.startswith("❌") or feedback_stripped.lower().startswith("fout") or feedback_stripped.lower().startswith("niet"):
        st.session_state.total_questions += 1
    
    st.session_state.history.append({"role": "assistant", "content": feedback})


def evaluate_exam():
    """Evalueer tentamen antwoorden - Multiple Choice."""
    results = []
    
    for i, question_data in enumerate(st.session_state.exam_questions):
        user_answer = st.session_state.exam_answers.get(i, "")
        correct_answer = question_data.get("correct_antwoord", "")
        
        # Check of antwoord correct is
        is_correct = user_answer == correct_answer
        
        results.append({
            "vraag": question_data.get("vraag", ""),
            "opties": question_data.get("opties", []),
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "uitleg": question_data.get("uitleg", ""),
            "correct": is_correct
        })
    
    return results


def reset_session():
    """Reset de sessie."""
    st.session_state.history = []
    st.session_state.context_set = False
    st.session_state.source_text = ""
    st.session_state.image_base64 = None
    st.session_state.file_type = None
    st.session_state.score = 0
    st.session_state.total_questions = 0
    st.session_state.exam_questions = []
    st.session_state.exam_answers = {}
    st.session_state.exam_completed = False
    st.session_state.flashcards = []
    st.session_state.remedial_topic = None
    st.rerun()


def start_remedial_session(question: str, correct_answer: str, explanation: str):
    """
    Callback functie voor de bijles knop.
    Navigeert naar het Oefen-scherm met het juiste boek geselecteerd.
    De gebruiker kan dan zelf op "Start Oefenen" klikken.
    
    De Auto-Loader in de sidebar zorgt voor het laden van de context,
    zodat de gele waarschuwing niet verschijnt.
    """
    # 1. Zet de studiemodus om naar Oefenen
    st.session_state.study_mode = "🟢 Oefenen"
    
    # 2. Sla de remediëringsdata op (voor visuele feedback)
    st.session_state.remedial_topic = {
        "vraag": question,
        "correct_antwoord": correct_answer,
        "uitleg": explanation
    }
    
    # 3. Herstel de bibliotheek selectie (voorkomt reset naar "-- Selecteer --")
    # De Auto-Loader in de sidebar zal automatisch de context laden zodra
    # library_selection wordt hersteld
    if "library_selection_backup" in st.session_state and st.session_state.library_selection_backup:
        st.session_state.library_selection = st.session_state.library_selection_backup
        # Force reload door last_loaded_source te resetten
        st.session_state.last_loaded_source = None
    
    # 4. CRUCIAAL: Zorg dat we NIET in de chat-interface belanden
    # Reset alle sessie variabelen zodat we op het "Start Oefenen" scherm landen
    st.session_state.context_set = False
    st.session_state.history = []
    st.session_state.source_text = ""
    st.session_state.image_base64 = None
    st.session_state.file_type = None


def main():
    """Hoofdfunctie voor de Streamlit app."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_EMOJI,
        layout="wide"
    )
    
    # Pas custom styling toe (kleuren en branding uit Cockpit)
    apply_custom_styling()
    
    initialize_session_state()
    
    # Sidebar navigatie
    with st.sidebar:
        st.title(f"⚙️ {CLIENT_NAME} Instellingen")
        
        # Score weergave (alleen bij oefenen)
        if st.session_state.study_mode == "🟢 Oefenen" and st.session_state.context_set:
            st.markdown("### 📊 Score")
            if st.session_state.total_questions > 0:
                score_display = f"{st.session_state.score} / {st.session_state.total_questions}"
                percentage = st.session_state.score / st.session_state.total_questions
                st.metric("Score", score_display)
                st.progress(percentage)
                st.caption(f"{int(percentage * 100)}% correct")
            else:
                st.metric("Score", "0 / 0")
                st.progress(0.0)
                st.caption("Nog geen vragen beantwoord")
            st.markdown("---")
        
        # Navigatie
        st.markdown("### 📚 Bron")
        
        # Bepaal beschikbare opties op basis van feature toggle
        if ENABLE_PERSONAL_UPLOADS:
            source_options = ["Eigen Bestand Uploaden", "Kies uit Bibliotheek"]
        else:
            source_options = ["Kies uit Bibliotheek"]
        
        # Als de huidige modus "Eigen Bestand Uploaden" is maar deze optie is uitgeschakeld,
        # reset dan naar "Kies uit Bibliotheek"
        if st.session_state.source_mode not in source_options:
            st.session_state.source_mode = "Kies uit Bibliotheek"
        
        st.session_state.source_mode = st.radio(
            "Kies je bron:",
            source_options,
            key="source_radio"
        )
        
        # Persoonlijke Bibliotheek Upload (indien ingeschakeld in Cockpit)
        if ENABLE_PERSONAL_UPLOADS:
            with st.expander("➕ Voeg toe aan Bibliotheek"):
                st.caption("Upload een bestand om het permanent toe te voegen aan je bibliotheek")
                library_file = st.file_uploader(
                    "Upload PDF of TXT bestand:",
                    type=["pdf", "txt"],
                    key="library_uploader"
                )
                
                if library_file is not None:
                    try:
                        file_name = library_file.name
                        file_extension = file_name.split('.')[-1].lower()
                        
                        # Check of bestand al bestaat
                        if file_name in st.session_state.personal_library:
                            st.warning(f"⚠️ '{file_name}' bestaat al in je bibliotheek")
                        else:
                            # Extraheer tekst
                            if file_extension == "pdf":
                                pdf_reader = PdfReader(library_file)
                                text_parts = []
                                for page in pdf_reader.pages:
                                    text_parts.append(page.extract_text())
                                extracted_text = "\n".join(text_parts)
                            elif file_extension == "txt":
                                extracted_text = library_file.read().decode('utf-8')
                            else:
                                st.error("Ongeldig bestandstype")
                                extracted_text = None
                            
                            if extracted_text and extracted_text.strip():
                                # Sla op in persoonlijke bibliotheek
                                st.session_state.personal_library[file_name] = extracted_text
                                st.success(f"✅ '{file_name}' toegevoegd aan bibliotheek!")
                                st.caption(f"📄 {len(extracted_text)} karakters geëxtraheerd")
                            else:
                                st.warning("⚠️ Geen tekst gevonden in bestand")
                            
                    except Exception as e:
                        st.error(f"❌ Fout bij verwerken: {str(e)}")
                
                # Toon huidige persoonlijke bibliotheek
                if st.session_state.personal_library:
                    st.markdown("**Jouw bibliotheek:**")
                    for filename in list(st.session_state.personal_library.keys()):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.caption(f"📁 {filename}")
                        with col2:
                            if st.button("🗑️", key=f"del_{filename}", help="Verwijder"):
                                del st.session_state.personal_library[filename]
                                st.rerun()
        else:
            # Uploads uitgeschakeld melding
            st.info("📚 Persoonlijke uploads zijn uitgeschakeld. Gebruik de vaste bibliotheek.")
        
        st.markdown("---")
        st.markdown("### 🎯 Studiemodus")
        # Radio button met key="study_mode" voor automatische sync
        st.radio(
            "Kies je modus:",
            ["🟢 Oefenen", "🔴 Tentamen Simulatie", "🃏 Flashcards"],
            key="study_mode"
        )
        
        # Tentamen instellingen
        if st.session_state.study_mode == "🔴 Tentamen Simulatie":
            st.markdown("#### Tentamen Instellingen")
            st.session_state.exam_num_questions = st.slider(
                "Aantal vragen:",
                min_value=5,
                max_value=20,
                value=10,
                step=1
            )
            
            st.session_state.exam_focus_mode = st.selectbox(
                "Kies focusgebied:",
                [
                    "🔀 Mix (Alles door elkaar)",
                    "🧬 Theorie & Mechanismen (Bachelor focus)",
                    "🩺 Klinische Casussen (Master/Arts focus)"
                ]
            )
        
        st.markdown("---")
        if st.button("🔄 Reset", use_container_width=True):
            reset_session()
        
        st.markdown("---")
        st.markdown("### 📖 Instructies")
        if st.session_state.study_mode == "🟢 Oefenen":
            st.markdown("""
            1. Upload bestand of kies uit bibliotheek
            2. Klik op "Start Oefenen"
            3. Beantwoord de vragen
            4. Krijg directe feedback
            """)
        elif st.session_state.study_mode == "🔴 Tentamen Simulatie":
            st.markdown("""
            1. Upload je PDF/afbeelding
            2. Stel aantal vragen in (5-20)
            3. **Kies focusgebied:**
               - 🧬 Theorie: Pure mechanismen
               - 🩺 Klinisch: Patiënt-casussen
               - 🔀 Mix: Beide door elkaar
            4. Klik op "Start Tentamen"
            5. Beantwoord Multiple Choice vragen
            6. Lever in en zie je cijfer
            """)
        else:
            st.markdown("""
            1. Kies je bron
            2. Klik op "Genereer Flashcards"
            3. Bestudeer de flashcards
            """)
    
    # Hoofdinterface
    st.title(f"{APP_TITLE} {APP_EMOJI}")
    st.markdown("Een interactieve studie-trainer die vragen stelt over oorzaak-gevolg relaties in je studieteksten.")
    st.markdown("---")
    
    client = get_openai_client()
    
    # Input interface
    if not st.session_state.context_set:
        st.subheader("📚 Stap 1: Selecteer je studiemateriaal")
        
        # Visuele feedback: Toon melding als er een bijles-onderwerp klaargezet is
        if st.session_state.remedial_topic is not None:
            vraag_preview = st.session_state.remedial_topic['vraag'][:100]
            if len(st.session_state.remedial_topic['vraag']) > 100:
                vraag_preview += "..."
            st.info(f"💡 **Klaargezet onderwerp voor bijles:** {vraag_preview}")
            st.caption("👆 Het juiste boek is al geselecteerd. Klik op 'Start Oefenen' om te beginnen met de bijles-sessie.")
        
        source_text = ""
        num_pages = 0
        image_base64 = None
        file_type = None
        
        # Bron selectie
        if st.session_state.source_mode == "Eigen Bestand Uploaden":
            uploaded_file = st.file_uploader(
                "Upload je samenvatting (PDF of afbeelding)",
                type=["pdf", "png", "jpg", "jpeg"],
                help="Upload een PDF bestand of afbeelding (PNG/JPG) met je studietekst of visuele content."
            )
            
            if uploaded_file is not None:
                file_extension = uploaded_file.name.split('.')[-1].lower()
                
                if file_extension == "pdf":
                    source_text, num_pages = extract_text_from_pdf(uploaded_file)
                    file_type = "pdf"
                elif file_extension in ["png", "jpg", "jpeg"]:
                    image_base64 = encode_image(uploaded_file)
                    file_type = "image"
                    uploaded_file.seek(0)
        else:
            # Bibliotheek selectie - Combineer vaste content met persoonlijke bibliotheek
            combined_library = {}
            
            # Voeg vaste bedrijfs-content toe met prefix
            for key, value in LIBRARY_CONTENT.items():
                combined_library[f"📚 {key}"] = value
            
            # Voeg persoonlijke bibliotheek toe met prefix
            for key, value in st.session_state.personal_library.items():
                combined_library[f"📁 {key}"] = value
            
            if not combined_library:
                st.warning("⚠️ Geen bibliotheek content beschikbaar. Voeg eerst bestanden toe.")
                source_text = ""
                file_type = "library"
            else:
                # 1. De Widget - Selectbox zonder callback
                library_options = list(combined_library.keys())
                library_choice = st.selectbox(
                    "Kies een hoofdstuk uit de bibliotheek:",
                    ["-- Selecteer --"] + library_options,
                    key="library_selection"
                )
                
                # 2. De "Auto-Loader" (Draait elke keer direct na de selectie)
                # Dit garandeert dat de context geladen is VOORDAT de main-code draait
                if st.session_state.library_selection != "-- Selecteer --":
                    selection = st.session_state.library_selection
                    
                    # Maak backup van de selectie (voor herstel na Smart Loop)
                    st.session_state.library_selection_backup = selection
                    
                    # Check of we moeten laden (bijv. na een refresh of mode switch)
                    if not st.session_state.context or st.session_state.get("last_loaded_source") != selection:
                        if selection.startswith("📚"):
                            real_key = selection.replace("📚 ", "")
                            if real_key in LIBRARY_CONTENT:
                                st.session_state.context = LIBRARY_CONTENT[real_key]
                                st.session_state.source_text = LIBRARY_CONTENT[real_key]
                        elif selection.startswith("📁"):
                            real_key = selection.replace("📁 ", "")
                            if real_key in st.session_state.personal_library:
                                st.session_state.context = st.session_state.personal_library[real_key]
                                st.session_state.source_text = st.session_state.personal_library[real_key]
                        
                        # Onthoud wat we geladen hebben om onnodig herladen te voorkomen
                        st.session_state.last_loaded_source = selection
                else:
                    # Als de gebruiker expliciet "-- Selecteer --" kiest, maak context leeg
                    st.session_state.context = ""
                    st.session_state.source_text = ""
                
                # 3. Zet source_text en file_type voor de rest van de code
                if library_choice != "-- Selecteer --":
                    source_text = st.session_state.context
                    file_type = "library"
                    
                    # Toon info met icoon
                    if library_choice.startswith("📚"):
                        st.info(f"✅ Geselecteerd: {library_choice} (Vaste content)")
                    else:
                        st.success(f"✅ Geselecteerd: {library_choice} (Jouw upload)")
                else:
                    source_text = ""
                    file_type = "library"
        
        # Start knop (afhankelijk van modus)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.session_state.study_mode == "🟢 Oefenen":
                if st.button("🚀 Start Oefenen", use_container_width=True, type="primary"):
                    start_practice_mode(source_text, client, num_pages, image_base64, file_type)
            elif st.session_state.study_mode == "🔴 Tentamen Simulatie":
                if st.button("📝 Start Tentamen", use_container_width=True, type="primary"):
                    start_exam_mode(source_text, client, st.session_state.exam_num_questions, st.session_state.exam_focus_mode)
            else:  # Flashcards
                if st.button("🃏 Genereer Flashcards", use_container_width=True, type="primary"):
                    start_flashcard_mode(source_text, client)
    
    # Actieve sessie
    else:
        if st.session_state.study_mode == "🟢 Oefenen":
            # Oefenmodus
            st.subheader("💬 Training Sessie")
            
            for message in st.session_state.history:
                if message["role"] == "assistant":
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])
                elif message["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(message["content"])
            
            if user_answer := st.chat_input("Type je antwoord hier..."):
                handle_practice_answer(user_answer, client)
                st.rerun()
        
        elif st.session_state.study_mode == "🔴 Tentamen Simulatie":
            # Tentamen modus - Universitair Multiple Choice
            if not st.session_state.exam_completed:
                st.subheader("📝 Universitair Tentamen - Multiple Choice")
                
                num_questions = len(st.session_state.exam_questions)
                st.info(f"📋 Tentamen met {num_questions} vragen | Geen feedback tussendoor | Lever in wanneer je klaar bent")
                
                # Formulier voor alle vragen
                with st.form("exam_form"):
                    for i, question_data in enumerate(st.session_state.exam_questions):
                        st.markdown(f"### Vraag {i+1}")
                        st.markdown(question_data.get("vraag", ""))
                        
                        # Radio buttons voor opties
                        options = question_data.get("opties", [])
                        selected = st.radio(
                            f"Kies je antwoord:",
                            options,
                            key=f"q_{i}",
                            index=None
                        )
                        
                        # Sla antwoord op in session state
                        if selected:
                            st.session_state.exam_answers[i] = selected
                        
                        st.markdown("---")
                    
                    # Submit knop
                    submitted = st.form_submit_button("✅ Lever Tentamen In", use_container_width=True, type="primary")
                    
                    if submitted:
                        # Check of alle vragen beantwoord zijn
                        if len(st.session_state.exam_answers) < num_questions:
                            st.error(f"⚠️ Je hebt nog niet alle vragen beantwoord ({len(st.session_state.exam_answers)}/{num_questions})")
                        else:
                            st.session_state.exam_completed = True
                            st.rerun()
            
            else:
                # Resultaten pagina
                st.subheader("📊 Tentamen Resultaten")
                
                results = evaluate_exam()
                
                # Bereken cijfer
                num_questions = len(results)
                correct_count = sum(1 for r in results if r["correct"])
                grade = (correct_count / num_questions) * 9 + 1
                
                # Toon cijfer
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.success(f"### 🎓 Je cijfer: {grade:.1f}")
                    st.progress(correct_count / num_questions)
                    st.caption(f"{correct_count} van {num_questions} vragen correct ({int(correct_count/num_questions*100)}%)")
                
                st.markdown("---")
                st.markdown("### 📋 Gedetailleerde Feedback")
                
                for i, result in enumerate(results):
                    # Bepaal emoji
                    emoji = "✅" if result["correct"] else "❌"
                    
                    with st.expander(f"{emoji} Vraag {i+1}: {result['vraag'][:60]}..."):
                        st.markdown(f"**Vraag:**\n{result['vraag']}")
                        st.markdown("---")
                        
                        # Toon opties
                        st.markdown("**Opties:**")
                        for opt in result['opties']:
                            st.markdown(f"- {opt}")
                        
                        st.markdown("---")
                        
                        # Jouw antwoord
                        if result["correct"]:
                            st.success(f"**Jouw antwoord:** {result['user_answer']} ✅")
                        else:
                            st.error(f"**Jouw antwoord:** {result['user_answer']} ❌")
                            st.info(f"**Correct antwoord:** {result['correct_answer']}")
                        
                        st.markdown("---")
                        st.markdown(f"**Uitleg:**\n{result['uitleg']}")
                        
                        # Smart Loop: Knop voor bijles bij foute antwoorden
                        if not result["correct"]:
                            st.markdown("---")
                            # Gebruik callback om StreamlitAPIException te voorkomen
                            st.button(
                                f"🧠 Oefen specifiek met dit onderwerp", 
                                key=f"remedial_btn_{i}", 
                                use_container_width=True,
                                on_click=start_remedial_session,
                                args=(result['vraag'], result['correct_answer'], result['uitleg'])
                            )
        
        else:  # Flashcards
            st.subheader("🃏 Flashcards")
            
            if st.session_state.flashcards:
                for i, card in enumerate(st.session_state.flashcards):
                    with st.expander(f"Flashcard {i+1}: {card['question'][:50]}..."):
                        st.markdown(f"**Vraag:**\n{card['question']}")
                        st.markdown("---")
                        st.markdown(f"**Antwoord:**\n{card['answer']}")
            else:
                st.info("Geen flashcards beschikbaar.")


if __name__ == "__main__":
    main()
