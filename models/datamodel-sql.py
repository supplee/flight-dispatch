#!/home/supplee/anaconda3/envs/flight-dispatch/bin/python

import pandas as pd
from PyQt5 import QtWidgets, QtCore
from haversine import haversine
from sqlalchemy import create_engine

#from PyQt5 import QtWidgets
#from PyQt5.QtWidgets import QApplication, QMainWindow
#from dispatcher import Ui_MainWindow

class FlightData:
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

    def select(self):
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


if __name__ == "__main__":
    import sys
    import os

    flightData = FlightData()      
    buildQuery = FlightQuery(flightData.pathByDBName['flights'],icao_dep='KLAX',weekdayId=[2])
    result = buildQuery.select()
    result = result.reset_index(drop = True)
    print(result.tail())

    
