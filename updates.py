from picker import calc_weights
import requests
import json 
import pandas as pd
from datetime import datetime, timedelta

columns = ['chance_of_playing_next_round', 'chance_of_playing_this_round', 'code',
 'element_type', 'ep_next',
       'ep_this',  'first_name', 'form', 'id', 'in_dreamteam',
        'now_cost', 'points_per_game',
       'second_name', 'selected_by_percent', 
        'team', 'team_code', 'total_points', 'transfers_in',
        'transfers_out',
       'value_form', 'value_season', 'web_name',      
        'influence', 'creativity', 'threat',
       'ict_index']

def update_team(email, password, id):
    
    session = requests.session()

    players_df, fixtures_df, gameweek=get_data()

    data = {'login' : email, 'password' : password, 'app' : 'plfpl-web', 'redirect_uri' : 'https://fantasy.premierleague.com/'}
    login_url = "https://users.premierleague.com/accounts/login/"
    
    t=session.post(url=login_url, data=data)
    url = "https://fantasy.premierleague.com/api/my-team/" + str(id)
    team = session.get(url)
    team = json.loads(team.content)

    bank = team['transfers']['bank']

    players = [x['element'] for x in team['picks']]

    my_team = players_df.loc[players_df.id.isin(players)]
    potential_players = players_df.loc[~players_df.id.isin(players)]

    player_out = calc_out_weight(my_team)
    rows_to_drop=player_out.index.values.astype(int)[0]
    my_team=my_team.drop(rows_to_drop)

    position = player_out.element_type.iat[0]
    out_cost = player_out.now_cost.iat[0]
    budget = bank + out_cost
    dups_team = my_team.pivot_table(index=['team'], aggfunc='size')
    invalid_teams = dups_team.loc[dups_team==3].index.tolist()

    potential_players=potential_players.loc[~potential_players.team.isin(invalid_teams)]
    potential_players=potential_players.loc[potential_players.element_type==position]
    potential_players = potential_players.loc[potential_players.now_cost<=budget]

    player_in = calc_in_weights(potential_players, fixtures_df)
    my_team = my_team.append(player_in)
    my_team = calc_starting_weight(my_team)
    my_team =my_team.sort_values('weight', ascending=False)

    goalies = my_team.loc[my_team.element_type==1]


    outfied_players = my_team.loc[my_team.element_type!=1]

    captain = outfied_players.id.iat[0]
    vice_captain = outfied_players.id.iat[1]

    starters = goalies.head(1).append(outfied_players[:10])
    subs = goalies.tail(1).append(outfied_players[10:])

    headers = {'content-type': 'application/json', 'origin': 'https://fantasy.premierleague.com', 'referer': 'https://fantasy.premierleague.com/transfers'}
    transfers = [{"element_in" : int(player_in.id.iat[0]), "element_out" : int(player_out.id.iat[0]),"purchase_price": int(player_in.now_cost.iat[0]), "selling_price" : int(player_out.now_cost.iat[0])}]
    transfer_payload = { "transfers" : transfers,"chip" : None,"entry" : id,"event" : int(gameweek)}
    url = 'https://fantasy.premierleague.com/api/transfers/'
    print("Transferring Out: " + player_out.web_name.iat[0] + ", Transferring In: " + player_in.web_name.iat[0])
    print("Starters: " + str(starters.web_name.tolist()))
    print("Subs: " + str(subs.web_name.tolist()))
    t=session.post(url=url, data=json.dumps(transfer_payload), headers=headers)
    
    picks =[]
    count = 1
    for i in range(1,5):
        players = starters.loc[starters.element_type==i]
        ids = players.id.tolist()
        for ide in ids:
            if ide == captain:
                player = {"element" : ide, "is_captain" : True, "is_vice_captain" : False, "position" : count}
            elif ide == vice_captain:
                player = {"element" : ide, "is_captain" : False, "is_vice_captain" : True, "position" : count}
            else:
                player = {"element" : ide, "is_captain" : False, "is_vice_captain" : False, "position" : count}
            picks.append(player.copy())
            count+=1
    ids = subs.id.tolist()
    for ide in ids:
        player = {"element" : ide, "is_captain" : False, "is_vice_captain" : False, "position" : count}
        picks.append(player.copy())
        count+=1
    team_sheet = {"picks" : picks,"chip" : None}
    headers = {'content-type': 'application/json', 'origin': 'https://fantasy.premierleague.com', 'referer': 'https://fantasy.premierleague.com/my-team'}
    url = 'https://fantasy.premierleague.com/api/my-team/'+str(id) + '/'
    t=session.post(url=url, json=team_sheet,headers=headers)

