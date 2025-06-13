import requests
import os

def download_file(url, save_directory):
    """
    Downloads a file from a given URL and saves it to a specified directory.

    Args:
        url (str): The URL of the file to download.
        save_directory (str): The local directory where the file should be saved.
    """
    # --- 1. Ensure the destination directory exists ---
    # The os.makedirs() function will create the directory if it doesn't exist.
    # The `exist_ok=True` argument prevents an error if the directory already exists.
    try:
        os.makedirs(save_directory, exist_ok=True)
    except OSError as e:
        print(f"Error creating directory {save_directory}: {e}")
        return

    # --- 2. Get the filename from the URL ---
    # We can split the URL by the '/' character and take the last part.
    if not url:
        print("Error: URL is empty.")
        return
        
    filename = url.split('/')[-1]
    full_path = os.path.join(save_directory, filename)

    # --- 3. Download the file and save it ---
    try:
        print(f"Downloading '{filename}' from {url}...")
        # Use requests.get() to fetch the file content
        response = requests.get(url, stream=True)
        
        # Raise an HTTPError if the HTTP request returned an unsuccessful status code
        response.raise_for_status()

        # Open the destination file in write-binary mode ('wb') and save the content
        with open(full_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192): 
                f.write(chunk)
        
        print(f"Successfully saved file to: {full_path}")

    except requests.exceptions.RequestException as e:
        # Handle potential network errors (e.g., DNS failure, refused connection)
        print(f"Error downloading the file: {e}")
    except Exception as e:
        # Handle other potential errors, like file writing permissions
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    # The URL of the file to download
    target_url = "https://cdnjs.cloudflare.com/ajax/libs/split.js/1.6.0/split.js"
    
    # The path to the directory where the file will be saved
    destination_folder = "/home/mike/repos/pipulate/static"
    
    # Call the function to perform the download
    download_file(target_url, destination_folder)