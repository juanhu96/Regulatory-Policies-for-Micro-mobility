"""
Created on Jan, 2020
@author: Jingyuan Hu
"""

import os
import sys
import utm
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import utils


def main():
    os.chdir("/Users/ArcticPirates/Desktop/Passport Project/Code")

    # scooter_data = preprocess()
    scooter_data = pd.read_csv('~/Desktop/Passport Project/Data/scooter_data.csv')
    print("Original dataset imported, size:", scooter_data.shape)
    scooter_data['start_time'] = pd.to_datetime(scooter_data['start_time'], format = '%H:%M:%S').dt.time
    scooter_data['end_time'] = pd.to_datetime(scooter_data['end_time'], format = '%H:%M:%S').dt.time
    # convert_data(scooter_data)
    # converted_data = pd.read_csv('~/Desktop/Passport Project/Data/converted_data.csv')
    # filtered_data = filter_data(converted_data, 'trip')
    # filtered_data = filter_data(filter_data(converted_data, 'trip'), 'rebalance', min_dist = -1) # set -1: keep scooters that pick and drop at same place
    # filtered_data.to_csv(r'/Users/ArcticPirates/Desktop/Passport Project/Data/'+'filtered_data.csv', encoding='utf-8', index=False, header = True)

    filtered_data = pd.read_csv('~/Desktop/Passport Project/Data/filtered_data.csv')
    # compute_inventory(filtered_data)
    # compute_trip_rebalance(filtered_data)


def preprocess():

    """
    Only for first time processing data
    Drop the un-categorized zone, 0 latitude, 0 longitude data
    Transfer the (latitude, longitude) to UTM data format
    """

    scooter_data = pd.read_csv('~/Desktop/Passport Project/Data/Charlotte_Pilot_3PreMonths_SafeData_Sorted.csv')
    print("Original dataset size:", scooter_data.shape)
    scooter_data = scooter_data[scooter_data['zone_number'] != -1]
    print("Uncategorized zone dropped:", scooter_data.shape)
    scooter_data = scooter_data[scooter_data['latitude'] != 0]
    scooter_data = scooter_data[scooter_data['longitude'] != 0]
    print("Wrong lat/long data dropped:", scooter_data.shape)
    scooter_data[['UTM_x', 'UTM_y']] = scooter_data.apply(lambda row: \
        pd.Series(utm.from_latlon(row['latitude'], row['longitude'])[:2]), axis = 1)
    scooter_data.to_csv('scooter_data.csv', encoding='utf-8', index=False)
    print("CSV file saved as scooter_data.csv")
    return scooter_data

    
