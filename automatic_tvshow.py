import requests
import os

episodes_to_keep = 1
tvshows_directory = '/home/mafetri/media/tvshows'

delete_episodes_paths = []
next_monitored_episodes_ids = []

# Downloaded Episodes
episodes = (requests.get(
    "http://192.168.1.10:8096/Users/0236ee774a5c44018580d15d4180838c/Items?Recursive=true&includeItemTypes=Episode&api_key=0171e1eba0804248b1a1d17bb4a66d4a"
)).json()['Items']

# All tv shows of Sonarr
all_tvshows = (requests.get('http://192.168.1.10:8989/api/v3/series?includeSeasonImages=false&apikey=92029b4236dd4099b5a8679cad32ce48')).json()

# Create a dictionary to store SeriesName as keys and a list of episodes as values
series_episodes_dict = {}

# For Each Episode
for episode in episodes:
	series_name = episode["SeriesName"]
	if series_name not in series_episodes_dict:
		series_episodes_dict[series_name] = []
	series_episodes_dict[series_name].append(episode)

# Sort the episodes based on their SeasonName and IndexNumber
for series_name, episodes in series_episodes_dict.items():
	sorted_episodes = sorted(episodes, key=lambda x: (x["SeasonName"], x["IndexNumber"]))
	series_episodes_dict[series_name] = sorted_episodes

# Convert the dictionary to a list of objects with SeriesName and episodes array
tvshows = [{"SeriesName": series_name, "Episodes": episodes} for series_name, episodes in series_episodes_dict.items()]

# For each Serie downloaded
for serie in tvshows:
	deleted = 0

	# If there are more than one episode, deletes the played ones and keeps x number
	if len(serie['Episodes']) > 1:
		for i, episode in enumerate(serie['Episodes']):
			# If the episode was not played, skips
			if episode['UserData']['Played'] == False:
				continue
			
			# If the next episodes_to_keep hasn't been played, skips
			if i + episodes_to_keep < len(serie['Episodes']) and serie['Episodes'][i + episodes_to_keep]['UserData']['Played'] == False:
				continue

			# Gets the file name and path
			delete_episode_name = serie['SeriesName'] + " - S" + episode['SeasonName'].split(" ")[1].zfill(2) + 'E' + str(episode['IndexNumber']).zfill(2)
			delete_episode_directory = '/' + serie['SeriesName'] + '/' + episode['SeasonName']

			# Adds to delete all the coincidence files (so it deletes the subtitles too)
			files_in_directory = os.listdir(tvshows_directory + delete_episode_directory)
			for file_name in files_in_directory:
				if file_name.startswith(delete_episode_name):
					delete_episodes_paths.append(delete_episode_directory + '/' + file_name)
					deleted += 1

	# Monitor next unmonitored episode
	if deleted > 0:
		# Searchs the id of the tvshow
		matching_id = next((serie_sonarr["id"] for serie_sonarr in all_tvshows if serie_sonarr["title"] == serie['SeriesName']), None)

		season = int(episode['SeasonName'].split(" ")[1])
		next_episodes = []

		# While the next_episodes to monitor are not gratter or equal to the ammount deleted
		while len(next_episodes) < deleted:
			# Gets the episodes of the season
			monitored_episodes = (requests.get('http://192.168.1.10:8989/api/v3/episode?seriesId=' + str(matching_id) +'&seasonNumber=' + str(season) + '&includeImages=false&apikey=92029b4236dd4099b5a8679cad32ce48')).json()
			
			if len(monitored_episodes) > 0: 
				# Find the index of the last monitored episode of that season
				last_monitored_index = len(monitored_episodes) - 1
				while last_monitored_index >= 0 and not monitored_episodes[last_monitored_index]['monitored']:
					last_monitored_index -= 1

				# From the last episode monitored, saves the next 'deleted' number of episodes are not monitored in that season
				for i in range(last_monitored_index + 1, len(monitored_episodes)):
					if not monitored_episodes[i]['monitored']:
						next_episodes.append(monitored_episodes[i]['id'])
					if len(next_episodes) == deleted:
						break
				
				# Jumps to the next season
				season += 1
			else:
				break

		# Adds the next_episodes of this season to the total
		next_monitored_episodes_ids.extend(next_episodes)

# Monitors and Searchs for the new added episodes
for id in next_monitored_episodes_ids:
	# Sets to monitor
	res = requests.put('http://192.168.1.10:8989/api/v3/episode/' + str(id) + '?apikey=92029b4236dd4099b5a8679cad32ce48', json={
		'monitored': True
	})

	# Searchs the episode
	res = requests.post('http://192.168.1.10:8989/api/v3/command?apikey=92029b4236dd4099b5a8679cad32ce48', json={
		"name": "MissingEpisodeSearch", 
		"episodeId": id
	})

# Deletes the files
for path in delete_episodes_paths:
	os.remove(tvshows_directory + path)

# # Rescans the serie
# res = requests.post('http://192.168.1.10:8989/api/v3/command?apikey=92029b4236dd4099b5a8679cad32ce48', json={
# 		"name": "rescanSeries", 
# 		"seriesId": matching_id 
# 	})