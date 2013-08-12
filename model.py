from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey, Table, Text
from sqlalchemy.orm import relationship, backref

RESET=1

Base = declarative_base()
engine = create_engine('sqlite:///hitz.sqlite')
Base.metadata.create_all(engine)

class Hitter(Base):
	__tablename__='hitters'
	id = Column(Integer, primary_key=True)
	name = Column(String, unique=True)
	#teams = relationship("Team", backref="hitter")
	rating = Column(PickleType)
	lastGamePlayed = Column(DateTime)
	def __init__(self, name,lastGamePlayed = datetime.datetime(2013,7,1),rating = env.Rating()):
		self.name = name
		self.lastGamePlayed = lastGamePlayed
		self.rating = rating
	def score(self):
		return (self.rating.mu - 3.0*self.rating.sigma)

hitter_team_table = Table('hitter_team', Base.metadata,
	Column('team_id', Integer, ForeignKey('teams.id')),
	Column('hitter_id', Integer, ForeignKey('hitters.id'))

)

class Team(Base):
	__tablename__='teams'
	id = Column(Integer,primary_key=True)
	name=Column(String)
	teamrating = Column(PickleType)
	hitters = relationship("Hitter", secondary=hitter_team_table, backref='teams')

	def __init__(self):
		self.teamrating = env.Rating()

	def ratings(self):
        ratingslist=[]
        for player in self.hitters:
            ratingslist.append(player.rating)

        return tuple(ratingslist)
    def setdatelastplayed(self, datePlayed=datetime.datetime.today()):
        
        for player in self.hitters:
            if datePlayed > player.lastGamePlayed:
                player.lastGamePlayed =datePlayed
        
    def getdatelastplayed(self):
        comparedate=datetime.datetime.today()
        for player in self.hitters:
            if player.lastGamePlayed < comparedate:
                comparedate=player.lastGamePlayed
        return comparedate
		

class Game(Base):
	__tablename__='games'
	#hometeam = ManyToOne('Teams', inverse='homegames')
	hometeam = relationship("Team", backref=backref('homegames', order_by=id))
	hometeam_id = Column(Integer, ForeignKey('teams.id'))
	#awayteam = ManyToOne('Teams', inverse='awaygames')
	awayteam = relationship("Team", backref=backref('awaygames', order_by=id))
	awayteam_id = Column(Integer, ForeignKey('teams.id'))
	#winner = ManyToOne('Teams', inverse = 'winner')
	winner = relationship('Team', backref=backref('winninggames', order_by=id))
	winner_id = Column(Integer, ForeignKey('teams.id'))

	#date = Field(DateTime, default=datetime.datetime.now())
	date = Column(DateTime)
	#event = Field(UnicodeText)
	event = Column(String)
	#gameNumber = Field(Integer)
	gameNumber = Column(Integer)
	def __init__(self, hometeam, awayteam, winner, date = datetime.datetime.now() ):
		self.date = date
		self.hometeam = hometeam
		self.awayteam = awayteam
		self.winner = winner



def get_or_create(session, model, **kwargs):
	instance = session.query(model).filter_by(**kwargs).first()
	if instance:
		return instance
	else:
		instance = model(**kwargs)
		return instance
	# myHitter = get_or_create(session, Hitter, name=hitterName)
def get_or_create_team(session, findplayers):
	create_team = session.query(Team).filter(Team.players.any(Hitter.name=findplayers[0])).filter(Team.players.any(Hitter.name=findplayers[1])).filter(Team.players.any(Hitter.name=findplayers[2]))

	if not create_team:
		create_team = Team()
		for newplayer in findplayers:
			create_team.hitters.append(get_or_create(session,Hitter,name=newplayer))
		session.commit()
	return create_team

def getRecordsBelowSigma(sigma=SIGMA_CUTOFF):
    records = session.query(Hitters).all()
    recordsbelowsigma = []
    #for record in records:
        #print "-" * 20
        #print record.name
    
    for record in records:
        if record.rating.sigma < sigma:
            recordsbelowsigma.append(record)
    recordsbelowsigma.sort(key=lambda player: player.rating.score())
    return recordsbelowsigma

