""" Helper functions shared by the apps in Pythm_AppdaemonApps

    Snapshots from a camera to the Home Assistant www folder, and cancelling listeners.

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.0"

import os
import time
from pathlib import Path


def local_path_from_target(target_dir: str) -> str:
    """
    Convert a path to a folder inside Home Assistant's ``www`` folder into the
    ``/local/...`` path that Home Assistant serves it on. The last ``www`` in the path is used.

    Example
    -------
    >>> local_path_from_target('/config/www/doorbell/')
    '/local/doorbell/'

    Files in ``www`` are served at ``/local/`` WITHOUT authentication.
    """
    parts = Path(target_dir).parts
    try:
        www_index = len(parts) - 1 - parts[::-1].index('www')
    except ValueError as exc:
        raise ValueError(
            f"target_directory must contain a 'www' sub-directory: {target_dir}"
        ) from exc

    local = Path('/local').joinpath(*parts[www_index + 1:])
    return local.as_posix().rstrip('/') + '/'


def remove_old_images(ADapi, target_directory: str, keep_days: float) -> None:
    """Delete snapshots (image_*.jpg) in target_directory that are older than keep_days."""
    cutoff = time.time() - keep_days * 86400
    try:
        names = os.listdir(target_directory)
    except OSError:
        return
    for name in names:
        if name.startswith('image_') and name.endswith('.jpg'):
            path = os.path.join(target_directory, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError as e:
                ADapi.log(f"Not able to remove old snapshot {path}: {e}", level='DEBUG')


def save_image_with_timestamp(
    ADapi,
    target_directory: str,
    local_directory: str,
    camera_entity: str,
    namespace: str,
    keep_days: float | None = None,
) -> str:
    """Save a camera snapshot with a timestamp and return the local path.

    target_directory must be a path that Home Assistant can write to (it must be in
    Home Assistant's ``allowlist_external_dirs``) and that AppDaemon can see.
    If keep_days is given, snapshots older than that are deleted.
    """
    # 1. Ensure target directory exists
    try:
        os.makedirs(target_directory, exist_ok=True)
    except OSError as e:
        ADapi.log(f"Not able to create {target_directory}: {e}", level='WARNING')

    # 2. Build a timestamped filename
    formatted_date = ADapi.get_now().strftime("%Y%m%d_%H%M%S")
    target_filename = f"image_{formatted_date}.jpg"

    # 3. Full path
    target_path = os.path.join(target_directory, target_filename)

    # 4. Convert target path to a HA-compatible local path
    local_path_prefix = local_path_from_target(target_directory)
    local_path = os.path.join(local_path_prefix, target_filename)

    # 5. Call Home Assistant
    ADapi.call_service(
        "camera/snapshot",
        filename=target_path,
        entity_id=camera_entity,
        namespace=namespace,
    )

    if keep_days is not None:
        remove_old_images(ADapi, target_directory, keep_days)

    return local_path


def cancel_listen_handler(ADapi, handler, name) -> bool:
    if handler is not None:
        try:
            ADapi.cancel_listen_state(handler, silent=True)
        except Exception as e:
            ADapi.log(
                f"Not able to stop listen handler for {name}. Exception: {e}",
                level = 'DEBUG'
            )
            return False
    return True
