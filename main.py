import glob
import os
import lib.subtitle_sync as subtitle_sync
import lib.utility as utility


def main():
    current_dir = os.getcwd()

    # Look for audio files (mp3) instead of video files
    reference_audio_files = sorted(glob.glob(os.path.join(current_dir, '*.mp3')),
                                   key=utility.file_name_sorter)

    # First try with just .srt files
    target_sub_files = sorted(glob.glob(os.path.join(current_dir, '*.srt')),
                              key=utility.file_name_sorter)

    # Only include .ass files if the counts don't match
    if len(reference_audio_files) != len(target_sub_files):
        target_sub_files = sorted(glob.glob(os.path.join(current_dir, '*.srt')) +
                                  glob.glob(os.path.join(current_dir, '*.ass')),
                                  key=utility.file_name_sorter)

    if len(reference_audio_files) != len(target_sub_files):
        raise ValueError(
            f"Number of audio files ({len(reference_audio_files)}) and subtitle files ({len(target_sub_files)}) do not match.")

    # Sync subtitles using audio as reference
    subtitle_sync.sync_subtitles(reference_audio_files, target_sub_files, current_dir)


if __name__ == '__main__':
    main()
