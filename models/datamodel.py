#!/home/supplee/anaconda3/envs/flight-dispatch/bin/python

import pandas as pd
from PyQt5 import QtWidgets, QtCore
from haversine import haversine
from sqlalchemy import create_engine, Table, Column, ForeignKey
from sqlalchemy.orm import Session, aliased
from sqlalchemy.ext.automap import automap_base
from timezonefinder import TimezoneFinder
from pytz import timezone, utc
from datetime import datetime, timedelta

#from PyQt5 import QtWidgets
#from PyQt5.QtWidgets import QApplication, QMainWindow
#from dispatcher import Ui_MainWindow

## GLOBAL ORM CONSTRUCTION ##
def ORMConstruction():
    global Base, engine, session, Flight, Airport, Aircraft, Day
    Base = automap_base()
    engine = create_engine("sqlite:///models/data.db")
    Base.prepare(engine, reflect=True)
    session = Session(engine)

    Flight = Base.classes.flight
    Airport = Base.classes.airport
    Aircraft = Base.classes.aircraft
    Day = Base.classes.weekdays
#################################

class Itinerary:
    def __init__(self,df=None,file=''):
        if df == None:
            self.df = pd.DataFrame(columns=['SadEmptyDataFrame'])
        else:
            self.df = df
        self.file = ''
        

    def add(self,labels,data):
        if self.df.empty:
            self.df = pd.DataFrame([data],columns=labels)
        else:
            newdf = pd.DataFrame([data],columns=labels)
            self.df = pd.concat([self.df, newdf],sort=False)
        self.df = self.df.reset_index(drop=True)
        
    
    def remove(self,index):
        if self.df.empty:
            return 0
        else:
            if index > len(self.df.index):
                return 0
            else:
                self.df = self.df.drop(index)
                self.df = self.df.reset_index(drop=True)

    def save(self,file=None):
        if not file and not self.file:
            return 0 # No path specified; what are we, mind readers?
        if not file and self.file:
            file = self.file
        try:
            self.df.to_excel(file,index=False)
            self.file = file
            return 1
        except:
            return 0
    
    def open(self,file=None):
        try:
            self.df = pd.read_excel(file)
            self.file = file
            return 1
        except:
            return 0

    def model(self):
        return self.df
    

class ModelMetaData:
    def __init__(self):
        self.frenchDays = {
           "Samedi" : 5,
           "Dimanche" : 6,
           "Lundi" : 0,
           "Mardi" : 1,
           "Mercredi" : 2,
           "Jeudi" : 3,
           "Vendredi" : 4
        }

        self.dayIndex = { 
            "Sat" : 5,
            "Sun" : 6,
            "Mon" : 0,
            "Tue" : 1,
            "Wed" : 2,
            "Thu" : 3,
            "Fri" : 4,
            0 : "Mon",
            1 : "Tue",
            2 : "Wed",
            3 : "Thu",
            4 : "Fri",
            5 : "Sat",
            6 : "Sun"
        }

        self.pathByDBName = {
            "flights" : 'models/flights.parquet.gzip',
            "airports" : 'models/airportposition.parquet'
        }

class AirportQuery:
    """
    Class building a query to the airport database to get, for example, position -- which can then be used to calcualte 
    distance and time for each flight in the data frame.
    """
    def __init__(self,flightResults,dataFile='models/airportposition.parquet.gzip'):
        self.airportdf = pd.read_parquet(dataFile)
        self.flightResults = flightResults
        header = { 'ident' : [], 'latitude_deg': [], 'longitude_deg': [] }
        self.airports = pd.DataFrame(data=header)
        for a in flightResults['icao_dep'].unique():
            thisAirport = self.airportdf[self.airportdf['ident'] == a]
            thisAirport = thisAirport[['ident','latitude_deg','longitude_deg']]
            self.airports = self.airports.append(thisAirport)
        for a in flightResults['icao_arr'].unique():
            thisAirport = self.airportdf[self.airportdf['ident'] == a]
            thisAirport = thisAirport[['ident','latitude_deg','longitude_deg']]
            self.airports = self.airports.append(thisAirport)
        self.airports = self.airports.reset_index(drop = True)
    
    def select(self):
        return self.airports
    
    def calculateDistance(self,icao_dep,icao_arr):
        airport1 = 'placeholder'
        #print("Location of departing airport: "+ str(lat1) + " " + str(lon1))
        
       

##
# Database entries were initially cleaned with the following:
##
#flightdb.drop(columns='id',inplace=True)
#flightdb=flightdb.assign(id = lambda x: flightdb.index)
#flightdb=flightdb.assign(weekdayId = lambda x : flightdb.day.map(frenchDays))
#flightdb.drop(columns='day',inplace=True)

