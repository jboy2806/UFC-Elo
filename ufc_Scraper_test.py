# This Python 3 environment comes with many helpful analytics libraries installed
# It is defined by the kaggle/python Docker image: https://github.com/kaggle/docker-python
# For example, here's several helpful packages to load

import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)

# Input data files are available in the read-only "../input/" directory
# For example, running this (by clicking run or pressing Shift+Enter) will list all files under the input directory

import os
for dirname, _, filenames in os.walk('/kaggle/input'):
    for filename in filenames:
        print(os.path.join(dirname, filename))

# You can write up to 20GB to the current directory (/kaggle/working/) that gets preserved as output when you create a version using "Save & Run All" 
# You can also write temporary files to /kaggle/temp/, but they won't be saved outside of the current session
# 
from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import pandas as pd
import numpy as np
import threading 
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)


lock = threading.Lock()

fight_details = []
new_fight_links_all = []
winner_names = []
fighter_detail_data = []


MAX_THREADS = 3 # change this to adjust the number of concurrent threads

ua = UserAgent()
chrome = ua.chrome

HEADER = {
    'User-Agent' : chrome
}



def create_session(): # Create a session with retry strategy
    """Create a requests session with retry strategy for handling network issues."""
    # This function sets up a session with a retry strategy to handle network issues. 
    
    session = requests.Session()
    retry_strat = Retry(
        backoff_factor=7, # Wait time between retries increases exponentially
        total=10, # Total number of retries
        status_forcelist= [429, 500, 502, 503, 504], # Retry on these status codes
        allowed_methods=['GET']
    )
    adapter = HTTPAdapter(max_retries= retry_strat)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

session = create_session()



ufc_link = "http://ufcstats.com/statistics/events/completed?page=all"

respone = session.get(ufc_link)

text = respone.text
soup = BeautifulSoup(text, 'lxml')

event_links_soup = soup.find_all('a', class_ = 'b-link b-link_style_black')

event_links = [link['href'] for link in event_links_soup] # Extracting href attributes from the links

print(len(event_links), "events found")
def get_event_data(item): # Function to scrape event data
    """Scrape event data from the given link."""
    idx, link = item
    link = link.strip()
    response = session.get(link, headers=HEADER, timeout= 15)
    response.raise_for_status()
    if (response.status_code == 200):
        soup = BeautifulSoup(response.text, 'lxml')
                
        event_id = link[-16:]
        date_loc_list = soup.find_all('li', 'b-list__box-list-item')
        date = date_loc_list[0].text.replace("Date:", "").strip()
        location = date_loc_list[1].text.replace("Location:", "").strip()
        fight_links = soup.find_all('tr', class_ = 'b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click')
        for i in fight_links:
            winner_name = None
            winner_id = None
            w_l_d = i.find('i', class_ = "b-flag__text").text
            fight_id = i['data-link'][-16:]
            # print(w_l_d)
            if w_l_d == "win":
                players = i.find('td', class_ = "b-fight-details__table-col l-page_align_left")
                players = players.find_all('a', class_= "b-link b-link_style_black")
                winner_name = players[0].text.strip()
                winner_id = players[0]['href'][-16:]
            # Making the data
            data_dic = {
                "event_id" : event_id,
                "fight_id" : fight_id,
                "date" : date,
                "location" : location,
                "winner" : winner_name,
                "winner_id" : winner_id
            }
            new_fight_links_all.append(i['data-link'])
            winner_names.append(data_dic)
        # print(f"Scrapped : {link}, {idx+1} / {len(event_links)}")
        idx += 1
    else:
        print("Could'nt retrive the link." + str(response.status_code))

with ThreadPoolExecutor(max_workers= MAX_THREADS) as executor:
    results = [executor.submit(get_event_data, item) for item in enumerate(event_links)]
    for r in results:
        r.result()

df_winner = pd.DataFrame(data=winner_names)
df_winner.to_csv("event_details.csv", index = False)
print(f"Successfully scrapped {len(df_winner)} event data.")
df_winner

