import os
from datetime import datetime
from appdaemon.plugins.hass.hassapi import Hass

def save_image_with_timestamp(
    ADapi,
    target_directory: str,
    local_directory: str,
    camera_entity: str,
    namespace: str,
) -> str:
    """Save a camera snapshot with a timestamp and return the local path."""
    # 1. Ensure target directory exists
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    # 2. Build a timestamped filename
    now = datetime.now()
    formatted_date = now.strftime("%Y%m%d_%H%M%S")
    target_filename = f"image_{formatted_date}.jpg"

    # 3. Full path
    target_path = os.path.join(target_directory, target_filename)
    local_path = os.path.join(local_directory, target_filename)

    # 4. Call Home Assistant
    ADapi.call_service(
        "camera/snapshot",
        filename=target_path,
        entity_id=camera_entity,
        namespace=namespace,
    )

    return local_path