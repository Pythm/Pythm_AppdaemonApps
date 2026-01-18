import os
from datetime import datetime
from pathlib import Path

def local_path_from_target(target_dir: str) -> str:
    """
    Convert a Home‑Assistant *target* path (the absolute path on the
    host that contains the `www` folder) into the corresponding
    *local* path that the HA web‑server can read.

    Example
    -------
    >>> local_path_from_target(
    ...     '/var/lib/docker/volumes/hass_config/_data/www/doorbell/')
    '/local/doorbell/'
    """
    # Normalise to a Path
    target = Path(target_dir)

    try:
        # Find the index of the part that is exactly 'www'
        www_index = target.parts.index('www')
    except ValueError as exc:
        raise ValueError(
            f"target_directory must contain a 'www' sub-directory: {target_dir}"
        ) from exc

    # Everything *after* the www part is the suffix for local path
    suffix = Path(*target.parts[www_index + 1:])          # e.g. doorbell
    # Prepend the HA “/local” prefix
    local = Path('/local') / suffix
    # Return a POSIX‑style string with a trailing slash
    return str(local.as_posix() + '/' if not local.as_posix().endswith('/') else local)

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

    # 4. Convert target path to a HA‑compatible local path
    local_path_prefix = local_path_from_target(target_directory)
    local_path = os.path.join(local_path_prefix, target_filename)

    # 5. Call Home Assistant
    ADapi.call_service(
        "camera/snapshot",
        filename=target_path,
        entity_id=camera_entity,
        namespace=namespace,
    )

    return local_path