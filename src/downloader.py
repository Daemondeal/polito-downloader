import os.path as path
import logging
import json
import os
import re

from polito_session import PolitoSession
from config import Configuration

log = logging.getLogger("polito_downloader")


def _convert_course_name(course_name: str) -> str:
    return course_name.lower().replace(" ", "-")


def _fix_date(name: str):
    return re.sub(r"(\d{2})/(\d{2})/(\d{4})", r"\3-\2-\1", name)


def _clean_filename(name: str) -> str:
    redated = _fix_date(name)
    replaced = redated.lower().replace(" ", "-").replace("/", "-")
    cleaned = re.sub(r"[^\da-zA-Z _-]", "", replaced)
    cleaned = re.sub(r"-+", "-", cleaned)

    return cleaned


class VirtualClassroomDownloader:
    session: PolitoSession
    config: Configuration

    already_downloaded: dict[str, str]

    course_name: str
    course_id: int

    ALREADY_DOWNLOADED_NAME = ".already_downloaded.vl.json"

    def __init__(
        self,
        session: PolitoSession,
        config: Configuration,
        course_name: str,
        course_id: int,
    ):
        self.session = session
        self.config = config
        self.course_name = course_name
        self.course_id = course_id

    def download_lectures(self):
        lectures = self.session.virtual_classrooms(self.course_id)["data"]

        root_path = path.join(
            self.config.courses_path, _convert_course_name(self.course_name)
        )

        course_path = path.join(root_path, "virtualclassrooms")

        already_downloaded_path = path.join(
            root_path,
            self.ALREADY_DOWNLOADED_NAME,
        )

        if not path.exists(course_path):
            os.makedirs(course_path)

        if path.exists(already_downloaded_path):
            with open(already_downloaded_path, "r") as ad_file:
                self.already_downloaded = json.load(ad_file)
        else:
            self.already_downloaded = {}

        for lecture in lectures:
            ext = lecture["videoUrl"].split(".")[-1]
            file_name = _clean_filename(lecture['title'])
            dest = path.join(course_path, f"{file_name}.{ext}")
            id = str(lecture['id'])
            if id in self.already_downloaded and self.already_downloaded[id] == lecture["createdAt"]:
                log.debug(f"skipping {dest}")
                continue

            log.info(f"downloading {dest}")

            self.session.download_lecture(lecture, dest)

            self.already_downloaded[id] = lecture["createdAt"]

            # NOTE: Since lectures are typically heavy, it is probably
            #       a good idea to save which ones we've already
            #       downloaded after each single download
            with open(already_downloaded_path, "w") as ad_file:
                json.dump(self.already_downloaded, ad_file)


class CourseDownloader:
    session: PolitoSession
    config: Configuration

    course_name: str
    course_id: int
    ignore: list[str]

    already_downloaded: dict[str, str]

    ALREADY_DOWNLOADED_NAME = ".already_downloaded.json"

    def __init__(
        self,
        session: PolitoSession,
        config: Configuration,
        course_name: str,
        course_id: int,
        ignore: list[str] = [],
    ):
        self.session = session
        self.config = config
        self.course_name = course_name
        self.course_id = course_id
        self.ignore = ignore

    def download_files(self):
        files = self.session.files(self.course_id)

        root_path = path.join(
            self.config.courses_path,
            _convert_course_name(self.course_name),
        )

        course_path = path.join(root_path, "files")

        already_downloaded_path = path.join(
            root_path,
            self.ALREADY_DOWNLOADED_NAME,
        )

        if not path.exists(course_path):
            os.makedirs(course_path)

        if path.exists(already_downloaded_path):
            with open(already_downloaded_path, "r") as ad_file:
                self.already_downloaded = json.load(ad_file)
        else:
            self.already_downloaded = {}

        for entry in files["data"]:
            self._download_entry(course_path, entry)

        with open(already_downloaded_path, "w") as ad_file:
            json.dump(self.already_downloaded, ad_file)

    def _is_ignored(self, file_name: str) -> bool:
        for ignore in self.ignore:
            if re.match(ignore, file_name):
                return True

        return False

    def _download_file(self, destination: str, file: dict):
        name = file["name"]
        id = file["id"]
        created_at = file["createdAt"]

        file_dest = path.join(destination, name)

        if id in self.already_downloaded and self.already_downloaded[id] == created_at:
            log.debug(f"skipping {file_dest}")
            return

        log.info(f"downloading {file_dest}")
        self.session.download_file(self.course_id, id, file_dest)

        self.already_downloaded[id] = created_at

    def _download_entry(self, destination: str, root_entry: dict):
        if self._is_ignored(root_entry["name"]):
            return

        if root_entry["type"] == "file":
            return self._download_file(destination, root_entry)

        new_destination = path.join(destination, root_entry["name"])
        if not path.exists(new_destination):
            os.makedirs(new_destination)

        # Entry is a directory
        for entry in root_entry["files"]:
            self._download_entry(new_destination, entry)
