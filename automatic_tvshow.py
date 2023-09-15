import requests
import json
import os
from datetime import datetime

# Constants
JELLYFIN_URL = 'http://192.168.1.10:8096'
JELLYFIN_API_KEY = '4a891548d8aa4394bd1d038535bc2193'
JELLYFIN_USER_ID = '773576a4379945e7893b08ced4ff4df0'
SONARR_URL = 'http://192.168.1.10:8989'
SONARR_API_KEY = '92029b4236dd4099b5a8679cad32ce48'
EPISODES_TO_KEEP = 1
EPISODES_TO_NEXT_SEASON = 5
TVSHOWS_DIRECTORY = '/home/mafetri/media/tvshows'

# Variable Arrays
delete_episodes_paths = []
next_monitored_episodes_ids = []
next_monitored_season_jsons = []
changed_tvshows_ids = []

# Downloaded Episodes
episodes = (requests.get(
    JELLYFIN_URL + "/Users/" + JELLYFIN_USER_ID + "/Items?Recursive=true&includeItemTypes=Episode&api_key=" + JELLYFIN_API_KEY
)).json()['Items']

# All tv shows of Sonarr
all_tvshows = (requests.get(SONARR_URL + '/api/v3/series?includeSeasonImages=false&apikey=' + SONARR_API_KEY)).json()

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
			
			# If it is the only episode in the serie or the next EPISODES_TO_KEEP hasn't been played, skips
			if i + EPISODES_TO_KEEP < len(serie['Episodes']) and serie['Episodes'][i + EPISODES_TO_KEEP]['UserData']['Played'] == False:
				continue

			# Gets the file name and path
			delete_episode_name = serie['SeriesName'] + " - S" + episode['SeasonName'].split(" ")[1].zfill(2) + 'E' + str(episode['IndexNumber']).zfill(2)
			delete_episode_directory = '/' + serie['SeriesName'] + '/' + episode['SeasonName']
			deleted += 1

			# Adds to delete all the coincidence files (so it deletes the subtitles too)
			files_in_directory = os.listdir(TVSHOWS_DIRECTORY + delete_episode_directory)
			for file_name in files_in_directory:
				if file_name.startswith(delete_episode_name):
					delete_episodes_paths.append(delete_episode_directory + '/' + file_name)

	# Monitor next unmonitored episode
	if deleted > 0:
		# Searchs the tvshow
		serie_sonarr = next((serie_sonarr for serie_sonarr in all_tvshows if serie_sonarr["title"] == serie['SeriesName']), None)
		
		# Gets the id of the serie
		matching_id = serie_sonarr['id']

		# Gets the last episode watched season number
		season = int(episode['SeasonName'].split(" ")[1])

		# If the season of the last episode watched was monitored and there are only
		# EPISODES_TO_NEXT_SEASON episodes unseen, it monitors the next season
		if (len(serie_sonarr['seasons']) > season + 1) and (serie_sonarr['seasons'][season]['monitored']) and (serie_sonarr['seasons'][season]['statistics']['episodeCount'] - deleted < EPISODES_TO_NEXT_SEASON):
			serie_sonarr['seasons'][season+1]['monitored'] = True
			next_monitored_season_jsons.append(serie_sonarr)
		else:
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

		# Adds the ID of the tv show to refresh it
		changed_tvshows_ids.append(matching_id)

# For logs
print('------------↓ ' + str(datetime.now()) + ' ↓------------')

# Deletes the files
for path in delete_episodes_paths:
	print('Deleting: ' + path)
	os.remove(TVSHOWS_DIRECTORY + path)

# Monitors the new added episodes
for id in next_monitored_episodes_ids:
	# Sets to monitor
	res = requests.put('http://192.168.1.10:8989/api/v3/episode/' + str(id) + '?apikey=92029b4236dd4099b5a8679cad32ce48', json={
		'monitored': True
	})
	print('Monitor episode ' + str(id) + ': ' + 'Ok!' if res.status_code == 202 else 'Error!')

# Monitors the next seasons
for serie in next_monitored_season_jsons:
	body = json.dumps(serie)

	# Updates the serie data
	res = requests.put('http://192.168.1.10:8989/api/v3/series/' + str(serie['id']) + '?apikey=92029b4236dd4099b5a8679cad32ce48', body)
	print('Monitor next season of ' + serie['title'] + ': ' + 'Ok!' if res.status_code == 202 else 'Error!')

# Searches the missing episodes
res = requests.post('http://192.168.1.10:8989/api/v3/command?apikey=92029b4236dd4099b5a8679cad32ce48', json={
	"name": "MissingEpisodeSearch"
})
print('Searching all missing episodes: ' + 'Ok!' if res.status_code == 201 else 'Error!')


# Refresh all series
for id in changed_tvshows_ids:
	print('Refreshing Show ID ' + str(id) + ': ', end='')
	res = requests.post('http://192.168.1.10:8989/api/v3/command?apikey=92029b4236dd4099b5a8679cad32ce48', json={
		"name": "RefreshSeries", 
		'seriesId': id
	})
	print('Ok!' if res.status_code == 201 else 'Error!')

print('')
