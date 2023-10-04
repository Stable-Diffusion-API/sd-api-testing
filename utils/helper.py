import os, sys
from os.path import dirname as up

sys.path.append(os.path.abspath(os.path.join(up(__file__), os.pardir)))

import pandas as pd
import json

# For making post requests
import requests
import time

from typing import Dict, Optional, Any, List, Union

from custom_logger import *
from utils.constants import *
from utils.models import *

def read_json_file(file_path: str) -> Any:
    """
    Reads a JSON file and returns its contents as a Python data structure.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        Any: The contents of the JSON file as a Python data structure.

    Raises:
        InvalidPathError: If the file path is not a string.
        ReadJSONFileError: If the file is not found, does not contain valid JSON,
            or an unexpected error occurs.
    """
    try:
        # Check if the file path is a string
        if not isinstance(file_path, str):
            raise InvalidPathError("File path must be a string")

        # Reading the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)

        return data

    except FileNotFoundError as e:
        error_message = f"The file {file_path} was not found"
        logger.error(error_message)
        raise ReadJSONFileError(error_message) from e
    
    except json.JSONDecodeError as e:
        error_message = f"The file {file_path} does not contain valid JSON"
        logger.error(error_message)
        raise ReadJSONFileError(error_message) from e
    
    except InvalidPathError as e:
        error_message = str(e)
        logger.error(error_message)
        raise
    
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logger.error(error_message)
        raise ReadJSONFileError(error_message) from e


def append_to_csv(endpoint, estimated_time_of_arrival, image_links, generation_time, images_delivery_time, status,filename='data.csv'):
    # Define the column names without spaces
    columns = ['SerialNumber', 'Endpoint', 'EstimatedTimeOfArrival', 'ImageLinks', 'GenerationTime', 'ImagesDeliveryTime', 'Status']

    # Read the existing CSV file if it exists, and get the last serial number
    try:
        existing_data = pd.read_csv(filename)
        last_serial_number = existing_data['SerialNumber'].max()
    except FileNotFoundError:
        last_serial_number = 0
        # Create an empty DataFrame with the columns if file doesn't exist
        existing_data = pd.DataFrame(columns=columns)
        # Write the empty DataFrame with headers to the CSV file
        existing_data.to_csv(filename, index=False)
    
    # Increment the serial number
    serial_number = last_serial_number + 1

    # Convert the image_links list to a string
    if isinstance(image_links, list):
        image_links_str = ', '.join(image_links)
    elif isinstance(image_links, str):
        image_links_str = image_links

    # Create a DataFrame with the provided data
    data = {
        'SerialNumber': [serial_number],
        'Endpoint': [endpoint],
        'EstimatedTimeOfArrival': [estimated_time_of_arrival],
        'ImageLinks': [image_links_str],
        'GenerationTime': [generation_time],
        'ImagesDeliveryTime': [images_delivery_time],
        'Status': [status]
    }
    df = pd.DataFrame(data, columns=columns)

    # Append the DataFrame to the existing CSV file
    df.to_csv(filename, mode='a', index=False, header=False)

def make_post_request(endpoint_url: str, 
                      prompt_body: Dict, 
                      headers: Dict[str, str], 
                      timeout_seconds: int = 60) -> Optional[Dict[str, Any]]:
    return process_response(endpoint_url, prompt_body, headers, timeout_seconds)

def process_response(endpoint_url: str, prompt_body: Dict, headers: Dict[str, str], timeout_seconds: int):
    start_time = time.time()
    retry_count = 0

    while retry_count < MAX_RETRIES:
        result = make_single_request(endpoint_url, prompt_body, headers, timeout_seconds)

        if result['status'] == "success":
            handle_success_response(endpoint_url, result, start_time, 0)
            return result
        elif result['status'] == "processing":
            handle_processing_response(endpoint_url, result, headers, timeout_seconds, start_time)
            return result
        elif result['status'] == "failed":
            logger.error(f"Request failed with status: {result['status']}. Retrying... retry_count: {retry_count}")
            retry_count += 1
        else:
            logger.error(f"Error. Unexpected status: {result['status']}. Message: {result['messege']}")
            append_to_csv(endpoint_url, "", [], 0, 0, f"{result['status']}: {result['messege']}")
            return result
    
    if retry_count == MAX_RETRIES:
        append_to_csv(endpoint_url, "", [], 0, 0, "failed")

