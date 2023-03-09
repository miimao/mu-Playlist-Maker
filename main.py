import requests
import os
from time import sleep
from bs4 import BeautifulSoup
from datetime import date
from datetime import timedelta
import json
import pathlib
import tomllib
import sys
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
import googleapiclient.discovery
import googleapiclient.errors


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # running as an executable (aka frozen)
    run_dir = pathlib.Path(sys.executable).parent
else:
    # running live
    run_dir = pathlib.Path(__file__).parent

config_path = pathlib.Path.cwd() / run_dir / "config.toml"
with config_path.open(mode="rb") as fp:
    config = tomllib.load(fp)

print(f"Config File loaded: {config_path}")



def get_thread_ids_from_archive(datetime_object):
    print(f'URL: https://desuarchive.org/mu/search/start/{datetime_object}/end/{datetime_object + timedelta(days=+1)}/results/thread/')
    url = f'https://desuarchive.org/mu/search/start/{datetime_object}/end/{datetime_object + timedelta(days=+1)}/results/thread/'
    webpage = requests.get(url)
    thread_ids = []
    found_last_page = False
    page = 1
    last_thread_count = 0
    while found_last_page == False:
        os.system('clear')
        print(f"Gathering all ACTIVE /mu/ threads on the date of [{datetime_object}]\nCurrently on Page: {page}\nThreads Found: {len(thread_ids)}")
        soup = BeautifulSoup(webpage.text, "html.parser")

        for thread in (soup.find_all(name="article")):
            if thread.get('data-board') == "mu":
                thread_ids.append(thread.get('id'))
        if len(thread_ids) == last_thread_count:
            found_last_page = True
            print("Found all Threads!")
        else:
            page += 1
            # sleep(0)
            webpage = requests.get(url+f"page/{page}/")
            last_thread_count = len(thread_ids)
    return thread_ids

def get_links_from_threads(list_of_thread_URLs):
    found_urls = []
    for index, url in enumerate(list_of_thread_URLs):
        os.system('clear')
        print(f"Gathing links...\nThreads Scanned: {index}\nLinks Found: {len(found_urls)}")
        webpage = requests.get(url)
        soup = BeautifulSoup(webpage.text, "html.parser")
        text_posts = soup.find_all(name='a', attrs={'target':'_blank','rel':'nofollow'})
        for i in text_posts:
            found_urls.append(i.get("href"))
    return found_urls

# Function to extract the video ID from a YouTube video URL
def extract_video_id(url):
    match = re.search(r"(?<=v=)[a-zA-Z0-9_-]+(?=&|$)|(?<=be/)[a-zA-Z0-9_-]+(?=&|$)", url)
    if match:
        return match.group(0)
    else:
        return None

def create_playlist_spotify(name, description, public=True):
    # Replace with your own Spotify API credentials
    CLIENT_ID = config["SPOTIFYAPI"]["CLIENTID"]
    CLIENT_SECRET = config["SPOTIFYAPI"]["CLIENTSECRET"]
    REDIRECT_URI = config["SPOTIFYAPI"]["REDIRECT_URI"]
    
    # Set up a Spotify OAuth2 authentication flow
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                                   client_secret=CLIENT_SECRET,
                                                   redirect_uri=REDIRECT_URI,
                                                   scope="playlist-modify-private,playlist-modify-public"))
    
    # Create the playlist
    playlist = sp.user_playlist_create(user=sp.current_user()["id"],
                                        name=name,
                                        description=description,
                                        public=public)
    
    # Return the playlist ID
    return playlist["id"]

def populate_playlist_spotify(playlist_id, links):
    #Make a list of all the title of youtube video we 
    video_titles = []
    for url in links:
        youtube_video_id = extract_video_id(url)
        if youtube_video_id != None:
            request = youtube_client.videos().list(
                part="snippet",
                id=youtube_video_id
            )
            response = request.execute()
            try:
                video_titles.append(response["items"][0]["snippet"]["title"])
            except Exception as e:
                pass
                # print(e)
                # print("This usually indicates a dead link.")
    if config["APP"]["DEBUG"] == True: #Dump all the titles for Debug
        with open("video_titles.json", 'w') as f:
            json.dump(video_titles, f, indent=2)

    CLIENT_ID = config["SPOTIFYAPI"]["CLIENTID"]
    CLIENT_SECRET = config["SPOTIFYAPI"]["CLIENTSECRET"]
    REDIRECT_URI = config["SPOTIFYAPI"]["REDIRECT_URI"]
    
    # Set up a Spotify OAuth2 authentication flow
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                                   client_secret=CLIENT_SECRET,
                                                   redirect_uri=REDIRECT_URI,
                                                   scope="playlist-modify-private,playlist-modify-public"))
    # Search for each song and add its URI to a list
    track_uris = []
    for song in video_titles:
        result = sp.search(q=song, type="track")
        if result["tracks"]["items"]:
            track_uris.append(result["tracks"]["items"][0]["uri"])
        else:
            print(f"Could not find {song} on Spotify.")
    
    # Add the songs to the playlist in batches if the payload is too large
    max_batch_size = 100
    num_songs = len(track_uris)
    if num_songs <= max_batch_size:
        sp.playlist_add_items(playlist_id=playlist_id, items=track_uris)
        print(f"Added {num_songs} songs to the playlist!")
    else:
        num_batches = (num_songs + max_batch_size - 1) // max_batch_size
        for i in range(num_batches):
            start_idx = i * max_batch_size
            end_idx = min((i + 1) * max_batch_size, num_songs)
            batch_uris = track_uris[start_idx:end_idx]
            sp.playlist_add_items(playlist_id=playlist_id, items=batch_uris)
            print(f"Added songs {start_idx+1}-{end_idx} of {num_songs} to the playlist!")
    # # Add the tracks to the specified playlist
    # if track_uris:
    #     sp.playlist_add_items(playlist_id=playlist_id, items=track_uris)
    #     print(f"Added {len(track_uris)} songs to the playlist!")
    # else:
    #     print("No songs found on Spotify.")
    




