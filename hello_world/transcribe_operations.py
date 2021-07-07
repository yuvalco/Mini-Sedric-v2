from typing import Optional
import time
import urllib3
import botocore.client
import json
from http import HTTPStatus


def transcribe_service_create_job(transcribe: botocore.client, job_uri: str, job_name: str) -> bool:
    """
    uploads a file from s3 bucket to transcribe service

    :param transcribe: transcribe object
    :param job_uri: the url of the audio file to pull from s3
    :param job_name: the name of the job to create

    :Return: True if job COMPLETED successfully
    """

    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': job_uri},
        MediaFormat='mp3',
        LanguageCode='en-US'
    )

    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        time.sleep(10)

    return status['TranscriptionJob']['TranscriptionJobStatus'] in 'COMPLETED'


def transcribe_retrieve_data(status: dict) -> Optional[dict]:
    """
    retrieve the  json transcription file from transcribe service.

    :param status: - job's status and transcription as a dict
    :return: if retrieval was successful returns the transcript data in a dict.
            else returns dict with fail code and message for the server to return.
    """

    job_status_ = status['TranscriptionJob']['TranscriptionJobStatus']
    transcript_uri_ = status['TranscriptionJob']['Transcript']['TranscriptFileUri']

    if job_status_ in ['COMPLETED']:
        http = urllib3.PoolManager()
        data = http.request('GET', transcript_uri_)
        data = json.loads(data.data.decode('utf-8'))
        return data
    elif job_status_ in ['FAILED']:
        return {
            'statusCode': HTTPStatus.BAD_REQUEST,
            'body': json.dumps("Retrieval of data failed. Job failed.")
        }
