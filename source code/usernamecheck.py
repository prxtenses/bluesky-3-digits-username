import requests
import itertools
import string
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, init

# Initialize colorama
init(autoreset=True)

# Global flag to stop the execution
stop_event = threading.Event()

def check_username(username):
    if stop_event.is_set():
        return None, None  # Stop execution if the stop_event is set

    url = f"https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle={username}.bsky.social"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"{Fore.RED}[-] Username '{username}' is not available.\n")
            return username, False  # Username is not available
        elif response.status_code == 400:
            print(f"{Fore.GREEN}[+] Username '{username}' is available!\n")
            return username, True  # Username is available
        else:
            print(f"{Fore.YELLOW}Received status code {response.status_code} for username '{username}'.\n")
            return username, False
    except requests.RequestException as e:
        print(f"{Fore.RED}An error occurred while checking username '{username}': {e}\n")
        return username, False

def generate_usernames(length=3):
    characters = string.ascii_lowercase
    for username_tuple in itertools.product(characters, repeat=length):
        yield ''.join(username_tuple)

def load_usernames(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return set(username for line in f for username in line.strip().split(','))
    return set()

def save_unavailable_usernames(file_path, usernames):
    with open(file_path, "a") as f:
        for i in range(0, len(usernames), 3):
            line = ','.join(usernames[i:i+3])
            f.write(f"{line}\n")

def save_available_username(file_path, username):
    with open(file_path, "a") as f:
        f.write(f"{username}\n")

def listen_for_close():
    input("Press Enter to stop...\n")
    stop_event.set()  # Set the stop_event to signal stopping

def main():
    # Start a thread to listen for the close input
    threading.Thread(target=listen_for_close, daemon=True).start()

    # Load previously checked usernames
    unavailable_usernames = load_usernames("unavailable_usernames.txt")
    available_usernames = load_usernames("available_usernames.txt")
    
    # Use ThreadPoolExecutor for concurrent username checking
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(check_username, username): username 
            for username in generate_usernames() 
            if username not in unavailable_usernames and username not in available_usernames
        }
        
        unavailable_usernames_batch = []
        for future in as_completed(futures):
            username, is_available = future.result()
            if stop_event.is_set():
                print(f"{Fore.YELLOW}Stopping execution...\n")
                break
            if is_available:
                available_usernames.add(username)
                save_available_username("available_usernames.txt", username)
                print(f"{Fore.GREEN}[+] Added available username: {username}\n")
            elif username is not None:
                unavailable_usernames.add(username)
                unavailable_usernames_batch.append(username)
                if len(unavailable_usernames_batch) >= 3:
                    save_unavailable_usernames("unavailable_usernames.txt", unavailable_usernames_batch)
                    unavailable_usernames_batch = []

        # Save any remaining usernames
        if unavailable_usernames_batch:
            save_unavailable_usernames("unavailable_usernames.txt", unavailable_usernames_batch)

    print("Execution completed.\n")

if __name__ == "__main__":
    main()
