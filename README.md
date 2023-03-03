# digimonkeys.com transcription tool
- FFmpeg installed on local machine is required 
- App uses Google Cloud Speech-to-text so you have to perform few steps to make it work:

    - Create Google Cloud project
    - Create Cloud Storage bucket named **speech-2-txt**
    - Create service account with Storage Admin permissions, generate it's json key and save it as **storage-sa.json** in this project directory
    - Create service account with Speech-to-text Admin permissions, generate it's json key and save it as **speech-2-txt-sa.json** in this project directory