class Results:
    def __init__(self,dataframe):
        self.df = dataframe.copy()
        #self.df = self.df.assign(distance = lambda x: haversine((x.icao_dep_latitude,x.icao_dep_longitude),(x.icao_arr_latitude,x.icao_arr_longitude),unit='nmi'))

        # (1) Calculate the haversine distance between origin and destination
        # (2) And, using GPS coordinates, look up the time zone offset on arrival!
        distances = []
        tzO = [] # List of timezones at origin airport(s)
        tzD = [] # List of timezone names at arrival airport(s)

        for r in self.df[['icao_dep_latitude','icao_dep_longitude','icao_arr_latitude','icao_arr_longitude']].itertuples(index=False):
            (lat1,lon1,lat2,lon2) = r
            tf = TimezoneFinder()
            dist = haversine((lat1,lon1),(lat2,lon2),unit='nmi')
            dist = int(dist)
            distances.append(dist)
            try:
                tzO_name = timezone(tf.closest_timezone_at(lat=lat1,lng=lon1))
            except:
                tzD_name = timezone(tf.closest_timezone_at(lat=lat2,lng=lon2))
                tzO_name = tzD_name
            
            try:
                tzD_name = timezone(tf.closest_timezone_at(lat=lat2,lng=lon2))
            except:
                tzD_name = tzO_name

            tzO.append(tzO_name)
            tzD.append(tzD_name)
            

        self.df = self.df.assign(distance = distances)
        self.df = self.df.assign(tzo = tzO) # hh:mm time zone difference
        self.df = self.df.assign(tzd = tzD) # time zone difference in minutes (as float)

        # Calculate the time en route based on aircraft climb/cruise speeds
        # and haversine distance
        #
        # Also, the estimated arrival time!
        ete = []
        arrivaltimes = []
        arrivaldays = []
        arrivaldisplay = []
        for i,r in self.df.iterrows():
            dist = float(r.distance)
            speed1 = float(r.speed1)
            speed2 = float(r.speed2)
            #offset = float(r.offset)
            
            if dist < 80:
                enroute = dist/speed1*60.0
                minutes = enroute % 60
                hours = int(enroute/60)
                minutes = int(minutes)
                hours = int(enroute/60)   
            else:
                enroute1 = 80.0/speed1*60.0
                enroute2 = (dist-80.0)/speed2*60.0
                enroute = enroute1 + enroute2
                minutes = enroute % 60
                minutes = int(minutes)
                hours = int(enroute/60)
            ete.append('{:02d}'.format(hours)+':'+'{:02d}'.format(minutes))

            # Calculate arrival time
            metadata = ModelMetaData()
            depstring = str(r.weekdayid)+' '+r.departing
            timeObject = datetime.strptime(depstring,'%w %H:%M')
            timeObject = timezone(str(r.tzo)).localize(timeObject)
            timeObject = timeObject + timedelta(minutes=enroute+20)
            arrivalObject = timeObject.astimezone(timezone(str(r.tzd)))
            arrivalDay = int(arrivalObject.strftime('%w'))
            arrivalDay -= 1
            arrivalDay = (int(r.weekdayid) + arrivalDay) % 7
            arrivaldays.append(arrivalDay)
            arrivaltimes.append(arrivalObject.strftime('%H:%M'))
            arrivaldisplay.append(metadata.dayIndex[arrivalDay]+' '+arrivalObject.strftime('%H:%M'))
            
        self.df = self.df.assign(duration = ete)
        self.df = self.df.assign(arrivalday = arrivaldays)
        self.df = self.df.assign(arrivaltime = arrivaltimes)
        self.df = self.df.assign(arriving = arrivaldisplay)


    def displayTable(self):
        tableView = self.df[['callsign','airline','aircraft','icao_dep','icao_arr','departing','weekdayid','duration','arriving']].copy()
        #tableView = tableView[['callsign','airline','aircraft','icao_dep','icao_arr']]
        tableView.columns = ['Flight', 'Airline', 'Aircraft', 'Origin', 'Destination','DepartureTime','weekdayid','ETE','Arriving']
        metadata = ModelMetaData()
        tableView = tableView.assign(Day = lambda x: x.weekdayid.map(metadata.dayIndex))
        tableView = tableView.assign(Departing = lambda x: x.Day+' '+x.DepartureTime)
        #tableView=tableView.drop('weekdayId',axis=1)
        tableView = tableView[['Flight', 'Airline', 'Aircraft', 'Origin', 'Departing','Destination','Arriving','ETE']]
        return tableView


