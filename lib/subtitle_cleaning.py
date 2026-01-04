from typing import List, Tuple, Callable, Dict, Set
import re
import tempfile
import os
import sys
import shutil
import pysubs2
from pysubs2 import SSAFile, SSAEvent

# Type aliases for better clarity
SubtitlePaths = List[str]
CleanupFunction = Callable[[], None]
StyleCounts = List[Tuple[str, int]]
StyleExamples = Dict[str, List[str]]

# Removed Japanese specific constants
SYMBOLS_TO_DELETE: Set[str] = {"♪", "~"}
# HEARING_IMPAIRED_REGEX (Japanese) removed
# FURIGANA_REGEX removed
INITIAL_BRACKETS: str = r"^\(.+\)"
TAGS_TO_IGNORE_AUTO: List[str] = [
    "Signs", "Caption", "Song", "ED", "OP",
    "Opening", "Ending", "Karaoke"
]


def extract_and_format_matches(text: str, regex: str) -> str:
    """Format regex matches with indentation for display."""
    matches = re.findall(regex, text)
    formatted_matches = '\n\t'.join([f"-->\t{match}" for match in matches])
    return f"{text}\n\t{formatted_matches}" if matches else text


def user_confirmation(matches: List[Tuple[str, str]], category: str) -> bool:
    """Get user confirmation for text removal in a specific category."""
    matches = matches[:10]  # Limit display to first 10 matches
    if not matches:
        return False

    prompt = "\n".join([extract_and_format_matches(text, regex)
                       for text, regex in matches])
    response = input(
        f"{prompt}\n\nFound the above lines and text to be removed in "
        f"category '{category}'. Press enter for delete. 'n' to keep. "
    ).strip().lower()
    return response != 'n'


def remove_special_texts(text: str, regex: str, clear_flag: bool) -> str:
    """Remove special text patterns if clear_flag is True."""
    return re.sub(regex, "", text) if clear_flag else text


def process_subtitle_line(line: SSAEvent, clear_flags: Dict[str, bool]) -> None:
    """Process a single subtitle line with the given clear flags."""
    line.text = line.text.replace(r"\N", "\n").replace(r"\n", " ")

    if clear_flags.get('special_symbols'):
        line.text = re.sub("|".join(map(re.escape, SYMBOLS_TO_DELETE)), "", line.text)
    if clear_flags.get('initial_brackets'):
        line.text = remove_special_texts(line.text, INITIAL_BRACKETS, True)

    line.text = re.sub(r"\s+", " ", line.text)


def collect_special_texts(subtitle: SSAFile) -> Dict[str, List[Tuple[str, str]]]:
    """Collect all special text patterns from subtitle file."""
    special_texts: Dict[str, List[Tuple[str, str]]] = {
        'special_symbols': [],
        'initial_brackets': []
    }

    for line in subtitle:
        line.text = line.text.replace(r"\N", "\n").replace(r"\n", " ")

        if any(symbol in line.text for symbol in SYMBOLS_TO_DELETE):
            special_texts['special_symbols'].append((line.text, "|".join(SYMBOLS_TO_DELETE)))
        if re.search(INITIAL_BRACKETS, line.text):
            special_texts['initial_brackets'].append((line.text, INITIAL_BRACKETS))

    return special_texts


