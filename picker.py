import requests
import json
import pandas as pd

columns = ['chance_of_playing_next_round', 'chance_of_playing_this_round', 'code',
 'element_type', 'ep_next',
       'ep_this',  'first_name', 'form', 'id','now_cost', 'points_per_game',
       'second_name', 'selected_by_percent', 
        'team', 'team_code', 'total_points', 'transfers_in',
        'transfers_out',
       'value_form', 'value_season', 'web_name',      
        'influence', 'creativity', 'threat',
       'ict_index']

def get_data():
    players =  get('https://fantasy.premierleague.com/api/bootstrap-static/')
    players_df = pd.DataFrame(players['elements'])
    teams_df = pd.DataFrame(players['teams'])
    players_df = players_df[columns]
    players_df.chance_of_playing_next_round = players_df.chance_of_playing_next_round.fillna(100.0)
    players_df.chance_of_playing_this_round = players_df.chance_of_playing_this_round.fillna(100.0)
    fixtures = get('https://fantasy.premierleague.com/api/fixtures/?event=1')
    fixtures_df = pd.DataFrame(fixtures)

    teams=dict(zip(teams_df.id, teams_df.name))
    fixtures_df['team_a_name'] = fixtures_df['team_a'].map(teams)
    fixtures_df['team_h_name'] = fixtures_df['team_h'].map(teams)

    team_strength = dict(zip(teams_df.id, teams_df.strength))
    players_df['team_strength'] = players_df['team'].map(team_strength)
    df = calc_weights(players_df)
    flag = False
    while flag == False:
        team = pick_player(df, [], 1, num_of_players=2)
        team = team.append(pick_player(df, [], 2, num_of_players=5))
        team = team.append(pick_player(df, [], 3, num_of_players=5))
        team = team.append(pick_player(df, [], 4, num_of_players=3))
        flag=check_team(team)
    return team
    pass

def calc_weights(df):
    df1 = pd.DataFrame(columns=df.columns.tolist())
    for x in df.iterrows():
        
        weight = 1
        weight += x[1]['team_strength'] * 3
        weight+= float(x[1]['points_per_game'])*4
        weight -= (100-float(x[1]['chance_of_playing_this_round'])) * 0.2
        weight -= (100-float(x[1]['chance_of_playing_next_round'])) * 0.2

        if weight < 0:
            weight = 0
        x[1]['weight'] = weight
        df1 = df1.append(x[1])
    df1=df1.sort_values('weight', ascending=False).iloc[0:200]
    return df1
    pass

def pick_player(df, current_team, position, num_of_players=1):
    pos = df.loc[df.element_type==position]
    player = pos.sample(num_of_players, weights=pos.weight)
    player_names = player.web_name.tolist()
    if player_names in current_team:
        return False
    return player
    pass
def check_team(df):
    dups_team = df.pivot_table(index=['team'], aggfunc='size')
    if dups_team.max() > 3:
        return False
    if df.now_cost.sum() >1000:
        return False
    if df.now_cost.sum() <950:
        return False
    return True

def get(url):
    response = requests.get(url)
    return json.loads(response.content)

if __name__ == '__main__':
    get_data()