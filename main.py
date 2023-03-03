import os
import sys
from google.cloud import speech
from google.cloud import storage
from pydub import AudioSegment
from easygui import msgbox, ccbox, fileopenbox, exceptionbox
from functools import lru_cache

STORAGE_CREDENTIALS_FILE = "storage-sa.json"
BUCKET_NAME = "speech-2-txt"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'speech-2-txt-sa.json'
speech_client = speech.SpeechClient()


class StorageClient:
    """
    Class creates a client that connects to Cloud Storage Bucket and uploads new files.
    :param: credentials_file: json key file to Google Cloud service account with Cloud Storage permissions
    :param: bucket_name: name of bucket that you want to place file in
    """
    def __init__(self, credentials_file: str, bucket_name: str):
        self._credentials_file = credentials_file
        self._bucket_name = bucket_name
        self._client = storage.Client.from_service_account_json(self._credentials_file)
        self._bucket = self._client.get_bucket(self._bucket_name)

    def upload(self, blob_name: str, path_to_file: str):
        blob = self._bucket.blob(blob_name)
        blob.upload_from_filename(path_to_file)

    def get_blob_uri(self, blob_name: str) -> str:
        blob = self._bucket.blob(blob_name)
        link = blob.path_helper(self._bucket_name, blob_name)
        gs_link = "gs://" + link
        return gs_link

    def delete_blob(self, blob_name: str):
        blob = self._bucket.blob(blob_name)
        blob.delete()


@lru_cache
def get_client() -> StorageClient:
    return StorageClient(STORAGE_CREDENTIALS_FILE, BUCKET_NAME)


storage_client = get_client()


class ExtensionException(Exception):
    def __init__(self):
        super().__init__(
            "Unsupported file extension."
        )


def convert_to_wav_and_save_file(filepath: str):
    """
    Func to convert given audio file to WAV extension and save it as new file.
    :param filepath: path to local audio file in .mp3, .mp4 or .m4a extension
    :return: path to converted WAV file
    """
    extension_list = ("mp4", "mp3", "m4a")
    filename = filepath.split("\\")[-1]
    dir_ = filepath.replace(filename, '')
    if not os.path.exists(dir_):
        os.mkdir(dir_)
    for extension in extension_list:
        if filename.lower().endswith(extension):
            audio = AudioSegment.from_file(filepath, extension)
            new_audio = audio.set_frame_rate(frame_rate=16000)
            new_filename = f"{dir_}{filename.split('.')[0]}.wav"
            new_audio.export(new_filename, format="wav")
            return new_filename
    if filename.lower().endswith("wav"):
        return filepath
    raise ExtensionException


def transcript_big_bucket_file_gcp(media_uri):
    """
    Uses Google speech-to-text to transcript file that is longer than 60 sec or weights more than 10MB.
    File has to be uploaded to Cloud Storage bucket.
    :param: media_uri: URI to file sored in Cloud Storage Bucket
    :return: transcript text and Google total billed time
    """
    audio = speech.RecognitionAudio(uri=media_uri)
    detail_config = dict(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="pl-PL",
        alternative_language_codes=["en-US"],
        enable_automatic_punctuation=True,
        use_enhanced=True,
        model='latest_long',
        audio_channel_count=1
    )
    config = speech.RecognitionConfig(detail_config)
    operation = speech_client.long_running_recognize(config=config, audio=audio)
    response = operation.result()
    return response.results


def auto_capitalize(text: str) -> str:
    return '. '.join(list(map(lambda x: x.strip().capitalize(), text.split('.'))))


def save_transcription(results):
    with open("aaa.txt", "a") as file:
        for result in results:
            file.write(f"- {auto_capitalize(str(result.alternatives[0].transcript))}\n")


def main():
    title = "digimonkeys.com transcriprion tool"
    msg = """
    Supported audio extensions: MP4, MP3, M4A, WAV.
    FFmpeg installed on your local machine is required.
    """
    msgbox(msg=msg, title=title)

    while 1:
        msg = "Choose audio file from your local storage."
        if ccbox(
                msg=msg,
                title=title,
                choices=["Ch[o]ose file", "C[a]ncel"],
                default_choice='Choose file',
                cancel_choice='Cancel'
        ):
            file_path = fileopenbox()
            try:
                new_filepath = convert_to_wav_and_save_file(filepath=file_path)
                storage_client.upload("audio_file.wav", new_filepath)

                if not file_path.endswith("wav"):
                    os.remove(new_filepath)

                blob_uri = storage_client.get_blob_uri("audio_file.wav")
                blob_uri = blob_uri.replace('/o/', '/')

                results = transcript_big_bucket_file_gcp(blob_uri)
                with open(f"{new_filepath[:-4]}.txt", "a") as file:
                    for result in results:
                        file.write(f"- {auto_capitalize(str(result.alternatives[0].transcript))}\n")
                msgbox(msg="Transcription file saved in the source file directory.", title=title)

            except ExtensionException:
                msgbox(msg="Unsupported file extension.", title=title)

            except AttributeError:
                pass

            except Exception as e:
                exceptionbox(str(e), title=title)

            finally:
                storage_client.delete_blob("audio_file.wav")

        else:
            sys.exit(0)


if __name__ == '__main__':
    main()