def convert_data(scooter_data):

    print("Start converting the data...")
    event_data_list = []
    
    for index, row in scooter_data.iterrows():
        
        """
        - consider the normal events only for now
        - ignore the first event
        - look for the same scooter
        """
        
        if (row['event_type_reason'] == 'trip_end' or row['event_type_reason'] == 'low_battery' or \
            row['event_type_reason'] == 'service_start' or row['event_type_reason'] == 'rebalance_drop_off' or \
                row['event_type_reason'] == 'maintenance_drop_off' or row['event_type_reason'] == 'service_start_implicit') and \
            index > 0 and row['Scooter_ID'] == scooter_data.iloc[[index - 1]]['Scooter_ID'].values[0]:

            if row['event_type_reason'] == 'trip_end':
                event_type = 'trip'
            elif row['event_type_reason'] == 'low_battery':
                event_type = 'low_battery'
            elif row['event_type_reason'] == 'service_start_implicit':
                event_type = 'service_start_implicit'
            else:
                event_type = 'rebalance'

            """
            NOTE:
            For zone/provider we convert to string to make it categorical

            This works even if the start and end time are not on the same day
            event_end_time = dt.time(0,10,00)
            event_start_time = dt.time(23,50,00)

            Straight line distance rounded as integers
            Later on we will add the route distance

            Creating a dictionary first is faster than appending to a data frame row by row directly
            """

            previous_event = scooter_data.iloc[[index - 1]]

            event_start_day = previous_event['End_Day'].values[0]
            event_start_time = previous_event['end_time'].values[0]
            event_start_time_hour = event_start_time.hour
            event_start_zone = str(previous_event['zone_number'].values[0])
            event_start_UTM_x = previous_event['UTM_x'].values[0]
            event_start_UTM_y = previous_event['UTM_y'].values[0]
            event_start_lat = previous_event['latitude'].values[0]
            event_start_long = previous_event['longitude'].values[0]

            event_end_day = row['Start_Day']
            event_end_time = row['start_time']
            event_end_time_hour = event_end_time.hour
            event_end_zone = str(row['zone_number'])
            event_end_UTM_x = row['UTM_x']
            event_end_UTM_y = row['UTM_y']
            event_end_lat = row['latitude']
            event_end_long = row['longitude']

            if (event_start_day % 7 == 0) or (event_start_day % 7 == 1): 
                event_day_type = 'weekend'
            else:
                event_day_type = 'weekday'

            # inventory day starts at 6am, for plots/analysis
            # inventory hour would be 24~30, indicates that it is not the same actual day
            if event_start_time < dt.time(5,59,59):
                start_inventory_day = event_start_day - 1
                start_inventory_hour = event_start_time_hour + 24
            else: 
                start_inventory_day = event_start_day
                start_inventory_hour = event_start_time_hour
            if (start_inventory_day % 7 == 0) or (start_inventory_day % 7 == 1): 
                start_inventory_day_type = 'weekend'
            else:
                start_inventory_day_type = 'weekday'

            if event_end_time < dt.time(5,59,59):
                end_inventory_day = event_end_day - 1
                end_inventory_hour = event_end_time_hour + 24
            else: 
                end_inventory_day = event_end_day
                end_inventory_hour = event_end_time_hour
            if (end_inventory_day % 7 == 0) or (end_inventory_day % 7 == 1): 
                end_inventory_day_type = 'weekend'
            else:
                end_inventory_day_type = 'weekday'

            event_duration = round((dt.datetime.combine(dt.date.min, event_end_time) - \
                 dt.datetime.combine(dt.date.min, event_start_time)).seconds/60, 2)
            line_dist = utils.distance_cartesian(event_start_UTM_x, event_start_UTM_y, event_end_UTM_x, event_end_UTM_y)
            provider = str(row['Mobility_Provider'])
            scooter_id = row['Scooter_ID']

            event = {"start_time": event_start_time, "start_time_hour": event_start_time_hour,\
                 "end_time": event_end_time, "end_time_hour": event_end_time_hour,\
                     "Start_Day": event_start_day, "End_Day": event_end_day, "Day_type": event_day_type,\
                         "start_inventory_day": start_inventory_day, "start_inventory_hour": start_inventory_hour, "start_inventory_day_type": start_inventory_day_type,\
                             "end_inventory_day": end_inventory_day,"end_inventory_hour": end_inventory_hour, "end_inventory_day_type": end_inventory_day_type,\
                             "start_zone": event_start_zone, "end_zone": event_end_zone, \
                                 "start_UTM_x": event_start_UTM_x, "start_UTM_y": event_start_UTM_y, \
                                     "end_UTM_x": event_end_UTM_x, "end_UTM_y": event_end_UTM_y, \
                                         "start_lat": event_start_lat, "start_long": event_start_long, \
                                             "end_lat": event_end_lat, "end_long": event_end_long, \
                                                 "line_dist": line_dist, "duration": event_duration, "Mobility_Provider": provider, \
                                                     "Scooter_ID": scooter_id, "event": event_type}
            event_data_list.append(event)
        
    print("All events converted.")
    event_data = pd.DataFrame(event_data_list)
    event_data['event_ID'] = event_data.index
    event_data.to_csv(r'/Users/ArcticPirates/Desktop/Passport Project/Data/'+'converted_data.csv', encoding='utf-8', index=False, header = True, \
        columns = ["start_time", "start_time_hour", "end_time", "end_time_hour", "Start_Day", "End_Day", "Day_type",\
            "start_inventory_day", "start_inventory_hour", "start_inventory_day_type", \
                "end_inventory_day","end_inventory_hour", "end_inventory_day_type",\
                    "start_zone", "end_zone", "start_UTM_x", "start_UTM_y", "end_UTM_x", "end_UTM_y",\
                        "start_lat", "start_long", "end_lat", "end_long", "line_dist", "duration", "Mobility_Provider",\
                            "Scooter_ID", "event", "event_ID"])
    print("File saved as converted_data.csv")


def filter_data(data, event, min_time = 1, min_dist = 0):
    
    """
    Filter the data by dropping events by specification

    event: the event type to be dropped
    below min_time OR min_dist
    NOTE: 
    Do we have to drop the ones that are too large?
    What if the scooters are returned at the exact same place?
    """

    filtered_data = data.drop(data[(data['event'] == event) & ((data['duration'] < min_time) | (data['line_dist'] < min_dist))].index)
    print("Data of event type: " + event + " have been filtered.")
    return filtered_data


