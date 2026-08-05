import os
import json

from helpers.availability import get_availability_file


def save_exception(username, date, data):

    path = get_availability_file(username)

    with open(path, "r") as file:
        availability = json.load(file)


    availability["exceptions"][str(date)] = data


    with open(path, "w") as file:
        json.dump(
            availability,
            file,
            indent=4
        )


def remove_exception(username, date):

    path = get_availability_file(username)

    with open(path, "r") as file:
        availability = json.load(file)


    if str(date) in availability["exceptions"]:
        del availability["exceptions"][str(date)]


    with open(path, "w") as file:
        json.dump(
            availability,
            file,
            indent=4
        )