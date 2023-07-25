import requests
import os

episodes_to_keep = 1
tvshows_directory = '/home/mafetri/media/tvshows'

delete_episodes_paths = []
new_episodes_ids = []

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

		# Gets the episodes of that season
		monitored_episodes = (requests.get('http://192.168.1.10:8989/api/v3/episode?seriesId=' + str(matching_id) +'&seasonNumber=' + episode['SeasonName'].split(" ")[1] + '&includeImages=false&apikey=92029b4236dd4099b5a8679cad32ce48')).json()
		
		# If the last episode of the season is not being monitored
		if monitored_episodes[len(monitored_episodes)-1]['monitored'] is False:
			# Gets the next episode unmonitored id
			for i in reversed(range(len(monitored_episodes))):
				if monitored_episodes[i]['monitored'] == True:
					next_episode = monitored_episodes[i + 1]['id']
					break
		else:
			# If it needs the next season
			monitored_episodes = (requests.get('http://192.168.1.10:8989/api/v3/episode?seriesId=' + str(matching_id) +'&seasonNumber=' + str(int(episode['SeasonName'].split(" ")[1]) + 1) + '&includeImages=false&apikey=92029b4236dd4099b5a8679cad32ce48')).json()
			# If the next season exists
			if len(monitored_episodes) > 0:
				# Gets the next episode unmonitored id
				for i in reversed(range(len(monitored_episodes))):
					if monitored_episodes[i]['monitored'] == True:
						next_episode = monitored_episodes[i + 1]['id']
						break
					elif i == 0:
						next_episode = monitored_episodes[0]['id']
			else:
				next_episode = -1

		# If there is another episode to monitor
		# if next_episode != -1:
		# 	# Sets to monitor
		# 	res = requests.put('http://192.168.1.10:8989/api/v3/episode/' + str(next_episode) + '?apikey=92029b4236dd4099b5a8679cad32ce48', json={
		# 		'monitored': True
		# 	})

		# 	# Searchs the episode
		# 	res = requests.post('http://192.168.1.10:8989/api/v3/command?apikey=92029b4236dd4099b5a8679cad32ce48', json={
		# 		"name": "MissingEpisodeSearch", 
		# 		"episodeId": next_episode
		# 	})

		# # Rescans the serie
		# res = requests.post('http://192.168.1.10:8989/api/v3/command?apikey=92029b4236dd4099b5a8679cad32ce48', json={
		# 		"name": "rescanSeries", 
		# 		"seriesId": matching_id 
		# 	})
		
for deleted_episode in delete_episodes_paths:
	print(deleted_episode)