def compute_inventory(data):
    
    """
    Compute the inventory at the beginning of every day
    NOTE: 
    We use inventory day where every day starts at 6am

    Extreme rare case: 
    trip from 5 to 7, which should be count as inventory
    our model takes this into consideration as well
    """

    inventory_by_hour_list = []

    for day in range(data['end_inventory_day'].min() + 1, data['end_inventory_day'].max() + 1):

        df_day = data[data['end_inventory_day'] == day]

        for hour in range(6, 30):

            """
            NOTE: 
            start inventory = available (end_hour = hour) + occupied (trip, low battery)
            all service_start_implicit happens between 6:00~6:59

            df_day['end_inventory_hour'] == hour:
            captures scooters that does not have any activies, or the ones being deployed by company within the hour

            In terms of the whole system:
            - inventory: rebalance start time within the hour
            + inventory: rebalance end time within the hour

            In terms of each zone/area:
            - inventory: rebalance start time, trip start time within the hour
            + inventory: rebalance end time, trip end time within the hour
            """

            if hour == 6:
                df_hour = df_day[(df_day['end_inventory_hour'] == hour) | \
                    (((df_day['event'] == 'trip') | (df_day['event'] == 'low_battery')) & \
                        (df_day['start_time_hour'] <= hour) & (df_day['end_time_hour'] >= hour))]
                total_inventory = len(df_hour['Scooter_ID'].unique())

                # TODO: if a trip from zone 1 to 2, from 5am to 7am, then which zone should it belong to at 6?
                # Use end zone as an approximation
                # for zone in range(1, 5):
                #     df_hour[]

            # the numbers are same with/without unique()
            inventory_added = len(df_day[(df_day['event'] == 'rebalance') & (df_day['end_inventory_hour'] == hour)])
            inventory_removed = len(df_day[(df_day['event'] == 'rebalance') & (df_day['start_inventory_hour'] == hour)])
            total_inventory = total_inventory + inventory_added - inventory_removed
            inventory_by_hour_list.append({"Day": day, "Hour": hour%24, "Inventory": total_inventory})
    
    inventory_by_hour = pd.DataFrame(inventory_by_hour_list)
    inventory_by_hour.to_csv(r'/Users/ArcticPirates/Desktop/Passport Project/Data/'+'inventory_by_hour.csv', encoding='utf-8', index=False, header = True, \
        columns = ["Day", "Hour", "Inventory"])
    print("Inventory data saved.")


def compute_trip_rebalance(data):
    
    """
    Generate csv file that has the within/between zone information for each event type for each hour/day
    trip: normal trips (demand)
    reblance_out: scooters taken away from the system
    reblance_in: scooters put back in the system
    """
    
    trip_rebalance_list = []

    for day in range(1, 92):

        day_type = data[data['Start_Day'] == day]['Day_type'].values[0]

        for hour in range(0, 24):

            df_trip = data[(data['Start_Day'] == day) & (data['start_time_hour'] == hour) & (data['event'] == 'trip')]
            df_rebalance_out = data[(data['Start_Day'] == day) & (data['start_time_hour'] == hour) & (data['event'] == 'rebalance')]
            df_rebalance_in = data[(data['End_Day'] == day) & (data['end_time_hour'] == hour) & (data['event'] == 'rebalance')]

            for start_zone in range(1, 5):
                for end_zone in range(1, 5):

                    if start_zone == end_zone:
                        event_type = 'within_zone'
                    else:
                        event_type = 'between_zone'

                    trip_count = len(df_trip[(df_trip['start_zone'] == start_zone) & (df_trip['end_zone'] == end_zone)])
                    rebalance_out_count = len(df_rebalance_out[(df_rebalance_out['start_zone'] == start_zone) & (df_rebalance_out['end_zone'] == end_zone)])
                    rebalance_in_count = len(df_rebalance_in[(df_rebalance_in['start_zone'] == start_zone) & (df_rebalance_in['end_zone'] == end_zone)])

                    trip_rebalance_list.append({"Day": day, "Day_type": day_type, "Hour": hour, "start_zone": start_zone, "end_zone": end_zone,\
                        "event": 'trip', "event_type": event_type, "count": trip_count})
                    trip_rebalance_list.append({"Day": day, "Day_type": day_type, "Hour": hour, "start_zone": start_zone, "end_zone": end_zone,\
                        "event": 'take_away', "event_type": event_type, "count": rebalance_out_count})
                    trip_rebalance_list.append({"Day": day, "Day_type": day_type, "Hour": hour, "start_zone": start_zone, "end_zone": end_zone,\
                        "event": 'put_back', "event_type": event_type, "count": rebalance_in_count})

    trip_rebalance = pd.DataFrame(trip_rebalance_list)
    trip_rebalance.to_csv(r'/Users/ArcticPirates/Desktop/Passport Project/Data/'+'trip_rebalance_by_area_over_days.csv', encoding='utf-8', index=False, header = True, \
        columns = ["Day", "Day_type", "Hour", "start_zone", "end_zone", "event", "event_type", "count"])
    print("File saved as trip_rebalance_by_area_over_days.csv")


if __name__ == "__main__":
    main()