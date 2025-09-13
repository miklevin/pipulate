# The file names containing the git history
active_file = 'history_active.txt'
lost_file = 'history_lost.txt'

try:
    # Read all lines from the first file into a set, stripping whitespace
    with open(active_file, 'r') as f:
        active_lines = {line.strip() for line in f}

    # Read all lines from the second file into a set
    with open(lost_file, 'r') as f:
        lost_lines = {line.strip() for line in f}

    # Find the lines that are in one set but not the other (symmetric difference)
    # unique_lines = active_lines.symmetric_difference(lost_lines)

    # Lost only
    unique_lines = lost_lines.difference(active_lines)

    if unique_lines:
        print("Commit history lines that are in one file but not the other:")
        # Sort the results for consistent output
        for line in sorted(list(unique_lines)):
            print(line)
    else:
        print("Both files contain the exact same commit history lines.")

except FileNotFoundError as e:
    print(f"Error: Could not find a file. Make sure '{e.filename}' is in the same directory.")
