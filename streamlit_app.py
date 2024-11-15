import streamlit as st
from openai import OpenAI
from streamlit_searchbox import st_searchbox
import json
# from difflib import get_close_matches
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import boto3
from geopy.distance import geodesic
import pandas as pd

def find_in_json(data, key):
    """
    Recursively find value for key in a json structure.
    Args:
        data (json): json to be searched
        key (string): key to be searched for
    Output:
        List of the values for the key
    """
    
    values = []
     
    if isinstance(data, dict): 
        for k, v in data.items(): 
            if k == key: 
                values.append(v) 
            values.extend(find_in_json(v, key)) 
    elif isinstance(data, list): 
        for item in data: 
            values.extend(find_in_json(item, key)) 
     
    return values


def load_conditions():
    """
    Load list of medical conditions from a file into global variable CONDITIONS_LIST.
    File should be in same directory as this file.
    """
    global CONDITIONS_LIST
    CONDITIONS_LIST = []
    
    conditions_filename = "conditions.txt"
    
    with open(conditions_filename, 'r') as conditions_file:
        for line in conditions_file:
            CONDITIONS_LIST.append(line.rstrip())  # Strip out whitespace, newlines


def find_conditions(searchTerm: str) -> list[any]:
    """
    Takes a string and returns a list of potential matches.

    Args:
        searchTerm (str): String to match

    Returns:
        List[any]: List of strings that are partial matches, sorted by closeness.
    """
    
    # return get_close_matches(searchTerm, CONDITIONS_LIST)
    return process.extract(searchTerm, CONDITIONS_LIST)

def create_location_index(client,index_name):

    get_indexes = client.list_place_indexes()

    entries = get_indexes.get('Entries')

    index_list = [entry.get('IndexName') for entry in entries]

    if index_name in index_list:
        pass
    else:
        client.create_place_index(IndexName=index_name,DataSource='Esri')

def covert_zip_to_geo(zip_code):
    
    # set AWS profile based on credentials file
    session = boto3.Session(profile_name='210_access_key')

    # start client
    client = session.client(service_name='location',region_name='us-west-2')

    # define index name
    index_name = 'ZipIndex'

    # create location index if needed
    create_location_index(client,index_name)

    # Perform the geocoding request
    response = client.search_place_index_for_text(
        IndexName=index_name,
        Text=zip_code,
        MaxResults=1
    )

    results = response.get('Results')

    if results:
        for result in results:
            place = result.get('Place')
            if place:
                geo = place.get('Geometry')
                if geo:
                    point = geo.get('Point')

    longitude, latitude = point

    zip_geo = (latitude,longitude)

    return zip_geo

def trials_within_distance(zip_code,max_miles,trials):

    #  convert zip to geocode
    zip_geo = covert_zip_to_geo(zip_code)

    # assuming we have our trials in a dataframe, explode to get all locations for all trials
    locations = trials[['nctid','location_geo_point']].explode('location_geo_point')

    # remove trials without location data since we cannot compare to zip code
    locations_clean = locations[locations.location_geo_point.notnull()]

    # format the coordinates
    locations_clean.location_geo_point = locations_clean.location_geo_point.apply(lambda x : (x.get('lat'),x.get('lon')))

    # calculate the distance to each trial in miles
    locations_clean['distance'] = locations_clean.location_geo_point.apply(lambda x: geodesic(zip_geo, x).miles)

    # get the trials within the distance
    acceptable_trials = locations_clean[locations_clean.distance <= max_miles]

    # get the unique trial ids
    acceptable_trial_ids = acceptable_trials.nctid.unique().tolist()

    within_distance = trials[trials['nctid'].isin(acceptable_trial_ids)]

    return within_distance

def call_retrieve_trials_API(patient):
    """
    Call the API to get matching clinical trials.
    For now, this will read a json file of clinical trials.
    """
    clinical_trials_file = open("clinical_trials_sample.json")

    trials = pd.read_json(path_or_buf='validation_clinical_trials.json')

    zip_code = patient.get('location')
    max_miles = patient.get('distance')

    within_distance = trials_within_distance(zip_code,max_miles,trials)

    return json.load(clinical_trials_file)


def find_trials(patient):
    """
    Function to find clinical trials.
    Args:
        patient (dict): patient information
    Output:
        list of jsons for clinical trials
    """
    
    return call_retrieve_trials_API(patient)


def show_clinical_trials(json_list):
    """
    Show clinical trials

    Args:
        json_list (list of jsons): List of clinical trials as jsons
    Output:
        None
    """
    for idx, ct in enumerate(json_list):
            
            # Show brief title if available, otherwise show official title
            nctId = find_in_json(ct,"nctId")[0]
            briefTitle_list = find_in_json(ct, "briefTitle")
            officialTitle_list = find_in_json(ct, "officialTitle")
            if briefTitle_list:
                expander_heading = nctId + " - " + briefTitle_list[0]
            else:
                expander_heading = nctId + " - " + officialTitle_list[0]
            
            with st.expander(expander_heading):
                # Show either detailed description of brief summary
                detailedDescription_list = find_in_json(ct, "detailedDescription")
                briefSummary_list = find_in_json(ct, "briefSummary")
                if detailedDescription_list:
                    st.text("Detailed Description:")
                    st.write(detailedDescription_list[0])
                elif briefSummary_list:
                    st.text("Brief Summary:")
                    st.write(briefSummary_list[0])
                    
                # Show eligibility criteria
                eligibilityCriteria_list = find_in_json(ct, "eligibilityCriteria")
                if eligibilityCriteria_list:
                    st.text("Eligibility Criteria:")
                    st.write(eligibilityCriteria_list[0])
                
                # Show link to clinicaltrials.gov
                url = f"https://clinicaltrials.gov/study/{nctId}"
                st.markdown("[See more details on ClinicalTrials.gov website](%s)" % url)


