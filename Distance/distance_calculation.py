import datetime, time
from geopy.distance import geodesic
import requests
import os
import sqlite3


prev_recorded_data = {}


def get_fleet():
    data = requests.get("https://depot.chartr.in/all_fleet/")
    data = data.json()

    fleet = []
    for bus in data:
        fleet += [bus['reg_num']]

    return fleet


def get_bus_gps_data():
    gps_data = requests.get("http://143.110.182.192:8090/tcil_all_buses_db.txt")
    dimts_data = requests.get("http://143.110.182.192:8090/tcil_all_dimts_buses_db.txt")
    gps_data = gps_data.text.split("\n")
    dimts_data = dimts_data.text.split("\n")
    gps_data = [gps_data[i].split(',') for i in range(len(gps_data))]
    dimts_data = [dimts_data[i].split(',') for i in range(len(dimts_data))]
    gps_data += dimts_data

    gps_data_dict = {}
    for i in range(len(gps_data)):
        try:
            gps_data_dict[gps_data[i][2]] = [gps_data[i][0], gps_data[i][1]]
        except:
            continue

    return gps_data_dict


def calculate_distance():
    global prev_recorded_data
    distance_travelled = {}
    current_gps_data = get_bus_gps_data()

    for bus, gps in current_gps_data.items():
        if bus == 'DL1PC6771':
            print()
        if bus in prev_recorded_data.keys():
            prev_gps = prev_recorded_data[bus]
            dist = geodesic(gps, prev_gps).km

            distance_travelled[bus] = dist
            if bus == 'DL1PD0010':
                print(prev_gps, gps, dist)

    prev_recorded_data = current_gps_data
    return distance_travelled
# 08:54


def main():
    global prev_recorded_data
    f_name = datetime.datetime.now().strftime("%Y_%m_%d") + ".db"
    db_file = 'bus_movements_' + f_name

    conn = None

    # check if the database file exists in the current directory
    if os.path.isfile(db_file):

        # create a connection to the existing database file
        conn = sqlite3.connect(db_file)

        # create a cursor object to execute SQL commands
        cursor = conn.cursor()

        # load data from the table named distance_travelled
        cursor.execute("SELECT * FROM distance_travelled")

    else:

        # create a connection to the new database file
        conn = sqlite3.connect(db_file)

        # create a cursor object to execute SQL commands
        cursor = conn.cursor()

        # create a table named distance_travelled with primary key as bus_no and default value 0
        cursor.execute('''CREATE TABLE distance_travelled
                        (bus_no varchar PRIMARY KEY,
                         distance float DEFAULT 0)''')

        fleet = get_fleet()

        for bus in fleet:
            cursor.execute('''INSERT INTO distance_travelled(bus_no, distance)
                                  VALUES(?,?)''', (bus, 0))

        # commit the changes to the database and close the connection
        conn.commit()

    cursor = conn.cursor()

    while True:
        print("Started Iter")
        start = time.time()
        if len(prev_recorded_data) == 0:
            prev_recorded_data = get_bus_gps_data()
            continue
        distance_dict = calculate_distance()
        for bus_no, extra_distance in distance_dict.items():
            cursor.execute('''UPDATE distance_travelled
                              SET distance = distance + ?
                              WHERE bus_no = ?''', (extra_distance, bus_no))

        conn.commit()
        end = time.time()
        print("Time Taken for Iter = ", end - start)
        time.sleep(10 - (end - start))


if __name__ == '__main__':
    main()
