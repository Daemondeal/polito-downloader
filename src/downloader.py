import os.path as path
import logging
import json
import os
import re

from polito_session import PolitoSession
from config import Configuration

log = logging.getLogger("polito_downloader")


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

        course_path = path.join(
            self.config.courses_path, self._convert_course_name(self.course_name)
        )

        already_downloaded_path = path.join(course_path, self.ALREADY_DOWNLOADED_NAME)

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

    def _convert_course_name(self, course_name: str) -> str:
        return course_name.lower().replace(" ", "-")

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
