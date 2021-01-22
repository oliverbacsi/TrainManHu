#!/usr/bin/python3

import sys

STATIONS={"_":"_"}

# Check if command line arguments specified
if len(sys.argv) < 3:
    print ("Usage: "+sys.argv[0]+" <Station1> <Station2>")
    exit()

# Load the Station database
fin = open("Stations.txt" , "r")
for sor in fin:
    if len(sor.split(" ")) > 4:
        id,tr,lat,lon,name = sor.split(" ")
        name = name[:-1]
        STATIONS[id] = [name,tr,lat,lon]
fin.close()

# Check if specified stations exist

S_F,S_T = sys.argv[1:3]
try:
    L_F = STATIONS[S_F]
except:
    print ("Source station "+S_F+" does not exist!")
    exit()
try:
    L_T = STATIONS[S_T]
except:
    print ("Destination station "+S_T+" does not exist!")
    exit()

nameF,nameT = L_F[0],L_T[0]

# Write the track data file
fout = open(S_F+"-"+S_T+".gpx","w")
fout.write("<?xml version=\"1.0\"?>\r\n")
fout.write("<gpx version=\"1.1\">\r\n")
fout.write("<rte>\r\n")
fout.write("\t<name>"+nameF+"--"+nameT+"</name>\r\n")
fout.write("\t<rtept lat=\""+L_F[2]+"\" lon=\""+L_F[3]+"\"></rtept>\r\n")
fout.write("\t<rtept lat=\""+L_T[2]+"\" lon=\""+L_T[3]+"\"></rtept>\r\n")
fout.write("</rte>\r\n")
fout.write("</gpx>\r\n")
fout.close()
