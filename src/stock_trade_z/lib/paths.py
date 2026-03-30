from pathlib import Path


def get_script_parent_folder_path():
    script_path = Path(__file__).resolve()

    parent_folder = script_path.parent.parent

    return parent_folder


def get_file_in_pack(*path_segments: str | Path) -> Path:
    combined_path = get_script_parent_folder_path()
    for segment in path_segments:
        combined_path = combined_path / segment

    resolved_absolute_path = combined_path.resolve()

    return resolved_absolute_path


if __name__ == "__main__":
    print(get_file_in_pack("../../stocklist.csv"))
