#!/usr/bin/env python3
"""
EUC-KR 인코딩된 파일명을 가진 zip 파일들을 재귀적으로 압축 해제하는 스크립트.
"""

import zipfile
import os
from pathlib import Path


def decode_filename(raw_name: str) -> str:
    """cp437로 인코딩된 파일명을 euc-kr로 디코딩."""
    try:
        return raw_name.encode('cp437').decode('euc-kr')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return raw_name


def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """zip 파일을 dest_dir에 압축 해제. 파일명 EUC-KR 디코딩 처리."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"  압축 해제: {zip_path} → {dest_dir}")

    with zipfile.ZipFile(zip_path, 'r') as zf:
        for zip_info in zf.infolist():
            decoded_name = decode_filename(zip_info.filename)
            target_path = dest_dir / decoded_name

            if zip_info.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(zip_info) as src, open(target_path, 'wb') as dst:
                    dst.write(src.read())


def process_directory(directory: Path) -> None:
    """디렉토리 안의 모든 zip 파일을 찾아 재귀적으로 압축 해제."""
    for zip_path in sorted(directory.glob('*.zip')):
        dest_dir = directory / zip_path.stem

        if dest_dir.exists():
            print(f"  스킵 (이미 존재): {dest_dir}")
            continue

        extract_zip(zip_path, dest_dir)
        # 해제된 폴더 안에 zip이 있으면 재귀 처리
        process_directory(dest_dir)


def main() -> None:
    data_raw = Path('/Users/seong-in/Desktop/Git/pyosim/data_raw')

    # 1. data_raw 최상위 zip 파일들 처리
    print("=== data_raw 최상위 zip 파일 처리 ===")
    process_directory(data_raw)

    # 2. 대통령선거 폴더 안의 zip 처리 (제17대 대통령선거 개표자료.zip)
    print("\n=== 대통령선거 개표결과(제14대~제18대) 내부 zip 처리 ===")
    presidential_dir = data_raw / '대통령선거 개표결과(제14대~제18대)'
    process_directory(presidential_dir)

    # 3. 재보궐선거 폴더 안의 zip 처리
    print("\n=== 04_재보궐선거_결과(1998년_이후) 내부 zip 처리 ===")
    byeol_dir = data_raw / '04_재보궐선거_결과(1998년_이후)'
    process_directory(byeol_dir)

    # 4. 결과 출력
    print("\n=== 압축 해제 완료 후 폴더 구조 ===")
    print_tree(data_raw, max_depth=3)


def print_tree(root: Path, max_depth: int, current_depth: int = 0, prefix: str = '') -> None:
    """디렉토리 트리를 출력."""
    if current_depth > max_depth:
        return

    entries = sorted(root.iterdir(), key=lambda entry: (entry.is_file(), entry.name))
    for index, entry in enumerate(entries):
        connector = '└── ' if index == len(entries) - 1 else '├── '
        print(prefix + connector + entry.name)
        if entry.is_dir() and current_depth < max_depth:
            extension = '    ' if index == len(entries) - 1 else '│   '
            print_tree(entry, max_depth, current_depth + 1, prefix + extension)


if __name__ == '__main__':
    main()
