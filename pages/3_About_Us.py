import streamlit as st
from PIL import Image

st.image('AllTrials_logo.jpg', width=150)
st.title("About Us")

st.write("AllTrials.info is a capstone project for the Fall 2024 semester of the University of California, Berkeley's Masters of Information and Data Science (MIDS) program.")

st.header("Our Team")
# st.write("The application was created by Angela Ingram, Conrad Chan, Dylan Fletcher, Jonathon Hodges, and Shaki Pothini.")
# For some reason, unable to open Jonathan's jpg directly in Streamlit
j_image = Image.open('photos/Jonathan_image.jpg')
st.image(['photos/Angela_image.jpg',
          'photos/Conrad_image.jpg',
          'photos/Dylan_image.jpg',
          j_image,
          'photos/Shaki_image.jpg'],
         caption=['Angela Ingram', 'Conrad Chan', 'Dylan Fletcher', 'Jonathan Hodges', 'Shaki Pothini'],
         width=140
         )

st.header("Why AllTrials.info?")

st.write("Clinical trials are research studies that are run to determine how effective medical treatments are and play an important part in the advancement of medicine.  Clinical trials typically target a specific medical condition and have eligibility criteria that participants must meet in order to participate.")
st.write("However, inequitable access to clinical trials is a problem. Patients in rural areas or underserved populations often miss out on direct trial recruitment and trial outreach through their physicians. Further, online trial information can be difficult to navigate on currently available platforms and require more advanced technical and medical skills to find relevant trials.")
st.write("With AllTrials.info, we hope to give regular people better access to information about clinical trials through personalized matches.  Users can enter their medical information and have our advanced algorithms find studies related to their specific condition.  Users no longer need to sift through dozens of clinical trials they are ineligible for just to find the few they do qualify for.  Instead, we bring these to the surface immediately, potentially giving them access to treatments they wouldn’t have otherwise received.")
st.write("Our application can also benefit researchers.  By exposing clinical trials to hard-to-reach populations, we can potentially diversify the demographics of the participants.")
st.write("Note: We want to emphasize that AllTrials.info does not replace users’ trusted medical professionals.  We strongly encourage users to speak to their doctors about the clinical trials they find on our site to ensure they studies are truly right for them.")

st.header("Acknowledgements")
st.write("We would like to thank our instructors, Korin Reid and Ramesh Sarukkai, for their guidance.")
st.write("We would also like to thank Kevin Lee, M.D. for creating synthetic patients and identifying clinical trails those patients are eligible for.")