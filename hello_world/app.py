from __future__ import print_function
from http import HTTPStatus
from typing import List
from icecream import ic
from text_analysis import TextAnalysis
import boto3
import hashlib
from transcribe_operations import *
import json
import icecream


def lambda_handler(event, context):
    response: List[dict]
    # initialize parameters
    job_uri, trackers, transcribe = init_params(event)

    if job_uri is None or trackers is None:
        return {'statusCode': HTTPStatus.BAD_REQUEST, 'body': json.dumps("Bad parameters")}

    # hashing the url to create unique job name for each url
    job_name = hashlib.md5(job_uri.encode("utf-8")).hexdigest()

    # checks if job's name already exists in transcribe
    job_exists = search_job_name(transcribe.list_transcription_jobs(), job_name)

    # creates job if is not exists.
    if not job_exists:
        job_creation_succeed = transcribe_service_create_job(transcribe, job_uri, job_name)
        if not job_creation_succeed:
            return {'statusCode': HTTPStatus.INTERNAL_SERVER_ERROR, 'body': json.dumps("Job creation failed")}

    # get job and retrieve it's transcription
    job = transcribe.get_transcription_job(TranscriptionJobName=job_name)
    job_result = transcribe_retrieve_data(job)

    # failed to get job
    if job_result.get("statusCode", None) == HTTPStatus.BAD_REQUEST:
        return job_result

    # analyze transcript and return response.
    transcript = job_result['results']['transcripts'][0]['transcript']
    text = TextAnalysis(transcript, trackers)
    response = text.analyze_and_get_response()

    return {'statusCode': HTTPStatus.OK, 'body': json.dumps(response)}


def init_params(event) -> tuple:
    """
    initialization of parameters
    """
    job_uri = event.get("queryStringParameters", dict()).get("interaction_url")

    if (val := event.get("queryStringParameters").get("trackers")) is not None:
        trackers = json.loads(val)
    else:
        trackers = None

    transcribe = boto3.client('transcribe')
    return job_uri, trackers, transcribe


def search_job_name(jobs_dict: dict, job_name: str) -> bool:
    """
    searches the job name in the retrieved job's list
    :param jobs_dict:
    :param job_name: job name to search for
    :returns: True if job names exists otherwise False
    """
    jobs_list = jobs_dict['TranscriptionJobSummaries']
    for job_ in jobs_list:
        if job_["TranscriptionJobName"] == job_name:
            return True
    return False
