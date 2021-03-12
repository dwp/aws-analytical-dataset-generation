import os

STEP_TO_START_FROM_FILE = "/opt/emr/step_to_start_from.txt"

def should_skip_step(logger, current_step_name):
    if os.path.isfile(STEP_TO_START_FROM_FILE):
        logger.info(
            "Previous step file found at '%s'",
            STEP_TO_START_FROM_FILE,
        )

        with open(STEP_TO_START_FROM_FILE, "r") as file_to_open:
            STEP = file_to_open.read().strip()
        
        logger.info(
            "Current step name is '%s'",
            current_step_name,
        )

        if STEP != current_step_name:
            logger.info(
                "Current step name is '%s', which doesn't match previously failed step '%s', so will exit",
                current_step_name,
                STEP,
            )
            return True
        else:
            logger.info(
                "Current step name is '%s', which matches previously failed step '%s', so deleting local file",
                current_step_name,
                STEP,
            )
            os.remove(STEP_TO_START_FROM_FILE)
    else:
        logger.info(
            "No previous step file found at '%s'",
            STEP_TO_START_FROM_FILE,
        )

    return False
        