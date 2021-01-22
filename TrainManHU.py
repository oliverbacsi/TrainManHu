#!/usr/bin/python3

import glob
import re
import tkinter as tk
import math
import random
from PIL import ImageTk, Image

TURNS = 0
LIVES = 3
POINTS = 0
DELIVERED = 0
UPDDELAY = 1000
#MAPCONV = { "LC":0.0 , "LP":0 , "RC":0.0 , "RP":0 , "TC":0.0 , "TP":0 , "BC":0.0 , "BP":0 }
MAPCONV = {}
TRACKS = { "_":[] }
STATIONS = { "_":[] }
LOCOS = list(())
MAPNAME = "HUN-simplified"
ZOOM = 1
IDOF = {"":""}

for z in range(1,4):
    for e in list(("L","R","T","B")):
        for t,v in list(( list(("P",0)) , list(("C",0.0)) )):
            MAPCONV[e+t+str(z)] = v



################################ CLASSES PART #################################



class Loco:
    '''Define the properties of a Locomotive'''

    def __init__(self, Type=1 , Elec=False , Name="0" , Station="BUD"):
        global STATIONS
        self.Type     = Type
        self.Elec     = Elec
        self.Name     = Name
        # Location: Track name and kilometers OR Station name and track number
        self.Location = { "Name": Station , "Pos": 0 }
        self.MaxSpeed = 60 + 20*Type
        # Not decided if speed should reduce with number of wagons
        # or height of territory -- approacing OTTD complexity already !
        self.CurSpeed = 0
        self.MaxCars  = tuple((0,3,4,6,8,11))[Type]
        self.CColor   = tuple(("#000000","#800040","#804000","#408000","#008040","#102080"))[Type]
        self.TColor   = "#2080C0" if Elec else "#C08020"
        self.Itiner   = []
        self.NextCar  = None
        self.LastSt   = Station
        self.Stopped  = True

    def attachWagon(self, newWagon):
        self.NextCar = newWagon

    def detachWagon(self):
        self.NextCar = None

    def getTrainLen(self):
        ''' Get the length of the attached train (excluding Loco)
        This is the number of the attached wagons only.
        '''
        Len = 0
        if self.NextCar: Len += self.NextCar.getGroupLen()
        return Len

    def start(self):
        '''Trigger the loco to start processing its itiner items.
        '''
        if len(self.Itiner) == 0:
            popupErrorMessage("No itiner specified for this Loco")
            self.Stopped = True
            self.CurSpeed = 0
            return
        if self.getTrainLen() > self.MaxCars:
            popupErrorMessage("Train is too long for Loco "+self.Name)
            self.Stopped = True
            self.CurSpeed = 0
            return
        self.Stopped = False
        self.CurSpeed = 0

    def step(self):
        '''This is the main cycle that is invoked at each step.
        '''
        global STATIONS
        global TRACKS

        if self.Stopped:
            self.CurSpeed = 0
            return

        if len(self.Location["Name"]) < 5:
            # Loco is at a station

            if len(self.Itiner) == 0:
                self.Stopped = True
                self.CurSpeed = 0
            else:
                # Loco starts from a station
                # Check if track exists
                trnm = self.Location["Name"]+"-"+self.Itiner[0]
                if trnm not in TRACKS["_"]:
                    trnm = self.Itiner[0]+"-"+self.Location["Name"]
                    if trnm not in TRACKS["_"]:
                        self.Itiner = self.Itiner[1:]
                        return
                # Check if track is free
                tr = TRACKS[trnm]
                if tr.IsOccupied:
                    return
                # Free the station, occupy the track, change the location
                stnm = self.Location["Name"]
                st = STATIONS[stnm]
                self.LastSt = stnm
                st.leaveTrain(self.Location["Pos"])
                tr.occupy()
                self.Location["Name"] = trnm
                self.Location["Pos"] = 0.0

        else:
            # Loco is on a track

            if self.CurSpeed < self.MaxSpeed and self.CurSpeed < TRACKS[self.Location["Name"]].MaxSpeed:
                self.CurSpeed += 10
            d = self.CurSpeed / 60

            # Check if finished the track
            # if yes, check if station is free
            if self.Location["Pos"] + d > TRACKS[self.Location["Name"]].Length:
                stnm = self.Itiner[0]
                st = STATIONS[stnm]
                if st.getNumFreeTracks():
                    self.CurSpeed = 0
                    TRACKS[self.Location["Name"]].free()
                    self.Location["Name"] = stnm
                    self.Itiner = self.Itiner[1:]
                    tr = st.getFirstFreeTrack()
                    st.arriveTrain(self,tr)
                    self.Location["Pos"] = tr

                else:
                    self.CurSpeed = 0

            else:
                self.Location["Pos"] = self.Location["Pos"] + d

    def getXY(self):
        '''Get the X,Y coordinates of Loco on the map'''
        global STATIONS
        global TRACKS
        lo = str(self.Location["Name"])
        if len(lo) < 4:
            [CurrLat,CurrLon] = Station.getCoords(STATIONS[lo])
        else:
            po=float(self.Location["Pos"])
            [CurrLat,CurrLon] = Track.getCoords(TRACKS[lo],self.LastSt,po)
        CurrY = mapconvLat2Y(CurrLat)
        CurrX = mapconvLon2X(CurrLon)
        return list((CurrX,CurrY))

    def addItiner(self,Station):
        '''Append a Station name to the itiner'''
        self.Itiner.append(Station)



