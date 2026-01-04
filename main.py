import glob
import os
import shutil
import lib.subtitle_sync as subtitle_sync
import lib.subtitle_cleaning as subtitle_cleaning
import lib.utility as utility


def main():
    root_dir = os.getcwd()
    file_work_dir = os.path.join(root_dir, 'file_work')

    if not os.path.exists(file_work_dir):
        print(f"Error: Directory '{file_work_dir}' does not exist.")
        return

    # Look for audio files (mp3)
    reference_audio_files = sorted(glob.glob(os.path.join(file_work_dir, '*.mp3')),
                                   key=utility.file_name_sorter)

    # Look for subtitle files (srt only)
    target_sub_files = sorted(glob.glob(os.path.join(file_work_dir, '*.srt')),
                              key=utility.file_name_sorter)

    if not reference_audio_files:
        print("No .mp3 files found in file_work directory.")
        return
    
    if not target_sub_files:
        print("No .srt files found in file_work directory.")
        return

    if len(reference_audio_files) != len(target_sub_files):
        print(f"Error: Number of audio files ({len(reference_audio_files)}) and "
              f"subtitle files ({len(target_sub_files)}) do not match.")
        return

    print(f"Found {len(reference_audio_files)} pairs of files.")

    # Step 1: Cleaning
    print("\n--- Step 1: Cleaning Subtitles ---")
    cleaned_sub_files, cleanup_temp = subtitle_cleaning.clean_subtitles(target_sub_files)

    # Step 2: Syncing
    print("\n--- Step 2: Syncing Subtitles ---")
    try:
        # We pass the cleaned files (which are in a temp dir) as targets
        # The output currently goes to file_work locally in sync_subtitles
        subtitle_sync.sync_subtitles(reference_audio_files, cleaned_sub_files, file_work_dir)
    finally:
        # Cleanup temporary files
        if cleanup_temp:
            cleanup_temp()

    print("\nProcessing complete.")


if __name__ == '__main__':
    main()