def get_fight_data(item): # Function to scrape fight data
    """Scrape fight data from the given link."""
    idx, link = item
    link = link.strip()
    try:
        response = session.get(link, headers=HEADER, timeout=15)
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # event name
        event_name = soup.find('a', class_ = "b-link").text.strip()
        # event id
        event_id = soup.find('a', class_ = "b-link")['href'][-16:]
        # fight id
        fight_id = link[-16:]
        
        # fighter names
        fighter_nams = soup.find_all('a', class_ = 'b-link b-fight-details__person-link')
        r_name = fighter_nams[0].text.strip()
        b_name = fighter_nams[1].text.strip()
        
        # fighter ids
        r_id = fighter_nams[0]['href'].strip()[-16:]
        b_id = fighter_nams[1]['href'].strip()[-16:]
        
        # title fight & division
        division_info = soup.find('i', class_= 'b-fight-details__fight-title').text.lower()
        is_title_fight = 0
        if 'title' in division_info:
            is_title_fight = 1
        division_info = division_info.replace('ufc', "")
        division_info = division_info.replace("title", "")
        division_info = division_info.replace("bout", "").strip()
        
        # method
        method = soup.find('i', style = 'font-style: normal').text.strip()
        
        
        p_tag_with_fight_detail = soup.find('p', class_ = "b-fight-details__text")
        fight_details_list = p_tag_with_fight_detail.find_all('i', class_ = 'b-fight-details__text-item')
        # finish-round
        finish_round = int(fight_details_list[0].text.lower().replace("round:", "").strip())
        # match-time
        match_timestamp = fight_details_list[1].text.lower().replace("time:", "").strip()
        match_timestamp_splited = match_timestamp.split(":")
        match_time_sec = int(match_timestamp_splited[0]) * 60 + int(match_timestamp_splited[-1])
        # total-round
        total_rounds = fight_details_list[2].text.lower().replace("time format:", "").strip()
        if total_rounds == "No Time Limit".lower():
            total_rounds = None
        else :
            total_rounds = int(total_rounds[0])
        # referee
        referee = fight_details_list[3].text.replace("Referee:", "").strip()
        
        
        # totals, SIG. STR.
        tables = soup.find_all('table', style = "width: 745px")
        
        # TOTALS TABLE
        if len(tables) > 0:
            table1 = tables[0]
            td_1_list = table1.find_all('td', class_ = 'b-fight-details__table-col')
            # KD
            kd_players = td_1_list[1].text.split()
            r_kd, b_kd = int(kd_players[0]), int(kd_players[1])
            # sig. str.
            sig_str_players = td_1_list[2].text.split() 
            r_sig_str_landed = int(sig_str_players[0])
            r_sig_str_atmpted = int(sig_str_players[2])
            b_sig_str_landed = int(sig_str_players[3])
            b_sig_str_atmpted = int(sig_str_players[5])
            # sig_str_acc
            sig_str_acc = td_1_list[3].text.split() 
            r_sig_str_acc = int(sig_str_acc[0].replace("%", "")) if sig_str_acc[0] != "---" else None
            b_sig_str_acc = int(sig_str_acc[1].replace("%", "")) if sig_str_acc[1] != "---" else None
            # total-str
            total_str = td_1_list[4].text.split() 
            r_total_str_landed = int(total_str[0])
            r_total_str_atmpted = int(total_str[2])
            b_total_str_landed = int(total_str[3])
            b_total_str_atmpted = int(total_str[5])
            # total-str-acc
            r_total_str_acc, b_total_str_acc = None, None
            try:
                r_total_str_acc = int(round(r_total_str_landed / r_total_str_atmpted, 2) * 100)
            except:
                pass
            try:
                b_total_str_acc = int(round(b_total_str_landed / b_total_str_atmpted, 2) * 100)
            except:
                pass
            # TD
            td_players = td_1_list[5].text.split() 
            r_td_landed = int(td_players[0])
            r_td_atmpted = int(td_players[2])
            b_td_landed = int(td_players[3])
            b_td_atmpted = int(td_players[5])
            # td_acc
            td_acc = td_1_list[6].text.split() 
            r_td_acc = int(td_acc[0].replace("%", "")) if td_acc[0] != "---" else None
            b_td_acc = int(td_acc[1].replace("%", "")) if td_acc[1] != "---" else None
            # sub. att
            sub_att = td_1_list[7].text.split()
            r_sub_att, b_sub_att = int(sub_att[0]), int(sub_att[1])
            # rev
            rev = td_1_list[8].text.split()
            r_rev, b_rev = int(rev[0]), int(rev[1])
            # Ctrl
            ctrl = td_1_list[9].text.split()
            r_ctrl = ctrl[0].split(":")
            r_ctrl = int(r_ctrl[0]) * 60 + int(r_ctrl[1]) if r_ctrl[0] != '--' else None
            b_ctrl = ctrl[1].split(":")
            b_ctrl = int(b_ctrl[0]) * 60 + int(b_ctrl[1]) if b_ctrl[0] != '--' else None
            
            # SIG. STR. TABLE
            table2 = tables[1]
            td_2_list = table2.find_all('td', class_ = 'b-fight-details__table-col')
            
            # HEAD
            head_list = td_2_list[3].text.split() 
            r_head_landed = int(head_list[0])
            r_head_atmpted = int(head_list[2])
            b_head_landed = int(head_list[3])
            b_head_atmpted = int(head_list[5])
            # HEAD
            r_head_acc, b_head_acc = None, None
            try:
                r_head_acc = int(round(r_head_landed / r_head_atmpted, 2) * 100)
            except:
                pass
            try:
                b_head_acc = int(round(b_head_landed / b_head_atmpted, 2) * 100)
            except:
                pass
            
            # BODY
            body_list = td_2_list[4].text.split() 
            r_body_landed = int(body_list[0])
            r_body_atmpted = int(body_list[2])
            b_body_landed = int(body_list[3])
            b_body_atmpted = int(body_list[5])
            # BODY ACC
            r_body_acc, b_body_acc = None, None
            try:
                r_body_acc = int(round(r_body_landed / r_body_atmpted, 2) * 100)
            except:
                pass
            try:
                b_body_acc = int(round(b_body_landed / b_body_atmpted, 2) * 100)
            except:
                pass
            
            # LEG
            leg_list = td_2_list[5].text.split() 
            r_leg_landed = int(leg_list[0])
            r_leg_atmpted = int(leg_list[2])
            b_leg_landed = int(leg_list[3])
            b_leg_atmpted = int(leg_list[5])
            # LEG ACC
            r_leg_acc, b_leg_acc = None, None
            try:
                r_leg_acc = int(round(r_leg_landed / r_leg_atmpted, 2) * 100)
            except:
                pass
            try:
                b_leg_acc = int(round(b_leg_landed / b_leg_atmpted, 2) * 100)
            except:
                pass
            
            # DISTANCE
            dist_list = td_2_list[6].text.split() 
            r_dist_landed = int(dist_list[0])
            r_dist_atmpted = int(dist_list[2])
            b_dist_landed = int(dist_list[3])
            b_dist_atmpted = int(dist_list[5])
            # DIST ACC
            r_dist_acc, b_dist_acc = None, None
            try:
                r_dist_acc = int(round(r_dist_landed / r_dist_atmpted, 2) * 100)
            except:
                pass
            try:
                b_dist_acc = int(round(b_dist_landed / b_dist_atmpted, 2) * 100)
            except:
                pass
            
            # CLINCH
            clinch_list = td_2_list[7].text.split() 
            r_clinch_landed = int(clinch_list[0])
            r_clinch_atmpted = int(clinch_list[2])
            b_clinch_landed = int(clinch_list[3])
            b_clinch_atmpted = int(clinch_list[5])
            # CLINCH ACC
            r_clinch_acc, b_clinch_acc = None, None
            try:
                r_clinch_acc = int(round(r_clinch_landed / r_clinch_atmpted, 2) * 100)
            except:
                pass
            try:
                b_clinch_acc = int(round(b_clinch_landed / b_clinch_atmpted, 2) * 100)
            except:
                pass
            
            # Ground
            ground_list = td_2_list[8].text.split() 
            r_ground_landed = int(ground_list[0])
            r_ground_atmpted = int(ground_list[2])
            b_ground_landed = int(ground_list[3])
            b_ground_atmpted = int(ground_list[5])
            # Ground ACC
            r_ground_acc, b_ground_acc = None, None
            try:
                r_ground_acc = int(round(r_ground_landed / r_ground_atmpted, 2) * 100)
            except:
                pass
            try:
                b_ground_acc = int(round(b_ground_landed / b_ground_atmpted, 2) * 100)
            except:
                pass
        else:
            r_kd,b_kd = None, None
            r_sig_str_landed,b_sig_str_landed = None, None
            r_sig_str_atmpted,b_sig_str_atmpted = None, None
            r_sig_str_acc,b_sig_str_acc = None, None
            r_total_str_landed,b_total_str_landed = None, None
            r_total_str_atmpted,b_total_str_atmpted = None, None
            r_total_str_acc,b_total_str_acc = None, None
            r_td_landed,b_td_landed= None, None
            r_td_atmpted,b_td_atmpted = None, None
            r_td_acc,b_td_acc= None, None
            r_sub_att,b_sub_att= None, None
            r_ctrl,b_ctrl= None, None
            
            r_head_landed , b_head_landed = None, None
            r_head_atmpted , b_head_atmpted = None, None
            r_head_acc , b_head_acc = None, None
            r_body_landed , b_body_landed = None, None
            r_body_atmpted , b_body_atmpted = None, None
            r_body_acc , b_body_acc = None, None
            r_leg_landed , b_leg_landed = None, None
            r_leg_atmpted , b_leg_atmpted = None, None
            r_leg_acc , b_leg_acc = None, None
            r_dist_landed , b_dist_landed = None, None
            r_dist_atmpted , b_dist_atmpted = None, None
            r_dist_acc , b_dist_acc = None, None
            r_clinch_landed , b_clinch_landed = None, None
            r_clinch_atmpted , b_clinch_atmpted= None, None
            r_clinch_acc , b_clinch_acc = None, None
            r_ground_landed , b_ground_landed = None, None
            r_ground_atmpted , b_ground_atmpted = None, None
            r_ground_acc , b_ground_acc = None, None
            r_landed_head_per , b_landed_head_per = None, None
            r_landed_body_per , b_landed_body_per= None, None
            r_landed_leg_per , b_landed_leg_per = None, None
            r_landed_dist_per , b_landed_dist_per = None, None
            r_landed_clinch_per , b_landed_clinch_per = None, None
            r_landed_ground_per , b_landed_ground_per = None, None
        
        # LANDED-head&dist
        try:
            r_landed_head_and_dist_list = soup.find_all('i', class_= "b-fight-details__charts-num b-fight-details__charts-num_style_red b-fight-details__charts-num_pos_left js-red")
            r_landed_head_per = int(r_landed_head_and_dist_list[0].text.strip().replace("%", ""))
            r_landed_dist_per = int(r_landed_head_and_dist_list[1].text.strip().replace("%", ""))
            b_landed_head_and_dist_list = soup.find_all('i', class_= "b-fight-details__charts-num b-fight-details__charts-num_style_blue b-fight-details__charts-num_pos_right js-blue")
            b_landed_head_per = int(b_landed_head_and_dist_list[0].text.strip().replace("%", ""))
            b_landed_dist_per = int(b_landed_head_and_dist_list[1].text.strip().replace("%", ""))
        except:
            r_landed_head_per, r_landed_dist_per = None, None
            b_landed_head_per, b_landed_dist_per = None, None
        # LANDED-Body&Clinch
        try:
            r_landed_body_and_clinch_list = soup.find_all('i', class_= "b-fight-details__charts-num b-fight-details__charts-num_style_dark-red b-fight-details__charts-num_pos_left js-red")
            r_landed_body_per = int(r_landed_body_and_clinch_list[0].text.strip().replace("%", ""))
            r_landed_clinch_per = int(r_landed_body_and_clinch_list[1].text.strip().replace("%", ""))
            b_landed_body_and_clinch_list = soup.find_all('i', class_= "b-fight-details__charts-num b-fight-details__charts-num_style_dark-blue b-fight-details__charts-num_pos_right js-blue")
            b_landed_body_per = int(b_landed_body_and_clinch_list[0].text.strip().replace("%", ""))
            b_landed_clinch_per = int(b_landed_body_and_clinch_list[1].text.strip().replace("%", ""))
        except:
            r_landed_body_per, r_landed_clinch_per = None, None
            b_landed_body_per, b_landed_clinch_per = None, None
            
        # LANDED-leg&ground
        try:
            r_landed_leg_and_ground_list = soup.find_all('i', class_= "b-fight-details__charts-num b-fight-details__charts-num_style_light-red b-fight-details__charts-num_pos_left js-red")
            r_landed_leg_per = int(r_landed_leg_and_ground_list[0].text.strip().replace("%", ""))
            r_landed_ground_per = int(r_landed_leg_and_ground_list[1].text.strip().replace("%", ""))
            b_landed_leg_and_ground_list = soup.find_all('i', class_= "b-fight-details__charts-num b-fight-details__charts-num_style_light-blue b-fight-details__charts-num_pos_right js-blue")
            b_landed_leg_per = int(b_landed_leg_and_ground_list[0].text.strip().replace("%", ""))
            b_landed_ground_per = int(b_landed_leg_and_ground_list[1].text.strip().replace("%", ""))
        except:
            # pass
            r_landed_leg_per, r_landed_ground_per = None, None
            b_landed_leg_per, b_landed_ground_per = None, None
            
        # MAKING THE DATA
        data_dic = {
            "event_name" : event_name,
            "event_id" : event_id,
            "fight_id" : fight_id,
            "r_name" : r_name,
            "r_id" : r_id,
            "b_name" : b_name,
            "b_id" : b_id,
            "division" : division_info,
            "title_fight" : is_title_fight,
            "method" : method,
            "finish_round" : finish_round,
            "match_time_sec" : match_time_sec,
            "total_rounds" : total_rounds,
            "referee" : referee,
            "r_kd" : r_kd,
            "r_sig_str_landed" : r_sig_str_landed,
            "r_sig_str_atmpted" : r_sig_str_atmpted,
            "r_sig_str_acc" : r_sig_str_acc,
            "r_total_str_landed" : r_total_str_landed,
            "r_total_str_atmpted" : r_total_str_atmpted,
            "r_total_str_acc" : r_total_str_acc,
            "r_td_landed" : r_td_landed,
            "r_td_atmpted" : r_td_atmpted,
            "r_td_acc" : r_td_acc,
            "r_sub_att" : r_sub_att,
            "r_ctrl" : r_ctrl,
            "r_head_landed" : r_head_landed,
            "r_head_atmpted" : r_head_atmpted,
            "r_head_acc" : r_head_acc,
            "r_body_landed" : r_body_landed,
            "r_body_atmpted" : r_body_atmpted,
            "r_body_acc" : r_body_acc,
            "r_leg_landed" : r_leg_landed,
            "r_leg_atmpted" : r_leg_atmpted,
            "r_leg_acc" : r_leg_acc,
            "r_dist_landed" : r_dist_landed,
            "r_dist_atmpted" : r_dist_atmpted,
            "r_dist_acc" : r_dist_acc,
            "r_clinch_landed" : r_clinch_landed,
            "r_clinch_atmpted" : r_clinch_atmpted,
            "r_clinch_acc" : r_clinch_acc,
            "r_ground_landed" : r_ground_landed,
            "r_ground_atmpted" : r_ground_atmpted,
            "r_ground_acc" : r_ground_acc,
            "r_landed_head_per" : r_landed_head_per,
            "r_landed_body_per" : r_landed_body_per,
            "r_landed_leg_per" : r_landed_leg_per,
            "r_landed_dist_per" : r_landed_dist_per,
            "r_landed_clinch_per" : r_landed_clinch_per,
            "r_landed_ground_per" : r_landed_ground_per,
            "b_kd" : b_kd,
            "b_sig_str_landed" : b_sig_str_landed,
            "b_sig_str_atmpted" : b_sig_str_atmpted,
            "b_sig_str_acc" : b_sig_str_acc,
            "b_total_str_landed" : b_total_str_landed,
            "b_total_str_atmpted" : b_total_str_atmpted,
            "b_total_str_acc" : b_total_str_acc,
            "b_td_landed" : b_td_landed,
            "b_td_atmpted" : b_td_atmpted,
            "b_td_acc" : b_td_acc,
            "b_sub_att" : b_sub_att,
            "b_ctrl" : b_ctrl,
            "b_head_landed" : b_head_landed,
            "b_head_atmpted" : b_head_atmpted,
            "b_head_acc" : b_head_acc,
            "b_body_landed" : b_body_landed,
            "b_body_atmpted" : b_body_atmpted,
            "b_body_acc" : b_body_acc,
            "b_leg_landed" : b_leg_landed,
            "b_leg_atmpted" : b_leg_atmpted,
            "b_leg_acc" : b_leg_acc,
            "b_dist_landed" : b_dist_landed,
            "b_dist_atmpted" : b_dist_atmpted,
            "b_dist_acc" : b_dist_acc,
            "b_clinch_landed" : b_clinch_landed,
            "b_clinch_atmpted" : b_clinch_atmpted,
            "b_clinch_acc" : b_clinch_acc,
            "b_ground_landed" : b_ground_landed,
            "b_ground_atmpted" : b_ground_atmpted,
            "b_ground_acc" : b_ground_acc,
            "b_landed_head_per" : b_landed_head_per,
            "b_landed_body_per" : b_landed_body_per,
            "b_landed_leg_per" : b_landed_leg_per,
            "b_landed_dist_per" : b_landed_dist_per,
            "b_landed_clinch_per" : b_landed_clinch_per,
            "b_landed_ground_per" : b_landed_ground_per
        }
        with lock:
            fight_details.append(data_dic)
            # print(f"Scraped {idx+1}/{len(new_fight_links_all)}: {link}")
            idx += 1
    except requests.exceptions.RequestException as e:
        print(f"Failed {idx}/{new_fight_links_all}: {link} - {str(e)}")
        return