def getStrength(homeNames,awayNames):
    #
    # ({'name':'alice','rating':2.0},{'name':'bob','rating':1.4},{'name':'charlie','rating':3.2})
    #
    homeTeam=get_or_create_team(homeNames)
    awayTeam=get_or_create_team(awayNames)
    homeRatings = homeTeam.tupleratings()
    awayRatings = awayTeam.tupleratings()
    return env.quality([homeRatings,awayRatings])

def getLastPlayed(homeNames,awayNames):
    #
    # ({'name':'alice','rating':2.0},{'name':'bob','rating':1.4},{'name':'charlie','rating':3.2})
    #
    homeTeam=get_or_create_team(homeNames)
    awayTeam=get_or_create_team(awayNames)
    homeDate = homeTeam.getdatelastplayed()
    awayDate = awayTeam.getdatelastplayed()
    if homeDate<awayDate:
        return homeDate
    else:
        return awayDate

def completeGame(homeTeam,awayTeam,winner,datePlayed=datetime.datetime.today()):
    homers=get_or_create_team(homeTeam)
    awayers=get_or_create_team(awayTeam)
    homers.setdatelastplayed(datePlayed)
    awayers.setdatelastplayed(datePlayed)

    print "\n----------\n%s vs %s  " % (awayers, homers)
    
    if winner=='home':
        winningteam=get_or_create_team(homeTeam)
        #team rating
        homers.teamrating,awayers.teamrating = rate_1vs1(homers.teamrating, awayers.teamrating)
        #individual ratings
        (awayers.players[0].rating, awayers.players[1].rating, awayers.players[2].rating),(homers.players[0].rating, homers.players[1].rating, homers.players[2].rating) = rate([[awayers.players[0].rating, awayers.players[1].rating, awayers.players[2].rating],[homers.players[0].rating, homers.players[1].rating, homers.players[2].rating]], ranks=[1,0])
            
    else:
        winningteam=get_or_create_team(awayTeam)
        #team ratings
        awayers.teamrating,homers.teamrating = rate_1vs1(awayers.teamrating, homers.teamrating)
        #individual ratings
        (awayers.players[0].rating, awayers.players[1].rating, awayers.players[2].rating),(homers.players[0].rating, homers.players[1].rating, homers.players[2].rating) = rate([[awayers.players[0].rating, awayers.players[1].rating, awayers.players[2].rating],[homers.players[0].rating, homers.players[1].rating, homers.players[2].rating]], ranks=[0,1])
    newgame = Games(hometeam=homers, awayteam=awayers, winner=winningteam,date=datePlayed)
    session.commit()

def getPlayersForTemplate(checkedPlayers):
	players = session.query(Hitter).all()
	names = []
	#defined in matchups.py
	#defaultPlayers = ['Nick', 'Ziplox', 'Rosen', 'Magoo', 'Ced', 'White Rob', 'Adi']
	for player in players:
		if player.name in defaultPlayers:
			isChecked=True
		else:
			isChecked = False
		names.append({'name':player.name, 'isChecked': isChecked} )
	return names

