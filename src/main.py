import logging
import logging.config
import json

from errors import ApiException
from downloader import CourseDownloader, VirtualClassroomDownloader
from polito_session import PolitoSession
from config import Configuration, PersistentState, parse_configuration

log = logging.getLogger("polito_downloader")


def setup_logging(app_config: Configuration):
    config_path = "./logging_config.json"
    with open(config_path, "r") as config_file:
        config = json.load(config_file)

    logging.config.dictConfig(config)

    if app_config.verbose:
        logging.getLogger().setLevel(logging.DEBUG)


def main():
    state = PersistentState.load()
    config = parse_configuration()
    setup_logging(config)

    session = PolitoSession()

    log.info("logging in...")
    try:
        login_result = session.login(
            config.username, config.password, state.client_id)
    except ApiException as e:
        if e.code == 401:
            log.error("invalid login credentials")
            return

        raise e

    log.info("login successful")

    if state.client_id != login_result["clientId"]:
        state.client_id = login_result["clientId"]
        state.save()
        log.debug("changed client id")

    courses_response = session.courses()
    courses = courses_response["data"]

    for course in courses:
        if course["name"] in config.courses:
            log.info(f"downloading course {course['name']}")

            course_config = config.courses[course["name"]]

            downloader = CourseDownloader(
                session=session,
                config=config,
                course_name=course["name"],
                course_id=course["id"],
                ignore=course_config.ignore,
            )

            downloader.download_files()

            if course_config.should_download_virtual_classroom:
                log.info(f"downloading virtual classroom for course {course['name']}")
                vc_downloader = VirtualClassroomDownloader(
                    session=session,
                    config=config,
                    course_name=course["name"],
                    course_id=course["id"],
                )

                vc_downloader.download_lectures()

            log.info("done!")

    session.logout()


if __name__ == "__main__":
    main()