with ThreadPoolExecutor(max_workers= MAX_THREADS) as executor:
    results = [executor.submit(get_fight_data, item) for item in enumerate(new_fight_links_all)]
    for r in results:
        r.result()
        
print(f"Successfully scraped all fight data. Scrapped data {len(fight_details)}")


df_fight = pd.DataFrame(data=fight_details)
df_fight.to_csv("fight_details.csv", index = False)
df_fight


r_fighter_id = df_fight['r_id'].unique()
b_fighter_id = df_fight['b_id'].unique()
all_ids = list(set(list(r_fighter_id) + list(b_fighter_id))) # Combining both fighter ids and removing duplicates

base_url = "http://ufcstats.com/fighter-details/" # Base URL for fighter details
def get_fighter_data(item): # Function to scrape fighter data
    """Scrape fighter data from the given link."""
    try:
        idx, id = item
        response = session.get(base_url+id, headers= HEADER, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        
        # ID FOR MAPPING
        fighter_id = id
        
        # NAMES
        fighter_name = soup.find('span', class_ = 'b-content__title-highlight').text.strip()
        fighter_nick_name = soup.find('p', class_ = "b-content__Nickname").text.strip()
        
        # RECORD DETAILS
        fighter_record = soup.find('span', class_= "b-content__title-record").text.replace("Record:", "").strip().split('-')
        fighter_wins = int(fighter_record[0].split()[0])
        fighter_losses = int(fighter_record[1].split()[0])
        fighter_draws = int(fighter_record[2].split()[0])
        
        # Details
        detail_list = soup.find_all('li', class_ = "b-list__box-list-item b-list__box-list-item_type_block")
        
        try:
            height = detail_list[0].text.replace("Height:", "").strip().replace("'", "").replace('"', '').split()
            height = round((int(height[0]) * 12 + int(height[1])) * 2.54, 2)
            
        except:
            height = None
        
        try:
            weight = detail_list[1].text.replace("Weight:", "").strip().replace(" lbs", "")
            weight = round(float(weight) * 0.45359237, 2)
            
        except:
            weight = None
        
        try:
            reach = detail_list[2].text.replace("Reach:", "").strip().replace('"', "")
            reach = round(int(reach) * 2.54, 2)
        except:
            reach = None
            
        try:
            stance = detail_list[3].text.replace("STANCE:", "").strip()
            stance = stance if stance != "" else None
        except:
            stance = None
        
        try:
            dob = detail_list[4].text.replace("DOB:", "").strip()
            dob = dob if dob != "--" else None
        except:
            dob = None
            
        splm = float(detail_list[5].text.replace("SLpM:", "").strip())
        str_acc = int(detail_list[6].text.replace("Str. Acc.:", "").strip().replace("%", ""))
        sapm = float(detail_list[7].text.replace("SApM:", "").strip())
        str_def = int(detail_list[8].text.replace("Str. Def:", "").strip().replace("%", ""))
        td_avg = float(detail_list[10].text.replace("TD Avg.:", "").strip())
        td_acc = int(detail_list[11].text.replace("TD Acc.:", "").strip().replace("%", ""))
        td_def = int(detail_list[12].text.replace("TD Def.:", "").strip().replace("%", ""))
        sub_avg = float(detail_list[13].text.replace("Sub. Avg.:", "").strip())
        
        # Making The Data
        data_dic = {
            "id" : fighter_id,
            "name" : fighter_name,
            "nick_name" : fighter_nick_name,
            "wins" : fighter_wins,
            "losses" : fighter_losses,
            "draws" : fighter_draws,
            "height" : height,
            "weight" : weight,
            "reach" : reach,
            "stance" : stance,
            "dob" : dob,
            "splm" : splm,
            "str_acc" : str_acc,
            "sapm" : sapm,
            "str_def" : str_def,
            "td_avg" : td_avg,
            "td_avg_acc" : td_acc,
            "td_def" : td_def,
            "sub_avg" : sub_avg
        } 
        with lock:
            fighter_detail_data.append(data_dic)
            # print(f"Scrapped {base_url+id}. {idx+1}/{len(all_ids)}")
            idx += 1
    except:
        print(f"Cannot process the link {base_url+id}. Skipping this link.")
        return
    
with ThreadPoolExecutor(max_workers= MAX_THREADS) as executor:
    results = [executor.submit(get_fighter_data, item) for item in enumerate(all_ids)]
    for r in results:
        r.result()

df_fighter = pd.DataFrame(data= fighter_detail_data)
df_fighter.to_csv("fighter_details.csv", index = False)
print(f"Successfully Scrapped {len(df_fighter)}")



df_fighter


df_merger_winners = df_winner.drop(columns=['event_id']).copy() # Copying the winners data to merge later
df_fight = df_fight.merge(right=df_merger_winners, on='fight_id') # Merging the winners data with fight data

# SAME ROWS HAD DIFF MEANING SO CHANGED THE AVG DATA
df_fighter_renamed__r = df_fighter.add_prefix('r_').drop(columns=['r_name']) # Renaming the columns for red fighter
df_fighter_renamed__b = df_fighter.add_prefix('b_').drop(columns=['b_name']) # Renaming the columns for blue fighter

df_fight = df_fight.merge(right=df_fighter_renamed__r, on='r_id') # Merging the red fighter data
df_fight = df_fight.merge(right=df_fighter_renamed__b, on='b_id') # Merging the blue fighter data

cols = df_fight.columns

r_cols = [col for col in cols if col.startswith('r_')]
b_cols = [col for col in cols if col.startswith('b_')]  
fighter_cols = r_cols + b_cols

re_ordered_cols = [
    'event_id',
    'event_name',
    'date',
    'location',
    'fight_id',
    'division',
    'title_fight',
    'method',
    'finish_round',
    'match_time_sec',
    'total_rounds',
    'referee'
]
re_ordered_cols += r_cols + b_cols
re_ordered_cols += ['winner', 'winner_id']
df_fight = df_fight[re_ordered_cols]

# Converting date and dob to datetime format and then to string in the desired format
df_fight['date'] = pd.to_datetime(df_fight['date']).dt.strftime("%Y/%m/%d")

df_fight['r_dob'] = pd.to_datetime(df_fight['r_dob']).dt.strftime("%Y/%m/%d")
df_fight['b_dob'] = pd.to_datetime(df_fight['b_dob']).dt.strftime("%Y/%m/%d")

df_fight.to_csv("UFC.csv", index = False)
df_fight