###############################################################################



class Wagon:
    '''Define the properties of a Wagon'''

    def __init__(self, Color, Source, Dest, Value, Time, Contents):
        self.Color = Color
        self.StFr  = Source
        self.StTo  = Dest
        self.InitVal = Value
        self.CurrVal = Value
        self.TimeInit = Time
        self.TimeLeft = Time
        self.Contents = Contents
        self.NextCar = None

    def getGroupLen(self):
        ''' Get the length of the group of wagons starting from myself.
        '''
        Len = 1
        if self.NextCar: Len += self.NextCar.getGroupLen()
        return Len

    def attachWagon(self, newWagon):
        self.NextCar = newWagon

    def detachWagon(self):
        self.NextCar = None




###############################################################################



class Track:
    '''Define the properties of a Track segment'''

    def __init__(self, Name, ST_Start, ST_End, IsDouble, IsElectrified, MaxSpeed, CoordList):
        self.Name = Name
        self.ST_Start = ST_Start
        self.ST_End = ST_End
        self.Length = 0.0
        self.IsDouble = IsDouble
        self.IsElectrified = IsElectrified
        self.IsOccupied = False
        self.MaxSpeed = MaxSpeed
        self.CoordList = []

        plat , plon = CoordList[0]
        self.CoordList.append(list((0.0,plat,plon)))
        for c in CoordList[1:]:
            lat , lon = c
            d = getDist(plat,plon,lat,lon)
            self.Length = self.Length + d
            self.CoordList.append(list((float(self.Length),lat,lon)))
            plat,plon = lat,lon

    def occupy(self):
        if self.IsDouble:
            self.IsOccupied = False
        else:
            self.IsOccupied = True

    def free(self):
        self.IsOccupied = False

    def getCoords(self, From, Dist):
        '''Return the coordinates of a point on the track
        that is <Dist> kms away from starting point <From>
        '''
        if self.ST_Start != From :
            Dist = self.Length - Dist
        p,plat,plon = -1.0,-1.0,-1.0
        for c in self.CoordList:
            t,lat,lon = c
            if t > Dist:
                r = (Dist-p)/(t-p)
                rlat = plat + (lat-plat)*r
                rlon = plon + (lon-plon)*r
                return list((rlat,rlon))
            p,plat,plon = t,lat,lon
        return list((lat,lon))



###############################################################################



class Station:
    '''Define the properties of a Station'''

    def __init__(self, ID, Name, Tracks, Lat, Lon):
        self.ID = ID
        self.Name = Name
        self.NumTracks = Tracks
        self.Lat = Lat
        self.Lon = Lon
        self.Neighbours = list(())
        self.Track = list(())
        for i in range(0,Tracks):
            self.Track.append(None)

    def getCoords(self):
        return list((self.Lat,self.Lon))

    def validDirection(self,Station):
        '''Check if <Station> (name) is a valid neighbour of self.
        (there is direct track between)'''
        return Station in self.Neighbours

    def getTrackName(self,Station):
        '''Get the name of the Track that is leading directly
        to the neigbouring station <Station> (name)'''
        global TRACKS
        if self.validDirection(Station):
            combo = self.ID+"-"+Station
            if combo in TRACKS["_"]:
                return combo
            combo = Station+"-"+self.ID
            if combo in TRACKS["_"]:
                return combo
        return ""

    def getNumFreeTracks(self):
        '''Get the number of available (empty) tracks'''
        ret=0
        for i in self.Track:
            if i is not None:
                ret+=1
        return ret

    def getFirstFreeTrack(self):
        '''Get the integer ID of the first available (empty) track'''
        ret = -1
        for i in range(0,self.NumTracks):
            if self.Track[i] is not None:
                ret = i
                break
        return ret

    def arriveTrain(self,loc,trk):
        '''Let a train arrive on a specific track and occupy it'''
        if self.Track[trk] is not None:
            raise Exception("You are trying to arrive a train on an occupied track!\nTrain={} Station={} Track={}",loc.Name,self.Name,trk)
        self.Track[trk] = loc

    def leaveTrain(self,trk):
        '''Release the train from a specific track'''
        self.Track[trk] = None



