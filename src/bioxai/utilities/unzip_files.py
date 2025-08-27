import gzip
import shutil
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import cast

from tqdm import tqdm

from bioxai.logger.log import setup_logger

logger = setup_logger()


def unzip_file(file_info: tuple[str, str, bool]) -> str | None:
    """Helper function to unzip a single .xml.gz file."""
    source_path, dest_path, overwrite = file_info
    extracted_file = None

    try:
        source_p = Path(source_path)
        dest_p = Path(dest_path)

        # Skip extraction if the file exists and overwrite is False
        if dest_p.exists() and not overwrite:
            logger.info(f"Skipping {dest_p}, already exists.")
            return None  # File not extracted

        with gzip.open(source_p, "rb") as f_in, open(dest_p, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        logger.info(f"Extracted: {dest_p}")
        extracted_file = str(dest_p)

    except Exception as e:
        logger.error(f"Error extracting {source_path}: {e}")

    return extracted_file  # Return extracted file name


def unzip_xml_gz_files(
    source_directory: list[str] | list[tuple[str, str, bool]],
    destination_directory: str | None = None,
    overwrite: bool = False,
) -> tuple[str, list[str]]:
    """
    Unzips .xml.gz files using multiprocessing.

    :param source_directory: List of file paths or a list of (source, destination, overwrite) tuples.
    :param destination_directory: Directory where extracted files will be saved (only needed for file lists).
    :param overwrite: Whether to overwrite existing extracted files.
    :return: Tuple (destination_directory, list of extracted files).
    """
    file_paths: list[tuple[str, str, bool]] = []

    if isinstance(source_directory, list):
        # Case 1: List contains (source_path, destination_path, overwrite) tuples (already formatted)
        if all(isinstance(item, tuple) and len(item) == 3 for item in source_directory):
            tuples_src = cast(list[tuple[str, str, bool]], source_directory)
            file_paths = tuples_src

        # Case 2: List contains only file paths (convert to tuples)
        elif all(isinstance(item, str) for item in source_directory):
            # Extract destination directory from the first file's parent
            str_list = cast(list[str], source_directory)
            first_file = Path(str_list[0]).resolve()
            default_dest_dir = first_file.parent / "unzipped"

            if destination_directory:
                destination_path = Path(destination_directory).resolve()
            else:
                destination_path = default_dest_dir

            destination_path.mkdir(parents=True, exist_ok=True)

            # Prepare (source, destination, overwrite) tuples
            file_paths = [
                (
                    str(Path(file).resolve()),
                    str(destination_path / Path(file).stem),
                    overwrite,
                )
                for file in str_list
            ]

        else:
            raise ValueError(
                "List must contain either raw file paths (str) or tuples of (source, destination, overwrite)."
            )

        # Extract destination directory from the first destination path
        destination_path = Path(file_paths[0][1]).parent

    else:
        raise TypeError(
            "source_directory must be a list of file paths or (source, destination, overwrite) tuples."
        )

    # Process files using multiprocessing
    with Pool(processes=cpu_count()) as pool:
        extracted_files: list[str] = list(
            filter(
                None,
                tqdm(
                    pool.imap_unordered(unzip_file, file_paths),
                    total=len(file_paths),
                    desc="Unzipping files",
                    unit="file",
                ),
            )
        )

    return str(destination_path), extracted_files