def make_single_request(endpoint_url: str, prompt_body: Dict, headers: Dict[str, str], timeout_seconds: int) -> Optional[Dict[str, Any]]:
    try:
        api_service = endpoint_url.split("/")[-1]
        prompt_body['key'] = API_KEY
        logger.info(f"Performing post request to {api_service} API . . . .")
        response = requests.post(endpoint_url, json=prompt_body, headers=headers, timeout=timeout_seconds)
        
        if response.status_code != 200:
            error_message = f"Request failed with status code {response.status_code}. Response: {response.text}"
            logger.error(error_message)
            raise PostRequestException(error_message)
        
        return response.json()

    except requests.exceptions.Timeout:
        error_message = f"Request timed out after {timeout_seconds} seconds."
        logger.error(error_message)
        return None  # Return None or some other value to indicate a timeout
    
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logger.error(error_message)
        raise PostRequestException(error_message)


def handle_success_response(endpoint_url: str, result: Dict[str, Any], start_time: float, eta: float):
    logger.info("Output generation was successful!")
    generation_time = result.get('generationTime', round(time.time() - start_time, 2))
    response_statuses = check_image_links(result['output'], start_time)
    if response_statuses == []:
        status = "failed: maximum retries exceeded"
    else:
        status = "success"
    append_to_csv(endpoint_url, eta, result['output'], generation_time, response_statuses, status)

def handle_processing_response(endpoint_url: str, result: Dict[str, Any], headers: Dict[str, str], timeout_seconds: int, start_time: float):
    eta = result['eta']
    logger.info(f"Results processing....Checking again in {eta} seconds.")
    time.sleep(eta)
    fetch_queued_images_url = result['fetch_result']
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        response = requests.post(url=fetch_queued_images_url, 
                                 json={"key": API_KEY}, 
                                 headers=headers, 
                                 timeout=timeout_seconds)
        result = response.json()

        if result['status'] == "success":
            handle_success_response(endpoint_url, result, start_time, eta)
            break
        elif result['status'] == "processing":
            logger.info(f"Results processing....Checking again in {SLEEP_TIME} seconds.")
            time.sleep(SLEEP_TIME)
            retry_count += 1
        else:
            logger.error(f"Unexpected status: {result['status']}. Retrying... retry_count: {retry_count}")

    if retry_count == MAX_RETRIES:
        logger.error("Maximum retries exceeded.")
        append_to_csv(endpoint_url, "", [], 0, 0, "failed: max_retries exceeded")

def check_image_links(image_links: Union[List[str], str], start_time: float) -> List[Dict[str, str]]:
    response_statuses = []
    retry_count = 0 
    if isinstance(image_links, list):
        for link in image_links:
            while retry_count <  MAX_RETRIES:
                response = requests.get(link)
                if response.status_code == 200:
                    image_delivery_time = round(time.time() - start_time, 2)
                    response_statuses.append({link: f"image_delivery_time: {image_delivery_time} retry_count: {retry_count}"})
                    break
                else:
                    logger.info(f"Link not working: Retrying...")
                    time.sleep(5)
                    retry_count += 1
    
    elif isinstance(image_links, str):
        while retry_count <  MAX_RETRIES:
            response = requests.get(image_links)
            if response.status_code == 200:
                image_delivery_time = round(time.time() - start_time, 2)
                response_statuses.append({image_links: f"image_delivery_time: {image_delivery_time} retry_count: {retry_count}"})
                break
            else:
                logger.info(f"Link not working: Retrying...")
                time.sleep(5)
                retry_count += 1
    
    return response_statuses

if __name__ == '__main__':
    data = pd.read_csv("data/endpoints.csv")
    for row in data.iterrows():
        endpoint = row[1]['EndPoint']
        request_body = json.loads(row[1]['Json'])
        for api_call_count in range(API_CALLS):
            logger.info(f"API call count: {api_call_count}")
            make_post_request(endpoint, request_body, HEADERS, TIMEOUT)