###############################################################################



class MainWindow(tk.Frame):
    '''Frame inherited subclass to have all items in one object instance'''

    def __init__(self, master=None):
        global ZOOM
        global IDOF
        global TRACKS
        global STATIONS
        super().__init__(master)
        self.master = master
        self.pack(side="top",expand="yes",fill="both",padx=0,pady=0)

        self.ltl = tk.Label(self,text="Stations",height=2,font="Verdana 10 bold")
        self.ltl.grid(column=0,row=0,columnspan=2,sticky="news",padx=2,pady=2)
        self.ctc = tk.Canvas(self,relief="sunken",background="purple",height=20)
        self.ctc.grid(column=2,row=0,columnspan=2,sticky="news",padx=2,pady=2)
        self.ltr = tk.Label(self,text="Trains",height=2,font="Verdana 10 bold")
        self.ltr.grid(column=4,row=0,columnspan=2,sticky="news",padx=2,pady=2)

        self.csta = tk.Canvas(self,relief="sunken",background="red",width=80)
        self.csta.grid(column=0,row=1,rowspan=3,sticky="news",padx=2,pady=2)
        self.ssta = tk.Scrollbar(self,orient="vertical",width=10)
        self.ssta.grid(column=1,row=1,rowspan=3,sticky="news",padx=2,pady=2)
        self.ssta["command"] = self.csta.yview
        self.csta["yscrollcommand"] = self.ssta.set

        self.c = tk.Canvas(self,relief="sunken")
        self.c.grid(column=2,row=1,sticky="news",padx=2,pady=2)
        self.scx = tk.Scrollbar(self,orient="horizontal",width=10)
        self.scx.grid(column=2,row=2,sticky="news",padx=2,pady=2)
        self.scy = tk.Scrollbar(self,orient="vertical",width=10)
        self.scy.grid(column=3,row=1,sticky="news",padx=2,pady=2)
        self.scy["command"] = self.c.yview
        self.scx["command"] = self.c.xview
        self.c["xscrollcommand"] = self.scx.set
        self.c["yscrollcommand"] = self.scy.set

        self.cloc = tk.Canvas(self,relief="sunken",background="green",width=80)
        self.cloc.grid(column=4,row=1,rowspan=2,sticky="news",padx=2,pady=2)
        self.sloc = tk.Scrollbar(self,orient="vertical",width=10)
        self.sloc.grid(column=5,row=1,rowspan=2,sticky="news",padx=2,pady=2)
        self.sloc["command"] = self.cloc.yview
        self.cloc["yscrollcommand"] = self.sloc.set

        self.cdtl = tk.Canvas(self,relief="sunken",background="cyan",height=40)
        self.cdtl.grid(column=2,row=3,columnspan=4,sticky="news",padx=2,pady=2)

        self.rowconfigure(1,weight=1)
        self.columnconfigure(2,weight=1)

        for i in range(1,4):
            IDOF["bg,"+str(i)] = self.c.create_image(0,0,image=ib[i],anchor="nw")

        w = ib[1].width()
        h = ib[1].height()
        self.c.config(scrollregion = list((0, 0, w, h)) )
        self.c.tag_raise(IDOF["bg,1"])

        for trnm in TRACKS["_"]:
            tr = TRACKS[trnm]
            color = "cyan" if tr.IsElectrified else "yellow"
            width = 4 if tr.IsDouble else 2
            coords = list(())
            for co in tr.CoordList:
                dis,lat,lon = co
                coords.append(mapconvLon2X(lon))
                coords.append(mapconvLat2Y(lat))
            IDOF["track,"+trnm] = self.c.create_line(coords,width=width,fill=color)

        self.c.b_st = {"":""}
        for stid in STATIONS["_"]:
            st = STATIONS[stid]
            #+++ Append the station to the station list canvas on the left side as well !!!
            #self.c.b_st[stid] = tk.Button(self.c , text=stid , font="Courier 7 bold" , width=3 , height=1 , command=self.stationClickedOnMap(st) )
            #IDOF["station,"+stid] = self.c.create_window( mapconvLon2X(st.Lon) , mapconvLat2Y(st.Lat) , window=self.c.b_st[stid] , anchor="center")
            CX = mapconvLon2X(st.Lon)
            CY = mapconvLat2Y(st.Lat)
            IDOF["station,l,"+stid] = self.c.create_rectangle( CX-50, CY-32, CX-10, CY-15, fill="gray", outline="gray")
            IDOF["station,b,"+stid] = self.c.create_text( CX-28, CY-18, text=stid , anchor="center" , font="Courier 14 bold" , fill="black")
            IDOF["station,f,"+stid] = self.c.create_text( CX-30, CY-20, text=stid , anchor="center" , font="Courier 14 bold" , fill="white")
            for i in tuple(('l','b','f')):
                self.c.tag_bind(IDOF["station,"+i+","+stid], "<Button-1>", self.stationClickedOnMap(st))

        self.addLocoToRandStation(typ=1,ele=False)
        self.addLocoToRandStation(typ=1,ele=False)
        self.addLocoToRandStation(typ=2,ele=False)

        self.refresh()



    def refresh(self):
        global LOCOS
        global MAPCONV
        global UPDDELAY
        global IDOF
        global TURNS

        for l in LOCOS:
            l.step()
            cx,cy = l.getXY()
            self.c.coords(IDOF["loco,c,"+l.Name],cx-10,cy-10,cx+10,cy+10)
            self.c.coords(IDOF["loco,t,"+l.Name],cx,cy)

        TURNS += 1
        self.after(UPDDELAY,self.refresh)



    def stationClickedOnMap(self,st):
        '''Handle the event if a Station Name is clicked on the main map'''
        pass



    def addLocoToRandStation(self,typ,ele):
        global LOCOS
        global STATIONS
        sta = random.choice(STATIONS["_"])
        nam = chr(65+len(LOCOS))
        l = Loco(Type=typ,Name=nam,Elec=ele,Station=sta)
        PX,PY = l.getXY()
        IDOF["loco,c,"+l.Name] = self.c.create_oval(PX-10,PY-10,PX+10,PY+10,fill=l.CColor,outline=l.TColor)
        IDOF["loco,t,"+l.Name] = self.c.create_text(PX,PY,text=l.Name,font="Arial 10 bold",anchor="center",fill=l.TColor)
        LOCOS.append(l)