def get_data():

    
    players =  get('https://fantasy.premierleague.com/api/bootstrap-static/')
    players_df = pd.DataFrame(players['elements'])
    teams_df = pd.DataFrame(players['teams'])
    fixtures_df = pd.DataFrame(players['events'])
    today = datetime.now().timestamp()
    fixtures_df = fixtures_df.loc[fixtures_df.deadline_time_epoch>today]
    # if check_update(fixtures_df) == False:
    #     print("Deadline Too Far Away")
    #     exit(0)
    gameweek =  fixtures_df.iloc[0].id
    players_df = players_df[columns]
    players_df.chance_of_playing_next_round = players_df.chance_of_playing_next_round.fillna(100.0)
    players_df.chance_of_playing_this_round = players_df.chance_of_playing_this_round.fillna(100.0)
    fixtures = get('https://fantasy.premierleague.com/api/fixtures/?event='+str(gameweek))
    fixtures_df = pd.DataFrame(fixtures)

    fixtures_df=fixtures_df.drop(columns=['id'])
    teams=dict(zip(teams_df.id, teams_df.name))
    players_df['team_name'] = players_df['team'].map(teams)
    fixtures_df['team_a_name'] = fixtures_df['team_a'].map(teams)
    fixtures_df['team_h_name'] = fixtures_df['team_h'].map(teams)

    home_strength=dict(zip(teams_df.id, teams_df.strength_overall_home))
    away_strength=dict(zip(teams_df.id, teams_df.strength_overall_home))

    fixtures_df['team_a_strength'] = fixtures_df['team_a'].map(away_strength)
    fixtures_df['team_h_strength'] = fixtures_df['team_h'].map(home_strength)

    a_players = pd.merge(players_df, fixtures_df, how="inner", left_on=["team"], right_on=["team_a"])
    h_players = pd.merge(players_df, fixtures_df, how="inner", left_on=["team"], right_on=["team_h"])

    a_players['diff'] = a_players['team_a_strength'] - a_players['team_h_strength']
    h_players['diff'] = h_players['team_h_strength'] - h_players['team_a_strength']

    players_df = a_players.append(h_players)
    return players_df, fixtures_df, gameweek
def get(url):
    response = requests.get(url)
    return json.loads(response.content)

def check_update(df):
    
    today = datetime.now()
    tomorrow=(today + timedelta(days=1)).timestamp()
    today = datetime.now().timestamp()
    df = df.loc[df.deadline_time_epoch>today]
    
    deadline = df.iloc[0].deadline_time_epoch
    if deadline<tomorrow:
        return True
    else:
        return False

def calc_in_weights(df, fixtures,mode="b"):
    df1 = pd.DataFrame(columns=df.columns.tolist())
    teams_playing = fixtures[["team_a", "team_h"]].values.ravel()
    teams_playing = pd.unique(teams_playing)
    teams_playing_twice = [x for x in teams_playing if list(teams_playing).count(x)>1]
    ps_not_playing = df.loc[~df.team.isin(teams_playing)]
    ps_playing_twice=df.loc[df.team.isin(teams_playing_twice)]
    for x in df.iterrows():
        
        weight = 0.1
        weight+= x[1]['diff']/5
        if mode == 'b':
            weight+= float(x[1]['points_per_game'])*4
        else:
            weight+= float(x[1]['form'])*4
        weight -= (100-float(x[1]['chance_of_playing_this_round'])) * 0.2
        weight -= (100-float(x[1]['chance_of_playing_next_round'])) * 0.2
        if weight < 0:
            weight = 0
        if x[1]['id'] in ps_not_playing['id']:
            weight+=5
        if x[1]['id'] in ps_playing_twice['id']:
            weight -=5
        
        if weight < 3:
            weight = 0
        x[1]['weight'] = weight
        df1 = df1.append(x[1])
    df1=df1.sort_values('weight', ascending=False).iloc[0:200]
    return df1.sample(1, weights=df1.weight)

def calc_out_weight(players):

    df1 = pd.DataFrame(columns=players.columns.tolist())

    for x in players.iterrows():
        weight = 20
        weight-= x[1]['diff']/5
        weight -= float(x[1]['form'])*5
        weight += (100-float(x[1]['chance_of_playing_this_round'])) * 0.2

        if weight < 0:
            weight = 0
        if x[1]['element_type'] == 1:
            weight == 0
        if weight < 0:
            weight = 0
        x[1]['weight'] = weight
        df1 = df1.append(x[1])
    return df1.sample(1, weights=df1.weight)

def calc_starting_weight(players):
    df1 = pd.DataFrame(columns=players.columns.tolist())

    for x in players.iterrows():
        weight = 0
        weight+= x[1]['diff']/5
        weight += float(x[1]['form'])*5
        weight -= (100-float(x[1]['chance_of_playing_this_round'])) * 0.2

        if weight < 0:
            weight = 0
        x[1]['weight'] = weight
        df1 = df1.append(x[1])
    return df1

def lambda_handler(event, context):
    email = "fwexnbhqowxfcdejdv@rffff.net"
    password = "password123"
    user_id = "6993864"
    update_team(email, password,user_id)
