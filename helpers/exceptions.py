from helpers.availability import remove_exception as remove_availability_exception
from helpers.availability import update_exception


def save_exception(username, date, data):
    update_exception(username, date, data)


def remove_exception(username, date):
    remove_availability_exception(username, date)