if __name__ == "__main__":
    
    #setup_all()
    #create_all()
    hitters=[]
    players = ["Adi","Bader","Ced","Gio","James","Jeff","Jesse","Jon","Kent","Koplow","Magoo","Nick","Rosen","Sean","White Rob","Ziplox", 'Drew', 'Crabman'];
    for player in players:
        #Hitters.get_by_or_init(name=player)
        hitters.append(get_or_create(session, Hitter, name=player))
    session.commit()

    if RESET==1:
        games = [
        {'away':['Nick','Ziplox','Ced'],'home':['Rosen','Crabman','Magoo'],'winner':'away', 'date':datetime.datetime(2013,7,13)},
        {'away':['Rosen','Ced','Magoo'],'home':['Nick','Ziplox','Crabman'],'winner':'away', 'date':datetime.datetime(2013,7,13)}, 
        {'home':['Rosen','Ced','Magoo'],'away':['Nick','Ziplox','Crabman'],'winner':'home', 'date':datetime.datetime(2013,7,13)},
        {'away':['Ziplox','Magoo','Nick'],'home':['Ced','Crabman','Rosen'],'winner':'away', 'date':datetime.datetime(2013,7,13)},
        {'away':['Ziplox','Rosen','Ced'],'home':['Nick','Magoo','Crabman'],'winner':'away', 'date':datetime.datetime(2013,7,13)}, 
        {'home':['Ziplox','Rosen','Ced'],'away':['Nick','Magoo','Crabman'],'winner':'home', 'date':datetime.datetime(2013,7,13)},
        {'home':['Ziplox','Rosen','Ced'],'away':['Nick','Magoo','Crabman'],'winner':'home', 'date':datetime.datetime(2013,7,13)},
        {'away':['Magoo','Crabman','Rosen'],'home':['Ziplox','Ced','Nick'],'winner':'home', 'date':datetime.datetime(2013,7,13)},
        {'home':['Ziplox','Rosen','Adi'],'away':['Crabman','Drew','Rob'],'winner':'home', 'date':datetime.datetime(2013,7,27)},
        {'away':['Ziplox','Nick','Adi'],'home':['Crabman','Drew','Rob'],'winner':'away', 'date':datetime.datetime(2013,7,27)},
        {'away':['Rosen','Crabman','Rob'],'home':['Ziplox','Nick','Adi'],'winner':'home', 'date':datetime.datetime(2013,7,27)},
        {'away':['Rosen','Rob','Adi'],'home':['Ziplox','Nick','Drew'],'winner':'home', 'date':datetime.datetime(2013,7,27)},      
        {'away':['Rosen','Rob','Crabman'],'home':['Ziplox','Nick','Drew'],'winner':'home', 'date':datetime.datetime(2013,7,27)},
        {'away':['Drew','Adi','Crabman'],'home':['Rosen','Nick','Ziplox'],'winner':'away', 'date':datetime.datetime(2013,7,27)},
        {'away':['Nick','Rob','Rosen'],'home':['Drew','Adi','Crabman'],'winner':'home', 'date':datetime.datetime(2013,7,27)},
        {'away':['Ziplox','Rob','Rosen'],'home':['Drew','Adi','Crabman'],'winner':'away', 'date':datetime.datetime(2013,7,27)},
        {'away':['Rob','Drew','Adi'],'home':['Ziplox','Nick','Rosen'],'winner':'home', 'date':datetime.datetime(2013,7,27)},
        {'away':['Rob','Crabman','Adi'],'home':['Ziplox','Nick','Rosen'],'winner':'away', 'date':datetime.datetime(2013,7,27)},
        {'away':['Ziplox','Nick','Drew'],'home':['Rob','Adi','Crabman'],'winner':'home', 'date':datetime.datetime(2013,7,27)},              
        {'away':['Ziplox','Rosen','Drew'],'home':['Rob','Adi','Crabman'],'winner':'home', 'date':datetime.datetime(2013,7,27)},  
        #{'away':['','',''],'home':['','',''],'winner':''},    
        ]
        # Adding records
    
    
        for game in games:
            completeGame(game['home'],game['away'],game['winner'], game['date'])
            
            
            
            

    
        #thisgame = Games.get_by_or_init(hometeam=homers, awayteam=awayers, winner=game['winner'], date=datetime.datetime.now)
    # --------------------------------------------------
    # Simple Queries
 
    # get all the records
    #records = Hitters.query.filter(Hitters.rating.sigma<8.0).all()
    records = session.query(Hitter).all()
    recordsbelowsigma = []
    #for record in records:
        #print "-" * 20
        #print record.name
    records.sort(key=lambda player: player.rating.sigma)
    for record in records:
        if record.rating.sigma < 8.0:
            recordsbelowsigma.append(record)



    recordsbelowsigma.sort(key=lambda player: player.rating.mu)
    print "\n\n\n%s\n\n\n" % recordsbelowsigma
    allteams=session.query(Team).all()
    #for allteam in allteams:
        #print "-" * 20
        #print allteam.players
    allteams.sort(key=lambda team: team.teamrating.mu)
    print allteams
 
    # find a specific record

    qry = session.query(Hitters).filter_by(name=u'Nick')
    record = qry.first()
    print "%s" % (record.rating.sigma)
    #collectionOfGames= generateGamePermutations([i.name for i in recordsbelowsigma], 20)
    #cls()
    #print list(collectionOfGames)
    # delete the record
    #record.delete()
    #session.commit()