###############################################################################



class FileWindow(tk.Frame):
    '''Frame inherited subclass to have all items in one object instance'''

    def __init__(self, master=None):
        global MAPNAME
        super().__init__(master)
        self.master = master
        self.fileName = tk.StringVar(self,name="fiName")
        self.pack()

        self.t_l1 = tk.Label(self,text="Choose a Map to play")
        self.t_f1 = tk.Frame(self,relief="sunken")
        self.t_f2 = tk.Frame(self,relief="flat")
        self.t_l1.pack(side="top",expand="yes",fill="x",padx=20,pady=20)
        self.t_f1.pack(side="top",expand="yes",fill="both",padx=20,pady=20)
        self.t_f2.pack(side="top",expand="yes",fill="both",padx=20,pady=20)
        self.t_f2_bok = tk.Button(self.t_f2,text="OK",command=self.pressedOK)
        self.t_f2_bcl = tk.Button(self.t_f2,text="Cancel",command=self.pressedCcl)
        self.t_f2_bok.pack(side="left",expand="yes",fill="none",padx=20,pady=20)
        self.t_f2_bcl.pack(side="left",expand="yes",fill="none",padx=20,pady=20)

        maplist = glob.glob("Maps/*")
        if not len(maplist):
            MAPNAME = "errorerrorerror"
            self.destroy()
        MAPNAME = maplist[0][5:]
        self.setvar(name="fiName",value=MAPNAME)

        for x in maplist:
            y = x[5:]
            self.t_f1_b = {"":""}
            self.t_f1_b[y] = tk.Radiobutton(self.t_f1,text=y,variable=self.fileName,value=y,indicatoron="yes")
            self.t_f1_b[y].pack(side="top",expand="yes",fill="x",padx=10,pady=5)

    def pressedOK(self):
        global MAPNAME
#        MAPNAME = str(self.fileName)
        MAPNAME = self.getvar(name="fiName")
        self.destroy()

    def pressedCcl(self):
        global MAPNAME
        MAPNAME = "errorerrorerror"
        self.destroy()



################################## PROC PART ##################################