class FlightQuery:
    def __init__(self,airline='%',icao_dep='%',icao_arr='%',aircraft='%',departing='%',callsign='%',tailnum='%',weekdayId=range(0,7)):
        self.airline = airline
        self.icao_dep = icao_dep
        self.icao_arr = icao_arr
        self.aircraft = aircraft
        self.departing = departing
        self.callsign = callsign
        self.tailnum = tailnum
        self.weekdayId = weekdayId
        origin = aliased(Airport)
        destination = aliased(Airport)
        self.sqlQuery = session.query(Flight, Aircraft.climb2.label('speed1'), \
        Aircraft.cruise.label('speed2'), origin.latitude_deg.label('icao_dep_latitude'), \
        origin.longitude_deg.label('icao_dep_longitude'), destination.latitude_deg.label('icao_arr_latitude'), \
        destination.longitude_deg.label('icao_arr_longitude'))\
        .filter(Flight.icao_dep==origin.ident)\
        .filter(Flight.icao_arr==destination.ident)\
        .filter(Flight.aircraft==Aircraft.name)\
        .filter(Flight.icao_dep.like(self.icao_dep))\
        .filter(Flight.icao_arr.like(self.icao_arr))\
        .filter(Flight.aircraft.like(self.aircraft))\
        .filter(Flight.airline.like(self.airline))\
        .filter(Flight.weekdayid.in_(self.weekdayId))
    
    def flush(self,method='sql'):
        #test1 = session.query(Flight).filter(Flight.icao_dep.like('KLAX'),Flight.weekdayid == 2).order_by(Flight.callsign) 
        if method == 'sql':
            self.airline = self.airline.replace('.*','%')
            self.icao_dep = self.icao_dep.replace('.*','%')
            self.icao_arr = self.icao_arr.replace('.*','%')
            self.aircraft = self.aircraft.replace('.*','%')
            self.departing = self.departing.replace('.*','%')
            self.callsign = self.callsign.replace('.*','%')
            self.tailnum = self.tailnum.replace('.*','%')

            results = pd.read_sql(self.sqlQuery.statement,session.bind)
            self.df = results
            newResult = Results(self.df.copy())
            
            return newResult
        if method == 'nosql':
            self.airline = self.airline.replace('%','.*')
            self.icao_dep = self.icao_dep.replace('%','.*')
            self.icao_arr = self.icao_arr.replace('%','.*')
            self.aircraft = self.aircraft.replace('%','.*')
            self.departing = self.departing.replace('%','.*')
            self.callsign = self.callsign.replace('%','.*')
            self.tailnum = self.tailnum.replace('%','.*')

            metadata = ModelMetaData()
            results = pd.read_parquet(metadata.pathByDBName['flights'])
            self.df = results
            self._select_nosql()
            return self.df
    
    def _select_nosql(self):
        self.df = self.df[self.df.airline.str.contains(self.airline, regex=True, na=False)]
        self.df = self.df[self.df.icao_dep.str.contains(self.icao_dep, regex=True, na=False)]
        self.df = self.df[self.df.icao_arr.str.contains(self.icao_arr, regex=True, na=False)]
        self.df = self.df[self.df.aircraft.str.contains(self.aircraft, regex=True, na=False)]
        self.df = self.df[self.df.departing.str.contains(self.departing, regex=True, na=False)]
        self.df = self.df[self.df.callsign.str.contains(self.callsign, regex=True, na=False)]
        self.df = self.df[self.df.tailnum.str.contains(self.tailnum, regex=True, na=False)]
        self.df = self.df[self.df.weekdayId.isin(self.weekdayId)]
        self.df = self.df.drop('id',axis=1)
        dataTypes = ModelMetaData()
        self.df = self.df.assign(weekday = lambda x: x.weekdayId.map(dataTypes.dayIndex))
        #self.df.drop('weekdayId',axis=1,inplace=True)
        self.df = self.df.reindex(columns=['callsign','airline','icao_dep','icao_arr','weekday','weekdayId','departing','aircraft','tailnum'])
