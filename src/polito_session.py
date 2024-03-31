import requests

from errors import ApiException
from tqdm import tqdm


class ApiUrl:
    BASE = "https://app.didattica.polito.it/api"
    LOGIN = BASE + "/auth/login"
    ME = BASE + "/me"
    LOGOUT = BASE + "/auth/logout"
    COURSES = BASE + "/courses"


CLIENT_NAME = "Polito Downloader Script"


class PolitoSession:
    session: requests.Session
    token: str

    def __init__(self):
        self.session = requests.Session()
        self.token = ""

    def headers(self):
        return {"Authorization": "Bearer " + self.token}

    def login(
        self, username: str, password: str, client_id: str = ""
    ) -> dict[str, str]:
        login_data = {
            "username": username,
            "password": password,
            "device": {
                # "name": "Daem Desktop",
                "platform": "Windows",
                "version": "10",
                "model": "???",
                # "manufacturer": "Microsoft"
            },
            "preferences": {
                "language": "it",
            },
        }

        if client_id != "":
            login_data["client"] = {
                "name": CLIENT_NAME,
                "id": client_id,
            }

        result = self.session.post(
            ApiUrl.LOGIN,
            json=login_data,
        )

        if result.status_code != 200:
            raise ApiException(f"Invalid Login: {result.json()}", result.status_code)

        data = result.json()["data"]
        self.token = data["token"]
        return data

    def logout(self):
        self.session.delete(ApiUrl.LOGOUT, headers=self.headers())

    def _fetch_from_api(self, url: str):
        if self.token == "":
            raise ApiException("Cannot make request before login")

        result = self.session.get(url, headers=self.headers())

        return result.json()

    def _download_file(self, url: str, destination: str):
        if self.token == "":
            raise ApiException("Cannot make request before login")

        with self.session.get(url, stream=True, headers=self.headers()) as r:
            r.raise_for_status()

            content_length_raw = r.headers.get("Content-length")
            if content_length_raw is not None:
                # TODO: I really hate that type:ignore, fix it
                content_length = float(content_length_raw)  # type:ignore
            else:
                content_length = None

            with open(destination, "wb") as f:
                with tqdm(
                    total=content_length, unit="b", unit_scale=True, unit_divisor=1024
                ) as progress_bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        progress_bar.update(8192)

    def me(self):
        return self._fetch_from_api(ApiUrl.ME)

    def files(self, course_id: int):
        return self._fetch_from_api(f"{ApiUrl.COURSES}/{course_id}/files")

    def download_lecture(self, lecture: dict, destination: str):
        return self._download_file(lecture["videoUrl"], destination)

    def download_file(self, course_id: int, file_id: int, destination: str):
        return self._download_file(
            f"{ApiUrl.COURSES}/{course_id}/files/{file_id}", destination
        )

    def courses(self):
        return self._fetch_from_api(ApiUrl.COURSES)

    def course(self, course_id: int):
        return self._fetch_from_api(f"{ApiUrl.COURSES}/{course_id}")

    def videolectures(self, course_id: int):
        return self._fetch_from_api(f"{ApiUrl.COURSES}/{course_id}/videolectures")

    def virtual_classrooms(self, course_id: int):
        return self._fetch_from_api(f"{ApiUrl.COURSES}/{course_id}/virtual-classrooms")