def mapconvLat2Y(_lat):
    '''Convert Latitude to Map Y coord'''
    global MAPCONV
    global ZOOM
    m = (MAPCONV["BP"+str(ZOOM)] - MAPCONV["TP"+str(ZOOM)]) / (MAPCONV["BC"+str(ZOOM)] - MAPCONV["TC"+str(ZOOM)])
    r = round(MAPCONV["TP"+str(ZOOM)] + (_lat - MAPCONV["TC"+str(ZOOM)]) * m)
    return r

def mapconvLon2X(_lon):
    '''Convert Longitude to Map X coord'''
    global MAPCONV
    global ZOOM
    m = (MAPCONV["RP"+str(ZOOM)] - MAPCONV["LP"+str(ZOOM)]) / (MAPCONV["RC"+str(ZOOM)] - MAPCONV["LC"+str(ZOOM)])
    r = round(MAPCONV["LP"+str(ZOOM)] + (_lon - MAPCONV["LC"+str(ZOOM)]) * m)
    return r

def getDist(lat1,lon1,lat2,lon2):
    '''Get the distance in km between two coordinate pairs'''
    hdist = (lon2-lon1)*75.894
    vdist = (lat2-lat1)*111.32
    dist = math.sqrt( hdist**2 + vdist**2 )
    return dist

def str2bool(v):
    return v.lower() in ("yes", "true", "y", "1")




################################## MAIN PART ##################################



root = tk.Tk()
root.wm_title("Train Manager HU")
root.wm_iconname("TrainManHU")
i_icon = tk.Image(imgtype="photo",file="images/icon.png")
root.wm_iconphoto(root,i_icon)
root.wm_geometry("600x600")

mw = FileWindow(master=root)
root.update_idletasks()
root.wait_window(mw)
root.update_idletasks()

if MAPNAME == "errorerrorerror":
    root.destroy()
    exit()

# Load the base map config and then the map data
fin = open("Maps/"+MAPNAME+"/Map.cfg" , "r")
for sor in fin:
    if len(sor.split(" ")) > 3:
        edge,zoom,pixel,coord = sor[:-1].split(" ")
        MAPCONV[edge+"P"+str(zoom)] = int(pixel)
        MAPCONV[edge+"C"+str(zoom)] = float(coord)
fin.close()

# Load the railroad tracks of the selected map
for TName in glob.glob("Maps/"+MAPNAME+"/Tracks/*"):
    data = list(())
    tracks = 1
    elec = False
    maxsp = 0
    fin = open(TName , "r")
    name = "error !!!"
    for sor in fin:
        match = re.search(".*<tracks>([1-9]+)</tracks>.*" , sor)
        if match :
            tracks = int(match[1])
            continue
        match = re.search(".*<maxspeed>([0-9]+)</maxspeed>.*" , sor)
        if match :
            maxsp = int(match[1])
            continue
        match = re.search(".*<section>(.*)</section>.*" , sor)
        if match :
            name = match[1]
            continue
        match = re.search(".*<electrified>(.*)</electrified>.*" , sor)
        if match :
            elec = str2bool(match[1])
            continue
        match = re.search(".*rtept.*lat=.([0-9\.]+).*lon=.([0-9\.]+).*" , sor)
        if match :
            coord = list((float(match[1]) , float(match[2])))
            data.append(coord)
    fin.close()
    tr = Track(name,TName[-7:-4],TName[-3:],tracks>1,elec,maxsp,data)
    TRACKS["_"].append(TName[-7:])
    TRACKS[TName[-7:]] = tr

# Load the stations of the selected map
fin = open("Maps/"+MAPNAME+"/Stations.txt" , "r")
for sor in fin:
    if len(sor.split(" ")) > 4:
        id,tr,lat,lon,name = sor.split(" ")
        name = name[:-1]
        STATIONS[id] = Station(id,name,int(tr),float(lat),float(lon))
        STATIONS["_"].append(id)
fin.close()

# Collect the possible neighbouring nodes for each station
for TrName in TRACKS["_"]:
    id1,id2 = TrName.split("-")
    STATIONS[id1].Neighbours.append(id2)
    STATIONS[id2].Neighbours.append(id1)


# Initialize the main window for the game
root.tk_setPalette("#404040")
root.wm_geometry("1200x700")
ib = list(())
ib.append(i_icon)
for x in range(1,4):
    ib.append(ImageTk.PhotoImage(Image.open("Maps/"+MAPNAME+"/BaseMap"+str(x)+".jpg")))

mw = MainWindow(master=root)

root.update_idletasks()
root.mainloop()

#+++ Announce the results. In a more sophisticated way than below:
print (f"You have played {TURNS} Turns")
print (f"You have collected {POINTS} Points")
print (f"You have delivered {DELIVERED} Wagons")