def clean_subtitles(subtitle_files: SubtitlePaths) -> Tuple[SubtitlePaths, CleanupFunction]:
    """Clean subtitles by removing various special text patterns."""
    temp_dir = tempfile.mkdtemp(prefix="cleaned_subs_")
    cleaned_paths: SubtitlePaths = []

    # Collect all special texts from all files
    special_texts: Dict[str, List[Tuple[str, str]]] = {
        'special_symbols': [],
        'initial_brackets': []
    }

    for subtitle_file in subtitle_files:
        subtitle = pysubs2.load(subtitle_file)
        file_special_texts = collect_special_texts(subtitle)
        for key in special_texts:
            special_texts[key].extend(file_special_texts[key])

    # Get user confirmation for each category
    clear_flags = {
        'special_symbols': user_confirmation(
            special_texts['special_symbols'], "special symbols"),
        'initial_brackets': user_confirmation(
            special_texts['initial_brackets'], "initial brackets")
    }

    # Process each subtitle file
    for subtitle_file in subtitle_files:
        subtitle = pysubs2.load(subtitle_file)
        for line in subtitle:
            process_subtitle_line(line, clear_flags)

        subtitle.events = [line for line in subtitle
                           if line.text and "NETFLIX" not in line.text]
        subtitle.remove_miscellaneous_events()

        new_file_name = os.path.join(temp_dir, os.path.splitext(os.path.basename(subtitle_file))[0] + ".srt")
        subtitle.save(new_file_name)
        cleaned_paths.append(new_file_name)
        print(f"Saving cleaned subtitle to {new_file_name}")

    print("Finished cleaning subtitles.")
    return cleaned_paths, lambda: shutil.rmtree(temp_dir)


def analyze_subtitle_styles(subtitle_list: SubtitlePaths) -> Tuple[StyleCounts, StyleExamples]:
    """Analyze styles in subtitle files and collect examples."""
    styles_counts: Dict[str, int] = {}
    styles_examples: StyleExamples = {}

    for subtitle_file in subtitle_list:
        subtitle = pysubs2.load(subtitle_file)
        for line in subtitle:
            if any(tag in line.style for tag in TAGS_TO_IGNORE_AUTO):
                continue

            styles_counts[line.style] = styles_counts.get(line.style, 0) + 1
            if line.style not in styles_examples:
                styles_examples[line.style] = []
            if len(styles_examples[line.style]) < 5:
                styles_examples[line.style].append(line.text)

    return sorted(styles_counts.items(), key=lambda x: x[1], reverse=True), styles_examples


def get_styles_to_keep(sorted_styles: StyleCounts, styles_examples: StyleExamples) -> List[str]:
    """Get user input for styles to keep."""
    print("Found the following styles:")
    for i, (style, count) in enumerate(sorted_styles):
        print(f"[{i}] {count} times; {style}")
        for example in styles_examples[style]:
            print(f"\t\t\t{example}")

    user_input = input(
        "Choose tags to keep by index separated by space "
        "(e.g. 1 2 4). No input to keep all listed.\n> "
    ).strip()

    if not user_input:
        return [style for style, _ in sorted_styles]

    tag_indices = [int(idx) for idx in user_input.split()]
    return [sorted_styles[i][0] for i in tag_indices]


def clean_tags(subtitle_list: SubtitlePaths) -> Tuple[SubtitlePaths, CleanupFunction]:
    """Clean subtitle tags based on user selection."""
    temp_dir = tempfile.mkdtemp(prefix="cleaned_subtitles_")
    cleaned_paths: SubtitlePaths = []

    try:
        sorted_styles, styles_examples = analyze_subtitle_styles(subtitle_list)
        styles_to_keep = get_styles_to_keep(sorted_styles, styles_examples)

        for subtitle_file in subtitle_list:
            subtitle = pysubs2.load(subtitle_file)
            subtitle.events = [line for line in subtitle
                               if line.style in styles_to_keep]
            subtitle.remove_miscellaneous_events()

            cleaned_path = os.path.join(
                temp_dir,
                os.path.splitext(os.path.basename(subtitle_file))[0] + ".srt"
            )
            subtitle.save(cleaned_path)
            cleaned_paths.append(cleaned_path)
            print(f"Saved cleaned subtitle to {cleaned_path}")

        return cleaned_paths, lambda: shutil.rmtree(temp_dir)

    except Exception as e:
        print(f"Error during subtitle cleaning: {str(e)}", file=sys.stderr)
        raise
