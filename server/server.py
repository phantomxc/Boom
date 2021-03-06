from txsockjs.factory import SockJSFactory
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.protocol import Factory, ClientFactory, Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, protocol

from player import Player
from bullet import Bullet

import time
import json
import sys
from random import randint

class WorldObjects(object):
    """
    A collection of all the objects that could be drawn
    """
    def __init__(self):
        self.object_list = []
    
    def add(self, obj):
        self.object_list.append(obj)

    def remove(self, obj):
        self.object_list.remove(obj)
        
    def update(self):
        for o in self.object_list:
            o.update()


class BoomProtocol(LineReceiver):

    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        print 'connection made'
        self.factory.addUser(self)

    def dataReceived(self, data):
        data = json.loads(data)
        self.factory.processData(data, self)

    def connectionLost(self, something):
        print 'connection lost'
        to_remove = None
        for u in self.factory.users:
            if u.boom == self:
                to_remove = u
       
        self.factory.removeUser(to_remove.pid)

        self.factory.users.remove(to_remove)
        

class GameFactory(Factory):

    def __init__(self, world):
        self.users = set()
        self.world = world

    @classmethod
    def currentTime(self):
        return int(round(time.time()*1000))

    def addUser(self, user):
        
        #random location
        rx = randint(10,500)
        ry = randint(10,500)
        p = Player(self.world, user, 300, 300)
        
        #send all the current players first
        p.boom.sendLine(json.dumps({"player_list":self.playerList()}))
        self.users.add(p)

        for u in self.users:
            if u.boom == user:
                u.boom.sendLine(json.dumps({'new_you':p.toJSON()}))
            else:
                u.boom.sendLine(json.dumps({'new_player':p.toJSON()}))

    def removeUser(self, pid):
        for u in self.users:
            u.boom.sendLine(json.dumps({'remove_player':pid}))
        

    def buildProtocol(self, addr):
        return BoomProtocol(self)

    def processData(self, data, boom):
        #print 'server'
        #print self.currentTime()
        for u in self.users:
            if u.boom == boom:
                u.processData(data)

    def broadcast(self):
        w.update()

        player_list = self.playerList()
        bullet_list = self.bulletList()
        new_bullets = self.newBullets()

        for u in self.users:
            u.boom.sendLine(json.dumps({
                "client_ts":u.last_ts,
                "server_ts":self.currentTime(),
                "user_info":u.toJSON(),
                "player_list":player_list,
                "bullet_list":bullet_list,
                "new_bullets":new_bullets
                })
            )

    def playerList(self):
        """
        Really returns a dict of {'playerid':player details}
        """
        player_list = {}
        for p in self.users:
            player_list[p.pid] = p.toObj()
        return player_list

    def bulletList(self):
        """
        A list of all the active bullets
        """
        bullet_list = []
        for p in self.users:
            for b in p.bullet_list:
                bullet_list.append(b.toObj())
        return bullet_list

    def newBullets(self):
        """
        A list of all the new bullets to be drawn
        """
        new_bullets = []
        for p in self.users:
            for b in p.new_bullets:
                new_bullets.append(b.toObj())
                b.broadcasted = True
        return new_bullets


w = WorldObjects()

f = GameFactory(w)
s = SockJSFactory(f)

#try to get the port specified, default to 8090
try:
    port = int(sys.argv[1])
except:
    port = 8090

reactor.listenTCP(port, s)

broadcast = LoopingCall(f.broadcast)
broadcast.start(0.1)

gameloop = LoopingCall(w.update)
gameloop.start(0.016666667)

reactor.run()



