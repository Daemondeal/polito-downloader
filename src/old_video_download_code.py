import os
import requests

from tqdm import tqdm
from polito_session import PolitoSession
from datetime import datetime


def download_vc(session: PolitoSession, courses):
    ca_id = 0
    for course in courses:
        if course["name"] == "Computer architectures":
            ca_id = course["id"]

    if ca_id == 0:
        print("Cannot find course")
        return

    ca_info = session.course(ca_id)

    prev_course = ca_info["data"]["vcOtherCourses"][0]["id"]

    download_all_virtual_classrooms(
        r"D:\Other\Lectures\ComputerArchitectures", prev_course, session
    )

    session.logout()


def list_virtual_classroom(lectures):
    result = []
    names = set()

    for lecture in lectures:
        date = datetime.fromisoformat(lecture["createdAt"])
        date_str = date.strftime("%Y-%m-%d")
        name = f"{date_str}.mp4"
        idx = 1

        while True:
            if name in names:
                name = f"{date_str}_{idx}.mp4"
                idx += 1
            else:
                break

        names.add(name)

        result.append({"filename": name, "url": lecture["videoUrl"]})
    return result


def filter_lectures(lectures, destination_path, ignores=set()):
    filtered = []
    files = set(os.listdir(destination_path))

    for lecture in lectures:
        if lecture["filename"] not in files and lecture["filename"] not in ignores:
            filtered.append(lecture)

    return filtered


def download_all_virtual_classrooms(
    destination_path: str, course_id: int, session: PolitoSession
):
    # Note: making a request and filtering every time is a very inefficient
    #       way of doing this, but since we're downloading an heavy file at
    #       each iteration it shouldn't matter that much

    ignores: set[str] = set()
    lectures_data = session.virtual_classrooms(course_id)["data"]
    lectures = filter_lectures(
        list_virtual_classroom(lectures_data), destination_path, ignores
    )

    total_downloads = len(lectures)
    current_download = 1

    while len(lectures) > 0:
        lecture_to_download = lectures[0]
        print(
            f"[{current_download:03}/{total_downloads:03}] Downloading {lecture_to_download['filename']}..."
        )
        try:
            download_file(
                lecture_to_download["url"],
                f"{destination_path}/{lecture_to_download['filename']}",
                session.headers(),
            )
        except requests.HTTPError as error:
            print(f"Error: {error}")
            ignores.add(lecture_to_download["filename"])

        lectures = list_virtual_classroom(session.virtual_classrooms(course_id)["data"])
        lectures = filter_lectures(lectures, destination_path, ignores)
        current_download += 1


def download_file(url: str, filename: str, headers: dict):
    with requests.get(url, stream=True, headers=headers) as r:
        r.raise_for_status()

        content_length_raw = r.headers.get("Content-length")
        if content_length_raw is not None:
            # TODO: I really hate that type:ignore, fix it
            content_length = float(content_length_raw)  # type:ignore
        else:
            content_length = None

        with open(filename, "wb") as f:
            with tqdm(
                total=content_length, unit="b", unit_scale=True, unit_divisor=1024
            ) as progress_bar:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    progress_bar.update(8192)