def format_clinical_trials_prompt(json_list):
    """
    Format a prompt for the clinical trials.

    Args:
        json_list (list of jsons): List of the clinical trials as jsons
    """
    prompt = "The user is eligible for the following clinical trials.  The NCT ID is the \
        unique identifier of the clinical trial.\n"
    for idx, ct in enumerate(json_list):
        nctId = find_in_json(ct,"nctId")[0]
        prompt = prompt + "Clinical Trial NCT ID: " + nctId
        briefTitle_list = find_in_json(ct, "briefTitle")
        if briefTitle_list:
            prompt = prompt + "Brief Title: " + briefTitle_list[0] + "\n"
        officialTitle_list = find_in_json(ct, "officialTitle")
        if officialTitle_list:
            prompt = prompt + "Official Title: " + officialTitle_list[0] + "\n"
        
        # Show either detailed description of brief summary
        detailedDescription_list = find_in_json(ct, "detailedDescription")
        if detailedDescription_list:
            prompt = prompt + "Detailed Description: " + detailedDescription_list[0] + "\n"
        briefSummary_list = find_in_json(ct, "briefSummary")
        if briefSummary_list:
            prompt = prompt + "briefSummary: " + briefSummary_list[0] + "\n"
            
        # Show eligibility criteria
        eligibilityCriteria_list = find_in_json(ct, "eligibilityCriteria")
        if eligibilityCriteria_list:
            prompt = prompt + "Eligibility Criteria for Clinical Trial: " + eligibilityCriteria_list[0] + "\n"
    
    return prompt

load_conditions()  # Load list of medical conditions user can search from

# Show title and description.
st.title("AllTrials.info")
st.write(
    "This is a simple chatbot that uses OpenAI's GPT-3.5 model to generate responses. "
    "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
    "You can also learn how to build this app step by step by [following our tutorial](https://docs.streamlit.io/develop/tutorials/llms/build-conversational-apps)."
)

# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:

    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "ct_results" not in st.session_state:
        st.session_state.ct_results = []  # json list of clinical trials
        st.session_state.ct_prompt = ""  # prompt for the clinical trials
    
    # ----- NEW -----
    
    with st.sidebar:
        reset_button = st.button(label="Start new search")
    
    
    # In the sidebar, show a button to setup a new search
    if reset_button:
        st.session_state.ct_results = []
        st.session_state.messages = []
        
    # with st.form("input"):
    with st.sidebar:
        st.title("Search for Clinical Trials")
        st.write("Enter your information below.")   
        age = st.number_input("Age", 0, 100, 0, 1)
        sex = st.radio("Sex", ["Female", "Male"])
        condition = st.selectbox("Medical Condition", ["Amblyopia", "Retinitis Pigmentosa"])
        # Note: Value of condition is not retained if use Searchbox
        #       The prompt that asks if user has any questions about condition doesn't work
        # condition = st_searchbox(search_function=find_conditions,
        #                          label="Medical Condition",
        #                          key="condition_searchbox")
        conditionText = st.text_area("Additional Information")
        acceptsHealthy = st.checkbox("Accepts healthy volunteers", value=False)
        location = st.text_input(label="Zip Code",value='94720',max_chars=5)
        distance = st.number_input("Miles you are able to travel", 0, 10000, 0, 1)

        # submit_button = st.form_submit_button(label="Find clinical trials")
        submit_button = st.button(label="Find clinical trials")
        
        if submit_button:
            # Create a dictionary for the patient profile
            patient = {}
            patient["condition"] = condition
            patient["conditionText"] = conditionText
            patient["age"] = age
            patient["sex"] = sex
            patient["acceptsHealthy"] = acceptsHealthy
            patient["location"] = location
            patient["distance"] = distance
            
            st.session_state.ct_results = find_trials(patient)
            
    # Display results
    if len(st.session_state.ct_results):
        st.write("We found ", len(st.session_state.ct_results), "clinical trials you might qualify for.")
        show_clinical_trials(st.session_state.ct_results)
        
        if not st.session_state.messages:
            ct_prompt = "Do you have any questions about clinical trials or " + condition + "?"
            st.session_state.messages.append({"role": "assistant", "content": ct_prompt})
    # if len(st.session_state.ct_results):
    #     # Add button for each clinical trial to sidebar
    #     button_names = []
    #     with st.sidebar:
    #         for idx, ct in enumerate(st.session_state.ct_results):
    #             button_names.append(find_in_json(ct, "nctId")[0])
    #             st.button(button_names[idx])
    
    
    # ----- NEW -----

    # Display the existing chat messages via `st.chat_message`.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
        
    # Create a chat input field to allow the user to enter a message. This will display
    # automatically at the bottom of the page.
    if prompt := st.chat_input("Type your questions here"):

        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate a response using the OpenAI API.
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )

        # Stream the response to the chat using `st.write_stream`, then store it in 
        # session state.
        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})
