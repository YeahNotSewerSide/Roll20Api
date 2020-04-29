import requests
import pickle
from bs4 import BeautifulSoup #pip install beautifulsoup4
import json
from time import time as timestamp
import socket
import websocket #pip install websocket-client
import ssl
import time
import random
import string
import threading


APP_URL = 'https://app.roll20.net'
MAIN_URL = 'https://roll20.net'
FIREBASE = 'wss://s-usc1c-nss-284.firebaseio.com/.ws?v=5&'
FIREBASE_ADDRESS = ('s-usc1c-nss-284.firebaseio.com',8080)





class api:
    def __init__(self,email=None,password=None,session_file=None):
        '''
        login data
        session_file - file with logined session/file were to save session
        '''
        self.session = requests.Session()
        self.session_file = session_file
        if session_file != None:
            self.session_file = session_file
            try:
                file = open(session_file,'rb')
                self.session.cookies.update(pickle.load(file))
                file.close()
                
            except:
                pass

        self.headers = {
                        'User-Agent':'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'
                        
                        }

        self.session.headers.update(self.headers)

        self.email = email
        self.password = password

        
    
    def dump_session(self):
        file = open(self.session_file,'wb')
        pickle.dump(self.session.cookies,file)
        file.close()

    def get_main_page(self):
        '''returns main page of site'''
        response = self.session.get(MAIN_URL+'/welcome')
        return response

    def login(self):
        '''True/False - Loged in/Nope'''
        headers = self.headers.update({'Content-Type':'application/x-www-form-urlencoded','Referer':'https://app.roll20.net/sessions/new'})
        data = {'email':self.email,'password':self.password}
        response = self.session.post(APP_URL+'/sessions/create',data=data,headers=headers)

        return response.text[10878:10901] == '<body class="loggedin">'


    def get_recent_games(self):
        '''
        doesnt return players and tags and info, only main info about game
        
        '''
        soup = BeautifulSoup(self.get_main_page().text,'html.parser')
        games = [] #Game type
        game_list = soup.find('div',attrs={'class':'col-md-8 homegamelist'}).find_all('div',attrs={'class':'listing'})
        for game_raw in game_list:
            image = game_raw.find('img').get('src')
            a_tag = game_raw.find('div',attrs={'class':'gameinfo'}).find('a')
            id = int(a_tag.get('href').split('/')[-1])
            name = a_tag.string           
            games.append(Game(name,id,image))

        return games

    def get_all_games(self,parse_tags=False):
        page = 1
        to_return = {'games':[]}
        if parse_tags:
            to_return['tags'] = {}
        while True: #Loop for pages
            soup = BeautifulSoup(self.session.get(APP_URL+f'/campaigns/search/?p={page}').text,'html.parser')
            campaigns = soup.find_all('tr',attrs={'class':'campaign'})
            if campaigns == []:
                break
            
            if parse_tags:
                for tag_sc in soup.find('div',attrs={'class':'campaigns'}).find_all('script'):
                    raw = tag_sc.string.split('=')[-1][1:-2]
                    if raw == '[]':
                        continue
                    tags_js = json.loads(raw)
                    to_return['tags'][tags_js[0]['campaign_id']] = {}
                    for tag in tags_js:
                        to_return['tags'][tag['campaign_id']].update({'id':tag['id'],'tag':tag['tag']})

            for campaign in campaigns:
                id = int(campaign.get('data-campaignid'))
                image = campaign.find('div',attrs={'class':'campaignthumb'}).find('img').get('src')
                name = campaign.find('div',attrs={'class':'campaigninfo'}).find('a').string[1:-1]
                players = []
                peeps = campaign.find('div',attrs={'class':'campaignpeeps'}).find_all('a')
                for peep in peeps:
                    players.append(Player(peep.img.get('title'),int(peep.get('href').split('/')[-1]),peep.img.get('src')))
                last = campaign.find('p',attrs={'class':'lastupdated'}).string.split(' ')[-1][:-1]
                to_return['games'].append(Game(name,id,image,Players=players,LastPlayed=last))

            page += 1

        return to_return


    def campaign(self,game):
        """
        game -> Game object
        """
        return Campaign(game,self.session)



    #def get_details(self,game): NOT READY!!!!!
    #    return None
    #    '''
    #    game - Game - object or id(int)
    #    if type(game) == Game -> game object will be changed
        
    #    if game - id(int) -> will be created new object
            
    #    if page not found -> return False
    #    '''
    #    id = 0
    #    if type(game) == int:
    #        id = game
    #        game = Game(None,None,None)
    #    elif type(game) == Game:
    #        id = game.ID
    #    else:
    #        raise Exception('get_details(game) - game must be id(int) or Game-object')

    #    page = self.session.get(APP_URL+f'/campaigns/details/{id}')
    #    soup = BeautifulSoup(page.text)
    #    if soup.find('div',attrs={'class':'conintro row'}) == None:
    #        return False

