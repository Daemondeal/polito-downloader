import argparse
import toml
import logging
import json

from getpass import getpass
from dataclasses import dataclass

log = logging.getLogger("polito_downloader")


@dataclass
class Course:
    name: str
    ignore: list[str]
    should_download_virtual_classroom: bool


@dataclass
class Configuration:
    username: str
    password: str | None
    courses_path: str
    courses: dict[str, Course]
    verbose: bool


def missing_argument(message: str):
    log.error(message)
    exit(-1)


def parse_configuration() -> Configuration:
    with open("configuration.toml", "r") as toml_config:
        defaults = toml.load(toml_config)

    parser = argparse.ArgumentParser(
        prog="polito_downloader", description="a downloader for polito courses files"
    )

    parser.add_argument("-u", "--username")
    parser.add_argument("-p", "--password")
    parser.add_argument("-d", "--destination")
    parser.add_argument("-c", "--course")
    parser.add_argument("-v", "--verbose", action="store_true")

    configs = parser.parse_args()

    username = (
        configs.username
        or (defaults.get("login") and defaults["login"].get("username"))
        or missing_argument("Missing username")
    )

    password = (
        configs.password
        or (defaults.get("login") and defaults["login"].get("password"))
        or getpass()
    )

    destination = (
        configs.destination
        or (defaults.get("download") and defaults["download"].get("download_path"))
        or missing_argument("Missing download path")
    )

    verbose = configs.verbose

    if configs.course is not None:
        courses = {
            configs.course: Course(
                name=configs.course, ignore=[], should_download_virtual_classroom=False
            )
        }

    elif "courses" in defaults:
        courses = {
            course["name"]: Course(
                name=course["name"],
                ignore=([] if "ignore" not in course else course["ignore"]),
                should_download_virtual_classroom=course.get(
                    "download_virtual_classroom"
                )
                == True,
            )
            for course in defaults["courses"]
        }
    else:
        missing_argument("Missing courses to download")

    return Configuration(
        username=username,
        password=password,
        courses_path=destination,
        courses=courses,
        verbose=verbose,
    )


@dataclass
class PersistentState:
    client_id: str

    @classmethod
    def load(cls):
        try:
            with open("persisent_state.json", "r") as json_state:
                state_raw = json.load(json_state)

            cls(client_id=state_raw["client_id"])
        except:
            return cls.default()

    def save(self):
        with open("persistent_state.json", "w") as json_state:
            json.dump({"client_id": self.client_id}, json_state)

    @classmethod
    def default(cls):
        return cls(client_id="")