'''
class FlightQuery:
    def __init__(self,dataFile,airline='.*',icao_dep='.*',icao_arr='.*',aircraft='.*',departing='.*',callsign='.*',tailnum='.*',weekdayId=range(0,7)):
        self.df = pd.read_parquet(dataFile)
        self.airline = airline
        self.icao_dep = icao_dep
        self.icao_arr = icao_arr
        self.aircraft = aircraft
        self.departing = departing
        self.callsign = callsign
        self.tailnum = tailnum
        self.weekdayId = weekdayId

    def select_nosql(self):
        self.df = self.df[self.df.airline.str.contains(self.airline, regex=True, na=False)]
        self.df = self.df[self.df.icao_dep.str.contains(self.icao_dep, regex=True, na=False)]
        self.df = self.df[self.df.icao_arr.str.contains(self.icao_arr, regex=True, na=False)]
        self.df = self.df[self.df.aircraft.str.contains(self.aircraft, regex=True, na=False)]
        self.df = self.df[self.df.departing.str.contains(self.departing, regex=True, na=False)]
        self.df = self.df[self.df.callsign.str.contains(self.callsign, regex=True, na=False)]
        self.df = self.df[self.df.tailnum.str.contains(self.tailnum, regex=True, na=False)]
        self.df = self.df[self.df.weekdayId.isin(self.weekdayId)]
        self.df = self.df.drop('id',axis=1)
        dataTypes = FlightData()
        self.df = self.df.assign(weekday = lambda x: x.weekdayId.map(dataTypes.dayIndex))
        self.df.drop('weekdayId',axis=1,inplace=True)
        self.df = self.df.reindex(columns=['callsign','airline','icao_dep','icao_arr','weekday','departing','aircraft','tailnum'])
        self.calculateETE()

        return self.df
    
    def calculateETE(self):
        query = AirportQuery(self.df)
        airportData = query.select()
        trips = self.df[['icao_dep','icao_arr','aircraft']]

        for f in trips.itertuples(index=False):
            (ap1, ap2, ac) = f
            apd1 = airportData[airportData['ident'] == ap1]
            apd2 = airportData[airportData['ident'] == ap2]
            try:
                lat1 = float(apd1.latitude_deg)
                lon1 = float(apd1.longitude_deg)
                lat2 = float(apd2.latitude_deg)
                lon2 = float(apd2.longitude_deg)
                distance = int(haversine((lat1,lon1),(lat2,lon2),unit='nmi'))
            except:
                # This will only fail if one or both of the airports is not in our database of airport by GPS coordinate
                distance = 0
            print (ap1 + " " + ap2 + " " + ": approx " + str(distance) + " ("+ac+")")
                
            
            #print(ap1.ident + " " + ap2.ident + " " + " Distance: " + distance)
'''
#class Aircraft(Base):
#    __tablename__ = 'aircraft'


if __name__ == "__main__":
    import sys
    import os

    Base = automap_base()
    engine = create_engine("sqlite:///data.db")
    Base.prepare(engine, reflect=True)
    session = Session(engine)
 
    Flight = Base.classes.flight
    Airport = Base.classes.airport
    Aircraft = Base.classes.aircraft
    Day = Base.classes.weekdays

    #test1 = session.query(Flight).filter(Flight.icao_dep.like('KLAX'),Flight.weekdayid == 2).order_by(Flight.callsign) 
    #origin = aliased(Airport)
    #destination = aliased(Airport)
    #test1 = session.query(Flight, Aircraft.climb2.label('speed1'), \
    #    Aircraft.cruise.label('speed2'), origin.latitude_deg.label('icao_dep_latitude'), \
    #    origin.longitude_deg.label('icao_dep_longitude'), destination.latitude_deg.label('icao_arr_latitude'), \
    #    destination.longitude_deg.label('icao_arr_longitude'))\
    #    .filter(Flight.icao_dep==origin.ident)\
    #    .filter(Flight.icao_arr==destination.ident)\
    ##    .filter(Flight.aircraft==Aircraft.name)\
    #    .filter(Flight.icao_dep.like('KLAX'),\
    #    Flight.weekdayid == 2)
    #results = pd.read_sql(test1.statement,session.bind)

    query = FlightQuery(weekdayId=[1],icao_dep='KLAX')
    results = query.flush()
    results = results.df
    
    print(results.head(),"\n",results.tail())
        #print ("[",r.flight.callsign,"/",r.flight.airline,"] ",r.flight.aircraft,"(",r.speed1,r.speed2,") ",\
        #    r.flight.icao_dep,"(",r.icao_dep_latitude,r.icao_dep_longitude,") ",\
        #    r.flight.icao_arr,"(",r.icao_arr_latitude,r.icao_arr_longitude,") at",r.flight.departing)

    print(len(results.index),"results found")
    flightData = ModelMetaData()      
    
from pytz import timezone, utc

def get_offset(lat, lng):
    """
    returns a location's time zone offset from UTC in minutes.
    """
    tf = TimezoneFinder()
    today = datetime.now()
    tz_name = timezone(tf.closest_timezone_at(lng=lng, lat=lat))
    # ATTENTION: tz_target could be None! handle error case
    today_target = tz_target.localize(today)
    today_utc = utc.localize(today)
    return (today_utc - today_target).total_seconds() / 60