class Sentry:
    def __init__(self,dsn:str):
        self.dsn = dsn
        self.User = None

    def setUser(self,user):
        self.User = user


class d20ext:
    def __init__(self):
        self.s3base = None
        self.videotype = None
        self.webrtcSetup = {'ip':'',
                            'turn_user':'',
                            'turn_pw':''}
        pass
    
class Stack:
    def __init__(self,max_size=20):
        
        self.stack = [None]*max_size
        self.max_size = len(self.stack)
        self.CO = 1
        self.NP = 0

    def append(self,data):
        self.stack[self.NP] = data
        if self.NP == self.max_size -1:
            self.NP = 0
        else:
            self.NP += 1

        if self.CO < self.max_size:
            self.CO += 1

    def pop(self):
        if self.CO == 0:
            return None
        to_return = self.stack.pop(0)
        self.stack.append(None)
        self.CO -= 1
        self.NP -= 1
        return to_return
        




def start_websocket(campaign):   
    while not campaign._thread_receiver_stop:
        data = campaign.websocket.recv()
        try:
            p_data = json.loads(data)
        except:
            p_data = data
        campaign.packets.append(p_data)

        



def ping(campaign,timeout = 20):
    while not campaign._ping_thread_stop:
        campaign.websocket.send('0')
        time.sleep(timeout)
        


