# Developed by IncendiaryMoose

from . import PrintSettingsAppender


def getMetaData():
    return {}


def register(app):
    return {"extension": PrintSettingsAppender.PrintSettingsAppender()}