youtube_client = googleapiclient.discovery.build("youtube", "v3", developerKey=config["YOUTUBEAPI"]["APIKEY"])
spotify_client = spotipy.oauth2.SpotifyOAuth(client_id=config["SPOTIFYAPI"]["CLIENTID"], client_secret=config["SPOTIFYAPI"]["CLIENTSECRET"], redirect_uri="http://fr1tz.fr/")

if __name__ == "__main__":
    #Check to see if we can skip finding links
    if config["APP"]["DEBUG"] == True and os.path.exists(run_dir / "debug_links.json") == True:
        with open(run_dir / "debug_links.json") as debug_links:
            file_contents = debug_links.read()
            debug_links = json.loads(file_contents)

    user_input_error = True
    while user_input_error == True and 'debug_links' not in globals():
        # Get a date from the user to search the 4chan /mu/ archive
        os.system('clear')
        # print(spotify_client.get_auth_response())
        print('''
        --- Fr1tZ' /mu/ Spotify Playlist Genereator ---

        Enter a date in the input section below to
        search the desuarchive.org /mu/ archive.
        The most reoccuring songs will be added to a
        spotify playlist for you to check out.

        Ex: 2018-03-26
        ''')
        if 'user_input_error_string' in globals():
            print(user_input_error_string)
        user_date_string = input("\nEnter Date: ")
        try:
            search_date_object = date.fromisoformat(user_date_string)
            user_input_error = False
        except Exception as e:
            user_input_error_string = e

    if 'debug_links' not in globals():
        threads = get_thread_ids_from_archive(search_date_object)
        for i in range(len(threads)): #Convert list of thread ids to usable URLs
            threads[i] = f"https://desuarchive.org/mu/thread/{threads[i]}"

        if config["APP"]["DEBUG"] == True: #Dump all the links for Debug
            with open("thread_links.json", 'w') as f:
                json.dump(threads, f, indent=2)

        links = get_links_from_threads(threads)
        if config["APP"]["DEBUG"] == True: #Dump all the links for Debug
            with open("urls_found.json", 'w') as f:
                json.dump(links, f, indent=2)
    else:
        links = debug_links
        search_date_object = date.today()
    user_input_error = True
    while user_input_error == True:
        #Ask user if they want a Spotify &/or YouTube Playlist.
        os.system('clear')
        print(f'''
        --- Fr1tZ' /mu/ Spotify Playlist Genereator ---

        We have found [{len(links)}] from the /mu/ 
        archive for the date of search_date_object.
        We are going to try and compile a list of songs
        based on the YouTube links in that list.

        You have the option of saving the generated
        Playlist to Spotify and/or YouTube. Spotify 
        Generally will do a better job of making sure 
        Your playlist is only filled with music but will
        miss more obsucure songs. Youtube will save them
        all but you may get some non-song videos.

        (current only spotify works)

        Ex: "spotify", "youtube", "both"
        ''')
        user_playlist_option_string = input("What playlist would you like?\n")

        match user_playlist_option_string.lower():
            case "spotify":
                user_input_error = False
                #Make an empty playlist in spotify and save the ID
                playlist_id = create_playlist_spotify(name=f"Fr1tZ /mu/ Playist Generator - {search_date_object}",
                                                      description="This playlist was made using Fr1tZ' /mu/ playlist generator. This tool will search the desuarchive.org /mu/ archive on a given date and make a playlist of every song its able to find. For more info please see (GITHUB LINK HERE!),")
                print(playlist_id)
                populate_playlist_spotify(playlist_id,links)
            case "youtube":
                user_input_error = False
                make_playlist_spotify("spotify", links)
            case "both":
                user_input_error = False
                make_playlist_spotify("spotify", links)