class Campaign:
    def __init__(self,game,session):
        """
        game -> Game object
        """
        if type(game) != Game:
            raise Exception(f'Campaign in __init__ expected {type(Game)} but got {type(game)}')
        self.game = game
        self.session = session
        self.Sentry = None
        self.FIREBASE_ROOT = None
        self.GNTKN = None
        self.RANDOM_ENTROPY = None
        self.d20ext = d20ext()
        self.campaign_id = None
        self.token_marker_array = None
        self.imgsrv_url = None
        self.campaign_storage_path = None
        self.d20_account_id = None
        self.d20_player_id = None
        self.d20_current_name = None
        self.gm = False
        self.websocket = None
        self._request_number = 1
        self._thread_receiver = None
        self._thread_receiver_stop = False
        self._ping_thread = None
        self._ping_thread_stop = False
        self.packets = Stack(30)
        self.players = {}
        

    def parse_config(self,data:str):#for launch with standart params
        commands = data[0:data.find('Object.defineProperty(window, "is_m')-2].replace('\n','').split(';')
        
        first_offset = commands[0].find(': "')+3
        url = commands[0][first_offset:commands[0].find('" ',first_offset)]
        self.Sentry = Sentry(url)

        first_offset = commands[1].find('(')+1
        user = json.loads(commands[1][first_offset:commands[1].find(')',first_offset)])
        self.Sentry.setUser(user)

        first_offset = commands[2].find('"')+1
        self.FIREBASE_ROOT = commands[2][first_offset:commands[2].find('"',first_offset)]

        first_offset = commands[3].find('"')+1
        self.GNTKN = commands[3][first_offset:commands[3].find('"',first_offset)]

        first_offset = commands[4].find('"')+1
        self.RANDOM_ENTROPY = commands[4][first_offset:commands[4].find('"',first_offset)]
        
        first_offset = commands[6].find('"')+1
        self.d20ext.s3base = commands[6][first_offset:commands[6].find('"',first_offset)]

        first_offset = commands[7].find('= ')+2
        self.campaign_id = int(commands[7][first_offset:])

        first_offset = commands[8].find('= ')+2
        self.token_marker_array = json.loads(commands[8][first_offset:])

        first_offset = commands[11].find('"')+1
        self.imgsrv_url = commands[11][first_offset:commands[11].find('"',first_offset)]

        first_offset = commands[12].find('"')+1
        self.d20ext.videotype = commands[12][first_offset:commands[12].find('"',first_offset)]

        first_offset = commands[13].find('"')+1#!!
        self.d20ext.webrtcSetup['ip'] = commands[13][first_offset:commands[13].find('"',first_offset)]

        first_offset = commands[14].find('"')+1
        self.d20ext.webrtcSetup['turn_user'] = commands[14][first_offset:commands[14].find('"',first_offset)]

        first_offset = commands[15].find('"')+1
        self.d20ext.webrtcSetup['turn_pw'] = commands[15][first_offset:commands[15].find('"',first_offset)]

        first_offset = commands[16].find('"')+1
        self.campaign_storage_path = commands[16][first_offset:commands[16].find('"',first_offset)]

        first_offset = commands[17].find('"')+1
        self.d20_account_id = int(commands[17][first_offset:commands[17].find('"',first_offset)])

        first_offset = commands[18].find('"')+1
        self.d20_player_id = commands[18][first_offset:commands[18].find('"',first_offset)]

        first_offset = commands[19].find('"')+1
        self.d20_current_name = commands[19][first_offset:commands[19].find('"',first_offset)]

        first_offset = commands[21].find(': ')+2
        self.gm = 'true' == commands[21][first_offset:commands[21].find(',',first_offset)]

        return None

    def get_request_number(self):
        self._request_number += 1
        return self._request_number-1

    def launch(self):
        """
        returns True/False
        """

        disablewebgl=False
        forcelongpolling=False
        offsite=False
        fbdebug=False
        forcetouch=False

        #setting campaign
        self.session.get(APP_URL+f'/editor/setcampaign/{self.game.ID}')       
        response = self.session.get(APP_URL+f'/editor/startjs/?timestamp={timestamp()}&disablewebgl={str(disablewebgl).lower()}&forcelongpolling={str(forcelongpolling).lower()}&offsite={str(offsite).lower()}&fbdebug={str(fbdebug).lower()}&forcetouch={str(forcetouch).lower()}')
        self.parse_config(response.text)


        #getting firebase for campaign
        response = self.session.get(self.FIREBASE_ROOT+f'/.lp?start=t&ser={random.randint(0,500000)}&cb=1&v=5').text
        offset = response.find('h":"')+4        
        FIREBASE = 'wss://'+response[offset:response.find('"',offset)] + '/.ws?v=5&'

        #Set websocket session
        
        self.websocket = websocket.create_connection(FIREBASE+f'ns={self.FIREBASE_ROOT[self.FIREBASE_ROOT.find("/")+2:self.FIREBASE_ROOT.find(".")]}')        
                        
        #Authenticate
        auth_data = '{"t":"d","d":{"r":'+str(self.get_request_number())+',"a":"auth","b":{"cred":"'+self.GNTKN+'"}}}'
        self.websocket.send(auth_data)
        data = self.websocket.recv()
        data = self.websocket.recv()
        p_data = json.loads(data)
        auth = p_data['d']['b']['s'] == 'ok'

        #Get players in campaign
        players_data = '{"t":"d","d":{"r":'+str(self.get_request_number())+',"a":"q","b":{"p":"/'+self.campaign_storage_path+'/players","h":""}}}'
        self.websocket.send(players_data)
        data = self.websocket.recv()
        p_data = json.loads(data)['d']['b']['d']
        for key,item in p_data.items():
            self.players[key] = item


        self._ping_thread = threading.Thread(target=ping,args=(self,),name='ping_thread')
        self._ping_thread.start()

        self._thread_receiver = threading.Thread(target=start_websocket,args=(self,),name='receive_thread')
        self._thread_receiver.start()
              
        return auth

    def close(self):
        self._ping_thread_stop = True
        self._thread_receiver_stop = True
        while self._ping_thread.is_alive():
            time.sleep(0.1)
        while self._thread_receiver.is_alive():
            time.sleep(0.1)
        self.websocket.close()

    def roll_dice_get(self,dice:int,sides:int,expr='str',resultType='sum',use3d=False,mods={}):
        '''
        DOESN'T ROLL DICE IN CAMPAIGN
        Just get response with data from server
        
        dice d sides + expr = dice-number
                              sides-sides
                              expr-modificator(+5/-2)
        Ex: mods = {"exploding":""}

        returns (roll_dice_get_data,signature,rollid)
        '''
        letters = string.ascii_lowercase+string.ascii_uppercase+string.digits+'-_'
        rollid = ''.join(random.sample(letters, 20))

        if expr == 0:
            data = {'cid':self.campaign_storage_path,
                    'fbnum':self.FIREBASE_ROOT,
                    'authkey':self.GNTKN,
                    'pid':self.d20_player_id,
                    'rolls':[{'vre':{
                                    'type':'V',
                                    'rolls':[{'type':'R',
                                              'dice':dice,
                                              'sides':sides,
                                              'mods':mods}
                                            ],
                                    'resultType':resultType
                                    },
                              'rollid':rollid,
                              'rolltype':"rollresult"
                              }],
                    'use3d':str(use3d).lower()
                    }
        else:
            data = {'cid':self.campaign_storage_path,
                    'fbnum':self.FIREBASE_ROOT,
                    'authkey':self.GNTKN,
                    'pid':self.d20_player_id,
                    'rolls':[{'vre':{
                                    'type':'V',
                                    'rolls':[{'type':'R',
                                              'dice':dice,
                                              'sides':sides,
                                              'mods':mods},
                                             {"type":"M",
                                              "expr":str(expr)}
                                            ],
                                    'resultType':resultType
                                    },
                              'rollid':rollid,
                              'rolltype':"rollresult"
                              }],
                    'use3d':str(use3d).lower()
                    }
       

        response = self.session.post(APP_URL+'/doroll',json=data).json()

        json_data = response[rollid]['json']

        signature = response[rollid]['signature']
        return (json_data,signature,rollid)

    def get_player_name(self):
        return self.players[self.d20_player_id]['displayname']

    def get_accountid_by_name(self,name:str)->int:
        '''
        works only for players in campaign
        returns accountid - id
        -1 not found
        '''
        id = 0
        for player in campaign.players.keys():
            if campaign.players[player]['displayname'] == name:
                id = int(campaign.players[player]['d20userid'])
                return id
        return -1


    def roll_dice_set(self,roll_dice_get_data,signature,rollid,origRoll:str,accountid=None,who=None):
        '''
        Ex: origRoll='5d20' just string to be written in chat
        '''
        if accountid == None:
            accountid = self.d20_account_id
        if who == None:
            who = self.get_player_name()
        
        data = {'t':'d',
                'd':{'r':self.get_request_number(),
                     'a':'p',
                     'b':{'p':'/'+self.campaign_storage_path+'/chat/'+rollid,
                          'd':{'avatar':f'/users/avatar/{accountid}/30',
                               'content':roll_dice_get_data,
                               'origRoll':origRoll,
                               'playerid':self.d20_player_id,
                               'signature':signature,
                               'type':'rollresult',
                               'who':who,
                               '.priority':{'.sv':'timestamp'}
                              }
                         }
                    }
                }

        self.websocket.send(json.dumps(data))

    def send_message(self,message:str,accountid=None,who=None):

        letters = string.ascii_lowercase+string.ascii_uppercase+string.digits+'-_'
        msgid = ''.join(random.sample(letters, 20))

        if accountid == None:
            accountid = self.d20_account_id
        if who == None:
            who = self.get_player_name()

        data = {'t':'d',
                'd':{'r':self.get_request_number(),
                     'a':'p',
                     'b':{'p':'/'+self.campaign_storage_path+'/chat/'+msgid,
                          'd':{'avatar':f'/users/avatar/{accountid}/30',
                               'content':message,
                               'playerid':self.d20_player_id,
                               'type':'general',
                               'who':who,
                               '.priority':{'.sv':'timestamp'}
                              }
                         }
                    }
                }

        self.websocket.send(json.dumps(data))

    

class Player:
    def __init__(self,Name,ID,image):
        self.Name = Name
        self.ID = ID
        self.Image = image

class Game:
    def __init__(self,Name,ID,image,Description=None,Players = None,LastPlayed = None):
        self.Name = Name
        self.ID = ID
        self.Image = image
        self.Description = Description
        self.Players = Players
        self.LastPlayed = LastPlayed
   






if __name__ == '__main__':
    ap = api(session_file='session.roll20') #CHECK class api!!! :24

    #main_page = ap.login() #IF SESSION DOESN'T EXIST

    games = ap.get_all_games(parse_tags=True)

    campaign = ap.campaign(games['games'][0])
    campaign.launch()
    name = 'Мидир'

    #ret = campaign.roll_dice_get(1,69,'+5')
    #campaign.roll_dice_set(ret[0],ret[1],ret[2],'1',5520898,who='1')
    #for i in range(1):
    
    #for player in campaign.players.keys():        
        #campaign.send_message('Party!',int(campaign.players[player]['d20userid']),who=campaign.players[player]['displayname'])
    campaign.send_message('!!',campaign.get_accountid_by_name(name),who=name)
    ap.dump_session()
    campaign.close()
    print(games)


